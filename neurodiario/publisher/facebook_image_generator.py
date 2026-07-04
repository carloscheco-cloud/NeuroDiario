"""
Generador de imágenes para posts de Facebook — NeuroDiario
Estilo BBC: foto de fondo + overlay oscuro + título completo + barra de marca.
"""

import io
import logging
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Dimensiones óptimas para Facebook ──
FB_W, FB_H = 1200, 630

# ── Colores de marca NeuroDiario ──
NAVY       = (11, 31, 59)
BLUE       = (0, 119, 255)
WHITE      = (255, 255, 255)
LIGHT_BLUE = (96, 165, 250)

# ── Ruta al favicon (N) ──
FAVICON_PATH = Path(__file__).resolve().parent / "assets" / "favicon_nd.png"

# ── Fuentes del sistema ──
FONT_BOLD   = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_NORMAL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _get_fonts():
    try:
        from PIL import ImageFont
        font_lg  = ImageFont.truetype(FONT_BOLD, 58)
        font_md  = ImageFont.truetype(FONT_BOLD, 50)
        font_nd  = ImageFont.truetype(FONT_BOLD, 30)
        font_url = ImageFont.truetype(FONT_BOLD, 28)
        return font_lg, font_md, font_nd, font_url
    except Exception:
        from PIL import ImageFont
        d = ImageFont.load_default()
        return d, d, d, d


def _wrap_text(draw, text: str, font, max_width: int) -> list:
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + " " + word if current else word
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_width:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _download_image(url: str):
    try:
        from PIL import Image
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as r:
            data = r.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        logger.info(f"  🖼 Imagen descargada: {url[:80]}")
        return img
    except Exception as e:
        logger.warning(f"  🖼 No se pudo descargar imagen: {e}")
        return None


def _make_fallback_background():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (FB_W, FB_H), NAVY)
    draw = ImageDraw.Draw(img)
    for x in range(0, FB_W, 40):
        for y in range(0, FB_H, 40):
            draw.ellipse([(x-1, y-1), (x+1, y+1)], fill=(20, 45, 80))
    return img


