"""Registro duradero e independiente del estado Facebook/Telegram."""
from datetime import datetime, timedelta
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from neurodiario.db.models import WhatsAppPublication
from .whatsapp_publisher import post_to_whatsapp


def needs_whatsapp(db, record, config, now=None):
    if config is None or record.published_at is None or record.published_at < config.start_at:
        return False
    now = now or datetime.utcnow()
    item = db.query(WhatsAppPublication).filter_by(article_id=record.id, channel_id=config.channel_id).first()
    return item is None or (
        item.status == "failed" and item.retryable and item.attempts < 3
        and (item.next_attempt_at is None or item.next_attempt_at <= now)
    )


def publish_record_to_whatsapp(db, record, config, wordpress_url, image_url=None,
                               sender=None, now=None):
    """Reserva y confirma antes del HTTP: otro worker no repite el envío."""
    now = now or datetime.utcnow()
    sender = sender or post_to_whatsapp
    if not needs_whatsapp(db, record, config, now):
        return None
    item = db.query(WhatsAppPublication).filter_by(article_id=record.id, channel_id=config.channel_id).first()
    if item is None:
        item = WhatsAppPublication(article_id=record.id, channel_id=config.channel_id,
                                   status="sending", attempts=1, updated_at=now)
        db.add(item)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # Otro worker reservó el mismo artículo/canal.
            return None
    else:
        count = db.query(WhatsAppPublication).filter(
            WhatsAppPublication.id == item.id,
            WhatsAppPublication.status == "failed",
            WhatsAppPublication.retryable.is_(True),
            WhatsAppPublication.attempts < 3,
            or_(WhatsAppPublication.next_attempt_at.is_(None), WhatsAppPublication.next_attempt_at <= now),
        ).update({"status": "sending", "attempts": WhatsAppPublication.attempts + 1, "updated_at": now}, synchronize_session=False)
        db.commit()
        if not count:
            return None
        db.refresh(item)
    # A crash after this point leaves 'sending' for manual reconciliation, never blind replay.
    try:
        result = sender(title=record.title, wordpress_url=wordpress_url, config=config, image_url=image_url)
    except Exception:
        item.status = "uncertain"
        item.error = "El publicador se interrumpió; revisar el canal antes de repetir."
        item.retryable = False
        item.updated_at = datetime.utcnow()
        db.commit()
        return None
    item.status = result.status
    item.message_id = result.message_id
    item.error = result.error
    item.retryable = result.retryable
    item.next_attempt_at = now + timedelta(seconds=result.retry_after) if result.retryable else None
    item.updated_at = datetime.utcnow()
    if result.status == "sent":
        item.sent_at = datetime.utcnow()
    db.commit()
    return result
