"""
Módulo de clasificación temática de artículos.
Asigna categorías (política, economía, deportes, etc.) a cada artículo.
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Palabras clave por categoría para clasificación heurística
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "politica": [
        "gobierno", "presidente", "congreso", "senado", "diputado", "partido",
        "elecciones", "ministro", "decreto", "ley", "constitución", "abinader",
    ],
    "economia": [
        "economía", "peso", "dólar", "inflación", "PIB", "banco", "inversión",
        "exportaciones", "importaciones", "empleo", "desempleo", "hacienda",
    ],
    "deportes": [
        "béisbol", "fútbol", "jugador", "equipo", "torneo", "campeonato",
        "liga", "gol", "partido", "deporte", "atleta", "medalla",
    ],
    "salud": [
        "salud", "hospital", "médico", "enfermedad", "vacuna", "paciente",
        "ministerio de salud", "epidemia", "dengue", "covid", "tratamiento",
    ],
    "tecnologia": [
        "tecnología", "internet", "digital", "software", "app", "startup",
        "inteligencia artificial", "ciberseguridad", "datos", "innovación",
    ],
    "cultura": [
        "cultura", "arte", "música", "cine", "teatro", "festival", "libro",
        "literatura", "merengue", "bachata", "patrimonio", "artista",
    ],
    "educacion": [
        "educación", "escuela", "universidad", "estudiante", "docente",
        "MINERD", "maestro", "aula", "currículo", "beca", "UASD",
    ],
    "internacional": [
        "internacional", "Estados Unidos", "ONU", "OEA", "Haití", "Venezuela",
        "Colombia", "España", "mundo", "global", "diplomacia", "embajada",
    ],
}


class ArticleClassifier:
    """Clasifica artículos de noticias por temática."""

    def __init__(self, method: str = "keyword"):
        """
        Args:
            method: Método de clasificación. Valores posibles:
                    - 'keyword': Heurístico por palabras clave (rápido, sin dependencias).
                    - 'ml': Modelo de machine learning (requiere entrenamiento previo).
        """
        self.method = method
        self._model = None  # Para uso futuro con método 'ml'

    def classify(self, text: str, title: str = "") -> Tuple[str, float]:
        """
        Clasifica un artículo y devuelve la categoría con su confianza.

        Args:
            text: Contenido del artículo.
            title: Título del artículo (tiene peso mayor en la clasificación).

        Returns:
            Tupla (categoría, confianza) donde confianza está en [0, 1].
        """
        if self.method == "keyword":
            return self._classify_by_keywords(text, title)
        raise NotImplementedError(f"Método '{self.method}' no implementado aún")

    def classify_batch(self, articles: List[Dict]) -> List[Dict]:
        """
        Clasifica una lista de artículos y añade 'category' y 'category_confidence'.

        Args:
            articles: Lista de artículos con claves 'raw_content' y 'title'.

        Returns:
            Lista de artículos con las claves de clasificación añadidas.
        """
        for article in articles:
            category, confidence = self.classify(
                article.get("raw_content", ""),
                article.get("title", ""),
            )
            article["category"] = category
            article["category_confidence"] = confidence
        return articles

    def _classify_by_keywords(self, text: str, title: str) -> Tuple[str, float]:
        """
        Clasifica usando conteo de palabras clave por categoría.
        El título pesa el doble que el cuerpo del artículo.
        """
        combined = f"{title} {title} {text}".lower()
        scores: Dict[str, int] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            scores[category] = sum(combined.count(kw.lower()) for kw in keywords)

        if not any(scores.values()):
            return "general", 0.0

        best_category = max(scores, key=lambda k: scores[k])
        total = sum(scores.values())
        confidence = scores[best_category] / total if total > 0 else 0.0

        return best_category, round(confidence, 3)
