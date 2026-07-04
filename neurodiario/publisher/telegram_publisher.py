"""
NeuroDiario - Telegram Publisher
Publica artículos automáticamente en el canal @NeuroDiario
usando la Bot API de Telegram con imagen + título + enlace.
"""

import logging
import os
import requests
from typing import Optional

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def post_to_telegram(
    title: str,
    wordpress_url: str,
    channel_id: str,
    bot_token: str,
    image_url: Optional[str] = None,
) -> Optional[str]:
    """
    Publica un artículo en el canal de Telegram.
    Si hay imagen, la envía como foto con caption.
    Si no hay imagen, envía solo texto con formato HTML.
    Retorna el message_id si fue exitoso, None si falló.
    """

    caption = (
        f"<b>{title}</b>\n\n"
        f"🔗 <a href='{wordpress_url}'>Leer artículo completo</a>\n\n"
        f"📰 <i>NeuroDiario — Noticias de República Dominicana</i>"
    )

    # Intentar con imagen primero
    if image_url:
        try:
            url = TELEGRAM_API.format(token=bot_token, method="sendPhoto")
            payload = {
                "chat_id": channel_id,
                "photo": image_url,
                "caption": caption,
                "parse_mode": "HTML",
            }
            response = requests.post(url, json=payload, timeout=15)

            if response.status_code == 200:
                result = response.json()
                message_id = str(result["result"]["message_id"])
                logger.info(f"  📱 Telegram: publicado con imagen — message_id {message_id}")
                return message_id
            else:
                logger.warning(f"  📱 Telegram: error con imagen ({response.status_code}) — intentando sin imagen")
        except Exception as e:
            logger.warning(f"  📱 Telegram: excepción con imagen — {e} — intentando sin imagen")

    # Fallback: solo texto
    try:
        url = TELEGRAM_API.format(token=bot_token, method="sendMessage")
        payload = {
            "chat_id": channel_id,
            "text": caption,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        response = requests.post(url, json=payload, timeout=15)

        if response.status_code == 200:
            result = response.json()
            message_id = str(result["result"]["message_id"])
            logger.info(f"  📱 Telegram: publicado sin imagen — message_id {message_id}")
            return message_id
        else:
            logger.error(f"  📱 Telegram: error al publicar — {response.status_code} — {response.text[:200]}")
            return None

    except Exception as e:
        logger.error(f"  📱 Telegram: excepción al publicar — {e}")
        return None
