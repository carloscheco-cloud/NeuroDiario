from contextlib import contextmanager
from datetime import datetime, timedelta
import importlib
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from neurodiario.db.models import Base, GeneratedArticle, WhatsAppPublication
from neurodiario.publisher.whatsapp_publisher import (
    WhatsAppConfig, WhatsAppResult, get_whatsapp_config, post_to_whatsapp,
)
from neurodiario.publisher.whatsapp_delivery import needs_whatsapp, publish_record_to_whatsapp
from migrate_whatsapp_publications import migrate
from neurodiario.tools.check_waha import check_waha


NOW = datetime(2026, 10, 22, 1, 0)
CONFIG = WhatsAppConfig("http://waha:3000", "private-test-key", "123@newsletter", "default", NOW - timedelta(days=1))


def response(status=200, data=None, headers=None):
    return SimpleNamespace(status_code=status, json=lambda: data if data is not None else {"id": "message-1"}, headers=headers or {})


def test_image_reuses_title_link_and_image_without_ai():
    http = Mock(); http.post.return_value = response()
    result = post_to_whatsapp("Noticia", "https://neurodiario.com/noticia", CONFIG, "https://images.example/foto.png", http)
    assert result == WhatsAppResult("sent", message_id="message-1")
    call = http.post.call_args
    assert call.args[0] == "http://waha:3000/api/sendImage"
    assert call.kwargs["json"]["file"] == {"url": "https://images.example/foto.png", "mimetype": "image/png"}
    assert "Noticia" in call.kwargs["json"]["caption"]
    assert "https://neurodiario.com/noticia" in call.kwargs["json"]["caption"]
    assert call.kwargs["json"]["chatId"] == CONFIG.channel_id
    assert call.kwargs["headers"] == {"X-Api-Key": "private-test-key"}
    assert call.kwargs["allow_redirects"] is False


@pytest.mark.parametrize("status", [400, 422])
def test_rejected_image_falls_back_to_text(status):
    http = Mock(); http.post.side_effect = [response(status), response(data={"id": {"_serialized": "text-1"}})]
    result = post_to_whatsapp("Noticia", "https://nd.example/post", CONFIG, "https://img.example/a.jpg", http)
    assert result.message_id == "text-1"
    assert http.post.call_count == 2
    assert http.post.call_args.args[0].endswith("/api/sendText")


@pytest.mark.parametrize("outcome", [requests.ReadTimeout("private content"), requests.ConnectionError("private-test-key"), response(500), response(200, {"unexpected": True})])
def test_ambiguous_result_never_falls_back_or_leaks_errors(outcome):
    http = Mock()
    if isinstance(outcome, Exception): http.post.side_effect = outcome
    else: http.post.return_value = outcome
    result = post_to_whatsapp("Noticia", "https://nd.example/post", CONFIG, "https://img.example/a.jpg", http)
    assert result.status == "uncertain"
    assert not result.retryable
    assert http.post.call_count == 1
    assert "private" not in result.error


def test_rate_limit_is_retryable_and_auth_failure_is_not():
    http = Mock(); http.post.return_value = response(429, headers={"Retry-After": "95"})
    result = post_to_whatsapp("Noticia", "https://nd.example/post", CONFIG, http=http)
    assert result.retryable and result.retry_after == 95
    http.post.return_value = response(401)
    assert not post_to_whatsapp("Noticia", "https://nd.example/post", CONFIG, http=http).retryable


def test_configuration_explicit_cutoff_private_connection_and_no_secret_repr():
    settings = SimpleNamespace(WHATSAPP_ENABLED=False)
    assert get_whatsapp_config(settings) is None
    settings = SimpleNamespace(WHATSAPP_ENABLED=True, WAHA_URL="http://waha:3000", WAHA_API_KEY="private-test-key", WAHA_SESSION="default", WHATSAPP_CHANNEL_ID="123@newsletter", WHATSAPP_START_AT="2026-10-21T20:00:00-04:00")
    assert get_whatsapp_config(settings).start_at == datetime(2026, 10, 22)
    assert "private-test-key" not in repr(get_whatsapp_config(settings))
    for key, value in [("WAHA_URL", "http://public.example"), ("WHATSAPP_CHANNEL_ID", "123@g.us"), ("WHATSAPP_START_AT", ""), ("WHATSAPP_START_AT", "2026-10-22")]:
        old = getattr(settings, key); setattr(settings, key, value)
        with pytest.raises(ValueError): get_whatsapp_config(settings)
        setattr(settings, key, old)


