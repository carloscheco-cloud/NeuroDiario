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
