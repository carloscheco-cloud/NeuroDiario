"""
Módulo generador de artículos periodísticos.
Usa Claude AI para generar resúmenes, análisis y artículos originales
basados en las noticias recolectadas.
"""

import logging
from typing import Dict, List, Optional

import anthropic

logger = logging.getLogger(__name__)

# Modelo de Claude a utilizar
DEFAULT_MODEL = "claude-opus-4-6"

# Prompt base para generación de artículos
SYSTEM_PROMPT = """Eres un periodista experto en noticias dominicanas.
Tu tarea es generar artículos periodísticos en español, claros, objetivos y bien estructurados.
Usa un tono profesional, evita sensacionalismo y cita las fuentes cuando corresponda.
Los artículos deben estar optimizados para SEO y WordPress."""


class ArticleGenerator:
    """Genera artículos periodísticos usando la API de Claude."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        """
        Args:
            api_key: Clave de API de Anthropic. Si es None, usa ANTHROPIC_API_KEY del entorno.
            model: ID del modelo de Claude a usar.
        """
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_summary(self, articles: List[Dict], topic: str) -> str:
        """
        Genera un resumen periodístico sobre un tema a partir de múltiples artículos.

        Args:
            articles: Lista de artículos fuente con 'title', 'url' y 'raw_content'.
            topic: Tema central del resumen.

        Returns:
            Texto del resumen generado por Claude.
        """
        sources_text = self._format_sources(articles)
        prompt = (
            f"Basándote en los siguientes artículos de noticias dominicanas sobre '{topic}', "
            f"redacta un resumen periodístico completo (500-800 palabras) que sintetice "
            f"los puntos más importantes:\n\n{sources_text}"
        )
        return self._call_api(prompt)

    def generate_analysis(self, articles: List[Dict], topic: str) -> str:
        """
        Genera un artículo de análisis o opinión fundamentado sobre un tema.

        Args:
            articles: Lista de artículos fuente.
            topic: Tema a analizar.

        Returns:
            Texto del análisis generado.
        """
        sources_text = self._format_sources(articles)
        prompt = (
            f"Basándote en las siguientes noticias, redacta un artículo de análisis "
            f"profundo sobre '{topic}' para la audiencia dominicana. "
            f"Incluye contexto histórico, implicaciones y perspectivas a futuro (800-1200 palabras):\n\n"
            f"{sources_text}"
        )
        return self._call_api(prompt)

    def generate_digest(self, trends: List[Dict]) -> str:
        """
        Genera un boletín diario con las principales tendencias del día.

        Args:
            trends: Lista de tendencias detectadas por TrendDetector.

        Returns:
            Texto del boletín diario.
        """
        trends_text = "\n".join(
            f"- {t['topic']} ({t['count']} menciones, categoría: {t['category']})"
            for t in trends
        )
        prompt = (
            f"Las siguientes son las principales tendencias en noticias dominicanas de hoy:\n\n"
            f"{trends_text}\n\n"
            f"Redacta un boletín periodístico diario (400-600 palabras) que presente "
            f"estas tendencias de forma ordenada y atractiva para el lector dominicano."
        )
        return self._call_api(prompt)

    def _call_api(self, user_prompt: str, max_tokens: int = 2048) -> str:
        """
        Realiza la llamada a la API de Claude y retorna el texto generado.

        Args:
            user_prompt: Instrucción específica para el modelo.
            max_tokens: Número máximo de tokens en la respuesta.

        Returns:
            Texto generado por el modelo.
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text
        except anthropic.APIError as e:
            logger.error(f"Error en llamada a Claude API: {e}")
            raise

    def _format_sources(self, articles: List[Dict]) -> str:
        """Formatea una lista de artículos como texto para incluir en el prompt."""
        parts = []
        for i, article in enumerate(articles[:10], 1):  # Máximo 10 fuentes
            parts.append(
                f"[Fuente {i}] {article.get('title', 'Sin título')}\n"
                f"URL: {article.get('url', '')}\n"
                f"Contenido: {article.get('raw_content', '')[:800]}..."
            )
        return "\n\n".join(parts)
