"""Comprueba sesión y permisos del canal sin publicar mensajes."""
from types import SimpleNamespace
from urllib.parse import quote
import requests

from neurodiario.config.settings import settings
from neurodiario.publisher.whatsapp_publisher import get_whatsapp_config


def check_waha(current_settings=settings, http=requests):
    names = ("WAHA_URL", "WAHA_API_KEY", "WAHA_SESSION", "WHATSAPP_CHANNEL_ID", "WHATSAPP_START_AT")
    config = get_whatsapp_config(SimpleNamespace(WHATSAPP_ENABLED=True, **{n: getattr(current_settings, n, "") for n in names}))
    def get(path):
        response = http.get(config.base_url + path, headers={"X-Api-Key": config.api_key}, timeout=(5, 15), allow_redirects=False)
        if response.status_code != 200:
            raise ValueError(f"WAHA rechazó la comprobación: HTTP {response.status_code}.")
        return response.json()
    session = get("/api/sessions/" + quote(config.session, safe=""))
    if session.get("status") != "WORKING":
        raise ValueError("La sesión WAHA debe estar WORKING.")
    channel = get("/api/" + quote(config.session, safe="") + "/channels/" + quote(config.channel_id, safe=""))
    if channel.get("id") != config.channel_id or channel.get("role") not in ("OWNER", "ADMIN"):
        raise ValueError("La cuenta de WAHA necesita ser OWNER o ADMIN del canal configurado.")
    return "Conexión preparada: sesión WORKING y permisos de publicación confirmados. No se enviaron mensajes."


if __name__ == "__main__":
    try:
        print(check_waha())
    except (ValueError, requests.RequestException):
        raise SystemExit("Comprobación fallida. Revisa red, variables WAHA, sesión WORKING y permisos de administrador del canal.")
