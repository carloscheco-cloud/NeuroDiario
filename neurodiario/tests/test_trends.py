"""
Tests para el Módulo 4 — Detección de Tendencias.

Valida:
  - TopicClusterer agrupa artículos en clusters.
  - TrendDetector.detect_trends() detecta temas con suficiente volumen y fuentes.
"""

import pytest
from unittest.mock import MagicMock, patch

from neurodiario.nlp.trend_detector import TrendDetector


# ------------------------------------------------------------------ #
#  Fixtures de datos                                                  #
# ------------------------------------------------------------------ #

def make_article(title: str, content: str, source_name: str) -> dict:
    """Crea un artículo de prueba en formato dict."""
    return {
        "title": title,
        "content": content,
        "source_name": source_name,
        "url": f"https://example.com/{title.replace(' ', '-').lower()}",
    }


LICENCIAS_ARTICLES = [
    make_article("Intrant suspende licencias vencidas", "El Intrant suspendió licencias vencidas.", "Listín Diario"),
    make_article("Licencias de conducir: nuevos requisitos", "Nuevos requisitos para licencias.", "Hoy"),
    make_article("Operativo de licencias en Santo Domingo", "Operativo de inspección de licencias.", "Diario Libre"),
    make_article("Intrant emite nuevas placas", "El Intrant emite nuevas placas.", "Hoy"),
]

FISCAL_ARTICLES = [
    make_article("Reforma fiscal impactará clase media", "La reforma fiscal afecta la clase media.", "El Caribe"),
    make_article("Congreso debate reforma fiscal", "Congreso Nacional debate nueva reforma.", "Listín Diario"),
    make_article("Impuestos subirán con reforma fiscal", "Los impuestos aumentarán.", "El Caribe"),
]


# ------------------------------------------------------------------ #
#  Tests de TopicClusterer                                            #
# ------------------------------------------------------------------ #

class TestTopicClusterer:
    """Tests para TopicClusterer con mock del modelo de embeddings."""

    def _make_clusterer_with_mock(self):
        """Crea un TopicClusterer con el modelo de embeddings mockeado."""
        import numpy as np
        from neurodiario.nlp.topic_cluster import TopicClusterer

        with patch("neurodiario.nlp.topic_cluster.SentenceTransformer") as mock_st:
            # Simular embeddings distintos para dos grupos de artículos
            n_licencias = len(LICENCIAS_ARTICLES)
            n_fiscal = len(FISCAL_ARTICLES)
            total = n_licencias + n_fiscal

            # Grupo 1 cerca de (1, 0, 0...), grupo 2 cerca de (0, 1, 0...)
            embeddings = np.zeros((total, 10))
            embeddings[:n_licencias, 0] = 1.0
            embeddings[n_licencias:, 1] = 1.0

            mock_instance = MagicMock()
            mock_instance.encode.return_value = embeddings
            mock_st.return_value = mock_instance

            clusterer = TopicClusterer(model_name="mock-model")
        return clusterer

    def test_cluster_returns_list(self):
        """cluster_articles debe retornar una lista."""
        clusterer = self._make_clusterer_with_mock()
        result = clusterer.cluster_articles(LICENCIAS_ARTICLES + FISCAL_ARTICLES, method="kmeans", n_clusters=2)
        assert isinstance(result, list)

    def test_cluster_produces_groups(self):
        """cluster_articles debe producir al menos un grupo."""
        clusterer = self._make_clusterer_with_mock()
        result = clusterer.cluster_articles(LICENCIAS_ARTICLES + FISCAL_ARTICLES, method="kmeans", n_clusters=2)
        assert len(result) >= 1

    def test_cluster_output_format(self):
        """Cada cluster debe tener topic_id, keywords y articles."""
        clusterer = self._make_clusterer_with_mock()
        result = clusterer.cluster_articles(LICENCIAS_ARTICLES + FISCAL_ARTICLES, method="kmeans", n_clusters=2)
        for cluster in result:
            assert "topic_id" in cluster
            assert "keywords" in cluster
            assert "articles" in cluster
            assert isinstance(cluster["keywords"], list)
            assert isinstance(cluster["articles"], list)

    def test_cluster_assigns_all_articles(self):
        """La suma de artículos en clusters debe cubrir todos los artículos de entrada."""
        clusterer = self._make_clusterer_with_mock()
        all_articles = LICENCIAS_ARTICLES + FISCAL_ARTICLES
        result = clusterer.cluster_articles(all_articles, method="kmeans", n_clusters=2)
        total_clustered = sum(len(c["articles"]) for c in result)
        assert total_clustered == len(all_articles)

    def test_cluster_empty_input(self):
        """cluster_articles con lista vacía debe retornar lista vacía."""
        from neurodiario.nlp.topic_cluster import TopicClusterer
        with patch("neurodiario.nlp.topic_cluster.SentenceTransformer"):
            clusterer = TopicClusterer(model_name="mock-model")
        result = clusterer.cluster_articles([])
        assert result == []

    def test_cluster_keywords_extracted(self):
        """Cada cluster debe tener keywords no vacías."""
        clusterer = self._make_clusterer_with_mock()
        result = clusterer.cluster_articles(LICENCIAS_ARTICLES + FISCAL_ARTICLES, method="kmeans", n_clusters=2)
        for cluster in result:
            assert len(cluster["keywords"]) > 0

    def test_dbscan_method_accepted(self):
        """cluster_articles debe aceptar method='dbscan' sin errores."""
        import numpy as np
        from neurodiario.nlp.topic_cluster import TopicClusterer

        with patch("neurodiario.nlp.topic_cluster.SentenceTransformer") as mock_st:
            embeddings = np.zeros((len(LICENCIAS_ARTICLES), 10))
            for i in range(len(LICENCIAS_ARTICLES)):
                embeddings[i, 0] = 1.0 + i * 0.01  # puntos muy cercanos → un cluster

            mock_instance = MagicMock()
            mock_instance.encode.return_value = embeddings
            mock_st.return_value = mock_instance

            clusterer = TopicClusterer(model_name="mock-model")

        result = clusterer.cluster_articles(LICENCIAS_ARTICLES, method="dbscan", eps=0.5, min_samples=2)
        assert isinstance(result, list)


