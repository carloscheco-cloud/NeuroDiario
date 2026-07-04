"""
Módulo de ingesta de noticias RSS.
Lee feeds de medios dominicanos y extrae artículos para su procesamiento.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

import feedparser
import requests

from .sources_config import SOURCES, FETCH_TIMEOUT, MAX_ARTICLES_PER_SOURCE

logger = logging.getLogger(__name__)

# User-Agent de browser real para fuentes que bloquean bots (ej. N Digital con Cloudflare)
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

BROWSER_HEADERS = {
    "User-Agent": BROWSER_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}


class RSSFetcher:
    """Obtiene y normaliza artículos desde feeds RSS de medios dominicanos."""

    def __init__(self, sources_config: Optional[List[Dict]] = None):
        self.sources = sources_config or SOURCES
        self.timeout = FETCH_TIMEOUT
        self.max_articles = MAX_ARTICLES_PER_SOURCE

    def fetch_feed(self, source: Dict) -> List[Dict]:
        articles = []
        try:
            response = requests.get(
                source["url"],
                headers=BROWSER_HEADERS,  # Browser UA — funciona para todos los sitios
                timeout=self.timeout,
            )
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if feed.bozo:
                logger.warning(f"Feed con errores de parseo: {source['name']}")

            limit = source.get("max_articles", self.max_articles)
            for entry in feed.entries[:limit]:
                article = self._normalize_entry(entry, source)
                if article:
                    articles.append(article)

            logger.info(f"Obtenidos {len(articles)} artículos de {source['name']}")
        except Exception as e:
            logger.error(f"Error al obtener feed de {source['name']}: {e}")

        return articles

    def fetch_articles(self) -> List[Dict]:
        all_articles = []
        active_sources = [s for s in self.sources if s.get("active", True)]

        for source in active_sources:
            articles = self.fetch_feed(source)
            all_articles.extend(articles)

        logger.info(f"Total artículos obtenidos: {len(all_articles)}")
        return all_articles

    def _extract_image(self, entry) -> Optional[str]:
        """Extrae la URL de imagen del entry RSS probando múltiples formatos."""
        # Método 1: media_content (Diario Libre, El Nacional)
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if media.get('url'):
                    return media['url']
        # Método 2: enclosures
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get('type', '').startswith('image'):
                    return enc.get('href') or enc.get('url')
        # Método 3: media_thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url')
        return None

    def _normalize_entry(self, entry, source: Dict) -> Optional[Dict]:
        try:
            return {
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", ""),
                "summary": entry.get("summary", ""),
                "published_at": self._parse_date(entry),
                "source_name": source["name"],
                "source_url": source["url"],
                "category": source.get("category", "general"),
                "language": source.get("language", "es"),
                "raw_content": "",  # Se llena en ArticleParser
                "image_url": self._extract_image(entry),
            }
        except Exception as e:
            logger.error(f"Error normalizando entrada: {e}")
            return None

    def _parse_date(self, entry) -> datetime:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        return datetime.utcnow()

    def save_to_db(self, articles: List[Dict], db_session) -> int:
        from neurodiario.db.models import Article, Source

        saved = 0
        source_cache: Dict[str, int] = {}

        for data in articles:
            url = data.get("url", "").strip()
            if not url:
                continue

            if db_session.query(Article.id).filter(Article.url == url).first():
                continue

            source_name = data.get("source_name", "")
            source_url = data.get("source_url", "")
            if source_name not in source_cache:
                source_row = db_session.query(Source).filter(Source.name == source_name).first()
                if not source_row:
                    source_row = Source(
                        name=source_name,
                        url=source_url,
                        category=data.get("category", "general"),
                        language=data.get("language", "es"),
                    )
                    db_session.add(source_row)
                    db_session.flush()
                source_cache[source_name] = source_row.id

            article = Article(
                title=data.get("title", "Sin título"),
                url=url,
                summary=data.get("summary") or None,
                raw_html=data.get("raw_html") or None,
                raw_content=data.get("raw_content", ""),
                word_count=data.get("word_count", 0),
                published_at=data.get("published_at"),
                source_id=source_cache.get(source_name),
                image_url=data.get("image_url") or None,
            )
            db_session.add(article)
            saved += 1

        db_session.commit()
        logger.info(f"Artículos nuevos guardados: {saved}")
        return saved