@pytest.mark.parametrize("status,role,success", [("WORKING", "ADMIN", True), ("WORKING", "SUBSCRIBER", False), ("STOPPED", "OWNER", False)])
def test_connection_check_does_not_send_messages(status, role, success):
    settings = SimpleNamespace(WAHA_URL=CONFIG.base_url, WAHA_API_KEY=CONFIG.api_key, WAHA_SESSION="default", WHATSAPP_CHANNEL_ID=CONFIG.channel_id, WHATSAPP_START_AT="2026-10-21T00:00:00Z")
    http = Mock(); http.get.side_effect = [response(data={"status": status}), response(data={"id": CONFIG.channel_id, "role": role})]
    if success: assert "No se enviaron mensajes" in check_waha(settings, http)
    else:
        with pytest.raises(ValueError): check_waha(settings, http)
    http.post.assert_not_called()


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        record = GeneratedArticle(title="Noticia", content="Contenido", status="published", wordpress_post_id=42, published_at=NOW)
        db.add(record); db.commit()
        yield db, record, engine
    engine.dispose()


def test_success_persists_and_is_not_replayed_after_session_reopen(database):
    db, record, engine = database
    sender = Mock(return_value=WhatsAppResult("sent", message_id="wa-1"))
    publish_record_to_whatsapp(db, record, CONFIG, "https://nd.example/post", sender=sender, now=NOW)
    assert not needs_whatsapp(db, record, CONFIG)
    with Session(engine) as other:
        assert not needs_whatsapp(other, other.get(GeneratedArticle, record.id), CONFIG)
    publish_record_to_whatsapp(db, record, CONFIG, "https://nd.example/post", sender=sender)
    assert sender.call_count == 1
    assert db.query(WhatsAppPublication).one().message_id == "wa-1"


def test_rate_retry_waits_and_stops_at_three_attempts(database):
    db, record, _ = database
    sender = Mock(return_value=WhatsAppResult("failed", error="rate", retryable=True, retry_after=60))
    for n in range(3):
        publish_record_to_whatsapp(db, record, CONFIG, "https://nd.example/post", sender=sender, now=NOW + timedelta(seconds=n*61))
        assert not needs_whatsapp(db, record, CONFIG, now=NOW + timedelta(seconds=n*61 + 1))
    assert sender.call_count == 3
    assert not needs_whatsapp(db, record, CONFIG, now=NOW + timedelta(days=1))


@pytest.mark.parametrize("status", ["sending", "uncertain", "sent"])
def test_pending_or_ambiguous_send_not_reclaimed(database, status):
    db, record, _ = database
    db.add(WhatsAppPublication(article_id=record.id, channel_id=CONFIG.channel_id, status=status, attempts=1)); db.commit()
    assert not needs_whatsapp(db, record, CONFIG)


def test_old_articles_and_other_channel_are_independent(database):
    db, record, _ = database
    record.published_at = CONFIG.start_at - timedelta(seconds=1); db.commit()
    assert not needs_whatsapp(db, record, CONFIG)
    record.published_at = NOW; db.commit()
    db.add(WhatsAppPublication(article_id=record.id, channel_id="other@newsletter", status="sent")); db.commit()
    assert needs_whatsapp(db, record, CONFIG)


def test_migration_twice_preserves_existing_rows(database):
    db, record, engine = database
    WhatsAppPublication.__table__.drop(engine)
    migrate(engine); migrate(engine)
    assert "whatsapp_publications" in inspect(engine).get_table_names()
    assert db.get(GeneratedArticle, record.id).title == "Noticia"