# ------------------------------------------------------------------ #
#  Tests de TrendDetector.detect_trends                               #
# ------------------------------------------------------------------ #

class TestTrendDetector:
    """Tests para el método detect_trends del TrendDetector."""

    def setup_method(self):
        self.detector = TrendDetector()

    def _make_cluster(self, topic_id: int, topic: str, keywords: list, articles: list) -> dict:
        return {
            "topic_id": topic_id,
            "topic": topic,
            "keywords": keywords,
            "articles": articles,
        }

    def test_detect_trends_returns_list(self):
        """detect_trends debe retornar una lista."""
        result = self.detector.detect_trends([])
        assert isinstance(result, list)

    def test_detect_trends_finds_valid_trend(self):
        """Cluster con >= 3 artículos y >= 2 medios debe detectarse como tendencia."""
        cluster = self._make_cluster(
            topic_id=0,
            topic="licencias",
            keywords=["licencias", "intrant"],
            articles=LICENCIAS_ARTICLES,
        )
        trends = self.detector.detect_trends([cluster])
        assert len(trends) == 1
        assert trends[0]["topic"] == "licencias"
        assert trends[0]["article_count"] == len(LICENCIAS_ARTICLES)

    def test_detect_trends_output_format(self):
        """Cada tendencia debe tener topic, article_count y sources."""
        cluster = self._make_cluster(
            topic_id=0,
            topic="reforma fiscal",
            keywords=["reforma", "fiscal"],
            articles=FISCAL_ARTICLES,
        )
        trends = self.detector.detect_trends([cluster])
        assert len(trends) >= 1
        trend = trends[0]
        assert "topic" in trend
        assert "article_count" in trend
        assert "sources" in trend
        assert isinstance(trend["sources"], list)

    def test_detect_trends_requires_min_articles(self):
        """Cluster con < 3 artículos no debe ser tendencia."""
        small_articles = LICENCIAS_ARTICLES[:2]  # solo 2
        cluster = self._make_cluster(
            topic_id=0,
            topic="poco volumen",
            keywords=["poco"],
            articles=small_articles,
        )
        trends = self.detector.detect_trends([cluster])
        assert len(trends) == 0

    def test_detect_trends_requires_min_sources(self):
        """Cluster con artículos de un solo medio no debe ser tendencia."""
        single_source_articles = [
            make_article("Artículo A", "Contenido A", "Listín Diario"),
            make_article("Artículo B", "Contenido B", "Listín Diario"),
            make_article("Artículo C", "Contenido C", "Listín Diario"),
        ]
        cluster = self._make_cluster(
            topic_id=0,
            topic="un solo medio",
            keywords=["solo"],
            articles=single_source_articles,
        )
        trends = self.detector.detect_trends([cluster])
        assert len(trends) == 0

    def test_detect_trends_multiple_clusters(self):
        """detect_trends debe procesar múltiples clusters."""
        cluster1 = self._make_cluster(
            topic_id=0,
            topic="licencias",
            keywords=["licencias"],
            articles=LICENCIAS_ARTICLES,
        )
        cluster2 = self._make_cluster(
            topic_id=1,
            topic="reforma fiscal",
            keywords=["reforma"],
            articles=FISCAL_ARTICLES,
        )
        trends = self.detector.detect_trends([cluster1, cluster2])
        assert len(trends) == 2

    def test_detect_trends_sources_are_unique(self):
        """La lista de medios en una tendencia no debe tener duplicados."""
        cluster = self._make_cluster(
            topic_id=0,
            topic="licencias",
            keywords=["licencias"],
            articles=LICENCIAS_ARTICLES,
        )
        trends = self.detector.detect_trends([cluster])
        sources = trends[0]["sources"]
        assert len(sources) == len(set(sources))

    def test_detect_trends_sorted_by_article_count(self):
        """Las tendencias deben ordenarse de mayor a menor número de artículos."""
        cluster1 = self._make_cluster(
            topic_id=0,
            topic="licencias",
            keywords=["licencias"],
            articles=LICENCIAS_ARTICLES,  # 4 artículos
        )
        cluster2 = self._make_cluster(
            topic_id=1,
            topic="reforma fiscal",
            keywords=["reforma"],
            articles=FISCAL_ARTICLES,  # 3 artículos
        )
        trends = self.detector.detect_trends([cluster1, cluster2])
        counts = [t["article_count"] for t in trends]
        assert counts == sorted(counts, reverse=True)
