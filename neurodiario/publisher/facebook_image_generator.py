"""
Generador de imágenes para posts de Facebook — NeuroDiario
Toma la foto de la noticia, superpone el título y la marca,
y devuelve la imagen lista para subir a Facebook.
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

# ── Ruta al favicon (N) — debe existir en el repo ──
FAVICON_PATH = Path(__file__).resolve().parent / "assets" / "favicon_nd.png"

# ── Fuentes del sistema (DejaVu disponible en Railway/Ubuntu) ──
FONT_BOLD   = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_NORMAL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _get_fonts():
    """Carga las fuentes. Cae a default si no están disponibles."""
    try:
        from PIL import ImageFont
        font_title = ImageFont.truetype(FONT_BOLD, 52)
        font_nd    = ImageFont.truetype(FONT_BOLD, 28)
        font_url   = ImageFont.truetype(FONT_BOLD, 30)
        return font_title, font_nd, font_url
    except Exception:
        from PIL import ImageFont
        default = ImageFont.load_default()
        return default, default, default


def _wrap_text(draw, text: str, font, max_width: int) -> list:
    """Divide el texto en líneas que caben dentro de max_width."""
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


def _download_image(url: str) -> Optional[object]:
    """Descarga una imagen desde URL y la retorna como objeto PIL Image."""
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
        with urllib.request.urlopen(req, timeout=12) as response:
            data = response.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        logger.info(f"  🖼 Imagen descargada OK desde: {url[:80]}")
        return img
    except Exception as e:
        logger.warning(f"  🖼 No se pudo descargar imagen ({e})")
        return None


def _make_fallback_background() -> object:
    """Crea un fondo navy sólido si no hay foto disponible."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (FB_W, FB_H), NAVY)
    draw = ImageDraw.Draw(img)
    # Patrón de puntos sutil
    for x in range(0, FB_W, 40):
        for y in range(0, FB_H, 40):
            draw.ellipse([(x-1, y-1), (x+1, y+1)], fill=(20, 45, 80))
    return img


