"""
WordPress Publisher usando REST API
Reemplazo de XML-RPC para evitar bloqueos 403
"""

import logging
import requests
from typing import Dict, Optional, List
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class WordPressPublisher:
    """
    Publicador de articulos en WordPress usando REST API.
    Mas confiable que XML-RPC y menos propenso a ser bloqueado.
    """

    def __init__(self, url: str, username: str, password: str):
        self.url = url.rstrip('/')
        self.api_url = f"{self.url}/wp-json/wp/v2"
        self.username = username
        self.password = password
        self.auth = HTTPBasicAuth(username, password)

        logger.info("=" * 70)
        logger.info("WORDPRESS PUBLISHER - REST API VERSION")
        logger.info(f"URL: {self.url}")
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"Usuario: {username}")
        logger.info("=" * 70)

    def _upload_image(self, image_url: str, title: str) -> Optional[int]:
        """Descarga una imagen y la sube a WordPress Media Library."""
        try:
            response = requests.get(
                image_url,
                timeout=15,
                headers={"User-Agent": "NeuroDiario/1.0"}
            )
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', 'image/jpeg').split(';')[0]
            ext = {
                'image/jpeg': 'jpg',
                'image/png': 'png',
                'image/webp': 'webp'
            }.get(content_type, 'jpg')

            filename = f"neurodiario-{title[:40].replace(' ', '-').lower()}.{ext}"

            media_response = requests.post(
                f"{self.api_url}/media",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": content_type,
                },
                data=response.content,
                auth=self.auth,
                timeout=30
            )

            if media_response.status_code == 201:
                media_id = media_response.json()['id']
                logger.info(f"Imagen subida a WordPress — Media ID: {media_id}")
                return media_id
            else:
                logger.warning(f"Error subiendo imagen: {media_response.status_code} — {media_response.text[:200]}")
                return None

        except Exception as e:
            logger.warning(f"No se pudo subir imagen desde {image_url}: {e}")
            return None

    def publish(self, article: Dict) -> Optional[int]:
        """
        Publica un articulo en WordPress como borrador.

        Returns:
            ID del post creado, o None si falla
        """
        try:
            logger.info("Usando REST API (NO XML-RPC)")

            category_ids = []
            if article.get('categories'):
                logger.info(f"Procesando categorias: {article['categories']}")
                category_ids = self._get_or_create_categories(article['categories'])

            tag_ids = []
            if article.get('tags'):
                logger.info(f"Procesando tags: {article['tags']}")
                tag_ids = self._get_or_create_tags(article['tags'])

            # Subir imagen destacada si existe  ← NUEVO
            featured_media_id = None
            if article.get('image_url'):
                logger.info(f"  → Subiendo imagen destacada...")
                featured_media_id = self._upload_image(article['image_url'], article['title'])

            post_data = {
                'title': article['title'],
                'content': article['content'],
                'status': article.get('status', 'draft'),
                'categories': category_ids,
                'tags': tag_ids,
            }

            # Asignar imagen destacada si se subió correctamente  ← NUEVO
            if featured_media_id:
                post_data['featured_media'] = featured_media_id
                logger.info(f"  ✓ Imagen destacada asignada — Media ID: {featured_media_id}")

            logger.info(f"Enviando POST a: {self.api_url}/posts")

            response = requests.post(
                f"{self.api_url}/posts",
                json=post_data,
                auth=self.auth,
                timeout=30
            )

            logger.info(f"Respuesta: {response.status_code}")

            if response.status_code == 201:
                post = response.json()
                post_id = post['id']
                logger.info(f"Post creado exitosamente - ID: {post_id}")
                logger.info(f"URL: {post.get('link', 'N/A')}")
                return post_id
            else:
                logger.error(f"Error al crear post: {response.status_code}")
                logger.error(f"Respuesta: {response.text[:500]}")
                return None

        except Exception as e:
            logger.error(f"Excepcion publicando articulo '{article.get('title', 'Sin titulo')}': {e}", exc_info=True)
            return None

    def update_post_content(self, post_id: int, content: str) -> bool:
        """
        Actualiza el contenido de un post ya publicado en WordPress.
        """
        try:
            response = requests.post(
                f"{self.api_url}/posts/{post_id}",
                json={"content": content},
                auth=self.auth,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Post {post_id} actualizado con URL de compartir correcta")
                return True
            else:
                logger.error(f"Error actualizando post {post_id}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Excepcion actualizando post {post_id}: {e}")
            return False

    def _get_or_create_categories(self, category_names: List[str]) -> List[int]:
        category_ids = []

        for name in category_names:
            try:
                response = requests.get(
                    f"{self.api_url}/categories",
                    params={'search': name},
                    auth=self.auth,
                    timeout=10
                )

                if response.status_code == 200:
                    categories = response.json()
                    for cat in categories:
                        if cat['name'].lower() == name.lower():
                            category_ids.append(cat['id'])
                            logger.debug(f"Categoria encontrada: {name} (ID: {cat['id']})")
                            break
                    else:
                        cat_id = self._create_category(name)
                        if cat_id:
                            category_ids.append(cat_id)

            except Exception as e:
                logger.error(f"Error obteniendo categoria '{name}': {e}")

        return category_ids

    def _create_category(self, name: str) -> Optional[int]:
        try:
            response = requests.post(
                f"{self.api_url}/categories",
                json={'name': name},
                auth=self.auth,
                timeout=10
            )

            if response.status_code == 201:
                category = response.json()
                logger.info(f"Categoria creada: {name} (ID: {category['id']})")
                return category['id']
            else:
                logger.error(f"Error creando categoria '{name}': {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error creando categoria '{name}': {e}")
            return None

    def _get_or_create_tags(self, tag_names: List[str]) -> List[int]:
        tag_ids = []

        for name in tag_names:
            try:
                response = requests.get(
                    f"{self.api_url}/tags",
                    params={'search': name},
                    auth=self.auth,
                    timeout=10
                )

                if response.status_code == 200:
                    tags = response.json()
                    for tag in tags:
                        if tag['name'].lower() == name.lower():
                            tag_ids.append(tag['id'])
                            logger.debug(f"Tag encontrado: {name} (ID: {tag['id']})")
                            break
                    else:
                        tag_id = self._create_tag(name)
                        if tag_id:
                            tag_ids.append(tag_id)

            except Exception as e:
                logger.error(f"Error obteniendo tag '{name}': {e}")

        return tag_ids

    def _create_tag(self, name: str) -> Optional[int]:
        try:
            response = requests.post(
                f"{self.api_url}/tags",
                json={'name': name},
                auth=self.auth,
                timeout=10
            )

            if response.status_code == 201:
                tag = response.json()
                logger.info(f"Tag creado: {name} (ID: {tag['id']})")
                return tag['id']
            else:
                logger.error(f"Error creando tag '{name}': {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error creando tag '{name}': {e}")
            return None
