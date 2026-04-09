"""
Pipeline de Publicación Automática - NeuroDiario Fase 1

Toma artículos procesados de la BD, los envía a Claude para reescritura,
y los publica automáticamente en WordPress citando las fuentes.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class PublishingPipeline:
    """Pipeline que genera y publica artículos automáticamente."""

    def __init__(self):
        from neurodiario.config.settings import settings
        self.settings = settings
        self._generator = None
        self._publisher = None

    @property
    def generator(self):
        if self._generator is None:
            from neurodiario.generator.article_generator import ArticleGenerator
            self._generator = ArticleGenerator(
                api_key=self.settings.CLAUDE_API_KEY,
                model=self.settings.CLAUDE_MODEL,
            )
        return self._generator

    @property
    def publisher(self):
        if self._publisher is None:
            from neurodiario.publisher.wordpress_publisher import WordPressPublisher
            self._publisher = WordPressPublisher(
                url=self.settings.WORDPRESS_URL,
                username=self.settings.WORDPRESS_USER,
                password=self.settings.WORDPRESS_PASSWORD,
            )
        return self._publisher

    def get_articles_to_publish(self, limit: int = 10) -> List[Dict]:
        """
        Obtiene artículos procesados que AÚN NO han sido publicados en WordPress.
        Filtra por: processed=True, category asignada, y SIN GeneratedArticle asociado.
        """
        from neurodiario.db.database import get_db
        from neurodiario.db.models import Article, GeneratedArticle
        from sqlalchemy.orm import joinedload
        from sqlalchemy import not_, exists

        try:
            with get_db() as db:
                # Subconsulta: IDs de artículos que ya tienen un GeneratedArticle publicado o en draft
                already_published = (
                    db.query(GeneratedArticle.source_article_id)
                    .filter(
                        GeneratedArticle.source_article_id != None,
                        GeneratedArticle.status.in_(["draft", "published"])
                    )
                    .subquery()
                )

                articles_orm = (
                    db.query(Article)
                    .options(joinedload(Article.source))
                    .filter(
                        Article.processed == True,        # noqa: E712
                        Article.category != None,         # noqa: E711
                        ~Article.id.in_(already_published),  # NO publicados aún
                    )
                    .order_by(Article.fetched_at.desc())
                    .limit(limit)
                    .all()
                )

                articles = []
                for a in articles_orm:
                    articles.append({
                        "id": a.id,
                        "title": a.title,
                        "content": a.clean_content or a.raw_content,
                        "summary": a.summary,
                        "category": a.category,
                        "entities": a.entities,
                        "url": a.url,
                        "source": a.source.name if a.source else "fuente local",
                        "published_at": a.published_at,
                    })

                logger.info(f"Artículos disponibles para publicar: {len(articles)}")
                return articles

        except Exception as e:
            logger.error(f"Error obteniendo artículos para publicar: {e}")
            return []

    def run_publishing_pipeline(self, max_articles: int = 10) -> int:
        """
        Ejecuta el pipeline completo de generación y publicación.

        Returns:
            Número de artículos publicados exitosamente
        """
        logger.info("=" * 70)
        logger.info("PIPELINE DE PUBLICACIÓN AUTOMÁTICA")
        logger.info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)

        # PASO 1: Obtener artículos NO publicados aún
        logger.info("\n[PASO 1] Obteniendo artículos pendientes...")
        articles = self.get_articles_to_publish(limit=max_articles)

        if not articles:
            logger.info("No hay artículos nuevos para publicar en este momento.")
            return 0

        logger.info(f"Artículos a procesar: {len(articles)}")

        # PASO 2: Generar y publicar cada artículo
        logger.info("\n[PASO 2] Generando y publicando artículos...")
        published_count = 0

        for i, article in enumerate(articles, 1):
            try:
                logger.info(f"\n--- Artículo {i}/{len(articles)} ---")
                logger.info(f"Título: {article['title'][:70]}")
                logger.info(f"Fuente: {article['source']} | Categoría: {article['category']}")

                # IMPORTANTE: Registrar en BD ANTES de generar para evitar
                # que otro ciclo concurrente tome el mismo artículo
                generated_record_id = self._reserve_article(article['id'])
                if not generated_record_id:
                    logger.warning(f"  ⚠ No se pudo reservar artículo {article['id']} — saltando")
                    continue

                # Generar artículo con Claude (sin wordpress_url aún — se actualiza después)
                logger.info("  → Generando con Claude AI...")
                generated = self.generator.generate_from_single_article(
                    title=article['title'],
                    content=article['content'],
                    source=article['source'],
                    category=article['category'],
                    url=article['url'],
                    published_at=article['published_at'],
                    wordpress_url="",  # Se actualizará tras publicar
                )
                logger.info(f"  ✓ Generado: {generated['title'][:60]}")

                # Preparar para WordPress
                wp_article = {
                    "title": generated['title'],
                    "content": generated['content'],
                    "categories": [generated['category'].title()],
                    "tags": generated.get('tags', []),
                    "status": "draft",
                }

                # Publicar en WordPress
                logger.info("  → Publicando en WordPress...")
                post_id = self.publisher.publish(wp_article)

                if post_id:
                    # Construir URL real del post en NeuroDiario
                    wp_base = self.settings.WORDPRESS_URL.rstrip('/')
                    wordpress_url = f"{wp_base}/?p={post_id}"
                    logger.info(f"  ✓ PUBLICADO — WordPress ID: {post_id} | URL: {wordpress_url}")

                    # Regenerar los botones compartir con la URL real de NeuroDiario
                    final_content = self.generator._replace_share_url(
                        generated['content'], wordpress_url
                    )

                    self._mark_as_published(
                        generated_record_id=generated_record_id,
                        article_id=article['id'],
                        wp_post_id=post_id,
                        title=generated['title'],
                        content=final_content,
                        category=article['category'],
                        tags=generated.get('tags', []),
                    )
                    published_count += 1
                else:
                    logger.error(f"  ✗ Error publicando en WordPress — marcando como fallido")
                    self._mark_as_failed(generated_record_id)

            except Exception as e:
                logger.error(f"  ✗ Error procesando artículo {article.get('id')}: {e}", exc_info=True)

        logger.info("\n" + "=" * 70)
        logger.info(f"PIPELINE COMPLETADO — Publicados: {published_count}/{len(articles)}")
        logger.info("=" * 70)

        return published_count

    def _reserve_article(self, article_id: int) -> Optional[int]:
        """
        Crea un registro GeneratedArticle en estado 'processing' para
        reservar el artículo y evitar duplicados en ciclos concurrentes.

        Returns:
            ID del GeneratedArticle creado, o None si ya estaba reservado
        """
        from neurodiario.db.database import get_db
        from neurodiario.db.models import GeneratedArticle

        try:
            with get_db() as db:
                # Verificar que no exista ya un registro para este artículo
                existing = db.query(GeneratedArticle).filter(
                    GeneratedArticle.source_article_id == article_id,
                    GeneratedArticle.status.in_(["processing", "draft", "published"])
                ).first()

                if existing:
                    logger.debug(f"Artículo {article_id} ya reservado (GeneratedArticle {existing.id})")
                    return None

                # Crear registro de reserva
                record = GeneratedArticle(
                    title="[generando...]",
                    content="",
                    source_article_id=article_id,
                    status="processing",
                    created_at=datetime.utcnow(),
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                logger.debug(f"Artículo {article_id} reservado como GeneratedArticle {record.id}")
                return record.id

        except Exception as e:
            logger.error(f"Error reservando artículo {article_id}: {e}")
            return None

    def _mark_as_published(
        self,
        generated_record_id: int,
        article_id: int,
        wp_post_id: int,
        title: str,
        content: str,
        category: str,
        tags: list,
    ) -> None:
        """Actualiza el GeneratedArticle con el resultado exitoso."""
        from neurodiario.db.database import get_db
        from neurodiario.db.models import GeneratedArticle

        try:
            with get_db() as db:
                record = db.query(GeneratedArticle).filter(
                    GeneratedArticle.id == generated_record_id
                ).first()

                if record:
                    record.title = title
                    record.content = content
                    record.category = category
                    record.tags = tags
                    record.status = "draft"
                    record.wordpress_post_id = wp_post_id
                    record.published_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"  ✓ BD actualizada — GeneratedArticle {generated_record_id} → draft (WP:{wp_post_id})")

        except Exception as e:
            logger.error(f"Error marcando artículo como publicado: {e}")

    def _mark_as_failed(self, generated_record_id: int) -> None:
        """Marca el GeneratedArticle como fallido para que pueda reintentarse."""
        from neurodiario.db.database import get_db
        from neurodiario.db.models import GeneratedArticle

        try:
            with get_db() as db:
                record = db.query(GeneratedArticle).filter(
                    GeneratedArticle.id == generated_record_id
                ).first()
                if record:
                    record.status = "failed"
                    db.commit()
        except Exception as e:
            logger.error(f"Error marcando artículo como fallido: {e}")


def run_publishing_pipeline(max_articles: int = 10) -> int:
    pipeline = PublishingPipeline()
    return pipeline.run_publishing_pipeline(max_articles=max_articles)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    run_publishing_pipeline(max_articles=10)
