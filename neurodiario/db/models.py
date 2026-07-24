"""
Modelos ORM de la base de datos de NeuroDiario.
Define las tablas: fuentes, artículos crudos y artículos generados.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Clase base para todos los modelos ORM."""
    pass


class Source(Base):
    """Representa una fuente de noticias (medio dominicano)."""

    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), unique=True, nullable=False)
    category = Column(String(100), default="general")
    language = Column(String(10), default="es")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    articles = relationship("Article", back_populates="source")

    def __repr__(self):
        return f"<Source(name='{self.name}', url='{self.url}')>"


class Article(Base):
    """Representa un artículo de noticias obtenido desde una fuente RSS."""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False)
    summary = Column(Text, nullable=True)
    raw_html = Column(Text, nullable=True)
    raw_content = Column(Text, default="")
    clean_content = Column(Text, default="")
    word_count = Column(Integer, default=0)
    image_url = Column(String(1000), nullable=True)

    # Metadatos de clasificación NLP
    category = Column(String(100), default="general")
    category_confidence = Column(Float, default=0.0)
    entities = Column(JSON, default=dict)

    # Control de flujo
    processed = Column(Boolean, default=False)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    source = relationship("Source", back_populates="articles")

    generated_articles = relationship("GeneratedArticle", back_populates="source_article")

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title[:50]}...')>"


class Trend(Base):
    """Representa una tendencia temática detectada por el Módulo 4."""

    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(500), nullable=False)
    article_count = Column(Integer, default=0)
    sources = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Trend(id={self.id}, topic='{self.topic[:50]}', articles={self.article_count})>"


class GeneratedArticle(Base):
    """Representa un artículo generado por IA y publicado en WordPress."""

    __tablename__ = "generated_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    article_type = Column(String(50), default="summary")
    category = Column(String(100), default="general")
    tags = Column(JSON, default=list)

    # Estado de publicación
    status = Column(String(50), default="draft")  # draft, published, failed
    wordpress_post_id = Column(Integer, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Facebook
    facebook_post_id = Column(String(200), nullable=True)
    facebook_posted_at = Column(DateTime, nullable=True)

    # Telegram
    telegram_message_id = Column(String(50), nullable=True)
    telegram_posted_at = Column(DateTime, nullable=True)

    # Metadatos del modelo usado
    model_used = Column(String(100), default="gpt-4o-mini")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)

    source_article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)
    source_article = relationship("Article", back_populates="generated_articles")

    def __repr__(self):
        return f"<GeneratedArticle(id={self.id}, status='{self.status}', type='{self.article_type}')>"

class MediaAsset(Base):
    """
    Representa un recurso multimedia reutilizable de NeuroDiario:
    fotos, caricaturas, ilustraciones e imágenes subidas a WordPress.
    """

    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True)

    # Entidad o tema asociado
    entity_name = Column(String(250), nullable=True, index=True)
    entity_type = Column(String(100), nullable=True, index=True)
    topic = Column(String(300), nullable=True, index=True)
    context = Column(Text, nullable=True)

    # Tipo de recurso
    media_type = Column(String(50), default="image", index=True)
    usage_type = Column(String(100), nullable=True, index=True)

    # Origen del recurso
    source_provider = Column(String(100), nullable=True, index=True)
    source_url = Column(String(1000), nullable=True)
    local_path = Column(String(1000), nullable=True)

    # WordPress Media Library
    wordpress_media_id = Column(Integer, nullable=True, index=True)
    wordpress_url = Column(String(1000), nullable=True)

    # Control editorial
    priority = Column(Integer, default=50, index=True)
    quality_score = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True, index=True)
    is_approved = Column(Boolean, default=False, index=True)
    notes = Column(Text, nullable=True)

    # Uso
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)

    # Metadata flexible
    extra_metadata = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<MediaAsset(id={self.id}, entity='{self.entity_name}', "
            f"type='{self.media_type}', wp_id={self.wordpress_media_id})>"
        )

