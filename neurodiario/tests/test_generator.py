"""
Tests básicos para el Módulo 5 — Generación de artículos.

Valida que ArticleGenerator.create_article() devuelve la estructura correcta
sin realizar llamadas reales a la API de Claude (usa mocks).
"""

import re
from unittest.mock import MagicMock, patch

import pytest

from neurodiario.generator.article_generator import ArticleGenerator


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

SAMPLE_TREND = {
    "topic": "Reforma fiscal entra en debate nacional",
    "article_count": 5,
    "sources": ["Listín Diario", "Diario Libre", "El Caribe"],
}

SAMPLE_ARTICLES = [
    {
        "title": "Congreso debate propuesta de reforma fiscal",
        "url": "https://listindiario.com/reforma-fiscal-1",
        "content": "El Congreso Nacional inició este martes el debate sobre la propuesta "
                   "de reforma fiscal presentada por el Poder Ejecutivo.",
    },
    {
        "title": "Empresarios rechazan nuevos impuestos",
        "url": "https://diariolibre.com/reforma-fiscal-2",
        "content": "El sector empresarial expresó su rechazo a varios de los puntos "
                   "incluidos en el proyecto de reforma tributaria.",
    },
    {
        "title": "Economistas analizan impacto de reforma",
        "url": "https://elcaribe.com.do/reforma-fiscal-3",
        "content": "Expertos económicos evaluaron los posibles efectos de la reforma "
                   "fiscal propuesta por el gobierno dominicano.",
    },
]

# Respuesta simulada de Claude con la estructura de secciones
MOCK_CLAUDE_RESPONSE = """## TÍTULO
Reforma fiscal entra en debate nacional con posturas divididas

## RESUMEN
El Congreso Nacional inició el debate sobre la propuesta de reforma fiscal del Ejecutivo. Empresarios y economistas expresan posiciones encontradas sobre su impacto.

## CONTEXTO
La propuesta de reforma fiscal fue presentada por el Poder Ejecutivo como parte de los esfuerzos por modernizar el sistema tributario dominicano.

## DETALLE
El Congreso Nacional inició este martes el debate formal sobre la propuesta. El sector empresarial, representado por diversas cámaras de comercio, expresó su rechazo a varios artículos del proyecto. Economistas consultados señalaron efectos mixtos sobre la economía.

## ANÁLISIS
La reforma fiscal representa uno de los debates más importantes del año legislativo. La discusión refleja tensiones entre la necesidad de aumentar la recaudación del Estado y las preocupaciones del sector productivo.
"""


# ------------------------------------------------------------------ #
#  Tests de ArticleGenerator.create_article()                         #
# ------------------------------------------------------------------ #

