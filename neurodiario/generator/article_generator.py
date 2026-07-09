"""
Modulo generador de articulos periodisticos - NeuroDiario
Imagenes: Serper.dev fuentes oficiales (prioritario) -> Serper.dev general con exclusion de medios -> Pexels (fallback)

CAMBIO (jul 2026): Los medios dominicanos comerciales (Diario Libre, Listin, etc.)
ya NO se usan como fuente de imagenes porque sus fotos llevan marca de agua / logo
y tienen derechos de autor. Ahora:
  - Nivel 1 prioriza fuentes OFICIALES (gobierno, congreso, partidos) cuyas fotos
    de prensa se publican para uso de los medios.
  - Nivel 2 busca en Google general EXCLUYENDO los dominios de esos medios.
  - BLOCKED_DOMAINS actua como red de seguridad final.
"""

import logging
import re
import os
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import anthropic

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

def fecha_en_espanol(dt: datetime) -> str:
    return f"{dt.day} de {MESES_ES[dt.month]} de {dt.year}"


# ─────────────────────────────────────────────
# FUENTES DE IMAGENES
# ─────────────────────────────────────────────

# Fuentes OFICIALES dominicanas — se busca aqui PRIMERO.
# Sus fotos de prensa se publican para que los medios las usen,
# no llevan marca de agua de medios competidores y la identidad
# de las personas retratadas es confiable.
OFFICIAL_IMAGE_SITES = [
    # Gobierno
    "presidencia.gob.do",
    "mirex.gob.do",
    "mepyd.gob.do",
    "mitur.gob.do",
    "micm.gob.do",
    "minerd.gob.do",
    "msp.gob.do",
    "mopc.gob.do",
    "hacienda.gob.do",
    # Congreso y organos electorales
    "senadord.gob.do",
    "camaradediputados.gob.do",
    "jce.gob.do",
    # Partidos politicos (salas de prensa)
    "fuerzadelpueblo.org.do",
    "prm.org.do",
    "pldaldia.com",
]

# Query de fuentes oficiales para Serper (formato site: OR site:)
OFFICIAL_SITES_QUERY = " OR ".join(f"site:{d}" for d in OFFICIAL_IMAGE_SITES)

# Medios dominicanos comerciales — EXCLUIDOS de toda busqueda de imagenes.
# Sus fotos llevan logo/marca de agua y tienen derechos de autor.
EXCLUDED_MEDIA_SITES = [
    "diariolibre.com",
    "listindiario.com",
    "elnacional.com.do",
    "eldia.com.do",
    "elcaribe.com.do",
    "hoy.com.do",
    "n.com.do",
    "ndigital.com.do",
    "acento.com.do",
    "elnuevodiario.com.do",
    "diariodominicano.com",
    "almomento.net",
    "noticiassin.com",
    "cdn.com.do",
    "z101digital.com",
    "remolacha.net",
    "periodicoeljaya.com",
    "proceso.com.do",
]

# String de exclusion para el query de Google (formato -site: -site:)
EXCLUDED_SITES_QUERY = " ".join(f"-site:{d}" for d in EXCLUDED_MEDIA_SITES)