def _apply_gradient_overlay(img):
    from PIL import Image, ImageDraw
    overlay = Image.new("RGBA", (FB_W, FB_H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    steps = 80
    for i in range(steps):
        alpha = int(235 * (i / steps) ** 0.9)
        y0 = int(FB_H * 0.20 + (FB_H * 0.80) * i / steps)
        y1 = int(FB_H * 0.20 + (FB_H * 0.80) * (i + 1) / steps)
        ov.rectangle([(0, y0), (FB_W, y1)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def generate_facebook_image(
    title: str,
    image_url: Optional[str] = None,
) -> Optional[str]:
    """
    Genera imagen estilo BBC: foto + overlay oscuro + título completo + barra NeuroDiario.
    Retorna ruta al archivo PNG temporal, o None si falla.
    """
    try:
        from PIL import Image, ImageDraw

        # 1. Fondo
        foto = _download_image(image_url) if image_url else None
        bg = foto.resize((FB_W, FB_H), Image.LANCZOS) if foto else _make_fallback_background()

        # 2. Overlay oscuro estilo BBC
        img = _apply_gradient_overlay(bg)
        draw = ImageDraw.Draw(img)

        # 3. Barra navy inferior
        BAR_H = 80
        draw.rectangle([(0, FB_H - BAR_H), (FB_W, FB_H)], fill=NAVY)
        draw.rectangle([(0, FB_H - BAR_H), (FB_W, FB_H - BAR_H + 5)], fill=BLUE)

        # 4. Fuentes
        font_lg, font_md, font_nd, font_url = _get_fonts()

        # 5. Título — intenta fuente grande, si pasa de 3 líneas usa mediana
        lines = _wrap_text(draw, title, font_lg, FB_W - 80)
        font_title = font_lg
        line_h = 68
        if len(lines) > 3:
            lines = _wrap_text(draw, title, font_md, FB_W - 80)
            font_title = font_md
            line_h = 60

        # Truncar a 4 líneas máximo con "..."
        if len(lines) > 4:
            lines = lines[:4]
            while True:
                bbox = draw.textbbox((0, 0), lines[-1] + "...", font=font_title)
                if bbox[2] <= FB_W - 80 or len(lines[-1]) < 5:
                    break
                lines[-1] = lines[-1].rsplit(" ", 1)[0]
            lines[-1] += "..."

        # Posición: título pegado justo arriba de la barra
        total_h = len(lines) * line_h
        y_title = FB_H - BAR_H - total_h - 24

        for line in lines:
            draw.text((42, y_title + 3), line, font=font_title, fill=(0, 0, 0))
            draw.text((40, y_title), line, font=font_title, fill=WHITE)
            y_title += line_h

        # 6. Favicon en barra
        fav_x, fav_h = 24, 56
        fav_y = FB_H - BAR_H + (BAR_H - fav_h) // 2

        if FAVICON_PATH.exists():
            favicon = Image.open(FAVICON_PATH).convert("RGBA")
            ratio = fav_h / favicon.height
            fav_w = int(favicon.width * ratio)
            favicon = favicon.resize((fav_w, fav_h), Image.LANCZOS)
            img.paste(favicon, (fav_x, fav_y), favicon)
            nd_x = fav_x + fav_w + 12
        else:
            draw.rectangle([(fav_x, fav_y), (fav_x + 56, fav_y + 56)], fill=BLUE)
            draw.text((fav_x + 14, fav_y + 10), "N", font=font_nd, fill=WHITE)
            nd_x = fav_x + 56 + 12

        # 7. "NeuroDiario" texto
        nd_y = FB_H - BAR_H + (BAR_H - 30) // 2
        draw.text((nd_x, nd_y), "NeuroDiario", font=font_nd, fill=WHITE)

        # 8. "neurodiario.com" derecha
        url_text = "neurodiario.com"
        url_bbox = draw.textbbox((0, 0), url_text, font=font_url)
        url_w = url_bbox[2]
        draw.text((FB_W - url_w - 36, FB_H - BAR_H + (BAR_H - 28) // 2), url_text, font=font_url, fill=LIGHT_BLUE)

        # 9. Guardar temporal
        tmp = tempfile.NamedTemporaryFile(suffix=".png", prefix="nd_fb_", delete=False)
        img.save(tmp.name, format="PNG", optimize=True)
        tmp.close()
        logger.info(f"  🖼 Imagen Facebook generada: {tmp.name}")
        return tmp.name

    except Exception as e:
        logger.error(f"  🖼 Error generando imagen Facebook: {e}", exc_info=True)
        return None


def upload_image_to_facebook(
    image_path: str,
    page_id: str,
    page_token: str,
) -> Optional[str]:
    """
    Sube imagen a Facebook como foto no publicada.
    Retorna photo_id o None.
    """
    try:
        import requests

        url = f"https://graph.facebook.com/v25.0/{page_id}/photos"
        with open(image_path, "rb") as f:
            response = requests.post(
                url,
                data={
                    "access_token": page_token,
                    "published": "false",
                },
                files={"source": ("image.png", f, "image/png")},
                timeout=30,
            )
        result = response.json()
        if "id" in result:
            logger.info(f"  📘 Foto subida — photo_id: {result['id']}")
            return result["id"]
        else:
            error = result.get("error", {})
            logger.error(f"  📘 Error subiendo foto: {error.get('message', result)}")
            return None
    except Exception as e:
        logger.error(f"  📘 Excepción subiendo foto: {e}")
        return None
    finally:
        try:
            if os.path.exists(image_path):
                os.unlink(image_path)
        except Exception:
            pass


def post_to_facebook_with_image(
    title: str,
    wordpress_url: str,
    page_id: str,
    page_token: str,
    image_url: Optional[str] = None,
) -> Optional[str]:
    """
    Genera la imagen estilo BBC, la sube a Facebook y publica el post con ella adjunta.
    Retorna el ID del post de Facebook o None.
    """
    import requests

    # 1. Generar imagen
    image_path = generate_facebook_image(title=title, image_url=image_url)

    # 2. Subir imagen como foto no publicada
    photo_id = None
    if image_path:
        photo_id = upload_image_to_facebook(image_path, page_id, page_token)

    # 3. Publicar post
    message = f"📰 {title}\n\n🔗 Lee la nota completa:\n{wordpress_url}"

    try:
        post_url = f"https://graph.facebook.com/v25.0/{page_id}/feed"
        payload = {
            "message": message,
            "access_token": page_token,
        }

        # Adjuntar imagen si se subió — sin enviar "link" para que la imagen domine
        if photo_id:
            payload["attached_media[0]"] = f'{{"media_fbid":"{photo_id}"}}'
        else:
            # Fallback: solo link si no hay imagen
            payload["link"] = wordpress_url

        response = requests.post(post_url, data=payload, timeout=15)
        result = response.json()

        if "id" in result:
            logger.info(f"  📘 Post publicado en Facebook con imagen — ID: {result['id']}")
            return result["id"]
        else:
            error = result.get("error", {})
            logger.error(f"  📘 Error publicando en Facebook: {error.get('message', result)}")
            return None

    except Exception as e:
        logger.error(f"  📘 Excepción publicando en Facebook: {e}")
        return None
