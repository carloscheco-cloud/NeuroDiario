"""
Pipeline de Publicación Automática - NeuroDiario Fase 1

Toma artículos procesados de la BD, los envía a Claude para reescritura,
y los publica automáticamente en WordPress citando las fuentes.

Uso:
    python -m neurodiario.scheduler.publishing_pipeline
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class PublishingPipeline:
    """Pipeline que genera y publica artículos automáticamente."""

    def __init__(self):
        """Inicializa el pipeline con configuración."""
        from neurodiario.config.settings import settings
        self.settings = settings
        self._generator = None
        self._publisher = None

    @property
    def generator(self):
        """Carga el generador de artículos bajo demanda."""
        if self._generator is None:
            from neurodiario.generator.article_generator import ArticleGenerator
            self._generator = ArticleGenerator(
                api_key=self.settings.CLAUDE_API_KEY,
                model=self.settings.CLAUDE_MODEL,
            )
        return self._generator

    @property
    def publisher(self):
        """Carga el publicador de WordPress bajo demanda."""
        if self._publisher is None:
            from neurodiario.publisher.wordpress_publisher import WordPressPublisher
            self._publisher = WordPressPublisher(
                url=self.settings.WORDPRESS_URL,
                username=self.settings.WORDPRESS_USER,
                password=self.settings.WORDPRESS_PASSWORD,
            )
        return self._publisher

    def get_articles_to_publish(self, limit: int = 5) -> List[Dict]:
        """
        Obtiene artículos procesados listos para publicar.

        Args:
            limit: Número máximo de artículos a publicar en esta ejecución

        Returns:
            Lista de artículos con metadata completa
        """
        from neurodiario.db.database import get_db
        from neurodiario.db.models import Article
        from sqlalchemy.orm import joinedload

        # Obtener artículos procesados (sin filtro de fecha)
        # que tengan categoría asignada
        try:
            with get_db() as db:
                articles_orm = (
                    db.query(Article)
                    .options(joinedload(Article.source))
                    .filter(
                        Article.processed == True,  # noqa: E712
                        Article.category != None,  # noqa: E711
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
                        "source": a.source.name if a.source else "Medio desconocido",
                        "published_at": a.published_at,
                    })

                return articles

        except Exception as e:
            logger.error(f"Error obteniendo artículos para publicar: {e}")
            return []

    def run_publishing_pipeline(self, max_articles: int = 5) -> int:
        """
        Ejecuta el pipeline completo de generación y publicación.

        Args:
            max_articles: Número máximo de artículos a publicar

        Returns:
            Número de artículos publicados exitosamente
        """
        logger.info("=" * 70)
        logger.info("PIPELINE DE PUBLICACIÓN AUTOMÁTICA")
        logger.info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)

        # PASO 1: Obtener artículos procesados
        logger.info("\n[PASO 1] Obteniendo artículos procesados...")
        articles = self.get_articles_to_publish(limit=max_articles)

        if not articles:
            logger.info("No hay artículos listos para publicar en este momento")
            return 0

        logger.info(f"Artículos encontrados: {len(articles)}")

        # PASO 2: Generar y publicar cada artículo
        logger.info("\n[PASO 2] Generando y publicando artículos...")
        published_count = 0

        for i, article in enumerate(articles, 1):
            try:
                logger.info(f"\n--- Artículo {i}/{len(articles)} ---")
                logger.info(f"Título original: {article['title'][:60]}...")
                logger.info(f"Fuente: {article['source']}")
                logger.info(f"Categoría: {article['category']}")

                # Generar artículo con Claude
                logger.info("  → Generando con Claude AI...")
                generated = self.generator.generate_from_single_article(
                    title=article['title'],
                    content=article['content'],
                    source=article['source'],
                    category=article['category'],
                    url=article['url'],
                    published_at=article['published_at'],
                )

                logger.info(f"  ✓ Generado: {generated['title'][:60]}...")

                # Preparar para WordPress
                wp_article = {
                    "title": generated['title'],
                    "content": generated['content'],
                    "categories": [generated['category'].title()],
                    "tags": generated.get('tags', []),
                    "status": "draft",  # Los artículos quedan como borradores para revisión
                }

                # Publicar en WordPress
                logger.info("  → Publicando en WordPress...")
                post_id = self.publisher.publish(wp_article)

                if post_id:
                    logger.info(f"  ✓ PUBLICADO - WordPress ID: {post_id}")
                    published_count += 1

                    # TODO: Marcar artículo como publicado en BD
                    self._mark_as_published(article['id'], post_id)
                else:
                    logger.error(f"  ✗ Error al publicar en WordPress")

            except Exception as e:
                logger.error(f"  ✗ Error procesando artículo: {e}", exc_info=True)

        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE COMPLETADO")
        logger.info(f"Artículos publicados: {published_count}/{len(articles)}")
        logger.info("=" * 70)

        return published_count

    def _mark_as_published(self, article_id: int, wp_post_id: int) -> None:
        """
        Marca un artículo como publicado en la BD.

        Args:
            article_id: ID del artículo en la BD
            wp_post_id: ID del post en WordPress
        """
        # TODO: Agregar campo 'wordpress_id' a la tabla Article
        # Por ahora solo logueamos
        logger.debug(f"Artículo {article_id} publicado como WP post {wp_post_id}")


def run_publishing_pipeline(max_articles: int = 5) -> int:
    """
    Función de conveniencia para ejecutar el pipeline de publicación.

    Args:
        max_articles: Número máximo de artículos a publicar

    Returns:
        Número de artículos publicados
    """
    pipeline = PublishingPipeline()
    return pipeline.run_publishing_pipeline(max_articles=max_articles)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    run_publishing_pipeline(max_articles=3)