class TestCreateArticle:
    """Valida que create_article devuelve la estructura y tipos correctos."""

    @patch("anthropic.Anthropic")
    def test_returns_dict_with_required_keys(self, mock_anthropic_cls):
        """El resultado debe ser un dict con title, summary, content, sources."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=MOCK_CLAUDE_RESPONSE)]
        )

        generator = ArticleGenerator(api_key="test-key")
        result = generator.create_article(SAMPLE_TREND, SAMPLE_ARTICLES)

        assert isinstance(result, dict), "El resultado debe ser un diccionario"
        assert "title" in result, "Debe incluir la clave 'title'"
        assert "summary" in result, "Debe incluir la clave 'summary'"
        assert "content" in result, "Debe incluir la clave 'content'"
        assert "sources" in result, "Debe incluir la clave 'sources'"

    @patch("anthropic.Anthropic")
    def test_title_is_non_empty_string(self, mock_anthropic_cls):
        """El título debe ser una cadena no vacía."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=MOCK_CLAUDE_RESPONSE)]
        )

        generator = ArticleGenerator(api_key="test-key")
        result = generator.create_article(SAMPLE_TREND, SAMPLE_ARTICLES)

        assert isinstance(result["title"], str)
        assert len(result["title"]) > 0, "El título no debe estar vacío"

    @patch("anthropic.Anthropic")
    def test_summary_is_string(self, mock_anthropic_cls):
        """El resumen debe ser una cadena."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=MOCK_CLAUDE_RESPONSE)]
        )

        generator = ArticleGenerator(api_key="test-key")
        result = generator.create_article(SAMPLE_TREND, SAMPLE_ARTICLES)

        assert isinstance(result["summary"], str)

    @patch("anthropic.Anthropic")
    def test_content_is_non_empty_string(self, mock_anthropic_cls):
        """El contenido debe ser una cadena no vacía."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=MOCK_CLAUDE_RESPONSE)]
        )

        generator = ArticleGenerator(api_key="test-key")
        result = generator.create_article(SAMPLE_TREND, SAMPLE_ARTICLES)

        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0, "El contenido no debe estar vacío"

    @patch("anthropic.Anthropic")
    def test_sources_is_list_of_urls(self, mock_anthropic_cls):
        """Las fuentes deben ser una lista con las URLs de los artículos de entrada."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=MOCK_CLAUDE_RESPONSE)]
        )

        generator = ArticleGenerator(api_key="test-key")
        result = generator.create_article(SAMPLE_TREND, SAMPLE_ARTICLES)

        assert isinstance(result["sources"], list)
        expected_urls = [a["url"] for a in SAMPLE_ARTICLES]
        assert result["sources"] == expected_urls

    @patch("anthropic.Anthropic")
    def test_title_parsed_from_section(self, mock_anthropic_cls):
        """El título debe extraerse correctamente de la sección ## TÍTULO."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=MOCK_CLAUDE_RESPONSE)]
        )

        generator = ArticleGenerator(api_key="test-key")
        result = generator.create_article(SAMPLE_TREND, SAMPLE_ARTICLES)

        assert "reforma fiscal" in result["title"].lower()

    @patch("anthropic.Anthropic")
    def test_api_called_once(self, mock_anthropic_cls):
        """La API debe llamarse exactamente una vez por invocación."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=MOCK_CLAUDE_RESPONSE)]
        )

        generator = ArticleGenerator(api_key="test-key")
        generator.create_article(SAMPLE_TREND, SAMPLE_ARTICLES)

        mock_client.messages.create.assert_called_once()


# ------------------------------------------------------------------ #
#  Tests de _parse_article_response()                                 #
# ------------------------------------------------------------------ #

class TestParseArticleResponse:
    """Valida el parseador interno de la respuesta estructurada de Claude."""

    def setup_method(self):
        with patch("anthropic.Anthropic"):
            self.generator = ArticleGenerator(api_key="test-key")

    def test_extracts_title(self):
        result = self.generator._parse_article_response(MOCK_CLAUDE_RESPONSE, SAMPLE_ARTICLES)
        assert "reforma fiscal" in result["title"].lower()

    def test_extracts_summary(self):
        result = self.generator._parse_article_response(MOCK_CLAUDE_RESPONSE, SAMPLE_ARTICLES)
        assert len(result["summary"]) > 10

    def test_content_contains_body_sections(self):
        result = self.generator._parse_article_response(MOCK_CLAUDE_RESPONSE, SAMPLE_ARTICLES)
        # El contenido debe incluir al menos una de las secciones del cuerpo
        assert any(
            keyword in result["content"].lower()
            for keyword in ["contexto", "detalle", "análisis", "congreso", "reforma"]
        )

    def test_fallback_title_when_section_missing(self):
        """Si no hay sección TÍTULO, el fallback debe ser 'Sin título'."""
        raw_without_title = "Texto sin sección de título definida."
        result = self.generator._parse_article_response(raw_without_title, [])
        assert result["title"] == "Sin título"

    def test_sources_from_input_articles(self):
        result = self.generator._parse_article_response(MOCK_CLAUDE_RESPONSE, SAMPLE_ARTICLES)
        assert result["sources"] == [a["url"] for a in SAMPLE_ARTICLES]

    def test_empty_sources_when_no_articles(self):
        result = self.generator._parse_article_response(MOCK_CLAUDE_RESPONSE, [])
        assert result["sources"] == []
