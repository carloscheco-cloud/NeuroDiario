"""
Tests para los módulos de procesamiento de lenguaje natural (NLP).
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from neurodiario.nlp.text_cleaner import TextCleaner
from neurodiario.nlp.classifier import ArticleClassifier
from neurodiario.nlp.trend_detector import TrendDetector


class TestTextCleaner:
    """Tests para TextCleaner."""

    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_clean_empty_string(self):
        """clean debe retornar cadena vacía para entrada vacía."""
        assert self.cleaner.clean("") == ""
        assert self.cleaner.clean(None) == ""

    def test_removes_html_tags(self):
        """clean debe eliminar etiquetas HTML."""
        result = self.cleaner.clean("<p>Hola <b>mundo</b></p>")
        assert "<p>" not in result
        assert "<b>" not in result
        assert "Hola" in result

    def test_removes_urls_when_enabled(self):
        """clean debe eliminar URLs cuando remove_urls=True."""
        cleaner = TextCleaner(remove_urls=True)
        result = cleaner.clean("Visita https://example.com para más info")
        assert "https://example.com" not in result
        assert "Visita" in result

    def test_keeps_urls_when_disabled(self):
        """clean no debe eliminar URLs cuando remove_urls=False."""
        cleaner = TextCleaner(remove_urls=False)
        text = "Visita https://example.com para más info"
        result = cleaner.clean(text)
        assert "https://example.com" in result

    def test_removes_emails(self):
        """clean debe eliminar correos electrónicos."""
        result = self.cleaner.clean("Contáctanos en info@neurodiario.com para consultas")
        assert "info@neurodiario.com" not in result

    def test_normalizes_whitespace(self):
        """clean debe normalizar múltiples espacios en uno."""
        result = self.cleaner.clean("Texto   con    muchos     espacios")
        assert "  " not in result

    def test_lowercase_option(self):
        """clean debe convertir a minúsculas cuando lowercase=True."""
        cleaner = TextCleaner(lowercase=True)
        result = cleaner.clean("HOLA MUNDO")
        assert result == "hola mundo"

    def test_preserves_spanish_chars(self):
        """clean debe preservar caracteres especiales del español."""
        text = "ÁrbolÉxico con ñoño y üñ"
        result = self.cleaner.clean(text)
        assert "ñ" in result

    def test_clean_batch(self):
        """clean_batch debe procesar una lista de textos."""
        texts = ["<p>Hola</p>", "  Mundo  ", ""]
        results = self.cleaner.clean_batch(texts)
        assert len(results) == 3
        assert results[0] == "Hola"
        assert results[1] == "Mundo"
        assert results[2] == ""

    def test_extract_sentences(self):
        """extract_sentences debe dividir el texto en oraciones."""
        text = "Primera oración larga aquí. Segunda oración también larga. Tercera."
        sentences = self.cleaner.extract_sentences(text)
        assert isinstance(sentences, list)
        assert len(sentences) >= 1


class TestArticleClassifier:
    """Tests para ArticleClassifier."""

    def setup_method(self):
        self.classifier = ArticleClassifier(method="keyword")

    def test_classify_returns_tuple(self):
        """classify debe retornar una tupla (categoría, confianza)."""
        result = self.classifier.classify("El presidente firmó un decreto", "Decreto presidencial")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_classify_political_article(self):
        """Artículos políticos deben clasificarse como 'politica'."""
        text = "El presidente del gobierno firmó un decreto en el congreso con el partido opositor"
        category, confidence = self.classifier.classify(text, "Nuevo decreto presidencial")
        assert category == "politica"
        assert 0 < confidence <= 1.0

    def test_classify_sports_article(self):
        """Artículos deportivos deben clasificarse como 'deportes'."""
        text = "El equipo de béisbol ganó el campeonato del torneo con un gol en el último inning"
        category, confidence = self.classifier.classify(text, "Victoria en el béisbol")
        assert category == "deportes"

    def test_classify_returns_general_for_empty_text(self):
        """Texto vacío debe clasificarse como 'general' con confianza 0."""
        category, confidence = self.classifier.classify("", "")
        assert category == "general"
        assert confidence == 0.0

    def test_confidence_between_zero_and_one(self):
        """La confianza debe estar siempre en el rango [0, 1]."""
        text = "Noticia genérica con información variada sobre múltiples temas"
        _, confidence = self.classifier.classify(text, "Noticia")
        assert 0.0 <= confidence <= 1.0

    def test_classify_batch_adds_keys(self):
        """classify_batch debe añadir 'category' y 'category_confidence' a cada artículo."""
        articles = [
            {"title": "Partido político", "raw_content": "El presidente y el gobierno"},
            {"title": "Deporte dominicano", "raw_content": "Béisbol y campeonato"},
        ]
        result = self.classifier.classify_batch(articles)
        for article in result:
            assert "category" in article
            assert "category_confidence" in article

    def test_unsupported_method_raises(self):
        """Método no implementado debe lanzar NotImplementedError."""
        classifier = ArticleClassifier(method="ml")
        with pytest.raises(NotImplementedError):
            classifier.classify("texto", "título")


class TestTrendDetector:
    """Tests para TrendDetector."""

    def setup_method(self):
        self.detector = TrendDetector(window_hours=24, top_n=5)

    def _make_article(self, entities=None, category="general", hours_ago=0):
        return {
            "title": "Test Article",
            "url": "https://example.com/article",
            "category": category,
            "entities": entities or {"persona": [], "organización": []},
            "published_at": datetime.utcnow() - timedelta(hours=hours_ago),
        }

    def test_detect_returns_list(self):
        """detect debe retornar una lista."""
        result = self.detector.detect([])
        assert isinstance(result, list)

    def test_detect_finds_frequent_entities(self):
        """detect debe identificar entidades frecuentes."""
        articles = [
            self._make_article(entities={"persona": ["Luis Abinader"], "organización": []}),
            self._make_article(entities={"persona": ["Luis Abinader"], "organización": ["Gobierno"]}),
            self._make_article(entities={"persona": ["Luis Abinader"], "organización": []}),
        ]
        trends = self.detector.detect(articles)
        topics = [t["topic"] for t in trends]
        assert "Luis Abinader" in topics

    def test_detect_respects_top_n(self):
        """detect no debe retornar más de top_n tendencias."""
        articles = [
            self._make_article(entities={"persona": [f"Persona {i}"]})
            for i in range(20)
        ]
        trends = self.detector.detect(articles)
        assert len(trends) <= self.detector.top_n

    def test_filter_recent_excludes_old_articles(self):
        """_filter_recent debe excluir artículos fuera de la ventana de tiempo."""
        old = self._make_article(hours_ago=48)
        recent = self._make_article(hours_ago=1)
        result = self.detector._filter_recent([old, recent])
        assert len(result) == 1
        assert result[0] == recent

    def test_get_trending_categories(self):
        """get_trending_categories debe retornar lista de tuplas (categoría, conteo)."""
        articles = [
            self._make_article(category="politica"),
            self._make_article(category="politica"),
            self._make_article(category="deportes"),
        ]
        result = self.detector.get_trending_categories(articles)
        assert isinstance(result, list)
        assert result[0][0] == "politica"
        assert result[0][1] == 2
