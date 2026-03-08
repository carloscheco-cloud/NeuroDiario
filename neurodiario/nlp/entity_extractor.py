"""
Módulo de extracción de entidades nombradas (NER).
Identifica personas, organizaciones, lugares y fechas en el texto.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Tipos de entidades de interés
ENTITY_TYPES = {
    "PER": "persona",
    "ORG": "organización",
    "LOC": "lugar",
    "GPE": "entidad_geopolítica",
    "DATE": "fecha",
    "MONEY": "dinero",
    "PERCENT": "porcentaje",
}


class EntityExtractor:
    """Extrae entidades nombradas de textos en español usando spaCy."""

    def __init__(self, model_name: str = "es_core_news_lg"):
        """
        Args:
            model_name: Nombre del modelo de spaCy a cargar.
                        Usar 'es_core_news_sm' para pruebas ligeras.
        """
        self.model_name = model_name
        self._nlp = None  # Carga perezosa para no ralentizar el inicio

    @property
    def nlp(self):
        """Carga el modelo de spaCy de forma perezosa."""
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load(self.model_name)
                logger.info(f"Modelo spaCy '{self.model_name}' cargado correctamente")
            except OSError:
                logger.error(
                    f"Modelo '{self.model_name}' no encontrado. "
                    f"Ejecuta: python -m spacy download {self.model_name}"
                )
                raise
        return self._nlp

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Alias de extract(). Extrae entidades del texto y las agrupa por tipo."""
        self._last_entities = self.extract(text)
        return self._last_entities

    def get_persons(self) -> List[str]:
        """Devuelve las personas extraídas en la última llamada a extract_entities()."""
        return getattr(self, "_last_entities", {}).get("persona", [])

    def get_locations(self) -> List[str]:
        """Devuelve los lugares extraídos en la última llamada a extract_entities()."""
        entities = getattr(self, "_last_entities", {})
        return entities.get("lugar", []) + entities.get("entidad_geopolítica", [])

    def get_organizations(self) -> List[str]:
        """Devuelve las organizaciones extraídas en la última llamada a extract_entities()."""
        return getattr(self, "_last_entities", {}).get("organización", [])

    def extract(self, text: str) -> Dict[str, List[str]]:
        """
        Extrae entidades de un texto y las agrupa por tipo.

        Args:
            text: Texto del artículo ya limpio.

        Returns:
            Diccionario con listas de entidades por tipo, por ejemplo:
            {"persona": ["Juan Bosch", ...], "organización": ["ONU", ...]}
        """
        entities: Dict[str, List[str]] = {v: [] for v in ENTITY_TYPES.values()}

        if not text:
            return entities

        doc = self.nlp(text)
        for ent in doc.ents:
            entity_type = ENTITY_TYPES.get(ent.label_)
            if entity_type and ent.text not in entities[entity_type]:
                entities[entity_type].append(ent.text)

        return entities

    def extract_batch(self, texts: List[str]) -> List[Dict[str, List[str]]]:
        """
        Extrae entidades de múltiples textos usando el pipeline en lote de spaCy.

        Args:
            texts: Lista de textos a procesar.

        Returns:
            Lista de diccionarios de entidades, uno por texto.
        """
        # TODO: Usar nlp.pipe() para mayor eficiencia en lotes grandes
        return [self.extract(t) for t in texts]

    def get_top_entities(self, entities: Dict[str, List[str]], top_n: int = 5) -> Dict[str, List[str]]:
        """
        Devuelve las entidades más frecuentes por tipo (placeholder para frecuencia).

        Args:
            entities: Diccionario de entidades extraídas.
            top_n: Número máximo de entidades por tipo.

        Returns:
            Diccionario recortado a top_n entidades por tipo.
        """
        return {k: v[:top_n] for k, v in entities.items()}