def test_second_worker_cannot_send_a_claimed_article(database):
    db, record, engine = database
    second_sender = Mock()
    def send(**kwargs):
        with Session(engine) as other:
            assert publish_record_to_whatsapp(other, other.get(GeneratedArticle, record.id), CONFIG,
                                               "https://nd.example/post", sender=second_sender) is None
        return WhatsAppResult("sent", message_id="wa-once")
    publish_record_to_whatsapp(db, record, CONFIG, "https://nd.example/post", sender=send)
    second_sender.assert_not_called()


def scheduler_module(monkeypatch):
    for path, attr in [("neurodiario.scheduler.pipeline", "run_ingestion_pipeline"), ("neurodiario.scheduler.nlp_pipeline", "run_nlp_pipeline")]:
        monkeypatch.setitem(sys.modules, path, SimpleNamespace(**{attr: Mock()}))
    return importlib.import_module("scheduler.auto_scheduler")


@pytest.mark.parametrize("telegram_done,enabled,wa_status", [(False, True, "sent"), (True, True, "sent"), (False, False, "sent"), (False, True, "uncertain")])
def test_scheduler_reuses_same_data_and_keeps_platforms_independent(database, monkeypatch, telegram_done, enabled, wa_status):
    db, record, engine = database
    if telegram_done: record.telegram_message_id = "already-tg"; db.commit()
    module = scheduler_module(monkeypatch)
    from neurodiario.config.settings import settings
    from neurodiario.db import database as connection
    from neurodiario.publisher import telegram_publisher, whatsapp_delivery
    values = dict(WORDPRESS_URL="https://nd.example", WORDPRESS_USER="test", WORDPRESS_PASSWORD="secret", FACEBOOK_PAGE_TOKEN="", FACEBOOK_PAGE_ID="", TELEGRAM_BOT_TOKEN="tg-key", TELEGRAM_CHANNEL_ID="tg-channel", WHATSAPP_ENABLED=enabled, WAHA_URL=CONFIG.base_url, WAHA_API_KEY=CONFIG.api_key, WAHA_SESSION="default", WHATSAPP_CHANNEL_ID=CONFIG.channel_id, WHATSAPP_START_AT="2026-10-21T00:00:00Z")
    for key, value in values.items(): monkeypatch.setattr(settings, key, value)
    @contextmanager
    def get_db():
        yield db
        db.commit()
    monkeypatch.setattr(connection, "get_db", get_db)
    monkeypatch.setitem(sys.modules, "neurodiario.publisher.facebook_image_generator", SimpleNamespace(post_to_facebook_with_image=Mock()))
    telegram = Mock(return_value="new-tg")
    whatsapp = Mock(return_value=WhatsAppResult(wa_status, message_id="wa-1" if wa_status == "sent" else None))
    monkeypatch.setattr(telegram_publisher, "post_to_telegram", telegram)
    monkeypatch.setattr(whatsapp_delivery, "post_to_whatsapp", whatsapp)
    monkeypatch.setattr(module, "_get_wordpress_image_url", lambda *a: "https://img.example/foto.jpg")
    monkeypatch.setattr(requests, "get", lambda *a, **kw: response(data={"status": "publish", "link": "https://nd.example/noticia"}))
    module._job_social_sync()
    assert telegram.call_count == (0 if telegram_done else 1)
    assert whatsapp.call_count == (1 if enabled else 0)
    if enabled:
        assert whatsapp.call_args.kwargs["title"] == record.title
        assert whatsapp.call_args.kwargs["wordpress_url"] == "https://nd.example/noticia"
        assert whatsapp.call_args.kwargs["image_url"] == "https://img.example/foto.jpg"
    if not telegram_done: assert record.telegram_message_id == "new-tg"
    module._job_social_sync()
    assert telegram.call_count == (0 if telegram_done else 1)
    assert whatsapp.call_count == (1 if enabled else 0)
