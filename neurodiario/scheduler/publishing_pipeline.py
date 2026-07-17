"""
Pipeline de Publicación Automática - NeuroDiario Fase 1

Toma artículos procesados de la BD, los envía a OpenAI para reescritura,
y los publica automáticamente en WordPress citando las fuentes.

Incluye:
- Auto-limpieza de artículos atascados en estado "processing"
- Publicación automática en Facebook al pasar a "published" en WordPress
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# FEATURE FLAGS
# ─────────────────────────────────────────────
USE_FACEBOOK_POSTING = True   # Cambiar a False para desactivar Facebook sin borrar código
PROCESSING_TIMEOUT_MINUTES = 30  # Artículos en "processing" por más de esto se limpian


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
                api_key=self.settings.OPENAI_API_KEY,
                model=self.settings.OPENAI_MODEL,
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

    # ─────────────────────────────────────────────
    # LIMPIEZA AUTOMÁTICA DE "PROCESSING" ATASCADOS
    # ─────────────────────────────────────────────

    def cleanup_stuck_processing(self) -> int:
        """
        Libera artículos que quedaron atascados en estado 'processing'
        por más de PROCESSING_TIMEOUT_MINUTES minutos.
        Esto evita que bloqueen el pipeline en ciclos posteriores.
        """
        from neurodiario.db.database import get_db
        from neurodiario.db.models import GeneratedArticle

        cutoff = datetime.utcnow() - timedelta(minutes=PROCESSING_TIMEOUT_MINUTES)
        cleaned = 0

        try:
            with get_db() as db:
                stuck = db.query(GeneratedArticle).filter(
                    GeneratedArticle.status == "processing",
                    GeneratedArticle.created_at < cutoff,
                ).all()

                for record in stuck:
                    record.status = "failed"
                    cleaned += 1

                if cleaned:
                    db.commit()
                    logger.info(f"  🧹 Auto-limpieza: {cleaned} artículo(s) atascados en 'processing' → marcados como 'failed'")
                else:
                    logger.info("  🧹 Auto-limpieza: sin artículos atascados.")

        except Exception as e:
            logger.error(f"Error en auto-limpieza de processing: {e}")

        return cleaned

    # ─────────────────────────────────────────────
    # FACEBOOK POSTING
    # ─────────────────────────────────────────────

    def post_to_facebook(self, title: str, wordpress_url: str, image_url: Optional[str] = None) -> Optional[str]:
        """
        Publica un artículo en Facebook con imagen generada.
        Retorna el ID del post de Facebook si fue exitoso, None si falló.
        """
        if not USE_FACEBOOK_POSTING:
            logger.info("  📘 Facebook posting desactivado (USE_FACEBOOK_POSTING=False)")
            return None

        page_token = getattr(self.settings, 'FACEBOOK_PAGE_TOKEN', None)
        page_id = getattr(self.settings, 'FACEBOOK_PAGE_ID', None)

        if not page_token or not page_id:
            logger.warning("  📘 Facebook: faltan FACEBOOK_PAGE_TOKEN o FACEBOOK_PAGE_ID en settings — saltando")
            return None

        try:
            from neurodiario.publisher.facebook_image_generator import post_to_facebook_with_image

            fb_post_id = post_to_facebook_with_image(
                title=title,
                wordpress_url=wordpress_url,
                page_id=page_id,
                page_token=page_token,
                image_url=image_url,
            )
            return fb_post_id

        except Exception as e:
            logger.error(f"  📘 Facebook: excepción al publicar — {e}")
            return None

    # ─────────────────────────────────────────────
    # OBTENER ARTÍCULOS
    # ─────────────────────────────────────────────

    def get_articles_to_publish(self, limit: int = 10) -> List[Dict]:
        """
        Obtiene artículos procesados que AÚN NO han sido publicados en WordPress.
        Filtra por: processed=True, category asignada, y SIN GeneratedArticle asociado.
        """
        from neurodiario.db.database import get_db
        from neurodiario.db.models import Article, GeneratedArticle
        from sqlalchemy.orm import joinedload

        try:
            with get_db() as db:
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
                        ~Article.id.in_(already_published),
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
                        "image_url": a.image_url,
                    })

                logger.info(f"Artículos disponibles para publicar: {len(articles)}")
                return articles

        except Exception as e:
            logger.error(f"Error obteniendo artículos para publicar: {e}")
            return []

    # ─────────────────────────────────────────────
    # PIPELINE PRINCIPAL
    # ─────────────────────────────────────────────

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

        # PASO 0: Limpieza de artículos atascados
        logger.info("\n[PASO 0] Auto-limpieza de artículos atascados...")
        self.cleanup_stuck_processing()

        logger.info("\n[PASO 1] Obteniendo artículos pendientes...")
        articles = self.get_articles_to_publish(limit=max_articles)

        if not articles:
            logger.info("No hay artículos nuevos para publicar en este momento.")
            return 0

        logger.info(f"Artículos a procesar: {len(articles)}")

        logger.info("\n[PASO 2] Generando y publicando artículos...")
        published_count = 0

        for i, article in enumerate(articles, 1):
            try:
                logger.info(f"\n--- Artículo {i}/{len(articles)} ---")
                logger.info(f"Título: {article['title'][:70]}")
                logger.info(f"Fuente: {article['source']} | Categoría: {article['category']}")
                logger.info(f"Imagen: {article.get('image_url') or 'sin imagen'}")

                generated_record_id = self._reserve_article(article['id'])
                if not generated_record_id:
                    logger.warning(f"  ⚠ No se pudo reservar artículo {article['id']} — saltando")
                    continue

                logger.info("  → Generando con OpenAI...")
                generated = self.generator.generate_from_single_article(
                    title=article['title'],
                    content=article['content'],
                    source=article['source'],
                    category=article['category'],
                    url=article['url'],
                    published_at=article['published_at'],
                    wordpress_url="",
                )
                logger.info(f"  ✓ Generado: {generated['title'][:60]}")

                wp_article = {
                    "title": generated['title'],
                    "content": generated['content'],
                    "categories": [generated['category'].title()],
                    "tags": generated.get('tags', []),
                    "status": "draft",
                    "image_url": generated.get('image_url'),
                }

                logger.info("  → Publicando en WordPress...")
                post_id = self.publisher.publish(wp_article)

                if post_id:
                    wp_base = self.settings.WORDPRESS_URL.rstrip('/')
                    wordpress_url = f"{wp_base}/?p={post_id}"
                    logger.info(f"  ✓ PUBLICADO — WordPress ID: {post_id} | URL: {wordpress_url}")

                    final_content = self.generator._replace_share_url(
                        generated['content'], wordpress_url
                    )

                    self.publisher.update_post_content(post_id, final_content)

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

                    # ── FACEBOOK: se publica cuando apruebes el borrador manualmente ──
                    # El flujo es: WordPress draft → tú apruebas → WordPress published → Facebook
                    # Esto se maneja en el webhook de WordPress (ver facebook_webhook.py)
                    # Por ahora guardamos la URL para cuando se apruebe
                    logger.info(f"  📘 Facebook: artículo en borrador — se publicará en FB cuando apruebes en WordPress")

                else:
                    logger.error(f"  ✗ Error publicando en WordPress — marcando como fallido")
                    self._mark_as_failed(generated_record_id)

            except Exception as e:
                logger.error(f"  ✗ Error procesando artículo {article.get('id')}: {e}", exc_info=True)

        logger.info("\n" + "=" * 70)
        logger.info(f"PIPELINE COMPLETADO — Publicados: {published_count}/{len(articles)}")
        logger.info("=" * 70)

        return published_count

    # ─────────────────────────────────────────────
    # FACEBOOK: PUBLICAR AL APROBAR BORRADOR
    # ─────────────────────────────────────────────

    def publish_approved_to_facebook(self) -> int:
        """
        Busca artículos aprobados en WordPress (status='published') que
        aún no se han publicado en Facebook, y los publica.
        
        Este método se llama en cada ciclo del scheduler, DESPUÉS del pipeline principal.
        Así cuando tú apruebas un borrador en WordPress, en el próximo ciclo
        (máx. 8 minutos) se publica automáticamente en Facebook.
        """
        from neurodiario.db.database import get_db
        from neurodiario.db.models import GeneratedArticle

        if not USE_FACEBOOK_POSTING:
            return 0

        fb_count = 0

        try:
            with get_db() as db:
                # Busca artículos que están en WordPress como "published"
                # pero que aún no tienen facebook_post_id
                pending_fb = db.query(GeneratedArticle).filter(
                    GeneratedArticle.status == "published",
                    GeneratedArticle.facebook_post_id == None,   # noqa: E711
                    GeneratedArticle.wordpress_post_id != None,  # noqa: E711
                ).all()

                if not pending_fb:
                    logger.info("  📘 Facebook: sin artículos aprobados pendientes de publicar.")
                    return 0

                logger.info(f"  📘 Facebook: {len(pending_fb)} artículo(s) aprobados para publicar en FB...")

                for record in pending_fb:
                    wp_base = self.settings.WORDPRESS_URL.rstrip('/')
                    wordpress_url = f"{wp_base}/?p={record.wordpress_post_id}"

                    # Obtener image_url del artículo fuente
                    image_url = None
                    if record.source_article_id:
                        from neurodiario.db.models import Article
                        source = db.query(Article).filter(
                            Article.id == record.source_article_id
                        ).first()
                        if source:
                            image_url = source.image_url

                    fb_post_id = self.post_to_facebook(
                        title=record.title,
                        wordpress_url=wordpress_url,
                        image_url=image_url,
                    )

                    if fb_post_id:
                        record.facebook_post_id = fb_post_id
                        record.facebook_posted_at = datetime.utcnow()
                        fb_count += 1

                db.commit()

        except Exception as e:
            logger.error(f"Error publicando aprobados en Facebook: {e}")

        return fb_count

    # ─────────────────────────────────────────────
    # HELPERS DE BD
    # ─────────────────────────────────────────────

    def _reserve_article(self, article_id: int) -> Optional[int]:
        from neurodiario.db.database import get_db
        from neurodiario.db.models import GeneratedArticle

        try:
            with get_db() as db:
                existing = db.query(GeneratedArticle).filter(
                    GeneratedArticle.source_article_id == article_id,
                    GeneratedArticle.status.in_(["processing", "draft", "published"])
                ).first()

                if existing:
                    logger.debug(f"Artículo {article_id} ya reservado (GeneratedArticle {existing.id})")
                    return None

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
    result = pipeline.run_publishing_pipeline(max_articles=max_articles)

    # Después del pipeline principal, verificar aprobados para Facebook
    logger.info("\n[PASO 3] Verificando artículos aprobados para Facebook...")
    pipeline.publish_approved_to_facebook()

    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    run_publishing_pipeline(max_articles=10)
