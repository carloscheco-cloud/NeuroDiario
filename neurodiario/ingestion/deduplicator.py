"""
Módulo de deduplicación de artículos.
Evita guardar artículos duplicados por URL exacta o título similar.
"""

import logging
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Umbral de similitud para considerar dos títulos como duplicados
SIMILARITY_THRESHOLD = 0.80


def is_duplicate(article_url: str, article_title: str, db_session: Session) -> bool:
    """
    Verifica si un artículo ya existe en la BD.

    Primero comprueba por URL exacta (más rápido, usa índice).
    Si la URL es nueva, compara el título contra los últimos 500
    artículos para detectar duplicados con URL distinta.

    Args:
        article_url: URL del artículo a verificar.
        article_title: Título del artículo a verificar.
        db_session: Sesión activa de SQLAlchemy.

    Returns:
        True si el artículo es duplicado, False si es nuevo.
    """
    from neurodiario.db.models import Article

    # 1. Verificación exacta por URL (O(1) con índice)
    exists = db_session.query(Article.id).filter(Article.url == article_url).first()
    if exists:
        logger.debug(f"Duplicado por URL: {article_url}")
        return True

    # 2. Verificación por similitud de título
    normalized_new = normalize_title(article_title)
    if not normalized_new:
        return False

    # Consultar últimos 500 títulos para limitar el coste de la comparación
    recent_titles = (
        db_session.query(Article.title)
        .order_by(Article.fetched_at.desc())
        .limit(500)
        .all()
    )

    for (existing_title,) in recent_titles:
        normalized_existing = normalize_title(existing_title)
        if similarity_ratio(normalized_new, normalized_existing) >= SIMILARITY_THRESHOLD:
            logger.debug(
                f"Duplicado por título similar: '{article_title[:60]}' ≈ '{existing_title[:60]}'"
            )
            return True

    return False


def normalize_title(title: str) -> str:
    """Normaliza un título para comparación: minúsculas y sin espacios extras."""
    return title.lower().strip() if title else ""


def similarity_ratio(a: str, b: str) -> float:
    """
    Calcula la similitud entre dos cadenas usando SequenceMatcher.

    Returns:
        Float en [0.0, 1.0]; 1.0 significa cadenas idénticas.
    """
    return SequenceMatcher(None, a, b).ratio()
