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

        Args:
            articles: Lista de artículos a guardar.
            db_session: Sesión activa de SQLAlchemy.

        Returns:
            Número de artículos nuevos insertados.
        """
        # TODO: Implementar lógica de upsert usando db/models.py
        # from neurodiario.db.models import Article
        # saved = 0
        # for data in articles:
        #     if not db_session.query(Article).filter_by(url=data["url"]).first():
        #         db_session.add(Article(**data))
        #         saved += 1
        # db_session.commit()
        # return saved
        raise NotImplementedError("save_to_db aún no está implementado")
