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
    Publicador de artículos en WordPress usando REST API.
    
    Más confiable que XML-RPC y menos propenso a ser bloqueado.
    """

    def __init__(self, url: str, username: str, password: str):
        """
        Inicializa el publicador con credenciales de WordPress.
        
        Args:
            url: URL base del sitio WordPress (ej: https://neurodiario.com)
            username: Nombre de usuario de WordPress
            password: Contraseña de aplicación de WordPress
        """
        self.url = url.rstrip('/')
        self.api_url = f"{self.url}/wp-json/wp/v2"
        self.username = username
        self.password = password
        self.auth = HTTPBasicAuth(username, password)
        
        logger.info(f"WordPress Publisher inicializado: {self.url}")

    def publish(self, article: Dict) -> Optional[int]:
        """
        Publica un artículo en WordPress como borrador.
        
        Args:
            article: Diccionario con:
                - title: Título del artículo
                - content: Contenido HTML del artículo
                - categories: Lista de nombres de categorías (opcional)
                - tags: Lista de nombres de tags (opcional)
                - status: 'draft' o 'publish' (por defecto: 'draft')
        
        Returns:
            ID del post creado, o None si falla
        """
        try:
            # 1. Obtener/crear categorías
            category_ids = []
            if article.get('categories'):
                category_ids = self._get_or_create_categories(article['categories'])
            
            # 2. Obtener/crear tags
            tag_ids = []
            if article.get('tags'):
                tag_ids = self._get_or_create_tags(article['tags'])
            
            # 3. Crear el post
            post_data = {
                'title': article['title'],
                'content': article['content'],
                'status': article.get('status', 'draft'),
                'categories': category_ids,
                'tags': tag_ids,
            }
            
            response = requests.post(
                f"{self.api_url}/posts",
                json=post_data,
                auth=self.auth,
                timeout=30
            )
            
            if response.status_code == 201:
                post = response.json()
                post_id = post['id']
                logger.info(f"✓ Post creado exitosamente - ID: {post_id}")
                return post_id
            else:
                logger.error(f"Error al crear post: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error publicando artículo '{article.get('title', 'Sin título')}': {e}")
            return None

    def _get_or_create_categories(self, category_names: List[str]) -> List[int]:
        """
        Obtiene IDs de categorías, creándolas si no existen.
        
        Args:
            category_names: Lista de nombres de categorías
            
        Returns:
            Lista de IDs de categorías
        """
        category_ids = []
        
        for name in category_names:
            try:
                # Buscar categoría existente
                response = requests.get(
                    f"{self.api_url}/categories",
                    params={'search': name},
                    auth=self.auth,
                    timeout=10
                )
                
                if response.status_code == 200:
                    categories = response.json()
                    
                    # Buscar coincidencia exacta
                    for cat in categories:
                        if cat['name'].lower() == name.lower():
                            category_ids.append(cat['id'])
                            logger.debug(f"Categoría encontrada: {name} (ID: {cat['id']})")
                            break
                    else:
                        # No existe, crear nueva
                        cat_id = self._create_category(name)
                        if cat_id:
                            category_ids.append(cat_id)
                            
            except Exception as e:
                logger.error(f"Error obteniendo categoría '{name}': {e}")
        
        return category_ids

    def _create_category(self, name: str) -> Optional[int]:
        """
        Crea una nueva categoría en WordPress.
        
        Args:
            name: Nombre de la categoría
            
        Returns:
            ID de la categoría creada, o None si falla
        """
        try:
            response = requests.post(
                f"{self.api_url}/categories",
                json={'name': name},
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code == 201:
                category = response.json()
                logger.info(f"✓ Categoría creada: {name} (ID: {category['id']})")
                return category['id']
            else:
                logger.error(f"Error creando categoría '{name}': {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creando categoría '{name}': {e}")
            return None

    def _get_or_create_tags(self, tag_names: List[str]) -> List[int]:
        """
        Obtiene IDs de tags, creándolos si no existen.
        
        Args:
            tag_names: Lista de nombres de tags
            
        Returns:
            Lista de IDs de tags
        """
        tag_ids = []
        
        for name in tag_names:
            try:
                # Buscar tag existente
                response = requests.get(
                    f"{self.api_url}/tags",
                    params={'search': name},
                    auth=self.auth,
                    timeout=10
                )
                
                if response.status_code == 200:
                    tags = response.json()
                    
                    # Buscar coincidencia exacta
                    for tag in tags:
                        if tag['name'].lower() == name.lower():
                            tag_ids.append(tag['id'])
                            logger.debug(f"Tag encontrado: {name} (ID: {tag['id']})")
                            break
                    else:
                        # No existe, crear nuevo
                        tag_id = self._create_tag(name)
                        if tag_id:
                            tag_ids.append(tag_id)
                            
            except Exception as e:
                logger.error(f"Error obteniendo tag '{name}': {e}")
        
        return tag_ids

    def _create_tag(self, name: str) -> Optional[int]:
        """
        Crea un nuevo tag en WordPress.
        
        Args:
            name: Nombre del tag
            
        Returns:
            ID del tag creado, o None si falla
        """
        try:
            response = requests.post(
                f"{self.api_url}/tags",
                json={'name': name},
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code == 201:
                tag = response.json()
                logger.info(f"✓ Tag creado: {name} (ID: {tag['id']})")
                return tag['id']
            else:
                logger.error(f"Error creando tag '{name}': {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creando tag '{name}': {e}")
            return None
