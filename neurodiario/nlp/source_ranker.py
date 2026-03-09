"""
Source Ranker — asigna un score de calidad a cada fuente de noticias dominicana.

Provee un diccionario de scores por dominio y una función para calcular
el promedio de calidad de un conjunto de artículos.
"""

from urllib.parse import urlparse

SOURCE_SCORES = {
    "listindiario.com": 0.9,
    "diariolibre.com": 0.9,
    "hoy.com.do": 0.8,
    "acento.com.do": 0.8,
    "elnacional.com.do": 0.7,
}

# Score por defecto para fuentes no listadas
_DEFAULT_SCORE = 0.5


def _domain_from_url(url: str) -> str:
    """Extrae el dominio (sin www.) de una URL."""
    try:
        host = urlparse(url).netloc or ""
        return host.removeprefix("www.")
    except Exception:
        return ""


def _score_for_url(url: str) -> float:
    """Devuelve el score de calidad de la fuente que corresponde a una URL."""
    domain = _domain_from_url(url)
    for known_domain, score in SOURCE_SCORES.items():
        if known_domain in domain:
            return score
    return _DEFAULT_SCORE


def calculate_source_score(articles: list) -> float:
    """
    Calcula el promedio de score de calidad de las fuentes de los artículos.

    Args:
        articles: Lista de dicts que deben contener al menos la clave 'url'.

    Returns:
        Score promedio (float) entre 0.0 y 1.0.
        Devuelve 0.0 si la lista está vacía.
    """
    if not articles:
        return 0.0

    scores = [_score_for_url(a.get("url", "")) for a in articles]
    return round(sum(scores) / len(scores), 4)
