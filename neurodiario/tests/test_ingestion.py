"""
Tests para el módulo de ingesta de noticias.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from neurodiario.ingestion.rss_fetcher import RSSFetcher
from neurodiario.ingestion.article_parser import ArticleParser
from neurodiario.ingestion.sources_config import SOURCES, VALID_CATEGORIES


class TestRSSFetcher:
    """Tests para RSSFetcher."""

    def setup_method(self):
        self.test_sources = [
            {
                "name": "Test Source",
                "url": "https://example.com/rss",
                "category": "general",
                "language": "es",
                "active": True,
            }
        ]
        self.fetcher = RSSFetcher(sources_config=self.test_sources)

    def test_init_with_custom_sources(self):
        """El fetcher debe inicializarse con las fuentes proporcionadas."""
        assert self.fetcher.sources == self.test_sources

    def test_init_with_default_sources(self):
        """El fetcher debe usar SOURCES por defecto si no se proveen fuentes."""
        fetcher = RSSFetcher()
        assert fetcher.sources == SOURCES

    def test_fetch_articles_returns_list(self):
        """fetch_articles debe devolver una lista."""
        with patch.object(self.fetcher, "fetch_feed", return_value=[]):
            result = self.fetcher.fetch_articles()
        assert isinstance(result, list)

    def test_fetch_feed_handles_error(self):
        """fetch_feed debe manejar errores y devolver lista vacía."""
        bad_source = {"name": "Bad", "url": "http://invalid-url-xyz.com/rss", "active": True}
        with patch("feedparser.parse", side_effect=Exception("Network error")):
            result = self.fetcher.fetch_feed(bad_source)
        assert result == []

    def test_normalize_entry_valid(self):
        """_normalize_entry debe retornar un diccionario con las claves esperadas."""
        mock_entry = MagicMock()
        mock_entry.get = lambda key, default="": {
            "title": "Test Title",
            "link": "https://example.com/article",
            "summary": "Summary text",
        }.get(key, default)
        mock_entry.published_parsed = None

        result = self.fetcher._normalize_entry(mock_entry, self.test_sources[0])

        assert result is not None
        assert "title" in result
        assert "url" in result
        assert "source_name" in result
        assert result["source_name"] == "Test Source"

    def test_parse_date_fallback(self):
        """_parse_date debe retornar datetime actual si no hay fecha."""
        mock_entry = MagicMock()
        mock_entry.published_parsed = None
        del mock_entry.published_parsed

        result = self.fetcher._parse_date(mock_entry)
        assert isinstance(result, datetime)

    def test_save_to_db_not_implemented(self):
        """save_to_db debe lanzar NotImplementedError."""
        with pytest.raises(NotImplementedError):
            self.fetcher.save_to_db([], MagicMock())


class TestArticleParser:
    """Tests para ArticleParser."""

    def setup_method(self):
        self.parser = ArticleParser(timeout=5)

    def test_parse_article_without_url(self):
        """parse debe devolver el artículo sin cambios si no tiene URL."""
        article = {"title": "Test", "url": ""}
        result = self.parser.parse(article)
        assert result["url"] == ""

    def test_parse_batch_returns_same_count(self):
        """parse_batch debe devolver la misma cantidad de artículos."""
        articles = [{"url": ""}, {"url": ""}]
        result = self.parser.parse_batch(articles)
        assert len(result) == len(articles)

    def test_extract_text_removes_scripts(self):
        """_extract_text debe eliminar etiquetas script y style."""
        html = "<html><head><script>alert('x')</script></head><body><p>Contenido real</p></body></html>"
        result = self.parser._extract_text(html)
        assert "alert" not in result
        assert "Contenido real" in result

    def test_fetch_content_handles_network_error(self):
        """_fetch_content debe devolver cadena vacía ante errores de red."""
        with patch.object(self.parser.session, "get", side_effect=Exception("timeout")):
            result = self.parser._fetch_content("https://example.com")
        assert result == ""


class TestSourcesConfig:
    """Tests para la configuración de fuentes."""

    def test_sources_is_list(self):
        assert isinstance(SOURCES, list)

    def test_sources_not_empty(self):
        assert len(SOURCES) > 0

    def test_sources_have_required_keys(self):
        required_keys = {"name", "url", "category", "language", "active"}
        for source in SOURCES:
            assert required_keys.issubset(source.keys()), f"Fuente incompleta: {source}"

    def test_valid_categories_not_empty(self):
        assert len(VALID_CATEGORIES) > 0

    def test_source_categories_are_valid(self):
        for source in SOURCES:
            assert source["category"] in VALID_CATEGORIES, (
                f"Categoría inválida '{source['category']}' en fuente '{source['name']}'"
            )
