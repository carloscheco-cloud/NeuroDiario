"""
Paquete de procesamiento de lenguaje natural.
Contiene módulos para limpiar texto, extraer entidades, clasificar y detectar tendencias.
"""

from .text_cleaner import TextCleaner
from .entity_extractor import EntityExtractor
from .classifier import ArticleClassifier
from .trend_detector import TrendDetector

__all__ = ["TextCleaner", "EntityExtractor", "ArticleClassifier", "TrendDetector"]