SYSTEM_PROMPT = """Eres el redactor principal de NeuroDiario, el medio digital mas inteligente de Republica Dominicana. Tu escritura es clara, profesional, directa y dominicana como un periodista senior con criterio propio.

INSTRUCCIONES DE REDACCION:

1. TITULAR: Directo e informativo. Maximo 12 palabras. Sin signos de interrogacion. Sin clickbait.

2. LEAD (primer parrafo): Resume el quien, que, cuando, donde y por que en 2-3 oraciones contundentes. NUNCA empieces con "Segun reporto..." ni con el nombre del medio. El lead engancha al lector de inmediato.

3. CUERPO DEL ARTICULO:
   - Entre 450 y 650 palabras en total
   - Usa <strong> para resaltar datos clave, nombres de personas y cifras importantes
   - Usa <em> para terminos tecnicos, titulos de cargos o frases textuales breves
   - Usa comillas para citas directas de personas
   - Parrafos cortos: maximo 4 oraciones por parrafo
   - Minimo 4 parrafos de desarrollo
   - Si aplica, incluye un parrafo de contexto historico o regional
   - Agrega un subtitulo <h2> a mitad del articulo. Ese <h2> NUNCA debe repetir el titular principal.

4. TONO: Neutral pero con criterio. NeuroDiario analiza, contextualiza y explica. Evita frases vacias como "cabe destacar que" o "es importante mencionar".

5. LO QUE NUNCA DEBES HACER:
   - Nunca escribir "Medio desconocido" o "Fuente desconocida"
   - Nunca mezclar ingles y espanol en fechas
   - Nunca comenzar el articulo con "Segun reporto..."
   - Nunca usar Markdown (#, ##, ---, **texto**) solo HTML
   - No inventes datos que no esten en la fuente original
   - No copies texto literal de la fuente
   - NUNCA incluyas el titulo del articulo como <h1> al inicio del cuerpo. WordPress lo coloca automaticamente. El cuerpo empieza directo con el primer <p>.

6. OUTPUT FORMAT: Devuelve SOLO el cuerpo del articulo en HTML limpio. NO incluyas <h1> en ninguna parte. Usa unicamente: <p>, <strong>, <em>, <blockquote>, <h2>. SIN comentarios, SIN explicaciones, SIN texto fuera del articulo."""


# ─────────────────────────────────────────────
# CLIENTE SERPER.DEV (PRINCIPAL - Google Images real)
# ─────────────────────────────────────────────
class SerperImageClient:
    """Busca imagenes usando Serper.dev - acceso real a Google Images."""

    BASE_URL = "https://google.serper.dev/images"

    # Red de seguridad: aunque el query ya excluye estos dominios via -site:,
    # aqui se descarta cualquier URL que se cuele (CDNs, subdominios, cache).
    BLOCKED_DOMAINS = [
        # Redes sociales (no cargan en WordPress)
        "fbsbx.com",
        "lookaside.facebook.com",
        "lookaside.instagram.com",
        "scontent.instagram.com",
        "cdninstagram.com",
        "tiktok.com",
        "ytimg.com",
        "youtube.com",
        # Medios dominicanos con marca de agua / derechos de autor
        "diariolibre.com",
        "listindiario.com",
        "elnacional.com.do",
        "eldia.com.do",
        "elcaribe.com.do",
        "hoy.com.do",
        "n.com.do",
        "ndigital.com.do",
        "acento.com.do",
        "elnuevodiario.com.do",
        "diariodominicano.com",
        "almomento.net",
        "noticiassin.com",
        "cdn.com.do",
        "z101digital.com",
        "remolacha.net",
        "periodicoeljaya.com",
        "proceso.com.do",
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")

    def _is_blocked(self, url: str) -> bool:
        return any(domain in url for domain in self.BLOCKED_DOMAINS)

    def search_image(self, query: str, site_filter: Optional[str] = None) -> Optional[Dict]:
        """
        Busca una imagen en Google Images via Serper.
        Si site_filter se provee, se agrega como prefijo al query (ej. "site:presidencia.gob.do OR site:prm.org.do").
        Retorna la PRIMERA imagen valida (comportamiento original, se mantiene por compatibilidad).
        """
        results = self.search_images(query, site_filter=site_filter, limit=1)
        return results[0] if results else None

    def search_images(
        self,
        query: str,
        site_filter: Optional[str] = None,
        limit: int = 5,
        exclude_sites: Optional[str] = None,
    ) -> List[Dict]:
        """
        Igual que search_image pero devuelve VARIAS imagenes validas (hasta `limit`).
        Esto permite tener URLs de respaldo si la primera falla al descargarse.

        exclude_sites: string de exclusiones estilo "-site:dominio.com -site:otro.com"
        que se agrega al final del query para que Google NO devuelva esos dominios.
        """
        if not self.api_key:
            logger.warning("SERPER_API_KEY no configurada.")
            return []

        full_query = f"({site_filter}) {query}" if site_filter else query
        if exclude_sites:
            full_query = f"{full_query} {exclude_sites}"
        found: List[Dict] = []

        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "q": full_query,
                "num": 10,
                "gl": "do",
                "hl": "es",
            }
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            images = data.get("images", [])
            for img in images:
                image_url = img.get("imageUrl", "")
                if image_url and image_url.startswith("http") and not self._is_blocked(image_url):
                    found.append({
                        "url": image_url,
                        "url_medium": image_url,
                        "source": img.get("source", "Google Images"),
                        "source_url": img.get("link", ""),
                        "alt": query,
                        "provider": "serper",
                        "title": img.get("title", ""),
                    })
                if len(found) >= limit:
                    break
        except Exception as e:
            logger.error(f"Error buscando imagen en Serper (query='{full_query[:60]}'): {e}")

        return found

    def build_image_html(self, image: Dict, caption: str = "") -> str:
        cap_text = caption or image.get("title") or image.get("alt", "")
        source_url = image.get("source_url", "")
        source_name = image.get("source", "Google Images")
        credit = (
            f'Imagen via <a href="{source_url}" target="_blank" rel="noopener">{source_name}</a>'
            if source_url else f"Imagen: {source_name}"
        )
        return (
            f'<figure class="nd-featured-image" style="margin:0 0 24px 0;padding:0;">'
            f'<img src="{image["url"]}" alt="{cap_text}" loading="lazy" '
            f'style="width:100%;max-width:680px;height:360px;object-fit:cover;display:block;border-radius:6px;" '
            f'onerror="this.parentElement.style.display=\'none\'" />'
            f'<figcaption style="font-size:12px;color:#888;margin-top:6px;font-style:italic;">'
            f'{cap_text} -- {credit}</figcaption>'
            f'</figure>'
        )


