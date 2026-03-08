"""
Módulo de limpieza y normalización de texto.
Prepara el texto de los artículos para su análisis NLP posterior.
"""

import re
import logging
import unicodedata
from typing import List, Optional

logger = logging.getLogger(__name__)

# Stopwords comunes en español
SPANISH_STOPWORDS = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las",
    "por", "un", "para", "con", "una", "su", "al", "lo", "como", "más",
    "pero", "sus", "le", "ya", "o", "este", "sí", "porque", "esta", "entre",
    "cuando", "muy", "sin", "sobre", "también", "me", "hasta", "hay", "donde",
    "quien", "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni",
    "contra", "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mí",
    "antes", "algunos", "qué", "unos", "yo", "otro", "otras", "otra", "él",
    "tanto", "esa", "estos", "mucho", "quienes", "nada", "muchos", "cual",
    "sea", "poco", "ella", "estar", "haber", "estas", "estaba", "estamos",
    "están", "era", "sido", "tiene", "han", "fue", "ser", "son", "hay",
}

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

    def clean_text(self, text: str) -> str:
        """Alias de clean(). Limpia caracteres especiales y normaliza el texto."""
        return self.clean(text)

    def remove_stopwords(self, text: str) -> str:
        """
        Elimina stopwords (palabras comunes) del texto en español.

        Args:
            text: Texto limpio.

        Returns:
            Texto sin stopwords.
        """
        words = text.split()
        filtered = [w for w in words if w.lower() not in SPANISH_STOPWORDS]
        return " ".join(filtered)

    def normalize_text(self, text: str) -> str:
        """
        Normaliza el texto para comparación: minúsculas, sin acentos, sin stopwords.

        Args:
            text: Texto a normalizar.

        Returns:
            Texto normalizado apto para comparaciones y búsquedas.
        """
        # Limpiar primero
        text = self.clean(text)
        # Convertir a minúsculas
        text = text.lower()
        # Eliminar acentos (NFD descompone, luego filtramos marcas diacríticas)
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        # Eliminar stopwords
        text = self.remove_stopwords(text)
        return _WHITESPACE_RE.sub(" ", text).strip()

    def get_summary(self, text: str, max_sentences: int = 3) -> str:
        """
        Extrae un resumen simple tomando las primeras oraciones del texto.

        Args:
            text: Texto del artículo.
            max_sentences: Número máximo de oraciones a incluir.

        Returns:
            Resumen como cadena de texto.
        """
        sentences = self.extract_sentences(text)
        return " ".join(sentences[:max_sentences])

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
