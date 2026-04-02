"""
Módulo generador de artículos periodísticos - MEJORADO PARA FASE 1
Usa Claude AI para generar artículos originales citando fuentes apropiadamente.
"""

import logging
import re
from typing import Dict, List, Optional
from datetime import datetime

import anthropic

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """Eres un periodista profesional de NeuroDiario, un medio digital dominicano.

Tu tarea es redactar artículos periodísticos originales basados en noticias de otros medios.

REGLAS CRÍTICAS:
1. NUNCA copies texto literal de las fuentes
2. SIEMPRE cita la fuente original al inicio del artículo
3. Reescribe completamente con tus propias palabras
4. Mantén un tono profesional y objetivo
5. Escribe en español dominicano natural
6. Optimiza para SEO y lectura web

ESTRUCTURA REQUERIDA:
- Título atractivo (máximo 70 caracteres)
- Párrafo inicial citando la fuente
- Desarrollo del tema (3-4 párrafos)
- Contexto relevante para audiencia dominicana
- Cierre con implicaciones o próximos pasos

Al final SIEMPRE incluye:
---
Fuente: [Nombre del medio]
Fecha: [Fecha de publicación]
"""


class ArticleGenerator:
    """Genera artículos periodísticos usando la API de Claude."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        """
        Args:
            api_key: Clave de API de Anthropic.
            model: ID del modelo de Claude a usar.
        """
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_from_single_article(
        self,
        title: str,
        content: str,
        source: str,
        category: str,
        url: str = "",
        published_at: Optional[datetime] = None,
    ) -> Dict:
        """
        Genera un artículo original para NeuroDiario basado en un artículo fuente.

        Args:
            title: Título del artículo original
            content: Contenido del artículo original
            source: Nombre del medio fuente (ej: "Diario Libre")
            category: Categoría del artículo
            url: URL del artículo original
            published_at: Fecha de publicación original

        Returns:
            Dict con title, content, excerpt, category, tags, source_citation
        """
        # Truncar contenido si es muy largo
        content_trimmed = content[:3000] if len(content) > 3000 else content

        fecha_str = ""
        if published_at:
            fecha_str = published_at.strftime("%d de %B, %Y")

        prompt = f"""Redacta un artículo periodístico ORIGINAL para NeuroDiario basado en esta noticia de {source}:

ARTÍCULO FUENTE:
Título: {title}
Medio: {source}
Categoría: {category}
{f'Fecha: {fecha_str}' if fecha_str else ''}
{f'URL: {url}' if url else ''}

Contenido:
{content_trimmed}

INSTRUCCIONES:
1. Crea un título NUEVO y atractivo (máximo 70 caracteres)
2. Primer párrafo debe mencionar: "Según reportó {source}..." o similar
3. Reescribe COMPLETAMENTE el contenido con tus propias palabras
4. Añade contexto relevante para lectores dominicanos
5. Mantén objetividad periodística
6. Al final incluye la cita de fuente en este formato exacto:

---
**Fuente:** {source}
{f'**Fecha:** {fecha_str}' if fecha_str else ''}
{f'**Enlace:** {url}' if url else ''}

Responde SOLO con el artículo completo, sin comentarios adicionales."""

        try:
            response_text = self._call_api(prompt, max_tokens=2000)
            
            # Parsear respuesta
            parsed = self._parse_generated_article(response_text, source, category)
            
            # Agregar metadata
            parsed["source_citation"] = {
                "source": source,
                "url": url,
                "published_at": published_at,
            }
            
            return parsed

        except Exception as e:
            logger.error(f"Error generando artículo: {e}")
            raise

    def generate_digest(self, trends: List[Dict]) -> str:
        """
        Genera un boletín diario con las principales tendencias.

        Args:
            trends: Lista de tendencias detectadas

        Returns:
            Texto del boletín
        """
        trends_text = "\n".join(
            f"- {t['topic']} ({t.get('article_count', 0)} artículos)"
            for t in trends[:5]
        )
        
        prompt = f"""Redacta un boletín periodístico diario para NeuroDiario.

TENDENCIAS DEL DÍA:
{trends_text}