# ─────────────────────────────────────────────
# CLIENTE PEXELS (FALLBACK FINAL)
# ─────────────────────────────────────────────
class PexelsClient:
    """Fallback de imagenes cuando Serper no encuentra resultados."""

    BASE_URL = "https://api.pexels.com/v1/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY", "")

    def search_image(self, query: str, orientation: str = "landscape") -> Optional[Dict]:
        results = self.search_images(query, orientation=orientation, limit=1)
        return results[0] if results else None

    def search_images(self, query: str, orientation: str = "landscape", limit: int = 3) -> List[Dict]:
        """Devuelve varias fotos de Pexels (hasta `limit`)."""
        if not self.api_key:
            return []
        found: List[Dict] = []
        try:
            headers = {"Authorization": self.api_key}
            params = {"query": query, "per_page": max(limit, 5), "orientation": orientation}
            response = requests.get(self.BASE_URL, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            photos = response.json().get("photos", [])
            for photo in photos[:limit]:
                found.append({
                    "url": photo["src"]["large2x"],
                    "url_medium": photo["src"]["medium"],
                    "photographer": photo.get("photographer", "Pexels"),
                    "photographer_url": photo.get("photographer_url", "https://www.pexels.com"),
                    "alt": query,
                    "pexels_url": photo.get("url", "https://www.pexels.com"),
                    "provider": "pexels",
                })
        except Exception as e:
            logger.error(f"Error buscando imagen en Pexels: {e}")
        return found

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
            f'{cap_text} -- {credit}</figcaption>'
            f'</figure>'
        )


