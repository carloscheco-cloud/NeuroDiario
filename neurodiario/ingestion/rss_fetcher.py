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


class RSSFetcher:
    """Obtiene y normaliza artículos desde feeds RSS de medios dominicanos."""

    def __init__(self, sources_config: Optional[List[Dict]] = None):
        """
        Inicializa el fetcher con la configuración de fuentes.

        Args:
            sources_config: Lista de fuentes a usar. Si es None, usa SOURCES por defecto.
        """
        self.sources = sources_config or SOURCES
        self.timeout = FETCH_TIMEOUT
        self.max_articles = MAX_ARTICLES_PER_SOURCE

    def fetch_feed(self, source: Dict) -> List[Dict]:
        """
        Obtiene artículos de un feed RSS individual.

        Args:
            source: Diccionario con metadatos de la fuente (url, name, category...).

        Returns:
            Lista de artículos normalizados como diccionarios.
        """
        articles = []
        try:
            feed = feedparser.parse(source["url"], request_headers={"User-Agent": "NeuroDiario/1.0"})
            if feed.bozo:
                logger.warning(f"Feed con errores de parseo: {source['name']}")

            for entry in feed.entries[: self.max_articles]:
                article = self._normalize_entry(entry, source)
                if article:
                    articles.append(article)

            logger.info(f"Obtenidos {len(articles)} artículos de {source['name']}")
        except Exception as e:
            logger.error(f"Error al obtener feed de {source['name']}: {e}")

        return articles

    def fetch_articles(self) -> List[Dict]:
        """
        Obtiene artículos de todas las fuentes activas.

        Returns:
            Lista combinada de artículos de todas las fuentes.
        """
        all_articles = []
        active_sources = [s for s in self.sources if s.get("active", True)]

        for source in active_sources:
            articles = self.fetch_feed(source)
            all_articles.extend(articles)

        logger.info(f"Total artículos obtenidos: {len(all_articles)}")
        return all_articles

    def _normalize_entry(self, entry, source: Dict) -> Optional[Dict]:
        """
        Normaliza una entrada de feed RSS al formato interno.

        Args:
            entry: Entrada del feed parseada por feedparser.
            source: Metadatos de la fuente.

        Returns:
            Diccionario con el artículo normalizado, o None si no es válido.
        """
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
            }
        except Exception as e:
            logger.error(f"Error normalizando entrada: {e}")
            return None

    def _parse_date(self, entry) -> datetime:
        """Extrae y convierte la fecha de publicación de una entrada."""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        return datetime.utcnow()

    def save_to_db(self, articles: List[Dict], db_session) -> int:
        """
        Guarda artículos en la base de datos, evitando duplicados por URL.

        Busca o crea la fila Source correspondiente a cada artículo y luego
        inserta el artículo solo si su URL todavía no existe en la tabla.

        Args:
            articles: Lista de artículos normalizados (salida de fetch_articles).
            db_session: Sesión activa de SQLAlchemy.

        Returns:
            Número de artículos nuevos insertados.
        """
        from neurodiario.db.models import Article, Source

        saved = 0
        # Cache local para evitar una consulta por cada artículo del mismo medio
        source_cache: Dict[str, int] = {}

        for data in articles:
            url = data.get("url", "").strip()
            if not url:
                continue

            # Saltar si ya existe en BD
            if db_session.query(Article.id).filter(Article.url == url).first():
                continue

            # Resolver source_id
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
                    db_session.flush()  # obtener el id sin commit
                source_cache[source_name] = source_row.id

            article = Article(
                title=data.get("title", "Sin título"),
                url=url,
                summary=data.get("summary", ""),
                raw_content=data.get("raw_content", ""),
                word_count=data.get("word_count", 0),
                published_at=data.get("published_at"),
                source_id=source_cache.get(source_name),
            )
            db_session.add(article)
            saved += 1

        db_session.commit()
        logger.info(f"Artículos nuevos guardados: {saved}")
        return saved
