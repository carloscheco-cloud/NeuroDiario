"""
Módulo de gestión de conexiones a la base de datos.
Configura SQLAlchemy con PostgreSQL y provee sesiones de BD.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from neurodiario.config.settings import settings
from .models import Base

logger = logging.getLogger(__name__)

# Motor de base de datos (singleton)
_engine = None
_SessionLocal = None


def get_engine():
    """Crea o retorna el motor de SQLAlchemy."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,  # Verifica la conexión antes de usarla
            pool_size=5,
            max_overflow=10,
            echo=settings.DEBUG,
        )
        logger.info("Motor de base de datos inicializado")
    return _engine


def get_session_factory():
    """Crea o retorna la fábrica de sesiones."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
        )
    return _SessionLocal


def init_db():
    """
    Crea todas las tablas definidas en los modelos si no existen.
    Debe llamarse al iniciar la aplicación.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Tablas de la base de datos creadas (si no existían)")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager que provee una sesión de base de datos.

    Uso:
        with get_db() as db:
            results = db.query(Article).all()

    La sesión hace commit automáticamente al salir sin errores,
    y rollback si ocurre una excepción.
    """
    SessionLocal = get_session_factory()
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def save_article(article_data: dict) -> bool:
    """
    Guarda un artículo en la BD dentro de una sesión propia.

    Args:
        article_data: Dict con claves title, content/raw_content, source_id,
                      url, published_at, word_count, summary.

    Returns:
        True si se insertó correctamente, False en caso de error o duplicado.
    """
    from .models import Article

    try:
        with get_db() as db:
            if db.query(Article.id).filter(Article.url == article_data["url"]).first():
                logger.debug(f"Artículo ya existe: {article_data['url']}")
                return False

            article = Article(
                title=article_data.get("title", "Sin título"),
                url=article_data["url"],
                summary=article_data.get("summary", ""),
                raw_content=article_data.get("raw_content", article_data.get("content", "")),
                word_count=article_data.get("word_count", 0),
                published_at=article_data.get("published_at"),
                source_id=article_data.get("source_id"),
            )
            db.add(article)
        logger.info(f"Artículo guardado: {article_data['url']}")
        return True
    except Exception as e:
        logger.error(f"Error guardando artículo: {e}")
        return False


def article_exists(url: str) -> bool:
    """
    Verifica si un artículo ya existe en la BD por su URL.

    Args:
        url: URL exacta del artículo.

    Returns:
        True si ya está almacenado, False en caso contrario.
    """
    from .models import Article

    try:
        with get_db() as db:
            return db.query(Article.id).filter(Article.url == url).first() is not None
    except Exception as e:
        logger.error(f"Error verificando existencia de artículo: {e}")
        return False


def get_unprocessed_articles(limit: int = 100) -> list:
    """
    Obtiene artículos que aún no han pasado por el módulo NLP.

    Args:
        limit: Número máximo de artículos a retornar.

    Returns:
        Lista de instancias Article con processed=False.
    """
    from .models import Article

    try:
        with get_db() as db:
            articles = (
                db.query(Article)
                .filter(Article.processed == False)  # noqa: E712
                .order_by(Article.fetched_at.asc())
                .limit(limit)
                .all()
            )
            # Expunge para poder usarlos fuera del contexto de sesión
            for a in articles:
                db.expunge(a)
            return articles
    except Exception as e:
        logger.error(f"Error obteniendo artículos no procesados: {e}")
        return []


def health_check() -> bool:
    """
    Verifica que la conexión a la base de datos esté funcionando.

    Returns:
        True si la conexión es exitosa, False en caso contrario.
    """
    try:
        with get_db() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Error en health check de BD: {e}")
        return False
