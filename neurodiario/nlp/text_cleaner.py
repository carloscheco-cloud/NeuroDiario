"""
Módulo de limpieza y normalización de texto.
Prepara el texto de los artículos para su análisis NLP posterior.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Patrones de limpieza
_WHITESPACE_RE = re.compile(r"\s+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
_SPECIAL_CHARS_RE = re.compile(r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ.,;:!?\"'()\-]", re.UNICODE)


class TextCleaner:
    """Limpia y normaliza texto en español para procesamiento NLP."""

    def __init__(
        self,
        remove_urls: bool = True,
        remove_emails: bool = True,
        remove_special_chars: bool = True,
        lowercase: bool = False,
    ):
        """
        Args:
            remove_urls: Eliminar URLs del texto.
            remove_emails: Eliminar direcciones de correo.
            remove_special_chars: Eliminar caracteres especiales no alfanuméricos.
            lowercase: Convertir todo el texto a minúsculas.
        """
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_special_chars = remove_special_chars
        self.lowercase = lowercase

    def clean(self, text: str) -> str:
        """
        Aplica la cadena completa de limpieza sobre un texto.

        Args:
            text: Texto crudo a limpiar.

        Returns:
            Texto limpio y normalizado.
        """
        if not text:
            return ""

        # Eliminar etiquetas HTML residuales
        text = _HTML_TAG_RE.sub(" ", text)

        if self.remove_urls:
            text = _URL_RE.sub(" ", text)

        if self.remove_emails:
            text = _EMAIL_RE.sub(" ", text)

        if self.remove_special_chars:
            text = _SPECIAL_CHARS_RE.sub(" ", text)

        # Normalizar espacios
        text = _WHITESPACE_RE.sub(" ", text).strip()

        if self.lowercase:
            text = text.lower()

        return text

    def clean_batch(self, texts: list) -> list:
        """
        Limpia una lista de textos.

        Args:
            texts: Lista de textos crudos.

        Returns:
            Lista de textos limpios.
        """
        return [self.clean(t) for t in texts]

    def extract_sentences(self, text: str) -> list:
        """
        Divide el texto en oraciones usando separadores simples.

        Args:
            text: Texto limpio.

        Returns:
            Lista de oraciones no vacías.
        """
        # TODO: Reemplazar con segmentación basada en spaCy para mayor precisión
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
