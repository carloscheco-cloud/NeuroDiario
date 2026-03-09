"""
Paquete de procesamiento de lenguaje natural.
Contiene módulos para limpiar texto, extraer entidades, clasificar y detectar tendencias.
"""

from .text_cleaner import TextCleaner
from .entity_extractor import EntityExtractor
from .classifier import ArticleClassifier
from .trend_detector import TrendDetector
from .source_ranker import calculate_source_score, SOURCE_SCORES
from .angle_detector import detect_angle, ANGLES
from .trend_ranker import rank_trends

__all__ = [
    "TextCleaner",
    "EntityExtractor",
    "ArticleClassifier",
    "TrendDetector",
    "calculate_source_score",
    "SOURCE_SCORES",
    "detect_angle",
    "ANGLES",
    "rank_trends",
]
