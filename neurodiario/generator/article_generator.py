"""
Módulo generador de artículos periodísticos - NeuroDiario
Genera artículos originales con formato HTML profesional.
Imágenes: Google Custom Search (principal) → Pexels (fallback)
"""

import logging
import re
import os
import requests
from typing import Dict, List, Optional
from datetime import datetime

import anthropic

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# ─────────────────────────────────────────────
# MESES EN ESPAÑOL
# ─────────────────────────────────────────────
MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

def fecha_en_espanol(dt: datetime) -> str:
    return f"{dt.day} de {MESES_ES[dt.month]} de {dt.year}"


# ─────────────────────────────────────────────
# PROMPT MAESTRO DE REDACCIÓN
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Eres el redactor principal de NeuroDiario, el medio digital más inteligente de República Dominicana. Tu escritura es clara, profesional, directa y dominicana — como un periodista senior con criterio propio.

INSTRUCCIONES DE REDACCIÓN:

1. TITULAR: Directo e informativo. Máximo 12 palabras. Sin signos de interrogación. Sin clickbait.

2. LEAD (primer párrafo): Resume el quién, qué, cuándo, dónde y por qué en 2-3 oraciones contundentes. NUNCA empieces con "Según reportó..." ni con el nombre del medio. El lead engancha al lector de inmediato.

3. CUERPO DEL ARTÍCULO:
   - Entre 450 y 650 palabras en total
   - Usa <strong> para resaltar datos clave, nombres de personas y cifras importantes
   - Usa <em> para términos técnicos, títulos de cargos o frases textuales breves
   - Usa comillas «» para citas directas de personas
   - Párrafos cortos: máximo 4 oraciones por párrafo
   - Mínimo 4 párrafos de desarrollo
   - Si aplica, incluye un párrafo de contexto histórico o regional
   - Añade un subtítulo <h2> a mitad del artículo para dividir el contenido. Ese <h2> NUNCA debe repetir el titular principal — debe ser un subtítulo nuevo que introduzca la segunda parte del desarrollo.

4. TONO: Neutral pero con criterio. NeuroDiario analiza, contextualiza y explica. Evita frases vacías como "cabe destacar que", "es importante mencionar" o "en ese sentido".

