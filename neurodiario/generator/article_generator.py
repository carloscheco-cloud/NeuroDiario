"""
Módulo generador de artículos periodísticos.
Usa Claude AI para generar resúmenes, análisis y artículos originales
basados en las noticias recolectadas.
"""

import logging
import re
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

    def create_article(self, trend: Dict, articles: List[Dict]) -> Dict:
        """
        Genera un artículo estructurado basado en una tendencia y sus artículos fuente.

        Args:
            trend: Diccionario con información de la tendencia (topic, category, etc.).
            articles: Lista de artículos fuente relacionados con la tendencia.

        Returns:
            Diccionario con title, summary, content y sources.
        """
        articles = articles[:5]  # Limitar a máximo 5 artículos para evitar prompts muy largos
        sources = [a.get("url", "") for a in articles if a.get("url")]
        sources_text = self._format_sources(articles)
        topic = trend.get("topic", "")
        category = trend.get("category", "")

        prompt = (
            f"Basándote en los siguientes artículos sobre '{topic}' (categoría: {category}), "
            f"redacta un artículo periodístico completo en español.\n\n"
            f"Usa EXACTAMENTE este formato con estos encabezados:\n\n"
            f"## Título\n[título del artículo]\n\n"
            f"## Resumen\n[resumen en 2-3 oraciones]\n\n"
            f"## Contexto\n[contexto e información de fondo]\n\n"
            f"## Detalle\n[desarrollo completo del tema]\n\n"
            f"## Análisis\n[análisis e implicaciones]\n\n"
            f"Artículos fuente:\n\n{sources_text}"
        )

        response_text = self._call_api(prompt)
        return self._parse_article_response(response_text, sources)

    def _parse_article_response(self, response_text: str, sources: List[str]) -> Dict:
        """
        Parsea la respuesta del modelo buscando secciones estructuradas.
        Si no se detectan las secciones esperadas, aplica un fallback usando el texto completo.

        Args:
            response_text: Texto devuelto por el modelo.
            sources: Lista de URLs de los artículos fuente.

        Returns:
            Diccionario con title, summary, content y sources.
        """
        section_pattern = re.compile(
            r"##\s*Título\s*\n(?P<title>.+?)\n.*?"
            r"##\s*Resumen\s*\n(?P<summary>.+?)\n.*?"
            r"##\s*Contexto\s*\n(?P<context>.+?)\n.*?"
            r"##\s*Detalle\s*\n(?P<detail>.+?)\n.*?"
            r"##\s*Análisis\s*\n(?P<analysis>.+?)(?:\Z|(?=##))",
            re.DOTALL | re.IGNORECASE,
        )

        match = section_pattern.search(response_text)
        if match:
            title = match.group("title").strip()
            summary = match.group("summary").strip()
            content = "\n\n".join([
                match.group("context").strip(),
                match.group("detail").strip(),
                match.group("analysis").strip(),
            ])
            return {"title": title, "summary": summary, "content": content, "sources": sources}

        # Fallback: secciones no encontradas, usar texto completo
        logger.warning("No se detectaron secciones estructuradas en la respuesta; aplicando fallback.")
        lines = [line for line in response_text.strip().splitlines() if line.strip()]
        title = lines[0].lstrip("#").strip() if lines else "Sin título"

        sentences = re.split(r"(?<=[.!?])\s+", response_text.strip())
        summary = " ".join(sentences[:2]).strip() if sentences else response_text[:200]

        return {"title": title, "summary": summary, "content": response_text.strip(), "sources": sources}

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