# ─────────────────────────────────────────────
# GENERADOR PRINCIPAL
# ─────────────────────────────────────────────
class ArticleGenerator:
    """Genera articulos periodisticos usando Claude + Serper Images + Pexels fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        pexels_api_key: Optional[str] = None,
        serper_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
        google_cse_id: Optional[str] = None,
    ):
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)
        self.serper = SerperImageClient(api_key=serper_api_key)
        self.pexels = PexelsClient(api_key=pexels_api_key)

    def _collect_image_candidates(
        self, query: str, caption: str, tiene_persona: bool = False
    ) -> Tuple[List[str], str]:
        """
        Estrategia de busqueda de imagenes con proteccion de identidad.

        Cuando tiene_persona=False (tema, lugar, evento):
          Nivel 1 → fuentes oficiales
          Nivel 2 → Google general (sin medios dominicanos)
          Nivel 3 → Pexels

        Cuando tiene_persona=True (titular nombra a una persona especifica):
          Nivel 1 → fuentes oficiales UNICAMENTE (identidad garantizada)
          Nivel 2 → Pexels con query generica de categoria (SIN nombre de persona)
                    para evitar devolver una foto de alguien equivocado.
          Se omite Google general porque es la fuente del error de identidad.

        Retorna (lista_de_urls, html_de_la_primera).
        """
        candidates: List[str] = []
        first_html = ""

        def _add(url: str):
            if url and url not in candidates:
                candidates.append(url)

        # NIVEL 1 — Fuentes oficiales (siempre, para todos los casos)
        logger.info(f"  Buscando en fuentes oficiales: '{query[:50]}'...")
        dom_images = self.serper.search_images(query, site_filter=OFFICIAL_SITES_QUERY, limit=5)
        for img in dom_images:
            _add(img.get("url", ""))
            if not first_html:
                first_html = self.serper.build_image_html(img, caption=caption)
        if dom_images:
            logger.info(f"  ✓ {len(dom_images)} imagen(es) oficial(es) encontrada(s)")

        if tiene_persona:
            # NIVEL 2 (persona) — Pexels con query generica, SIN nombre de persona.
            # Razon: Google general confunde identidades con personas poco conocidas.
            # Es mejor una foto generica que una foto de la persona equivocada.
            pexels_query = caption.split()[0] if caption else "politica dominicana"
            logger.info(f"  Persona detectada — omitiendo Google general para evitar confusion de identidad.")
            logger.info(f"  Usando Pexels con query generica: '{pexels_query}'...")
            pex_images = self.pexels.search_images(pexels_query, limit=3)
            for img in pex_images:
                _add(img.get("url_medium", ""))
                if not first_html:
                    first_html = self.pexels.build_image_html(img, caption=caption)
            if pex_images:
                logger.info(f"  ✓ {len(pex_images)} imagen(es) de Pexels agregada(s)")
        else:
            # NIVEL 2 (no persona) — Google general excluyendo medios dominicanos
            logger.info(f"  Buscando en Google general (sin medios locales)...")
            gen_images = self.serper.search_images(query, limit=5, exclude_sites=EXCLUDED_SITES_QUERY)
            for img in gen_images:
                _add(img.get("url", ""))
                if not first_html:
                    first_html = self.serper.build_image_html(img, caption=caption)
            if gen_images:
                logger.info(f"  ✓ {len(gen_images)} imagen(es) general(es) encontrada(s)")

            # NIVEL 3 — Pexels (red de seguridad final)
            logger.info(f"  Agregando respaldo de Pexels...")
            pex_images = self.pexels.search_images(query, limit=3)
            for img in pex_images:
                _add(img.get("url_medium", ""))
                if not first_html:
                    first_html = self.pexels.build_image_html(img, caption=caption)
            if pex_images:
                logger.info(f"  ✓ {len(pex_images)} imagen(es) de Pexels agregada(s) como respaldo")

        logger.info(f"  Total de URLs candidatas: {len(candidates)}")
        return candidates, first_html

    def _get_image_with_url(self, query: str, caption: str) -> Tuple[Optional[str], str]:
        """
        Compatibilidad: devuelve (primera_url, html) como antes.
        Internamente ahora usa la recoleccion de candidatas.
        Sin deteccion de persona (metodo legacy).
        """
        candidates, html_out = self._collect_image_candidates(query, caption, tiene_persona=False)
        first_url = candidates[0] if candidates else None
        if not first_url:
            logger.warning("  No se encontro imagen en ninguna fuente.")
        return first_url, html_out

    def _get_image(self, query: str, caption: str) -> str:
        """Retorna solo el HTML de la imagen."""
        _, image_html = self._get_image_with_url(query, caption)
        return image_html

    def generate_from_single_article(
        self,
        title: str,
        content: str,
        source: str,
        category: str,
        url: str = "",
        published_at: Optional[datetime] = None,
        wordpress_url: str = "",
    ) -> Dict:
        content_trimmed = content[:3000] if len(content) > 3000 else content
        fecha_str = fecha_en_espanol(published_at) if published_at else ""
        source_display = (
            source if source and source.lower() not in ("", "desconocido", "medio desconocido")
            else "fuente local"
        )

        prompt = f"""Redacta un articulo periodistico ORIGINAL para NeuroDiario basado en esta noticia:

DATOS DE LA FUENTE:
- Titulo original: {title}
- Medio: {source_display}
- Categoria: {category}
{f'- Fecha: {fecha_str}' if fecha_str else ''}
{f'- URL: {url}' if url else ''}