5. LO QUE NUNCA DEBES HACER:
   - Nunca escribir "Medio desconocido" o "Fuente desconocida"
   - Nunca mezclar inglés y español ("06 de April" está MAL — escribe "6 de abril")
   - Nunca comenzar el artículo con "Según reportó..."
   - Nunca usar Markdown (#, ##, ---, **texto**) — SOLO HTML
   - No inventes datos que no estén en la fuente original
   - No copies texto literal de la fuente
   - NUNCA incluyas el título del artículo como <h1> al inicio del cuerpo — WordPress lo coloca automáticamente. El cuerpo empieza directo con el primer <p>.

6. OUTPUT FORMAT: Devuelve SOLO el cuerpo del artículo en HTML limpio. NO incluyas <h1> en ninguna parte. Usa únicamente: <p>, <strong>, <em>, <blockquote>, <h2>. SIN comentarios, SIN explicaciones, SIN texto fuera del artículo."""


# ─────────────────────────────────────────────
# CLIENTE GOOGLE CUSTOM SEARCH (PRINCIPAL)
# ─────────────────────────────────────────────
class GoogleImageClient:
    """Busca imágenes usando Google Custom Search API."""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: Optional[str] = None, cse_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self.cse_id = cse_id or os.getenv("GOOGLE_CSE_ID", "")

    def search_image(self, query: str) -> Optional[Dict]:
        """
        Busca una imagen real y relevante en Google.

        Args:
            query: Palabras clave (ej: "Luis Abinader presidente República Dominicana")

        Returns:
            Dict con url, source, alt o None si no encuentra
        """
        if not self.api_key or not self.cse_id:
            logger.warning("GOOGLE_API_KEY o GOOGLE_CSE_ID no configurados.")
            return None

        try:
            params = {
                "key": self.api_key,
                "cx": self.cse_id,
                "q": query,
                "searchType": "image",
                "num": 5,
                "imgSize": "large",
                "imgType": "photo",
                "safe": "active",
                "rights": "cc_publicdomain|cc_attribute|cc_sharealike",
            }
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if items:
                item = items[0]
                return {
                    "url": item["link"],
                    "url_medium": item.get("image", {}).get("thumbnailLink", item["link"]),
                    "source": item.get("displayLink", "Google"),
                    "source_url": item.get("image", {}).get("contextLink", ""),
                    "alt": query,
                    "provider": "google",
                }
        except Exception as e:
            logger.error(f"Error buscando imagen en Google: {e}")

        return None

    def build_image_html(self, image: Dict, caption: str = "") -> str:
        cap_text = caption or image.get("alt", "")
        source_url = image.get("source_url", "")
        source_name = image.get("source", "")
        credit = (
            f'Imagen vía <a href="{source_url}" target="_blank" rel="noopener">{source_name}</a>'
            if source_url else f"Imagen: {source_name}"
        )
        return (
            f'<figure class="nd-featured-image" style="margin:0 0 24px 0;padding:0;">'
            f'<img src="{image["url"]}" alt="{cap_text}" loading="lazy" '
            f'style="width:100%;max-width:680px;height:360px;object-fit:cover;display:block;border-radius:6px;" />'
            f'<figcaption style="font-size:12px;color:#888;margin-top:6px;font-style:italic;">'
            f'{cap_text} — {credit}</figcaption>'
            f'</figure>'
        )


# ─────────────────────────────────────────────
# CLIENTE PEXELS (FALLBACK)
# ─────────────────────────────────────────────
class PexelsClient:
    """Fallback de imágenes cuando Google no encuentra resultados."""

    BASE_URL = "https://api.pexels.com/v1/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY", "")

    def search_image(self, query: str, orientation: str = "landscape") -> Optional[Dict]:
        if not self.api_key:
            logger.warning("PEXELS_API_KEY no configurada.")
            return None
        try:
            headers = {"Authorization": self.api_key}
            params = {"query": query, "per_page": 5, "orientation": orientation}
            response = requests.get(self.BASE_URL, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            photos = response.json().get("photos", [])
            if photos:
                photo = photos[0]
                return {
                    "url": photo["src"]["large2x"],
                    "url_medium": photo["src"]["medium"],
                    "photographer": photo.get("photographer", "Pexels"),
                    "photographer_url": photo.get("photographer_url", "https://www.pexels.com"),
                    "alt": query,
                    "pexels_url": photo.get("url", "https://www.pexels.com"),
                    "provider": "pexels",
                }
        except Exception as e:
            logger.error(f"Error buscando imagen en Pexels: {e}")
        return None

    def build_image_html(self, image: Dict, caption: str = "") -> str:
        cap_text = caption or image.get("alt", "")
        credit = (
            f'Foto: <a href="{image["photographer_url"]}" target="_blank" rel="noopener">'
            f'{image["photographer"]}</a> en '
            f'<a href="{image["pexels_url"]}" target="_blank" rel="noopener">Pexels</a>'
        )
        return (
            f'<figure class="nd-featured-image" style="margin:0 0 24px 0;padding:0;">'
            f'<img src="{image["url_medium"]}" alt="{cap_text}" loading="lazy" '
            f'style="width:100%;max-width:680px;height:360px;object-fit:cover;display:block;border-radius:6px;" />'
            f'<figcaption style="font-size:12px;color:#888;margin-top:6px;font-style:italic;">'
            f'{cap_text} — {credit}</figcaption>'
            f'</figure>'
        )


# ─────────────────────────────────────────────
# GENERADOR PRINCIPAL
# ─────────────────────────────────────────────
class ArticleGenerator:
    """Genera artículos periodísticos usando Claude + Google Images + Pexels fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        pexels_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
        google_cse_id: Optional[str] = None,
    ):
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)
        self.google = GoogleImageClient(api_key=google_api_key, cse_id=google_cse_id)
        self.pexels = PexelsClient(api_key=pexels_api_key)

    def _get_image(self, query: str, caption: str) -> str:
        """
        Busca imagen en Google primero, Pexels como fallback.
        Retorna HTML de la figura o cadena vacía si no hay imagen.
        """
        # Intento 1: Google Custom Search
        image = self.google.search_image(query)
        if image:
            logger.info(f"  ✓ Imagen obtenida de Google: {image['url'][:60]}...")
            return self.google.build_image_html(image, caption=caption)

        # Intento 2: Pexels fallback
        logger.info("  → Google sin resultados, intentando Pexels...")
        image = self.pexels.search_image(query)
        if image:
            logger.info(f"  ✓ Imagen obtenida de Pexels: {image['url_medium'][:60]}...")
            return self.pexels.build_image_html(image, caption=caption)

        logger.warning("  ⚠ No se encontró imagen en ninguna fuente.")
        return ""

    # ─────────────────────────────────────────
    # MÉTODO PRINCIPAL — Artículo desde una fuente
    # ─────────────────────────────────────────
    def generate_from_single_article(
        self,
        title: str,
        content: str,
        source: str,
        category: str,
        url: str = "",
        published_at: Optional[datetime] = None,
    ) -> Dict:
        content_trimmed = content[:3000] if len(content) > 3000 else content
        fecha_str = fecha_en_espanol(published_at) if published_at else ""
        source_display = (
            source if source and source.lower() not in ("", "desconocido", "medio desconocido")
            else "fuente local"
        )

        prompt = f"""Redacta un artículo periodístico ORIGINAL para NeuroDiario basado en esta noticia:

DATOS DE LA FUENTE:
- Título original: {title}
- Medio: {source_display}
- Categoría: {category}
{f'- Fecha: {fecha_str}' if fecha_str else ''}
{f'- URL: {url}' if url else ''}

CONTENIDO FUENTE:
{content_trimmed}

IMPORTANTE: Devuelve SOLO el cuerpo en HTML. El primer elemento debe ser un <p>, NUNCA un <h1> ni el título repetido. WordPress coloca el título automáticamente. Sin comentarios. Sin Markdown."""

        try:
            article_html = self._call_api(prompt, max_tokens=2000)
            article_html = self._clean_html(article_html)
            article_html = self._remove_h1_from_html(article_html)

            # Query inteligente para imagen
            image_query = self._build_image_query(title, category)
            image_html = self._get_image(image_query, caption=title)

            footer_html = self._build_footer(source_display, fecha_str, url)
            share_html = self._build_share_icons(url or "")
            full_content = f"{image_html}\n{article_html}\n{footer_html}\n{share_html}"

            clean_title = self._clean_title(title)
            excerpt = self._extract_excerpt(article_html)
            tags = [t for t in [category, source_display, "República Dominicana", "NeuroDiario"] if t]

            return {
                "title": clean_title,
                "content": full_content,
                "excerpt": excerpt,
                "category": category,
                "tags": tags,
                "source_citation": {
                    "source": source_display,
                    "url": url,
                    "published_at": published_at,
                },
            }

        except Exception as e:
            logger.error(f"Error generando artículo: {e}")
            raise

    # ─────────────────────────────────────────
    # MÉTODO — Artículo desde tendencia
    # ─────────────────────────────────────────
    def create_article(self, trend: Dict, articles: List[Dict]) -> Dict:
        articles = articles[:5]
        sources_text = self._format_sources(articles)
        topic = trend.get("topic", "")
        category = trend.get("category", "general")

        source_names = list({a.get("source", "") for a in articles if a.get("source")})
        source_names = [s for s in source_names if s.lower() not in ("", "desconocido", "medio desconocido")]
        sources_citation = ", ".join(source_names[:3]) if source_names else "medios locales"

        prompt = f"""Redacta un artículo periodístico ORIGINAL sobre el tema '{topic}' para NeuroDiario.

FUENTES BASE:
{sources_text}

MEDIOS CONSULTADOS: {sources_citation}
CATEGORÍA: {category}

IMPORTANTE: Devuelve SOLO el cuerpo en HTML. El primer elemento debe ser un <p>, NUNCA un <h1>. Sin comentarios. Sin Markdown."""

        try:
            article_html = self._call_api(prompt, max_tokens=2500)
            article_html = self._clean_html(article_html)
            article_html = self._remove_h1_from_html(article_html)

            image_query = self._build_image_query(topic, category)
            image_html = self._get_image(image_query, caption=topic)

            fecha_str = fecha_en_espanol(datetime.now())
            footer_html = self._build_footer(sources_citation, fecha_str, "")
            share_html = self._build_share_icons("")
            full_content = f"{image_html}\n{article_html}\n{footer_html}\n{share_html}"

            return {
                "title": self._clean_title(topic),
                "content": full_content,
                "excerpt": self._extract_excerpt(article_html),
                "category": category,
                "tags": [category, "República Dominicana", "NeuroDiario"],
                "sources": [a.get("url", "") for a in articles if a.get("url")],
            }

        except Exception as e:
            logger.error(f"Error generando artículo desde tendencia: {e}")
            raise

    # ─────────────────────────────────────────
    # MÉTODO — Boletín diario
    # ─────────────────────────────────────────
    def generate_digest(self, trends: List[Dict]) -> str:
        trends_text = "\n".join(
            f"- {t['topic']} ({t.get('article_count', 0)} artículos)" for t in trends[:5]
        )
        prompt = f"""Redacta un boletín periodístico diario para NeuroDiario.

TENDENCIAS DEL DÍA:
{trends_text}

FORMATO HTML: <h2> título, <p> introducción, un <h2> y <p> por tendencia, <p> cierre.
Extensión: 400-600 palabras. Devuelve SOLO HTML. Sin <h1>."""
        return self._call_api(prompt)

    # ─────────────────────────────────────────
    # UTILIDADES PRIVADAS
    # ─────────────────────────────────────────
    def _call_api(self, user_prompt: str, max_tokens: int = 2048) -> str:
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text
        except anthropic.APIError as e:
            logger.error(f"Error en Claude API: {e}")
            raise

    def _clean_html(self, html: str) -> str:
        html = re.sub(r"```html?\s*", "", html)
        html = re.sub(r"```\s*", "", html)
        return html.strip()

    def _clean_title(self, title: str) -> str:
        return title.strip().lstrip("#").strip()

    def _remove_h1_from_html(self, html: str) -> str:
        return re.sub(r"<h1[^>]*>.*?</h1>", "", html, flags=re.IGNORECASE | re.DOTALL).strip()

    def _extract_excerpt(self, html: str) -> str:
        match = re.search(r"<p[^>]*>(.*?)</p>", html, re.IGNORECASE | re.DOTALL)
        if match:
            text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            return (text[:200] + "...") if len(text) > 200 else text
        return ""

    def _build_image_query(self, title: str, category: str) -> str:
        """
        Claude genera una query de búsqueda inteligente basada en el título.
        Para noticias dominicanas incluye el contexto del país.
        """
        category_fallbacks = {
            "politica": "gobierno República Dominicana política",
            "política": "gobierno República Dominicana política",
            "economia": "economía negocios finanzas",
            "economía": "economía negocios finanzas",
            "deportes": "deportes atletas competencia",
            "internacional": "diplomacia mundo noticias",
            "tecnologia": "tecnología innovación digital",
            "tecnología": "tecnología innovación digital",
            "sociedad": "comunidad personas sociedad dominicana",
            "salud": "salud medicina hospital",
            "cultura": "cultura artes República Dominicana",
        }
        fallback = category_fallbacks.get(category.lower(), "República Dominicana noticias")

        try:
            prompt = f"""Dado este titular de noticia: "{title}"
Categoría: {category}

Genera UNA query de búsqueda de 4-6 palabras para encontrar una imagen periodística real en Google Images.

REGLAS:
- Si la noticia menciona una persona famosa (político, artista, deportista), incluye su nombre completo
- Si menciona un lugar en República Dominicana, inclúyelo
- Si es un evento específico, describe el evento visualmente
- Prioriza términos en español para noticias dominicanas
- Responde SOLO con las palabras clave, sin explicación

EJEMPLOS:
"Abinader anuncia reforma fiscal" → Luis Abinader presidente República Dominicana
"Huracán amenaza el Caribe" → huracán tormenta caribe República Dominicana
"Tigres del Licey ganan campeonato" → Tigres Licey béisbol dominicano campeones
"Trump critica a la OTAN" → Donald Trump Casa Blanca conferencia prensa
"Hospital de Santiago inaugura áreas" → Hospital Regional Santiago República Dominicana"""

            query = self._call_api(prompt, max_tokens=30).strip()
            query = query.split("\n")[0].strip().strip('"').strip("'").strip(".")
            if 3 <= len(query) <= 100:
                return query
            return fallback
        except Exception as e:
            logger.warning(f"Error generando query de imagen: {e}")
            return fallback

    def _build_footer(self, source: str, fecha: str, url: str) -> str:
        url_html = (
            f'<a href="{url}" target="_blank" rel="noopener noreferrer">Ver nota original</a>'
            if url else ""
        )
        parts = [
            '<div class="nd-source-footer">',
            f'<span class="nd-source-label">Fuente:</span> <span class="nd-source-name">{source}</span>',
        ]
        if fecha:
            parts.append(f'<span class="nd-source-date"> · {fecha}</span>')
        if url_html:
            parts.append(f'<span class="nd-source-link"> · {url_html}</span>')
        parts.append('</div>')
        return "\n".join(parts)

    def _build_share_icons(self, article_url: str) -> str:
        encoded_url = requests.utils.quote(article_url, safe="") if article_url else ""

        icon_facebook = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"><path fill="#1877F2" d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047V9.41c0-3.025 1.792-4.697 4.533-4.697 1.312 0 2.686.236 2.686.236v2.97h-1.513c-1.491 0-1.956.93-1.956 1.884v2.25h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/></svg>'
        icon_x = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"><path fill="#000000" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.737-8.835L1.254 2.25H8.08l4.253 5.622 5.911-5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>'
        icon_whatsapp = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"><path fill="#25D366" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>'
        icon_rss = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"><path fill="#F26522" d="M6.18 15.64a2.18 2.18 0 0 1 2.18 2.18C8.36 19.01 7.38 20 6.18 20C4.98 20 4 19.01 4 17.82a2.18 2.18 0 0 1 2.18-2.18M4 4.44A15.56 15.56 0 0 1 19.56 20h-2.83A12.73 12.73 0 0 0 4 7.27V4.44m0 5.66a9.9 9.9 0 0 1 9.9 9.9h-2.83A7.07 7.07 0 0 0 4 12.93V10.1z"/></svg>'

        base_style = "display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;margin:0 4px;text-decoration:none;"
        return (
            f'<div style="display:flex;align-items:center;gap:4px;margin:20px 0;padding:12px 0;border-top:1px solid #e5e5e5;">'
            f'<span style="font-size:13px;color:#666;margin-right:8px;font-family:sans-serif;">Compartir:</span>'
            f'<a href="https://www.facebook.com/sharer/sharer.php?u={encoded_url}" target="_blank" rel="noopener" aria-label="Compartir en Facebook" style="{base_style}background:#e8f0fe;">{icon_facebook}</a>'
            f'<a href="https://twitter.com/intent/tweet?url={encoded_url}" target="_blank" rel="noopener" aria-label="Compartir en X" style="{base_style}background:#f0f0f0;">{icon_x}</a>'
            f'<a href="https://wa.me/?text={encoded_url}" target="_blank" rel="noopener" aria-label="Compartir en WhatsApp" style="{base_style}background:#e8f8ee;">{icon_whatsapp}</a>'
            f'<a href="/feed" target="_blank" rel="noopener" aria-label="RSS Feed" style="{base_style}background:#fff3eb;">{icon_rss}</a>'
            f'</div>'
        )

    def _format_sources(self, articles: List[Dict]) -> str:
        parts = []
        for i, article in enumerate(articles[:5], 1):
            source = article.get("source", "")
            if not source or source.lower() in ("desconocido", "medio desconocido"):
                source = "fuente local"
            parts.append(
                f"[Fuente {i}] {article.get('title', 'Sin título')}\n"
                f"Medio: {source}\n"
                f"URL: {article.get('url', '')}\n"
                f"Contenido: {article.get('raw_content', '')[:500]}..."
            )
        return "\n\n".join(parts)
