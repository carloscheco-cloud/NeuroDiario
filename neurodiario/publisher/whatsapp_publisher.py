"""Publicación en canales WhatsApp mediante WAHA, sin Make ni Whapi."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import ipaddress
import mimetypes
import re
from typing import Optional
from urllib.parse import urlsplit

import requests


@dataclass(frozen=True)
class WhatsAppConfig:
    base_url: str
    api_key: str = field(repr=False)
    channel_id: str
    session: str
    start_at: datetime


def get_whatsapp_config(settings) -> Optional[WhatsAppConfig]:
    if not getattr(settings, "WHATSAPP_ENABLED", False):
        return None
    base = getattr(settings, "WAHA_URL", "").rstrip("/")
    key = getattr(settings, "WAHA_API_KEY", "")
    channel = getattr(settings, "WHATSAPP_CHANNEL_ID", "")
    session = getattr(settings, "WAHA_SESSION", "default")
    since = getattr(settings, "WHATSAPP_START_AT", "")
    if not all((base, key, channel, session, since)):
        raise ValueError("WhatsApp requiere WAHA_URL, WAHA_API_KEY, WAHA_SESSION, WHATSAPP_CHANNEL_ID y WHATSAPP_START_AT.")
    url = urlsplit(base)
    if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("WAHA_URL debe ser una URL de API sin credenciales, consulta ni fragmento.")
    if url.scheme == "http":
        private = url.hostname in {"localhost", "waha", "universidad-waha-1", "host.docker.internal"}
        try:
            private = private or ipaddress.ip_address(url.hostname).is_private
        except ValueError:
            pass
        if not private:
            raise ValueError("Usa HTTPS o una dirección privada para conectar WAHA.")
    if not re.fullmatch(r"\d+@newsletter", channel):
        raise ValueError("WHATSAPP_CHANNEL_ID debe terminar en @newsletter; no es un número de teléfono.")
    try:
        start = datetime.fromisoformat(since.replace("Z", "+00:00"))
        if start.tzinfo is None:
            raise ValueError()
    except ValueError:
        raise ValueError("WHATSAPP_START_AT requiere fecha ISO con zona horaria, por ejemplo 2026-10-22T00:00:00Z.") from None
    return WhatsAppConfig(base, key, channel, session, start.astimezone(timezone.utc).replace(tzinfo=None))


@dataclass(frozen=True)
class WhatsAppResult:
    status: str  # sent, failed (rejected), uncertain (may have reached WhatsApp)
    message_id: Optional[str] = None
    error: str = ""
    retryable: bool = False
    retry_after: int = 720


def _message_id(data) -> Optional[str]:
    value = data.get("id") if isinstance(data, dict) else None
    if isinstance(value, dict):
        value = value.get("_serialized")
    return value if isinstance(value, str) and value else None


def post_to_whatsapp(title: str, wordpress_url: str, config: WhatsAppConfig,
                     image_url: Optional[str] = None, http=None) -> WhatsAppResult:
    """Mismo título/enlace/imagen de Telegram; solo cambia el transporte.

    Una respuesta ambigua no se reenvía automáticamente. El fallback a texto
    solo ocurre si WAHA rechazó explícitamente la imagen (HTTP 400/422).
    """
    if not title.strip() or urlsplit(wordpress_url).scheme not in ("http", "https"):
        return WhatsAppResult("failed", error="Contenido o enlace de WordPress inválido.")
    caption = f"*{title.strip()}*\n\n🔗 Leer artículo completo: {wordpress_url}\n\n📰 NeuroDiario — Noticias de República Dominicana"
    client = http or requests

    def send(path, body):
        try:
            response = client.post(config.base_url + path, json=body,
                                   headers={"X-Api-Key": config.api_key},
                                   timeout=(5, 30), allow_redirects=False)
        except requests.ConnectTimeout:
            return WhatsAppResult("failed", error="WAHA: tiempo de conexión agotado.", retryable=True)
        except requests.RequestException:
            return WhatsAppResult("uncertain", error="WAHA: envío sin confirmación; revisar el canal antes de repetir.")
        if 200 <= response.status_code < 300:
            try:
                message_id = _message_id(response.json())
            except ValueError:
                message_id = None
            if message_id:
                return WhatsAppResult("sent", message_id=message_id)
            return WhatsAppResult("uncertain", error="WAHA aceptó la solicitud sin devolver un identificador.")
        if response.status_code == 429:
            retry = response.headers.get("Retry-After", "720")
            seconds = int(retry) if retry.isdigit() else 720
            return WhatsAppResult("failed", error="WAHA: límite temporal de envíos.", retryable=True, retry_after=max(60, seconds))
        if response.status_code >= 500:
            return WhatsAppResult("uncertain", error=f"WAHA HTTP {response.status_code}: comprobar el canal antes de repetir.")
        return WhatsAppResult("failed", error=f"WAHA rechazó el envío: HTTP {response.status_code}.")

    common = {"session": config.session, "chatId": config.channel_id}
    if image_url and urlsplit(image_url).scheme in ("http", "https"):
        mime = mimetypes.guess_type(urlsplit(image_url).path)[0] or "image/jpeg"
        result = send("/api/sendImage", {**common, "file": {"url": image_url, "mimetype": mime}, "caption": caption})
        if result.status != "failed" or result.error not in {"WAHA rechazó el envío: HTTP 400.", "WAHA rechazó el envío: HTTP 422."}:
            return result
    return send("/api/sendText", {**common, "text": caption, "linkPreview": False})
