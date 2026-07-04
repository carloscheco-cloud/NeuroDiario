"""
Generador de imágenes para posts de Facebook — NeuroDiario
Estilo BBC: foto de fondo + overlay oscuro + título completo + barra de marca.
"""

import html
import io
import logging
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

FB_W, FB_H = 1200, 630
NAVY       = (11, 31, 59)
BLUE       = (0, 119, 255)
WHITE      = (255, 255, 255)
LIGHT_BLUE = (96, 165, 250)

FAVICON_PATH = Path(__file__).resolve().parent / "assets" / "favicon_nd.png"
FONT_BOLD    = str(Path(__file__).resolve().parent / "assets" / "DejaVuSans-Bold.ttf")


def _get_fonts():
    try:
        from PIL import ImageFont
        return (
            ImageFont.truetype(FONT_BOLD, 62),
            ImageFont.truetype(FONT_BOLD, 52),
            ImageFont.truetype(FONT_BOLD, 36),
            ImageFont.truetype(FONT_BOLD, 34),
        )
    except Exception:
        from PIL import ImageFont
        d = ImageFont.load_default()
        return d, d, d, d


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = current + " " + word if current else word
        if draw.textbbox((0, 0), test, font=font)[2] > max_width:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _clean_title(title: str) -> str:
    """Decodifica entidades HTML y limpia el título."""
    return html.unescape(title).strip()


def _download_image(url: str):
    try:
        from PIL import Image
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        logger.info(f"  🖼 Imagen descargada: {url[:70]}")
        return img
    except Exception as e:
        logger.warning(f"  🖼 No se pudo descargar imagen ({e}): {url[:70]}")
        return None


def _make_fallback():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (FB_W, FB_H), (20, 50, 100))
    draw = ImageDraw.Draw(img)
    for x in range(0, FB_W, 60):
        for y in range(0, FB_H, 60):
            draw.ellipse([(x-2, y-2), (x+2, y+2)], fill=(30, 65, 120))
    return img


