"""
Módulo generador de artículos periodísticos - NeuroDiario
Genera artículos originales con formato HTML profesional e imágenes automáticas via Pexels.
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
    """Convierte datetime a formato '8 de abril de 2026'."""
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
   - Añade un subtítulo <h2> a mitad del artículo para dividir el contenido

4. TONO: Neutral pero con criterio. NeuroDiario analiza, contextualiza y explica. Evita frases vacías como "cabe destacar que", "es importante mencionar" o "en ese sentido".

5. LO QUE NUNCA DEBES HACER:
   - Nunca escribir "Medio desconocido" o "Fuente desconocida"
   - Nunca mezclar inglés y español ("06 de April" está MAL — escribe "6 de abril")
   - Nunca comenzar el artículo con "Según reportó..."
   - Nunca usar Markdown (#, ##, ---, **texto**) — SOLO HTML
   - No inventes datos que no estén en la fuente original
   - No copies texto literal de la fuente

6. OUTPUT FORMAT: Devuelve SOLO el artículo en HTML limpio, listo para WordPress. Usa únicamente estas etiquetas: <p>, <strong>, <em>, <blockquote>, <h2>. SIN comentarios, SIN explicaciones, SIN texto fuera del artículo."""


# ─────────────────────────────────────────────
# CLIENTE PEXELS
# ─────────────────────────────────────────────
class PexelsClient:
    """Busca imágenes libres de derechos en Pexels."""

    BASE_URL = "https://api.pexels.com/v1/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY", "")

    def search_image(self, query: str, orientation: str = "landscape") -> Optional[Dict]:
        """
        Busca una imagen en Pexels por palabras clave.

        Args:
            query: Palabras clave de búsqueda (ej: "economía República Dominicana")
            orientation: "landscape" | "portrait" | "square"

        Returns:
            Dict con url, photographer, alt o None si no se encuentra
        """
        if not self.api_key:
            logger.warning("PEXELS_API_KEY no configurada — artículo sin imagen.")
            return None

        try:
            headers = {"Authorization": self.api_key}
            params = {
                "query": query,
                "per_page": 5,
                "orientation": orientation,
                "locale": "es-ES",
            }
            response = requests.get(self.BASE_URL, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            photos = data.get("photos", [])
            if not photos:
                # Reintento en inglés si no hay resultados en español
                params["locale"] = "en-US"
                response = requests.get(self.BASE_URL, headers=headers, params=params, timeout=10)
                data = response.json()
                photos = data.get("photos", [])

            if photos:
                photo = photos[0]
                return {
                    "url": photo["src"]["large2x"],
                    "url_medium": photo["src"]["large"],
                    "photographer": photo.get("photographer", "Pexels"),
                    "photographer_url": photo.get("photographer_url", "https://www.pexels.com"),
                    "alt": query,
                    "pexels_url": photo.get("url", "https://www.pexels.com"),
                }
        except Exception as e:
            logger.error(f"Error buscando imagen en Pexels: {e}")

        return None

    def build_image_html(self, image: Dict, caption: str = "") -> str:
        """
        Genera el HTML de la imagen con crédito Pexels.

        Args:
            image: Dict retornado por search_image()
            caption: Texto del caption (opcional)

        Returns:
            HTML de la figura completa
        """
        cap_text = caption or image.get("alt", "")
        credit = f'Foto: <a href="{image["photographer_url"]}" target="_blank" rel="noopener">{image["photographer"]}</a> en <a href="{image["pexels_url"]}" target="_blank" rel="noopener">Pexels</a>'

        return (
            f'<figure class="nd-featured-image">'
            f'<img src="{image["url_medium"]}" alt="{cap_text}" loading="lazy" />'
            f'<figcaption>{cap_text} — {credit}</figcaption>'
            f'</figure>'
        )


# ─────────────────────────────────────────────
# GENERADOR PRINCIPAL
# ─────────────────────────────────────────────
class ArticleGenerator:
    """Genera artículos periodísticos usando la API de Claude + imágenes Pexels."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        pexels_api_key: Optional[str] = None,
    ):
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)
        self.pexels = PexelsClient(api_key=pexels_api_key)

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
        """
        Genera un artículo HTML original para NeuroDiario desde un artículo fuente.

        Args:
            title: Título del artículo original
            content: Contenido del artículo original
            source: Nombre del medio fuente (ej: "Diario Libre")
            category: Categoría del artículo
            url: URL del artículo original
            published_at: Fecha de publicación original

        Returns:
            Dict con title, content (HTML completo), excerpt, category, tags,
                  source_citation, featured_image
        """
        content_trimmed = content[:3000] if len(content) > 3000 else content
        fecha_str = fecha_en_espanol(published_at) if published_at else ""
        source_display = source if source and source.lower() not in ("", "desconocido", "medio desconocido") else "fuente local"

        prompt = f"""Redacta un artículo periodístico ORIGINAL para NeuroDiario basado en esta noticia:

DATOS DE LA FUENTE:
- Título original: {title}
- Medio: {source_display}
- Categoría: {category}
{f'- Fecha: {fecha_str}' if fecha_str else ''}
{f'- URL: {url}' if url else ''}

CONTENIDO FUENTE:
{content_trimmed}

Recuerda: devuelve SOLO el artículo en HTML. Sin comentarios. Sin Markdown."""

        try:
            article_html = self._call_api(prompt, max_tokens=2000)
            article_html = self._clean_html(article_html)

            # Imagen desde Pexels
            image_query = self._build_image_query(title, category)
            image = self.pexels.search_image(image_query)
            image_html = self.pexels.build_image_html(image, caption=title) if image else ""

            # Pie de fuente profesional
            footer_html = self._build_footer(source_display, fecha_str, url)

            # Íconos compartir
            share_html = self._build_share_icons(url or "")

            # HTML completo del post
            full_content = f"{image_html}\n{article_html}\n{footer_html}\n{share_html}"

            # Título limpio
            clean_title = self._extract_title_from_html(article_html) or self._clean_title(title)

            # Excerpt
            excerpt = self._extract_excerpt(article_html)

            # Tags
            tags = [t for t in [category, source_display, "República Dominicana", "NeuroDiario"] if t]

            return {
                "title": clean_title,
                "content": full_content,
                "excerpt": excerpt,
                "category": category,
                "tags": tags,
                "featured_image": image,
                "source_citation": {
                    "source": source_display,
                    "url": url,
                    "published_at": published_at,
                },
            }

        except Exception as e:
            logger.error(f"Error generando artículo desde fuente única: {e}")
            raise

    # ─────────────────────────────────────────
    # MÉTODO — Artículo desde tendencia + múltiples fuentes
    # ─────────────────────────────────────────
    def create_article(self, trend: Dict, articles: List[Dict]) -> Dict:
        """
        Genera artículo basado en tendencia y múltiples fuentes.

        Args:
            trend: Tendencia detectada
            articles: Artículos relacionados

        Returns:
            Dict con artículo estructurado
        """
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

Recuerda: devuelve SOLO el artículo en HTML. Sin comentarios. Sin Markdown."""

        try:
            article_html = self._call_api(prompt, max_tokens=2500)
            article_html = self._clean_html(article_html)

            # Imagen
            image_query = self._build_image_query(topic, category)
            image = self.pexels.search_image(image_query)
            image_html = self.pexels.build_image_html(image, caption=topic) if image else ""

            # Pie de fuente
            fecha_str = fecha_en_espanol(datetime.now())
            footer_html = self._build_footer(sources_citation, fecha_str, "")

            # Íconos compartir
            share_html = self._build_share_icons("")

            full_content = f"{image_html}\n{article_html}\n{footer_html}\n{share_html}"
            clean_title = self._extract_title_from_html(article_html) or topic
            excerpt = self._extract_excerpt(article_html)

            return {
                "title": clean_title,
                "content": full_content,
                "excerpt": excerpt,
                "category": category,
                "tags": [category, "República Dominicana", "NeuroDiario"],
                "featured_image": image,
                "sources": [a.get("url", "") for a in articles if a.get("url")],
            }

        except Exception as e:
            logger.error(f"Error generando artículo desde tendencia: {e}")
            raise

    # ─────────────────────────────────────────
    # MÉTODO — Boletín diario
    # ─────────────────────────────────────────
    def generate_digest(self, trends: List[Dict]) -> str:
        """
        Genera un boletín diario con las principales tendencias.

        Args:
            trends: Lista de tendencias detectadas

        Returns:
            HTML del boletín
        """
        trends_text = "\n".join(
            f"- {t['topic']} ({t.get('article_count', 0)} artículos)"
            for t in trends[:5]
        )

        prompt = f"""Redacta un boletín periodístico diario para NeuroDiario.

TENDENCIAS DEL DÍA:
{trends_text}

FORMATO HTML:
- <h1> con título atractivo del boletín
- <p> de introducción breve
- Un <h2> y <p> por cada tendencia
- <p> de cierre con perspectiva general

Extensión: 400-600 palabras. Devuelve SOLO HTML."""

        return self._call_api(prompt)

    # ─────────────────────────────────────────
    # UTILIDADES PRIVADAS
    # ─────────────────────────────────────────
    def _call_api(self, user_prompt: str, max_tokens: int = 2048) -> str:
        """Llama a la API de Claude."""
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
        """Elimina bloques de código Markdown si Claude los incluye por error."""
        html = re.sub(r"```html?\s*", "", html)
        html = re.sub(r"```\s*", "", html)
        return html.strip()

    def _clean_title(self, title: str) -> str:
        """Limpia el título removiendo Markdown y espacios."""
        return title.strip().lstrip("#").strip()

    def _extract_title_from_html(self, html: str) -> str:
        """Intenta extraer el primer <h1> o <h2> del HTML generado como título del post."""
        match = re.search(r"<h[12][^>]*>(.*?)</h[12]>", html, re.IGNORECASE | re.DOTALL)
        if match:
            raw = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            # Si el h1/h2 está en el cuerpo, lo removemos para que el título no se duplique
            return raw
        return ""

    def _extract_excerpt(self, html: str) -> str:
        """Extrae el primer párrafo como excerpt."""
        match = re.search(r"<p[^>]*>(.*?)</p>", html, re.IGNORECASE | re.DOTALL)
        if match:
            text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            return (text[:200] + "...") if len(text) > 200 else text
        return ""

    def _build_image_query(self, title: str, category: str) -> str:
        """Construye la query de búsqueda para Pexels."""
        # Palabras clave por categoría
        category_keywords = {
            "politica": "politics government",
            "política": "politics government",
            "economia": "economy business",
            "economía": "economy business finance",
            "deportes": "sports Dominican Republic",
            "internacional": "world international news",
            "tecnologia": "technology innovation",
            "tecnología": "technology innovation",
            "sociedad": "community society people",
            "salud": "health medicine",
            "cultura": "culture arts",
        }
        cat_key = category_keywords.get(category.lower(), "Dominican Republic")

        # Usar las primeras 4 palabras del título + categoría
        title_words = " ".join(title.split()[:4])
        return f"{title_words} {cat_key}"

    def _build_footer(self, source: str, fecha: str, url: str) -> str:
        """Genera el pie de fuente en HTML profesional."""
        url_html = f'<a href="{url}" target="_blank" rel="noopener noreferrer">Ver nota original</a>' if url else ""
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
        """Genera íconos de compartir para redes sociales."""
        encoded_url = requests.utils.quote(article_url, safe="") if article_url else ""
        return f"""<div class="nd-share-bar">
  <span class="nd-share-label">Compartir:</span>
  <a class="nd-share-btn nd-share-facebook" href="https://www.facebook.com/sharer/sharer.php?u={encoded_url}" target="_blank" rel="noopener" aria-label="Compartir en Facebook">
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg> Facebook
  </a>
  <a class="nd-share-btn nd-share-twitter" href="https://twitter.com/intent/tweet?url={encoded_url}" target="_blank" rel="noopener" aria-label="Compartir en X/Twitter">
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M4 4l16 16M4 20L20 4"/><path d="M4 4l16 16M4 20L20 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg> X / Twitter
  </a>
  <a class="nd-share-btn nd-share-whatsapp" href="https://wa.me/?text={encoded_url}" target="_blank" rel="noopener" aria-label="Compartir en WhatsApp">
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg> WhatsApp
  </a>
  <a class="nd-share-btn nd-share-rss" href="/feed" target="_blank" rel="noopener" aria-label="RSS Feed">
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/></svg> RSS
  </a>
</div>"""

    def _format_sources(self, articles: List[Dict]) -> str:
        """Formatea artículos como texto para el prompt."""
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
