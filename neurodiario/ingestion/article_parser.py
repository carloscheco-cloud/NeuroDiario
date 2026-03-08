"""
Módulo de parseo y extracción de contenido de artículos.
Descarga el HTML completo de cada artículo y extrae el texto limpio.
"""

import logging
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Cabeceras HTTP para simular un navegador real
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NeuroDiario/1.0; "
        "+https://neurodiario.com/bot)"
    )
}


class ArticleParser:
    """Descarga y extrae el contenido completo de artículos de noticias."""

    def __init__(self, timeout: int = 20):
        """
        Args:
            timeout: Tiempo máximo de espera para cada petición HTTP (segundos).
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def parse(self, article: Dict) -> Dict:
        """
        Descarga y enriquece un artículo con su contenido completo.

        Args:
            article: Diccionario de artículo con al menos la clave 'url'.

        Returns:
            El mismo diccionario con 'raw_html', 'raw_content' y 'word_count' añadidos.
        """
        url = article.get("url", "")
        if not url:
            logger.warning("Artículo sin URL, omitiendo parseo")
            return article

        raw_html, content = self._fetch_content(url)
        article["raw_html"] = raw_html
        article["raw_content"] = content
        article["word_count"] = len(content.split()) if content else 0
        return article

    def parse_batch(self, articles: list) -> list:
        """
        Parsea una lista de artículos en secuencia.

        Args:
            articles: Lista de artículos a parsear.

        Returns:
            Lista de artículos enriquecidos con contenido.
        """
        parsed = []
        for article in articles:
            parsed.append(self.parse(article))
        return parsed

    def _fetch_content(self, url: str) -> tuple:
        """
        Descarga una página y extrae el texto del artículo principal.

        Intenta primero con newspaper3k (MEJORA 3A: con timeout explícito).
        Si falla, usa requests + BeautifulSoup como fallback.

        Args:
            url: URL del artículo a descargar.

        Returns:
            Tupla (raw_html, texto_plano). Ambos cadena vacía si falla.
        """
        # MEJORA 3A: usar newspaper3k con timeout para mejor extracción
        try:
            from newspaper import Article as NewspaperArticle

            article_obj = NewspaperArticle(url, language="es", request_timeout=self.timeout)
            article_obj.download()
            raw_html = article_obj.html
            article_obj.parse()
            content = article_obj.text
            if content:
                return raw_html, content
            logger.debug(f"newspaper3k no extrajo contenido de {url}, usando fallback")
        except Exception as e:
            logger.debug(f"newspaper3k falló para {url}: {e}, usando fallback")

        # Fallback: requests + BeautifulSoup
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            raw_html = response.text
            return raw_html, self._extract_text(raw_html)
        except requests.RequestException as e:
            logger.error(f"Error descargando {url}: {e}")
            return "", ""

    def _extract_text(self, html: str) -> str:
        """
        Extrae el texto principal de un HTML usando BeautifulSoup.

        Args:
            html: Contenido HTML de la página.

        Returns:
            Texto limpio del artículo.
        """
        soup = BeautifulSoup(html, "lxml")

        # Eliminar elementos no deseados
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Intentar seleccionar el contenedor principal del artículo
        # TODO: Añadir selectores específicos por dominio en sources_config.py
        article_tag = (
            soup.find("article")
            or soup.find(class_=["article-body", "post-content", "entry-content", "content"])
            or soup.find("main")
        )

        target = article_tag or soup.body or soup
        return " ".join(target.get_text(separator=" ").split())