def _apply_overlay(img):
    from PIL import Image, ImageDraw
    overlay = Image.new("RGBA", (FB_W, FB_H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    steps = 80
    for i in range(steps):
        alpha = int(240 * (i / steps) ** 0.85)
        y0 = int(FB_H * 0.15 + (FB_H * 0.85) * i / steps)
        y1 = int(FB_H * 0.15 + (FB_H * 0.85) * (i + 1) / steps)
        ov.rectangle([(0, y0), (FB_W, y1)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def generate_facebook_image(title: str, image_url: Optional[str] = None) -> Optional[str]:
    """Genera imagen estilo BBC. Retorna ruta al PNG temporal o None."""
    try:
        from PIL import Image, ImageDraw

        # Limpiar título — decodificar entidades HTML (&amp; &#37; etc.)
        title = _clean_title(title)

        # 1. Fondo
        foto = _download_image(image_url) if image_url else None
        bg = foto.resize((FB_W, FB_H), Image.LANCZOS) if foto else _make_fallback()

        # 2. Overlay oscuro
        img = _apply_overlay(bg)
        draw = ImageDraw.Draw(img)

        # 3. Barra navy inferior
        BAR_H = 90
        draw.rectangle([(0, FB_H - BAR_H), (FB_W, FB_H)], fill=NAVY)
        draw.rectangle([(0, FB_H - BAR_H), (FB_W, FB_H - BAR_H + 5)], fill=BLUE)

        # 4. Fuentes
        font_lg, font_md, font_nd, font_url = _get_fonts()

        # 5. Título — grande si ≤3 líneas, mediano si >3
        lines = _wrap_text(draw, title, font_lg, FB_W - 80)
        font_title, line_h = font_lg, 74
        if len(lines) > 3:
            lines = _wrap_text(draw, title, font_md, FB_W - 80)
            font_title, line_h = font_md, 64

        # Máx 4 líneas con "..."
        if len(lines) > 4:
            lines = lines[:4]
            while draw.textbbox((0, 0), lines[-1] + "...", font=font_title)[2] > FB_W - 80 and len(lines[-1]) > 5:
                lines[-1] = lines[-1].rsplit(" ", 1)[0]
            lines[-1] += "..."

        # Posición: pegado arriba de la barra
        y_title = FB_H - BAR_H - len(lines) * line_h - 28
        for line in lines:
            draw.text((42, y_title + 3), line, font=font_title, fill=(0, 0, 0))
            draw.text((40, y_title), line, font=font_title, fill=WHITE)
            y_title += line_h

        # 6. Favicon
        fav_h, fav_x = 68, 20
        fav_y = FB_H - BAR_H + (BAR_H - fav_h) // 2
        if FAVICON_PATH.exists():
            favicon = Image.open(FAVICON_PATH).convert("RGBA")
            fav_w = int(favicon.width * fav_h / favicon.height)
            favicon = favicon.resize((fav_w, fav_h), Image.LANCZOS)
            img.paste(favicon, (fav_x, fav_y), favicon)
            nd_x = fav_x + fav_w + 14
        else:
            draw.rectangle([(fav_x, fav_y), (fav_x + 68, fav_y + 68)], fill=BLUE)
            draw.text((fav_x + 14, fav_y + 10), "N", font=font_nd, fill=WHITE)
            nd_x = fav_x + 82

        # 7. "NeuroDiario"
        nd_y = FB_H - BAR_H + (BAR_H - 36) // 2
        draw.text((nd_x, nd_y), "NeuroDiario", font=font_nd, fill=WHITE)

        # 8. "neurodiario.com" derecha
        url_text = "neurodiario.com"
        url_w = draw.textbbox((0, 0), url_text, font=font_url)[2]
        draw.text((FB_W - url_w - 30, FB_H - BAR_H + (BAR_H - 34) // 2), url_text, font=font_url, fill=LIGHT_BLUE)

        # 9. Guardar temporal
        tmp = tempfile.NamedTemporaryFile(suffix=".png", prefix="nd_fb_", delete=False)
        img.save(tmp.name, format="PNG", optimize=True)
        tmp.close()
        logger.info(f"  🖼 Imagen generada: {tmp.name}")
        return tmp.name

    except Exception as e:
        logger.error(f"  🖼 Error generando imagen: {e}", exc_info=True)
        return None


def post_to_facebook_with_image(
    title: str,
    wordpress_url: str,
    page_id: str,
    page_token: str,
    image_url: Optional[str] = None,
) -> Optional[str]:
    """
    Publica en Facebook usando /photos con caption — imagen grande en el feed.
    Retorna el post_id o None.
    """
    import requests

    # Limpiar título para el caption
    clean_title = _clean_title(title)

    # 1. Generar imagen
    image_path = generate_facebook_image(title=clean_title, image_url=image_url)

    if not image_path:
        # Fallback: solo link
        logger.warning("  📘 Sin imagen — publicando solo link")
        try:
            r = requests.post(
                f"https://graph.facebook.com/v25.0/{page_id}/feed",
                data={
                    "message": f"📰 {clean_title}\n\n🔗 {wordpress_url}",
                    "link": wordpress_url,
                    "access_token": page_token,
                },
                timeout=15,
            )
            return r.json().get("id")
        except Exception as e:
            logger.error(f"  📘 Error publicando fallback: {e}")
            return None

    # 2. Publicar con /photos — imagen grande en el feed
    try:
        caption = f"📰 {clean_title}\n\n🔗 Lee la nota completa:\n{wordpress_url}"

        with open(image_path, "rb") as f:
            response = requests.post(
                f"https://graph.facebook.com/v25.0/{page_id}/photos",
                data={
                    "caption": caption,
                    "access_token": page_token,
                    "published": "true",
                },
                files={"source": ("image.png", f, "image/png")},
                timeout=30,
            )

        result = response.json()

        if "post_id" in result:
            logger.info(f"  📘 Post publicado con imagen — post_id: {result['post_id']}")
            return result["post_id"]
        elif "id" in result:
            logger.info(f"  📘 Foto publicada — id: {result['id']}")
            return result["id"]
        else:
            error = result.get("error", {})
            logger.error(f"  📘 Error publicando foto: {error.get('message', result)}")
            return None

    except Exception as e:
        logger.error(f"  📘 Excepción publicando foto: {e}")
        return None
    finally:
        try:
            if image_path and os.path.exists(image_path):
                os.unlink(image_path)
        except Exception:
            pass
