"""
Generador de imágenes para posts de Facebook — NeuroDiario
Estilo BBC: foto de fondo + overlay oscuro + título completo + barra de marca.

Mejoras:
- Intenta descargar VARIAS URLs candidatas hasta que una funcione
  (antes se rendía con la primera y caía al fondo oscuro).
- Fallback rediseñado: gradiente limpio con marca, se ve intencional.
- Reporta al pipeline cuál URL funcionó, para que WordPress use la misma.
"""

import html
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Union

import requests

logger = logging.getLogger(__name__)

FB_W, FB_H = 1200, 630
NAVY       = (11, 31, 59)
BLUE       = (0, 119, 255)
WHITE      = (255, 255, 255)
LIGHT_BLUE = (96, 165, 250)

FAVICON_PATH = Path(__file__).resolve().parent / "assets" / "favicon_nd.png"
FONT_BOLD    = str(Path(__file__).resolve().parent / "assets" / "DejaVuSans-Bold.ttf")

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://neurodiario.com/",
}


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
    return html.unescape(title).strip()


def _download_one(url: str):
    """
    Intenta descargar UNA imagen. Retorna un objeto PIL.Image (RGB) o None.
    Valida que el contenido sea realmente una imagen y no una página HTML de error.
    """
    try:
        from PIL import Image
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=15)
        r.raise_for_status()

        # Verificar que sea imagen y no HTML (algunos sitios devuelven pagina de error 200)
        content_type = r.headers.get("Content-Type", "").lower()
        if "image" not in content_type and "octet-stream" not in content_type:
            logger.warning(f"  🖼 URL no es imagen (Content-Type={content_type}): {url[:60]}")
            return None

        # Imagen demasiado pequeña = probablemente un icono o pixel de rastreo
        if len(r.content) < 3000:
            logger.warning(f"  🖼 Imagen demasiado pequeña ({len(r.content)} bytes): {url[:60]}")
            return None

        img = Image.open(io.BytesIO(r.content)).convert("RGB")

        # Rechazar imagenes minusculas por dimension
        if img.width < 300 or img.height < 200:
            logger.warning(f"  🖼 Imagen muy pequeña ({img.width}x{img.height}): {url[:60]}")
            return None

        logger.info(f"  🖼 ✓ Imagen descargada OK: {url[:70]}")
        return img
    except Exception as e:
        logger.warning(f"  🖼 ✗ Falló descarga ({type(e).__name__}): {url[:70]}")
        return None


def _download_first_working(urls: List[str]) -> Tuple[Optional["object"], Optional[str]]:
    """
    Recorre la lista de URLs candidatas e intenta descargar cada una
    hasta que alguna funcione.
    Retorna (imagen_PIL, url_que_funciono) o (None, None) si todas fallan.
    """
    for i, url in enumerate(urls, 1):
        if not url:
            continue
        logger.info(f"  🖼 Intentando candidata {i}/{len(urls)}...")
        img = _download_one(url)
        if img is not None:
            return img, url
    return None, None


