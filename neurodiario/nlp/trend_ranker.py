"""
Trend Ranker — ordena tendencias por score de importancia.

Formula de score:
    score = (article_count_norm * 0.4) + (source_diversity_norm * 0.3) + (recency_score * 0.3)

Donde:
    - article_count_norm  : article_count normalizado al rango [0, 1] respecto al máximo del conjunto.
    - source_diversity_norm: número de fuentes únicas normalizado al rango [0, 1].
    - recency_score       : valor ya normalizado [0, 1] provisto en el dict de tendencia
                            (por defecto 1.0 si no está presente).
"""


def rank_trends(trends: list) -> list:
    """
    Ordena tendencias por score de importancia y añade el campo 'score' a cada una.

    Args:
        trends: Lista de dicts de tendencia. Cada dict debe tener:
                  - 'article_count' (int)
                  - 'sources'       (list[str])
                  - 'recency_score' (float, opcional; por defecto 1.0)

    Returns:
        Nueva lista de tendencias ordenada de mayor a menor score,
        con el campo 'score' (float, 4 decimales) añadido a cada elemento.
    """
    if not trends:
        return []

    max_count = max(t.get("article_count", 1) for t in trends) or 1
    max_diversity = max(len(t.get("sources", [])) for t in trends) or 1

    ranked = []
    for trend in trends:
        article_count = trend.get("article_count", 1)
        source_diversity = len(trend.get("sources", []))
        recency_score = float(trend.get("recency_score", 1.0))

        count_norm = article_count / max_count
        diversity_norm = source_diversity / max_diversity

        score = (count_norm * 0.4) + (diversity_norm * 0.3) + (recency_score * 0.3)
        ranked.append({**trend, "score": round(score, 4)})

    ranked.sort(key=lambda t: t["score"], reverse=True)
    return ranked
