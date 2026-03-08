"""
Paquete de ingesta de noticias.
Contiene módulos para obtener y parsear artículos de medios dominicanos.
"""

from .rss_fetcher import RSSFetcher
from .article_parser import ArticleParser
from .sources_config import SOURCES

__all__ = ["RSSFetcher", "ArticleParser", "SOURCES"]