def _make_fallback(title: str = ""):
    """
    Fallback rediseñado: gradiente navy->azul limpio con textura sutil de puntos,
    pensado para verse intencional (no roto). El título se dibuja encima después.
    """
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (FB_W, FB_H), NAVY)
    draw = ImageDraw.Draw(img)

    # Gradiente vertical navy -> azul mas claro
    top = (11, 31, 59)
    bottom = (18, 52, 104)
    for y in range(FB_H):
        t = y / FB_H
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (FB_W, y)], fill=(r, g, b))

    # Textura sutil de red neuronal (puntos + lineas tenues) en la esquina superior derecha
    import random
    random.seed(42)  # determinista: siempre igual
    nodes = [(random.randint(FB_W // 2, FB_W - 40), random.randint(30, FB_H // 2)) for _ in range(14)]
    for i, (x, y) in enumerate(nodes):
        for (x2, y2) in nodes[i + 1:]:
            dist = ((x - x2) ** 2 + (y - y2) ** 2) ** 0.5
            if dist < 220:
                draw.line([(x, y), (x2, y2)], fill=(30, 70, 130), width=1)
    for (x, y) in nodes:
        draw.ellipse([(x - 4, y - 4), (x + 4, y + 4)], fill=(0, 119, 255))

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


def _normalize_urls(image_url: Union[str, List[str], None]) -> List[str]:
    """
    Acepta tanto una sola URL (str) como una lista de URLs.
    Devuelve siempre una lista limpia, sin duplicados ni vacíos.
    Esto permite que el resto del pipeline llame igual que antes.
    """
    if image_url is None:
        return []
    if isinstance(image_url, str):
        return [image_url] if image_url else []
    # es lista/tupla
    seen = set()
    out = []
    for u in image_url:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def generate_facebook_image(
    title: str,
    image_url: Union[str, List[str], None] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Genera imagen estilo BBC.
    `image_url` puede ser una sola URL o una lista de candidatas.
    Retorna (ruta_al_png_temporal, url_que_funciono).
    Si ninguna URL funciona, usa el fallback y retorna (ruta, None).
    Si falla la generación por completo, retorna (None, None).
    """
    try:
        from PIL import Image, ImageDraw

        title = _clean_title(title)
        candidates = _normalize_urls(image_url)

        # 1. Fondo — intentar cada candidata hasta que una funcione
        foto, url_ok = (None, None)
        if candidates:
            logger.info(f"  🖼 {len(candidates)} URL(s) candidata(s) para el fondo")
            foto, url_ok = _download_first_working(candidates)

        if foto:
            logger.info(f"  🖼 Usando foto real de fondo: {url_ok[:60]}...")
            bg = foto.resize((FB_W, FB_H), Image.LANCZOS)
        else:
            logger.info("  🖼 Ninguna foto funcionó — usando fallback con marca")
            bg = _make_fallback(title)

        # 2. Overlay oscuro (solo si hay foto real; el fallback ya es oscuro)
        img = _apply_overlay(bg) if foto else bg
        draw = ImageDraw.Draw(img)

        # 3. Barra navy inferior
        BAR_H = 90
        draw.rectangle([(0, FB_H - BAR_H), (FB_W, FB_H)], fill=NAVY)
        draw.rectangle([(0, FB_H - BAR_H), (FB_W, FB_H - BAR_H + 5)], fill=BLUE)

        # 4. Fuentes
        font_lg, font_md, font_nd, font_url = _get_fonts()

        # 5. Título
        lines = _wrap_text(draw, title, font_lg, FB_W - 80)
        font_title, line_h = font_lg, 74
        if len(lines) > 3:
            lines = _wrap_text(draw, title, font_md, FB_W - 80)
            font_title, line_h = font_md, 64

        if len(lines) > 4:
            lines = lines[:4]
            while draw.textbbox((0, 0), lines[-1] + "...", font=font_title)[2] > FB_W - 80 and len(lines[-1]) > 5:
                lines[-1] = lines[-1].rsplit(" ", 1)[0]
            lines[-1] += "..."

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
        return tmp.name, url_ok

    except Exception as e:
        logger.error(f"  🖼 Error generando imagen: {e}", exc_info=True)
        return None, None


def post_to_facebook_with_image(
    title: str,
    wordpress_url: str,
    page_id: str,
    page_token: str,
    image_url: Union[str, List[str], None] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Publica en Facebook usando /photos con caption — imagen grande en el feed.
    `image_url` puede ser una sola URL o una lista de candidatas.

    Retorna (post_id, url_de_imagen_que_funciono).
    La segunda parte permite que el pipeline actualice WordPress con
    la misma foto que sí funcionó en Facebook.
    """
    clean_title = _clean_title(title)

    # 1. Generar imagen (intenta todas las candidatas internamente)
    image_path, working_url = generate_facebook_image(title=clean_title, image_url=image_url)

    if not image_path:
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
            return r.json().get("id"), None
        except Exception as e:
            logger.error(f"  📘 Error publicando fallback: {e}")
            return None, None

    # 2. Publicar con /photos
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
            return result["post_id"], working_url
        elif "id" in result:
            logger.info(f"  📘 Foto publicada — id: {result['id']}")
            return result["id"], working_url
        else:
            error = result.get("error", {})
            logger.error(f"  📘 Error publicando foto: {error.get('message', result)}")
            return None, working_url

    except Exception as e:
        logger.error(f"  📘 Excepción publicando foto: {e}")
        return None, working_url
    finally:
        try:
            if image_path and os.path.exists(image_path):
                os.unlink(image_path)
        except Exception:
            pass
