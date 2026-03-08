"""
Paquete de base de datos.
Define modelos ORM y gestión de conexiones con PostgreSQL.
"""

from .database import get_db, init_db
from .models import Article, Source, GeneratedArticle

__all__ = ["get_db", "init_db", "Article", "Source", "GeneratedArticle"]
