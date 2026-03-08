"""
Clustering de artículos por tema.
Agrupa noticias similares.
"""

import logging
from typing import List, Dict

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)


class TopicClusterer:
    """Agrupa artículos en temas."""

    def __init__(self, model_name: str = 'distiluse-base-multilingual-cased-v2'):
        """
        Inicializa el modelo de embeddings.

        Args:
            model_name: Nombre del modelo sentence-transformers a usar.
        """
        logger.info(f"Cargando modelo: {model_name}")
        self.model = SentenceTransformer(model_name)

    def cluster_articles(self, articles: List[Dict], n_clusters: int = 5) -> List[Dict]:
        """
        Agrupa artículos similares por tema.

        Args:
            articles: Lista de artículos con 'title' y 'content'.
            n_clusters: Número de clusters deseados.

        Returns:
            Lista de clusters, cada uno con 'topic', 'articles' y 'count'.
        """
        if not articles:
            logger.warning("No hay artículos para clustering")
            return []

        if len(articles) < n_clusters:
            n_clusters = max(1, len(articles) // 2)

        logger.info(f"Clustering {len(articles)} artículos en {n_clusters} temas...")

        # Crear embeddings combinando título y primeros 300 chars de contenido
        texts = [f"{a['title']} {a.get('content', a.get('raw_content', ''))[:300]}" for a in articles]
        embeddings = self.model.encode(texts)

        # KMeans clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(embeddings)

        # Agrupar resultados por cluster
        clusters: Dict[int, List[Dict]] = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(articles[idx])

        # Construir resultado final con tema principal de cada cluster
        result = []
        for cluster_id, cluster_articles in clusters.items():
            theme = cluster_articles[0]['title'][:50]
            result.append({
                'topic': theme,
                'articles': cluster_articles,
                'count': len(cluster_articles),
            })

        logger.info(f"✓ {len(result)} temas detectados")
        return result