FORMATO:
- Título atractivo para el boletín
- Introducción breve
- Resumen de cada tendencia (1 párrafo cada una)
- Cierre con perspectiva general

Extensión: 400-600 palabras
Tono: Profesional pero accesible"""

        return self._call_api(prompt)

    def create_article(self, trend: Dict, articles: List[Dict]) -> Dict:
        """
        MÉTODO ORIGINAL - Genera artículo basado en tendencia y múltiples fuentes.

        Args:
            trend: Tendencia detectada
            articles: Artículos relacionados

        Returns:
            Dict con artículo estructurado
        """
        # Limitar artículos
        articles = articles[:5]
        sources_text = self._format_sources(articles)
        topic = trend.get("topic", "")
        category = trend.get("category", "general")

        # Extraer nombres de medios únicos
        source_names = list(set(a.get("source", "Medios locales") for a in articles if a.get("source")))
        sources_citation = ", ".join(source_names[:3])

        prompt = f"""Redacta un artículo periodístico ORIGINAL sobre '{topic}' para NeuroDiario.

FUENTES BASE:
{sources_text}

INSTRUCCIONES:
1. Título atractivo (máximo 70 caracteres)
2. Primer párrafo menciona: "Según reportaron {sources_citation}..."
3. Reescribe completamente con tus palabras
4. Estructura: Introducción → Desarrollo → Contexto → Cierre
5. 600-800 palabras
6. Al final incluye:

---
**Fuentes:** {sources_citation}
**Categoría:** {category}

Responde SOLO con el artículo."""

        response_text = self._call_api(prompt, max_tokens=2500)
        return self._parse_article_response(response_text, articles)

    def _call_api(self, user_prompt: str, max_tokens: int = 2048) -> str:
        """Llama a la API de Claude."""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text
        except anthropic.APIError as e:
            logger.error(f"Error en Claude API: {e}")
            raise

    def _parse_generated_article(self, response_text: str, source: str, category: str) -> Dict:
        """
        Parsea el artículo generado y extrae componentes.

        Args:
            response_text: Texto generado por Claude
            source: Medio fuente
            category: Categoría del artículo

        Returns:
            Dict con title, content, excerpt, category, tags
        """
        lines = response_text.strip().split("\n")
        
        # Extraer título (primera línea no vacía)
        title = ""
        for line in lines:
            clean_line = line.strip().lstrip("#").strip()
            if clean_line and len(clean_line) > 10:
                title = clean_line
                break
        
        if not title:
            title = "Artículo de NeuroDiario"

        # Contenido completo
        content = response_text.strip()

        # Extracto (primeras 2-3 oraciones)
        sentences = re.split(r"(?<=[.!?])\s+", content)
        excerpt = " ".join(sentences[:3]) if len(sentences) >= 3 else sentences[0] if sentences else ""
        excerpt = excerpt[:200] + "..." if len(excerpt) > 200 else excerpt

        # Tags básicos basados en categoría
        tags = [category, source, "República Dominicana"]

        return {
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "category": category,
            "tags": tags,
        }

    def _parse_article_response(self, response_text: str, articles: List[Dict]) -> Dict:
        """MÉTODO ORIGINAL - Parsea respuesta estructurada."""
        sources = [a.get("url", "") for a in articles if a.get("url")]
        
        # Intentar extraer título
        lines = [line for line in response_text.strip().splitlines() if line.strip()]
        title = lines[0].lstrip("#").strip() if lines else "Sin título"

        # Extracto
        sentences = re.split(r"(?<=[.!?])\s+", response_text.strip())
        summary = " ".join(sentences[:2]).strip() if sentences else response_text[:200]

        return {
            "title": title,
            "summary": summary,
            "content": response_text.strip(),
            "sources": sources,
        }

    def _format_sources(self, articles: List[Dict]) -> str:
        """Formatea artículos como texto para el prompt."""
        parts = []
        for i, article in enumerate(articles[:5], 1):
            parts.append(
                f"[Fuente {i}] {article.get('title', 'Sin título')}\n"
                f"Medio: {article.get('source', 'Desconocido')}\n"
                f"URL: {article.get('url', '')}\n"
                f"Contenido: {article.get('raw_content', '')[:500]}..."
            )
        return "\n\n".join(parts)