CONTENIDO FUENTE:
{content_trimmed}

IMPORTANTE: Devuelve SOLO el cuerpo en HTML. El primer elemento debe ser un <p>, NUNCA un <h1> ni el titulo repetido. WordPress coloca el titulo automaticamente. Sin comentarios. Sin Markdown."""

        try:
            article_html = self._call_api(prompt, max_tokens=2000)
            article_html = self._clean_html(article_html)
            article_html = self._remove_h1_from_html(article_html)

            image_query, tiene_persona = self._build_image_query(title, category)
            image_candidates, image_html = self._collect_image_candidates(image_query, caption=title, tiene_persona=tiene_persona)
            image_url = image_candidates[0] if image_candidates else None

            footer_html = self._build_footer(source_display, fecha_str, url)
            share_url = wordpress_url if wordpress_url else url
            share_html = self._build_share_icons(share_url)

            full_content = f"{article_html}\n{footer_html}\n{share_html}"
            clean_title = self._clean_title(title)
            excerpt = self._extract_excerpt(article_html)
            tags = [t for t in [category, source_display, "Republica Dominicana", "NeuroDiario"] if t]

            return {
                "title": clean_title,
                "content": full_content,
                "excerpt": excerpt,
                "category": category,
                "tags": tags,
                "image_url": image_url,
                "image_candidates": image_candidates,
                "source_citation": {
                    "source": source_display,
                    "url": url,
                    "published_at": published_at,
                },
            }
        except Exception as e:
            logger.error(f"Error generando articulo: {e}")
            raise

    def create_article(self, trend: Dict, articles: List[Dict]) -> Dict:
        articles = articles[:5]
        sources_text = self._format_sources(articles)
        topic = trend.get("topic", "")
        category = trend.get("category", "general")

        source_names = list({a.get("source", "") for a in articles if a.get("source")})
        source_names = [s for s in source_names if s.lower() not in ("", "desconocido", "medio desconocido")]
        sources_citation = ", ".join(source_names[:3]) if source_names else "medios locales"

        prompt = f"""Redacta un articulo periodistico ORIGINAL sobre el tema '{topic}' para NeuroDiario.

FUENTES BASE:
{sources_text}

MEDIOS CONSULTADOS: {sources_citation}
CATEGORIA: {category}

IMPORTANTE: Devuelve SOLO el cuerpo en HTML. El primer elemento debe ser un <p>, NUNCA un <h1>. Sin comentarios. Sin Markdown."""

        try:
            article_html = self._call_api(prompt, max_tokens=2500)
            article_html = self._clean_html(article_html)
            article_html = self._remove_h1_from_html(article_html)

            image_query, tiene_persona = self._build_image_query(topic, category)
            image_candidates, image_html = self._collect_image_candidates(image_query, caption=topic, tiene_persona=tiene_persona)
            image_url = image_candidates[0] if image_candidates else None

            fecha_str = fecha_en_espanol(datetime.now())
            footer_html = self._build_footer(sources_citation, fecha_str, "")
            share_html = self._build_share_icons("")
            full_content = f"{article_html}\n{footer_html}\n{share_html}"

            return {
                "title": self._clean_title(topic),
                "content": full_content,
                "excerpt": self._extract_excerpt(article_html),
                "category": category,
                "tags": [category, "Republica Dominicana", "NeuroDiario"],
                "image_url": image_url,
                "image_candidates": image_candidates,
                "sources": [a.get("url", "") for a in articles if a.get("url")],
            }
        except Exception as e:
            logger.error(f"Error generando articulo desde tendencia: {e}")
            raise

    def generate_digest(self, trends: List[Dict]) -> str:
        trends_text = "\n".join(
            f"- {t['topic']} ({t.get('article_count', 0)} articulos)" for t in trends[:5]
        )
        prompt = f"""Redacta un boletin periodistico diario para NeuroDiario.

TENDENCIAS DEL DIA:
{trends_text}

