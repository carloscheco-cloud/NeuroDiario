"""
Detección de story velocity — Módulo de análisis de velocidad de crecimiento.

Identifica historias que están creciendo rápidamente comparando el volumen
de artículos en la última hora versus la hora anterior.

Una historia se marca como breaking story si:
  - velocity >= 2.0  (al menos el doble de artículos que la hora anterior)
  - article_count >= 5
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict

logger = logging.getLogger(__name__)

_VELOCITY_THRESHOLD = 2.0
_MIN_ARTICLE_COUNT = 5


def detect_story_velocity(clusters: List[Dict]) -> List[Dict]:
    """
    Detecta historias con crecimiento rápido (breaking stories).

    Calcula la velocidad de cada cluster comparando artículos publicados
    en la última hora vs la hora anterior. Usa el campo 'fetched_at' de
    cada artículo para determinar a qué ventana pertenece.

    Args:
        clusters: Lista de clusters generados por TopicClusterer.cluster_articles().
                  Cada cluster debe tener 'topic' y 'articles'. Cada artículo
                  puede tener 'fetched_at' (datetime) para cálculo de velocity.

    Returns:
        Lista de clusters enriquecidos con los campos adicionales:
        - 'velocity': float — artículos_última_hora / artículos_hora_anterior
        - 'is_breaking_story': bool — True si velocity >= 2 y article_count >= 5
    """
    now = datetime.now(tz=timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    two_hours_ago = now - timedelta(hours=2)

    result = []

    for cluster in clusters:
        topic = cluster.get("topic", "")
        articles = cluster.get("articles", [])
        article_count = len(articles)

        articles_last_hour = 0
        articles_previous_hour = 0

        for article in articles:
            ts = article.get("fetched_at")
            if ts is None:
                continue

            # Normalizar a aware datetime si llega como naive
            if isinstance(ts, datetime) and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            if ts >= one_hour_ago:
                articles_last_hour += 1
            elif ts >= two_hours_ago:
                articles_previous_hour += 1

        # Calcular velocity evitando división por cero
        if articles_previous_hour > 0:
            velocity = articles_last_hour / articles_previous_hour
        elif articles_last_hour > 0:
            # Sin artículos en la hora anterior pero con artículos recientes
            # → crecimiento total; usar conteo directo como score
            velocity = float(articles_last_hour)
        else:
            velocity = 0.0

        is_breaking = velocity >= _VELOCITY_THRESHOLD and article_count >= _MIN_ARTICLE_COUNT

        enriched = {
            **cluster,
            "velocity": round(velocity, 2),
            "is_breaking_story": is_breaking,
        }
        result.append(enriched)

        if is_breaking:
            logger.info(f"Breaking story detectada: {topic}")
            logger.info(f"Velocity score: {velocity:.2f}")
        else:
            logger.debug(
                f"  {topic} — velocity={velocity:.2f}, artículos={article_count}"
            )

    return result
