"""
Clustering de artículos por tema — Módulo 4.

Agrupa noticias similares usando embeddings semánticos (sentence-transformers)
y algoritmos de clustering (DBSCAN o KMeans) de scikit-learn.
Extrae keywords representativas por cluster via TF-IDF.
"""

import logging
from collections import Counter
from typing import List, Dict

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN, KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "all-MiniLM-L6-v2"


class TopicClusterer:
    """Agrupa artículos en temas mediante embeddings semánticos."""

    def __init__(self, model_name: str = _DEFAULT_MODEL):
        """
        Inicializa el modelo de embeddings.

        Args:
            model_name: Nombre del modelo sentence-transformers a usar.
                        Por defecto 'all-MiniLM-L6-v2'.
        """
        logger.info(f"Cargando modelo de embeddings: {model_name}")
        self.model = SentenceTransformer(model_name)

    def cluster_articles(
        self,
        articles: List[Dict],
        method: str = "dbscan",
        n_clusters: int = 5,
        eps: float = 0.35,
        min_samples: int = 2,
        n_keywords: int = 5,
    ) -> List[Dict]:
        """
        Agrupa artículos similares por tema.

        Args:
            articles: Lista de dicts con claves 'title' y 'content'/'raw_content'.
            method: 'dbscan' (clusters naturales) o 'kmeans' (número fijo).
            n_clusters: Solo para KMeans — número de grupos deseados.
            eps: Radio máximo entre puntos para DBSCAN (con embeddings normalizados).
            min_samples: Mínimo de artículos por cluster en DBSCAN.
            n_keywords: Número de keywords a extraer por cluster.

        Returns:
            Lista de clusters, cada uno con:
            - 'topic_id': identificador numérico
            - 'topic': etiqueta del tema (primera keyword)
            - 'keywords': lista de palabras clave representativas
            - 'articles': artículos que pertenecen al cluster
        """
        if not articles:
            logger.warning("No hay artículos para clustering")
            return []

        logger.info(f"Clustering {len(articles)} artículos con {method.upper()}...")

        # Combinar título + primeros 300 chars de contenido para cada artículo
        texts = [
            f"{a.get('title', '')} {a.get('content', a.get('raw_content', ''))[:300]}"
            for a in articles
        ]

        # Generar embeddings y normalizar (convierte similitud coseno en distancia euclidiana)
        embeddings = self.model.encode(texts, show_progress_bar=False)
        embeddings_norm = normalize(embeddings)

        if method == "dbscan":
            labels = self._cluster_dbscan(embeddings_norm, eps, min_samples)
        else:
            labels = self._cluster_kmeans(embeddings_norm, n_clusters, len(articles))

        # Agrupar artículos por label
        groups: Dict[int, List[Dict]] = {}
        for idx, label in enumerate(labels):
            groups.setdefault(int(label), []).append(articles[idx])

        # Construir resultado final ignorando el cluster de ruido (-1) de DBSCAN
        result = []
        topic_id = 0
        for label in sorted(groups.keys()):
            if label == -1:
                # Artículos que DBSCAN no pudo agrupar — omitir
                logger.debug(f"  {len(groups[label])} artículos sin grupo (ruido DBSCAN)")
                continue

            group_articles = groups[label]
            keywords = self._extract_keywords(group_articles, n_keywords)
            topic_label = keywords[0] if keywords else group_articles[0].get("title", "")[:50]

            result.append({
                "topic_id": topic_id,
                "topic": topic_label,
                "keywords": keywords,
                "articles": group_articles,
            })
            logger.info(
                f"  Cluster detectado: {topic_label} ({len(group_articles)} artículos)"
            )
            topic_id += 1

        logger.info(f"✓ {len(result)} clusters formados")
        return result

    # ------------------------------------------------------------------ #
    #  Algoritmos de clustering                                           #
    # ------------------------------------------------------------------ #

    def _cluster_dbscan(
        self, embeddings: np.ndarray, eps: float, min_samples: int
    ) -> np.ndarray:
        """Aplica DBSCAN para encontrar clusters de forma automática."""
        db = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean")
        labels = db.fit_predict(embeddings)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = int(np.sum(labels == -1))
        logger.info(f"  DBSCAN: {n_clusters} clusters encontrados, {n_noise} sin grupo")
        return labels

    def _cluster_kmeans(
        self, embeddings: np.ndarray, n_clusters: int, n_articles: int
    ) -> np.ndarray:
        """Aplica KMeans con número fijo de clusters."""
        n_clusters = min(n_clusters, max(1, n_articles // 2))
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        return km.fit_predict(embeddings)

    # ------------------------------------------------------------------ #
    #  Extracción de keywords                                             #
    # ------------------------------------------------------------------ #

    def _extract_keywords(self, articles: List[Dict], n: int) -> List[str]:
        """
        Extrae las keywords más representativas del cluster usando TF-IDF.

        Fallback a frecuencia simple de palabras si TF-IDF falla.
        """
        texts = [
            f"{a.get('title', '')} {a.get('content', a.get('raw_content', ''))[:500]}"
            for a in articles
        ]
        try:
            vectorizer = TfidfVectorizer(
                max_features=300,
                ngram_range=(1, 2),
                min_df=1,
                token_pattern=r"(?u)\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{3,}\b",
            )
            tfidf_matrix = vectorizer.fit_transform(texts)
            scores = tfidf_matrix.sum(axis=0).A1
            feature_names = vectorizer.get_feature_names_out()
            top_indices = scores.argsort()[::-1][:n]
            return [feature_names[i] for i in top_indices]
        except Exception as exc:
            logger.warning(f"TF-IDF falló, usando frecuencia simple: {exc}")
            words: Counter = Counter()
            for text in texts:
                words.update(w.lower() for w in text.split() if len(w) > 3)
            return [w for w, _ in words.most_common(n)]
