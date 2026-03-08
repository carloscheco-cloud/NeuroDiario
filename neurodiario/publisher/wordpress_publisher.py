"""
Módulo de publicación en WordPress.
Publica los artículos generados en un sitio WordPress vía XML-RPC.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class WordPressPublisher:
    """Publica artículos en WordPress usando la API XML-RPC."""

    def __init__(self, url: str, username: str, password: str):
        """
        Args:
            url: URL del sitio WordPress (ej: https://neurodiario.com).
            username: Nombre de usuario de WordPress con permisos de publicación.
            password: Contraseña del usuario.
        """
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self._client = None

    @property
    def client(self):
        """Inicializa el cliente XML-RPC de forma perezosa."""
        if self._client is None:
            try:
                from wordpress_xmlrpc import Client
                self._client = Client(
                    f"{self.url}/xmlrpc.php",
                    self.username,
                    self.password,
                )
                logger.info(f"Conectado a WordPress en {self.url}")
            except Exception as e:
                logger.error(f"Error conectando a WordPress: {e}")
                raise
        return self._client

    def publish(self, article: Dict) -> Optional[int]:
        """
        Publica un artículo en WordPress como borrador o publicado.

        Args:
            article: Diccionario con los campos del artículo:
                     - title (str): Título del artículo.
                     - content (str): Contenido HTML o texto plano.
                     - categories (List[str]): Categorías de WordPress.
                     - tags (List[str]): Etiquetas del artículo.
                     - status (str): 'publish', 'draft' o 'private'.

        Returns:
            ID del post creado en WordPress, o None si falló.
        """
        try:
            from wordpress_xmlrpc import WordPressPost
            from wordpress_xmlrpc.methods.posts import NewPost

            post = WordPressPost()
            post.title = article.get("title", "Sin título")
            post.content = article.get("content", "")
            post.post_status = article.get("status", "draft")
            post.terms_names = {
                "category": article.get("categories", ["General"]),
                "post_tag": article.get("tags", []),
            }

            post_id = self.client.call(NewPost(post))
            logger.info(f"Artículo publicado con ID {post_id}: {post.title}")
            return int(post_id)

        except Exception as e:
            logger.error(f"Error publicando artículo '{article.get('title')}': {e}")
            return None

    def publish_batch(self, articles: List[Dict]) -> List[Optional[int]]:
        """
        Publica una lista de artículos en WordPress.

        Args:
            articles: Lista de artículos a publicar.

        Returns:
            Lista de IDs de posts creados (None para los que fallaron).
        """
        results = []
        for article in articles:
            post_id = self.publish(article)
            results.append(post_id)
        return results

    def get_categories(self) -> List[Dict]:
        """
        Obtiene las categorías disponibles en el sitio WordPress.

        Returns:
            Lista de categorías con 'id' y 'name'.
        """
        # TODO: Implementar usando wordpress_xmlrpc.methods.taxonomies.GetTerms
        raise NotImplementedError("get_categories aún no implementado")

    def update_post(self, post_id: int, article: Dict) -> bool:
        """
        Actualiza un post existente en WordPress.

        Args:
            post_id: ID del post a actualizar.
            article: Nuevos datos del artículo.

        Returns:
            True si la actualización fue exitosa.
        """
        # TODO: Implementar usando wordpress_xmlrpc.methods.posts.EditPost
        raise NotImplementedError("update_post aún no implementado")