def _apply_gradient_overlay(img) -> object:
    """Aplica overlay oscuro gradiente en la mitad inferior."""
    from PIL import Image
    overlay = Image.new("RGBA", (FB_W, FB_H), (0, 0, 0, 0))
    from PIL import ImageDraw
    ov_draw = ImageDraw.Draw(overlay)
    steps = 60
    for i in range(steps):
        alpha = int(220 * (i / steps) ** 1.3)
        y0 = int(FB_H * 0.30 + (FB_H * 0.70) * i / steps)
        y1 = int(FB_H * 0.30 + (FB_H * 0.70) * (i + 1) / steps)
        ov_draw.rectangle([(0, y0), (FB_W, y1)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def generate_facebook_image(
    title: str,
    image_url: Optional[str] = None,
) -> Optional[str]:
    """
    Genera la imagen de Facebook para un artículo de NeuroDiario.

    Args:
        title:     Título del artículo (se trunca a 2 líneas automáticamente)
        image_url: URL de la imagen de la noticia (Serper.dev / Pexels)

    Returns:
        Ruta al archivo PNG temporal generado, o None si falla.
    """
    try:
        from PIL import Image, ImageDraw

        # 1. Fondo: foto de la noticia o fallback navy
        if image_url:
            foto = _download_image(image_url)
        else:
            foto = None

        if foto:
            bg = foto.resize((FB_W, FB_H), Image.LANCZOS)
        else:
            logger.info("  🖼 Sin imagen — usando fondo navy de marca")
            bg = _make_fallback_background()

        # 2. Overlay gradiente oscuro
        img = _apply_gradient_overlay(bg)
        draw = ImageDraw.Draw(img)

        # 3. Barra navy inferior
        BAR_H = 90
        draw.rectangle([(0, FB_H - BAR_H), (FB_W, FB_H)], fill=NAVY)
        draw.rectangle([(0, FB_H - BAR_H), (FB_W, FB_H - BAR_H + 5)], fill=BLUE)

        # 4. Fuentes
        font_title, font_nd, font_url = _get_fonts()

        # 5. Título (máx 2 líneas)
        lines = _wrap_text(draw, title, font_title, FB_W - 80)
        lines = lines[:2]

        # Si la segunda línea es muy larga, truncar con "..."
        if len(lines) == 2:
            while True:
                bbox = draw.textbbox((0, 0), lines[1] + "...", font=font_title)
                if bbox[2] <= FB_W - 80 or len(lines[1]) < 5:
                    break
                lines[1] = lines[1].rsplit(" ", 1)[0]
            lines[1] = lines[1] + "..."

        line_h = 64
        y_title = FB_H - BAR_H - len(lines) * line_h - 20
        for line in lines:
            # Sombra
            draw.text((42, y_title + 2), line, font=font_title, fill=(0, 0, 0))
            # Texto blanco
            draw.text((40, y_title), line, font=font_title, fill=WHITE)
            y_title += line_h

        # 6. Favicon (N) en barra inferior
        fav_x = 24
        fav_y = FB_H - BAR_H + (BAR_H - 62) // 2

        if FAVICON_PATH.exists():
            favicon = Image.open(FAVICON_PATH).convert("RGBA")
            fav_h = 62
            ratio = fav_h / favicon.height
            fav_w = int(favicon.width * ratio)
            favicon = favicon.resize((fav_w, fav_h), Image.LANCZOS)
            img.paste(favicon, (fav_x, fav_y), favicon)
            nd_x = fav_x + fav_w + 14
        else:
            # Si no hay favicon, dibujar cuadrado azul con "N"
            draw.rectangle([(fav_x, fav_y), (fav_x + 62, fav_y + 62)], fill=BLUE)
            draw.text((fav_x + 14, fav_y + 10), "N", font=font_nd, fill=WHITE)
            nd_x = fav_x + 62 + 14

        # 7. "NeuroDiario" junto al favicon
        nd_y = FB_H - BAR_H + (BAR_H - 28) // 2
        draw.text((nd_x, nd_y), "NeuroDiario", font=font_nd, fill=WHITE)

        # 8. "neurodiario.com" a la derecha
        url_text = "neurodiario.com"
        url_bbox = draw.textbbox((0, 0), url_text, font=font_url)
        url_w = url_bbox[2]
        url_y = FB_H - BAR_H + (BAR_H - 30) // 2
        draw.text((FB_W - url_w - 40, url_y), url_text, font=font_url, fill=LIGHT_BLUE)

        # 9. Guardar en archivo temporal
        tmp = tempfile.NamedTemporaryFile(
            suffix=".png", prefix="nd_fb_", delete=False
        )
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
    Sube una imagen a Facebook como 'unpublished photo' y retorna su ID.
    Este ID se usa luego al crear el post para adjuntar la imagen.

    Args:
        image_path:  Ruta local al archivo PNG
        page_id:     ID de la página de Facebook
        page_token:  Page Access Token

    Returns:
        photo_id de Facebook, o None si falla.
    """
    try:
        import requests

        url = f"https://graph.facebook.com/v25.0/{page_id}/photos"

        with open(image_path, "rb") as f:
            response = requests.post(
                url,
                data={
                    "access_token": page_token,
                    "published": "false",  # No publicar la foto sola, solo adjuntarla
                },
                files={"source": ("image.png", f, "image/png")},
                timeout=30,
            )

        result = response.json()

        if "id" in result:
            photo_id = result["id"]
            logger.info(f"  📘 Foto subida a Facebook — photo_id: {photo_id}")
            return photo_id
        else:
            error = result.get("error", {})
            logger.error(f"  📘 Error subiendo foto a Facebook: {error.get('message', result)}")
            return None

    except Exception as e:
        logger.error(f"  📘 Excepción subiendo foto a Facebook: {e}")
        return None
    finally:
        # Limpiar archivo temporal
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
    Función principal: genera la imagen, la sube a Facebook y publica el post.

    Args:
        title:         Título del artículo
        wordpress_url: URL del artículo en NeuroDiario
        page_id:       ID de la página de Facebook
        page_token:    Page Access Token permanente
        image_url:     URL de la imagen de la noticia (opcional)

    Returns:
        ID del post de Facebook, o None si falla.
    """
    import requests

    # 1. Generar imagen
    image_path = generate_facebook_image(title=title, image_url=image_url)

    # 2. Si hay imagen, subirla primero
    photo_id = None
    if image_path:
        photo_id = upload_image_to_facebook(image_path, page_id, page_token)

    # 3. Publicar post
    message = f"📰 {title}\n\n🔗 Lee la nota completa:\n{wordpress_url}"

    try:
        url = f"https://graph.facebook.com/v25.0/{page_id}/feed"

        payload = {
            "message": message,
            "link": wordpress_url,
            "access_token": page_token,
        }

        # Adjuntar imagen si se subió correctamente
        if photo_id:
            payload["attached_media[0]"] = f'{{"media_fbid":"{photo_id}"}}'

        response = requests.post(url, data=payload, timeout=15)
        result = response.json()

        if "id" in result:
            fb_post_id = result["id"]
            logger.info(f"  📘 Post publicado en Facebook con imagen — ID: {fb_post_id}")
            return fb_post_id
        else:
            error = result.get("error", {})
            logger.error(f"  📘 Error publicando en Facebook: {error.get('message', result)}")
            return None

    except Exception as e:
        logger.error(f"  📘 Excepción publicando en Facebook: {e}")
        return None