FORMATO HTML: <h2> titulo, <p> introduccion, un <h2> y <p> por tendencia, <p> cierre.
Extension: 400-600 palabras. Devuelve SOLO HTML. Sin <h1>."""
        return self._call_api(prompt)

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

    def _build_image_query(self, title: str, category: str) -> Tuple[str, bool]:
        """
        Genera la query de imagen y detecta si el titular nombra una persona especifica.

        Retorna (query, tiene_persona):
        - query: string de busqueda para Google Images
        - tiene_persona: True si el titular menciona un nombre propio de persona.
          Cuando es True, _collect_image_candidates restringe la busqueda a fuentes
          oficiales para evitar confundir identidades.

        Razon del cambio: Google Images puede devolver la foto equivocada cuando se
        busca por nombre de persona poco conocida. Las fuentes oficiales
        (gobierno, congreso, partidos) garantizan que la foto corresponde a quien
        dice el pie de foto.
        """
        category_fallbacks = {
            "politica":      "gobierno Republica Dominicana politica",
            "economia":      "economia negocios finanzas dominicana",
            "deportes":      "deportes atletas Republica Dominicana",
            "internacional": "noticias internacionales mundo",
            "tecnologia":    "tecnologia innovacion digital",
            "sociedad":      "comunidad personas sociedad dominicana",
            "salud":         "salud medicina hospital dominicano",
            "cultura":       "cultura artes entretenimiento dominicano",
            "educacion":     "educacion escuela universidad dominicana",
        }
        fallback = category_fallbacks.get(category.lower(), "Republica Dominicana noticias")

        try:
            prompt = f"""Dado este titular de noticia: "{title}"
Categoria: {category}

Responde en DOS lineas exactas, sin explicacion adicional:
Linea 1: La query de busqueda (4-6 palabras para Google Images)
Linea 2: PERSONA o NO_PERSONA (si el titular nombra a una persona real especifica)

REGLAS para la query:
- Si menciona una persona famosa dominicana o internacional, incluye su nombre completo
- Si menciona un lugar en Republica Dominicana, incluyelo
- Prioriza terminos en espanol

EJEMPLOS:
Titular: "Abinader anuncia reforma fiscal"
Luis Abinader presidente Republica Dominicana 2026
PERSONA

Titular: "Huracan amenaza el Caribe"
huracan tormenta caribe Republica Dominicana
NO_PERSONA

Titular: "Tigres del Licey ganan campeonato"
Tigres Licey beisbol dominicano campeones
NO_PERSONA

Titular: "Ginnette Bournigal defiende la Policia"
Ginnette Bournigal senadora dominicana
PERSONA

Titular: "COE alerta por inundaciones en el pais"
inundaciones Santo Domingo Republica Dominicana
NO_PERSONA"""

            respuesta = self._call_api(prompt, max_tokens=40).strip()
            lineas = [l.strip() for l in respuesta.split("\n") if l.strip()]

            query = lineas[0].strip('"').strip("'").strip(".") if lineas else fallback
            tiene_persona = len(lineas) >= 2 and "PERSONA" in lineas[1].upper() and "NO_PERSONA" not in lineas[1].upper()

            if not (3 <= len(query) <= 100):
                query = fallback
                tiene_persona = False

            logger.info(f"  Query imagen: '{query}' | persona_detectada={tiene_persona}")
            return query, tiene_persona

        except Exception as e:
            logger.warning(f"Error generando query de imagen: {e}")
            return fallback, False

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
            parts.append(f'<span class="nd-source-date"> - {fecha}</span>')
        if url_html:
            parts.append(f'<span class="nd-source-link"> - {url_html}</span>')
        parts.append('</div>')
        return "\n".join(parts)

    def _build_share_icons(self, share_url: str) -> str:
        encoded_url = requests.utils.quote(share_url, safe="") if share_url else ""

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
                f"[Fuente {i}] {article.get('title', 'Sin titulo')}\n"
                f"Medio: {source}\n"
                f"URL: {article.get('url', '')}\n"
                f"Contenido: {article.get('raw_content', '')[:500]}..."
            )
        return "\n\n".join(parts)

    def _replace_share_url(self, content: str, wordpress_url: str) -> str:
        """Reemplaza la URL en los botones de compartir con la URL real de WordPress."""
        encoded = requests.utils.quote(wordpress_url, safe="")
        content = re.sub(
            r'(sharer\.php\?u=|intent/tweet\?url=|wa\.me/\?text=)[^"]*',
            lambda m: m.group(1) + encoded,
            content
        )
        return content
