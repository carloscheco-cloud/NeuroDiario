"""
Módulo de detección de tendencias.
Identifica los temas más relevantes y recurrentes entre los artículos recientes.
"""

import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TrendDetector:
    """Detecta tendencias y temas emergentes en el corpus de noticias."""

    def __init__(self, window_hours: int = 24, top_n: int = 10):
        """
        Args:
            window_hours: Ventana de tiempo en horas para considerar artículos recientes.
            top_n: Número de tendencias principales a retornar.
        """
        self.window_hours = window_hours
        self.top_n = top_n

    def detect(self, articles: List[Dict]) -> List[Dict]:
        """
        Detecta las tendencias principales en una lista de artículos.

        Args:
            articles: Lista de artículos con claves 'entities', 'category' y 'published_at'.

        Returns:
            Lista de tendencias ordenadas por relevancia, cada una con:
            - 'topic': nombre del tema o entidad
            - 'count': número de menciones
            - 'category': categoría dominante
            - 'articles': lista de URLs relacionadas
        """
        recent = self._filter_recent(articles)
        entity_counter: Counter = Counter()
        entity_articles: Dict[str, List[str]] = {}
        entity_categories: Dict[str, Counter] = {}

        for article in recent:
            entities = article.get("entities", {})
            url = article.get("url", "")
            category = article.get("category", "general")

            for entity_type, entity_list in entities.items():
                for entity in entity_list:
                    entity_counter[entity] += 1
                    entity_articles.setdefault(entity, []).append(url)
                    entity_categories.setdefault(entity, Counter())[category] += 1

        trends = []
        for entity, count in entity_counter.most_common(self.top_n):
            dominant_category = entity_categories[entity].most_common(1)[0][0]
            trends.append({
                "topic": entity,
                "count": count,
                "category": dominant_category,
                "articles": entity_articles[entity][:5],  # Máximo 5 URLs de referencia
            })

        logger.info(f"Detectadas {len(trends)} tendencias en ventana de {self.window_hours}h")
        return trends

    def get_trending_categories(self, articles: List[Dict]) -> List[Tuple[str, int]]:
        """
        Devuelve las categorías más publicadas en la ventana de tiempo.

        Args:
            articles: Lista de artículos con clave 'category'.

        Returns:
            Lista de tuplas (categoría, conteo) ordenada de mayor a menor.
        """
        recent = self._filter_recent(articles)
        category_counter: Counter = Counter(a.get("category", "general") for a in recent)
        return category_counter.most_common(self.top_n)

    def detect_trends(self, clustered_topics: List[Dict]) -> List[Dict]:
        """
        Detecta tendencias a partir de clusters de artículos.

        Un tema se considera tendencia si cumple:
          - artículos >= 3
          - medios distintos >= 2

        Args:
            clustered_topics: Salida de TopicClusterer.cluster_articles().
                Cada elemento tiene 'topic_id', 'keywords', 'topic' y 'articles'.

        Returns:
            Lista de tendencias detectadas, ordenadas por número de artículos, cada una con:
            - 'topic': nombre o keyword principal del tema
            - 'article_count': número de artículos en el cluster
            - 'sources': lista de nombres de medios (únicos)
        """
        trends = []
        for cluster in clustered_topics:
            articles = cluster.get("articles", [])
            article_count = len(articles)

            # Recopilar medios distintos presentes en el cluster
            sources = sorted({
                a.get("source_name") or a.get("source") or "Desconocido"
                for a in articles
            })
            n_sources = len(sources)

            topic = (
                cluster.get("topic")
                or (cluster.get("keywords") or [""])[0]
                or "Sin tema"
            )

            if article_count >= 3 and n_sources >= 2:
                trends.append({
                    "topic": topic,
                    "article_count": article_count,
                    "sources": sources,
                })
                logger.info(
                    f"Tendencia detectada: {topic} en {n_sources} medios "
                    f"({article_count} artículos)"
                )

        trends.sort(key=lambda t: t["article_count"], reverse=True)
        logger.info(f"Total de tendencias detectadas: {len(trends)}")
        return trends

    def _filter_recent(self, articles: List[Dict]) -> List[Dict]:
        """Filtra artículos publicados dentro de la ventana de tiempo configurada."""
        cutoff = datetime.utcnow() - timedelta(hours=self.window_hours)
        recent = []
        for article in articles:
            published = article.get("published_at")
            if isinstance(published, datetime) and published >= cutoff:
                recent.append(article)
            elif published is None:
                # Si no hay fecha, incluir por defecto
                recent.append(article)
        return recent
