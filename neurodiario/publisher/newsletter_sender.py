"""
NeuroDiario - Newsletter Sender
Envía el newsletter semanal via Mailchimp API
"""

import base64
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional

import requests

logger = logging.getLogger(__name__)

MAILCHIMP_API_KEY = os.getenv("MAILCHIMP_API_KEY", "")
MAILCHIMP_AUDIENCE_ID = os.getenv("MAILCHIMP_AUDIENCE_ID", "")
MAILCHIMP_SERVER = MAILCHIMP_API_KEY.split("-")[-1] if MAILCHIMP_API_KEY else "us7"

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

def _auth():
    return ("anystring", MAILCHIMP_API_KEY)

def _base_url():
    return f"https://{MAILCHIMP_SERVER}.api.mailchimp.com/3.0"


def build_email_html(
    editorial_summary: str,
    articles: List[Dict],
    pdf_filename: str,
    youtube_url: str,
    week_label: str,
    wp_base: str,
) -> str:
    """Construye el HTML completo del email."""

    articles_html = ""
    for i, a in enumerate(articles, 1):
        url = f"{wp_base}/?p={a['wordpress_post_id']}"
        cat = a["category"].upper()
        articles_html += f"""
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #eee;">
            <span style="font-size:10px;font-weight:700;color:#0077FF;letter-spacing:1px;">{cat}</span><br>
            <a href="{url}" style="font-size:15px;font-weight:700;color:#0B1F3B;text-decoration:none;">
              {i}. {a['title']}
            </a>
          </td>
        </tr>"""

    youtube_section = ""
    if youtube_url:
        youtube_section = f"""
        <tr>
          <td style="padding:20px 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="background:#0B1F3B;border-radius:8px;padding:20px;text-align:center;">
                  <p style="color:#60A5FA;font-size:11px;font-weight:700;letter-spacing:1px;margin:0 0 8px 0;">VIDEO DE LA SEMANA</p>
                  <a href="{youtube_url}" style="color:#fff;font-size:16px;font-weight:700;text-decoration:none;">
                    ▶ Ver en YouTube
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F4F4F4;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F4F4F4;padding:20px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;max-width:600px;">

        <!-- HEADER -->
        <tr>
          <td style="background:#0B1F3B;padding:30px 40px;text-align:center;">
            <h1 style="color:#fff;font-size:28px;margin:0;">NeuroDiario</h1>
            <p style="color:#60A5FA;font-size:12px;margin:6px 0 0 0;letter-spacing:1px;">REPORTE SEMANAL — {week_label.upper()}</p>
          </td>
        </tr>

        <!-- BODY -->
        <tr>
          <td style="padding:30px 40px;">

            <!-- EDITORIAL -->
            <div style="color:#333;font-size:14px;line-height:1.7;">
              {editorial_summary}
            </div>

            <!-- NOTICIAS -->
            <h2 style="color:#0B1F3B;font-size:16px;border-bottom:2px solid #0077FF;padding-bottom:8px;margin-top:30px;">
              Las 5 Noticias de la Semana
            </h2>
            <table width="100%" cellpadding="0" cellspacing="0">
              {articles_html}
            </table>

            {youtube_section}

            <!-- PDF -->
            <tr>
              <td style="padding:20px 0 0 0;">
                <p style="font-size:13px;color:#555;">
                  📄 <strong>Reporte PDF adjunto</strong> — Incluye análisis completo de las noticias de la semana, distribución por categorías y contexto editorial.
                </p>
              </td>
            </tr>

          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#0B1F3B;padding:20px 40px;text-align:center;">
            <p style="color:#60A5FA;font-size:12px;margin:0;">
              <a href="{wp_base}" style="color:#60A5FA;">neurodiario.com</a> —
              El Primer Periódico IA de República Dominicana
            </p>
            <p style="color:#334;font-size:10px;margin:8px 0 0 0;color:#4a6080;">
              Recibes este email porque te suscribiste a NeuroDiario Semanal.
              <br>*|UNSUB|*
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_weekly_newsletter(
    articles: List[Dict],
    editorial_summary: str,
    pdf_path: Optional[str],
    youtube_url: str = "",
    wp_base: str = "https://neurodiario.com",
) -> bool:
    """
    Crea y envía la campaña semanal en Mailchimp.
    Retorna True si fue exitoso.
    """
    if not MAILCHIMP_API_KEY or not MAILCHIMP_AUDIENCE_ID:
        logger.error("  📧 Faltan MAILCHIMP_API_KEY o MAILCHIMP_AUDIENCE_ID")
        return False

    now = datetime.now()
    week_label = f"{now.day} de {MESES_ES[now.month]} de {now.year}"
    subject = f"NeuroDiario Semanal — Las noticias que importan ({week_label})"

    html_content = build_email_html(
        editorial_summary=editorial_summary,
        articles=articles,
        pdf_filename=f"NeuroDiario_Reporte_{now.strftime('%Y%m%d')}.pdf",
        youtube_url=youtube_url,
        week_label=week_label,
        wp_base=wp_base,
    )

    # 1. Crear campaña
    campaign_payload = {
        "type": "regular",
        "recipients": {"list_id": MAILCHIMP_AUDIENCE_ID},
        "settings": {
            "subject_line": subject,
            "preview_text": f"Las 5 noticias más importantes de la semana en República Dominicana",
            "title": f"NeuroDiario Semanal {now.strftime('%Y-%m-%d')}",
            "from_name": "NeuroDiario",
            "reply_to": "contacto@neurodiario.com",
        },
    }

    try:
        r = requests.post(
            f"{_base_url()}/campaigns",
            json=campaign_payload,
            auth=_auth(),
            timeout=15,
        )
        if r.status_code != 200:
            logger.error(f"  📧 Error creando campaña: {r.status_code} — {r.text[:200]}")
            return False

        campaign_id = r.json()["id"]
        logger.info(f"  📧 Campaña creada: {campaign_id}")

        # 2. Agregar contenido HTML
        content_r = requests.put(
            f"{_base_url()}/campaigns/{campaign_id}/content",
            json={"html": html_content},
            auth=_auth(),
            timeout=15,
        )
        if content_r.status_code != 200:
            logger.error(f"  📧 Error agregando contenido: {content_r.text[:200]}")
            return False

        # 3. Enviar campaña
        send_r = requests.post(
            f"{_base_url()}/campaigns/{campaign_id}/actions/send",
            auth=_auth(),
            timeout=15,
        )
        if send_r.status_code == 204:
            logger.info(f"  📧 Newsletter enviado exitosamente — campaña {campaign_id}")
            return True
        else:
            logger.error(f"  📧 Error enviando: {send_r.status_code} — {send_r.text[:200]}")
            return False

    except Exception as e:
        logger.error(f"  📧 Excepción enviando newsletter: {e}")
        return False
