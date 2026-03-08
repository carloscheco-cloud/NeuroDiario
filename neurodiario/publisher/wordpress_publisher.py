"""
Módulo de publicación en WordPress — Módulo 6.
Publica los artículos generados en un sitio WordPress vía REST API (wp-json).
Usa autenticación básica (usuario + contraseña de aplicación).
"""

import logging
from typing import Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from neurodiario.config.settings import settings

logger = logging.getLogger(__name__)

# Endpoint de la API REST de WordPress para posts
WP_API_POSTS = "/wp-json/wp/v2/posts"


class WordPressPublisher:
    """Publica artículos en WordPress usando la API REST con autenticación básica."""

    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Lee las credenciales desde los parámetros o, si no se proporcionan,
        desde las variables de entorno WORDPRESS_URL / WORDPRESS_USER / WORDPRESS_PASSWORD.

        Args:
            url:      URL base del sitio WordPress (ej: https://neurodiario.com).
            username: Usuario de WordPress con permisos de publicación.
            password: Contraseña o Application Password del usuario.
        """
        self.url = (url or settings.WORDPRESS_URL).rstrip("/")
        self.username = username or settings.WORDPRESS_USER
        self.password = password or settings.WORDPRESS_PASSWORD
        self._auth = HTTPBasicAuth(self.username, self.password)

    # ------------------------------------------------------------------ #
    #  Formateo del contenido                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_content(article: Dict) -> str:
        """
        Construye el cuerpo HTML del post a partir de los campos del artículo.

        Formato resultante:
            <h2>Resumen</h2>
            <p>[resumen]</p>

            <h2>Artículo</h2>
            <p>[contenido]</p>

            <h2>Fuentes</h2>
            <ul>
              <li>medio 1</li>
              <li>medio 2</li>
            </ul>

        Args:
            article: Dict con title, summary, content y sources.

        Returns:
            Cadena HTML lista para enviar a WordPress.
        """
        summary = article.get("summary", "").strip()
        content = article.get("content", "").strip()
        sources: List[str] = article.get("sources", [])

        parts: List[str] = []

        if summary:
            parts.append(f"<h2>Resumen</h2>\n<p>{summary}</p>")

        if content:
            parts.append(f"<h2>Artículo</h2>\n<p>{content}</p>")

        if sources:
            items = "\n".join(f"  <li>{src}</li>" for src in sources if src)
            parts.append(f"<h2>Fuentes</h2>\n<ul>\n{items}\n</ul>")

        return "\n\n".join(parts)

    # ------------------------------------------------------------------ #
    #  Publicación principal                                               #
    # ------------------------------------------------------------------ #

    def create_post(self, article: Dict) -> Optional[int]:
        """
        Publica un artículo en WordPress como borrador (draft).

        Args:
            article: Diccionario generado por ArticleGenerator.create_article() con los campos:
                     - title   (str):       Título del artículo.
                     - summary (str):       Resumen breve.
                     - content (str):       Cuerpo del artículo.
                     - sources (List[str]): URLs de las fuentes utilizadas.

        Returns:
            ID del post creado en WordPress, o None si la publicación falló.
        """
        title = article.get("title", "Sin título")
        html_content = self._build_content(article)

        payload = {
            "title": title,
            "content": html_content,
            "status": "draft",
        }

        endpoint = f"{self.url}{WP_API_POSTS}"

        try:
            response = requests.post(
                endpoint,
                json=payload,
                auth=self._auth,
                timeout=30,
            )
            response.raise_for_status()
            post_id = response.json().get("id")
            logger.info(f"Artículo enviado a WordPress: {title}")
            return int(post_id) if post_id is not None else None

        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Error HTTP al publicar '{title}' en WordPress "
                f"({response.status_code}): {e}"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red al publicar '{title}' en WordPress: {e}")

        return None

    # ------------------------------------------------------------------ #
    #  Publicación en lote                                                 #
    # ------------------------------------------------------------------ #

    def publish_batch(self, articles: List[Dict]) -> List[Optional[int]]:
        """
        Publica una lista de artículos en WordPress, uno a uno.

        Args:
            articles: Lista de artículos (mismos campos que create_post).

        Returns:
            Lista de IDs de posts creados (None para los que fallaron).
        """
        results: List[Optional[int]] = []
        for article in articles:
            post_id = self.create_post(article)
            results.append(post_id)
        return results
