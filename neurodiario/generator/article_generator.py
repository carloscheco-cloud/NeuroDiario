"""
NeuroDiario - Auto Scheduler
Flujo de producción normal para ~100 artículos diarios.
Intervalos:
- Cada 3 min:  Ingesta RSS
- Cada 6 min:  Procesamiento NLP
- Cada 8 min:  Generación + Publicación (10 artículos por ciclo)
- Cada 5 min:  Sincronización WordPress → Facebook
"""
import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler
from neurodiario.scheduler.pipeline import run_ingestion_pipeline
from neurodiario.scheduler.nlp_pipeline import run_nlp_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _job_ingestion():
    logger.info("=" * 60)
    logger.info("JOB: Ingesta RSS")
    logger.info("=" * 60)
    try:
        run_ingestion_pipeline()
    except Exception as e:
        logger.error(f"Error en ingesta RSS: {e}", exc_info=True)


def _job_nlp():
    logger.info("=" * 60)
    logger.info("JOB: Pipeline NLP")
    logger.info("=" * 60)
    try:
        run_nlp_pipeline(batch_size=50)
    except Exception as e:
        logger.error(f"Error en pipeline NLP: {e}", exc_info=True)


def _job_publishing():
    logger.info("=" * 60)
    logger.info("JOB: Generación y Publicación")
    logger.info("=" * 60)
    try:
        from neurodiario.scheduler.publishing_pipeline import run_publishing_pipeline
        published = run_publishing_pipeline(max_articles=10)
        logger.info(f"Publicados en este ciclo: {published} artículos")
    except Exception as e:
        logger.error(f"ERROR EN PUBLICACIÓN: {e}", exc_info=True)


def _job_facebook_sync():
    """
    Consulta WordPress para detectar artículos que pasaron de draft a published,
    actualiza el status en la BD y los publica en Facebook con imagen.
    """
    logger.info("=" * 60)
    logger.info("JOB: Sincronización WordPress → Facebook")
    logger.info("=" * 60)
    try:
        from neurodiario.config.settings import settings
        from neurodiario.db.database import get_db
        from neurodiario.db.models import GeneratedArticle, Article
        from neurodiario.publisher.facebook_image_generator import post_to_facebook_with_image
        import requests

        page_token = getattr(settings, 'FACEBOOK_PAGE_TOKEN', None)
        page_id = getattr(settings, 'FACEBOOK_PAGE_ID', None)

        if not page_token or not page_id:
            logger.warning("  📘 Facebook sync: faltan variables FACEBOOK_PAGE_TOKEN o FACEBOOK_PAGE_ID")
            return

        wp_base = settings.WORDPRESS_URL.rstrip('/')
        auth = (settings.WORDPRESS_USER, settings.WORDPRESS_PASSWORD)

        with get_db() as db:
            # Buscar artículos en BD con status "draft" que tienen wordpress_post_id
            # y que aún no fueron posteados en Facebook
            pending = db.query(GeneratedArticle).filter(
                GeneratedArticle.status == "draft",
                GeneratedArticle.wordpress_post_id != None,   # noqa: E711
                GeneratedArticle.facebook_post_id == None,    # noqa: E711
            ).all()

            if not pending:
                logger.info("  📘 Facebook sync: sin artículos pendientes.")
                return

            logger.info(f"  📘 Facebook sync: verificando {len(pending)} artículo(s) en WordPress...")

            for record in pending:
                try:
                    # Consultar WordPress para ver si fue aprobado (status = publish)
                    wp_url = f"{wp_base}/wp-json/wp/v2/posts/{record.wordpress_post_id}"
                    response = requests.get(wp_url, auth=auth, timeout=10)

                    if response.status_code != 200:
                        logger.debug(f"  WP post {record.wordpress_post_id}: status HTTP {response.status_code}")
                        continue

                    wp_post = response.json()
                    wp_status = wp_post.get("status", "")

                    if wp_status != "publish":
                        logger.debug(f"  WP post {record.wordpress_post_id}: aún en '{wp_status}' — saltando")
                        continue

                    # ¡Fue aprobado! Actualizar BD y publicar en Facebook
                    logger.info(f"  ✓ WP post {record.wordpress_post_id} está publicado — enviando a Facebook...")

                    # Actualizar status en BD
                    record.status = "published"

                    # Obtener image_url del artículo fuente
                    image_url = None
                    if record.source_article_id:
                        source = db.query(Article).filter(
                            Article.id == record.source_article_id
                        ).first()
                        if source:
                            image_url = source.image_url

                    # Obtener permalink real de WordPress
                    try:
                        wp_resp = requests.get(
                            f"{wp_base}/wp-json/wp/v2/posts/{record.wordpress_post_id}",
                            auth=auth, timeout=10
                        )
                        wordpress_url = wp_resp.json().get("link", f"{wp_base}/?p={record.wordpress_post_id}")
                    except Exception:
                        wordpress_url = f"{wp_base}/?p={record.wordpress_post_id}"

                    # Publicar en Facebook con imagen
                    fb_post_id = post_to_facebook_with_image(
                        title=record.title,
                        wordpress_url=wordpress_url,
                        page_id=page_id,
                        page_token=page_token,
                        image_url=image_url,
                    )

                    if fb_post_id:
                        from datetime import datetime
                        record.facebook_post_id = fb_post_id
                        record.facebook_posted_at = datetime.utcnow()
                        logger.info(f"  📘 Facebook: publicado — ID {fb_post_id}")
                    else:
                        logger.error(f"  📘 Facebook: falló la publicación del post {record.wordpress_post_id}")

                except Exception as e:
                    logger.error(f"  Error procesando WP post {record.wordpress_post_id}: {e}")

            db.commit()

    except Exception as e:
        logger.error(f"ERROR EN FACEBOOK SYNC: {e}", exc_info=True)


def start_scheduler() -> BackgroundScheduler:
    logger.info("=" * 60)
    logger.info("NeuroDiario Scheduler — MODO PRODUCCIÓN")
    logger.info("  Ingesta RSS:    cada 3 minutos")
    logger.info("  NLP:            cada 6 minutos")
    logger.info("  Publicación:    cada 8 minutos (10 artículos)")
    logger.info("  Facebook sync:  cada 5 minutos")
    logger.info("=" * 60)

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        _job_ingestion,
        trigger="interval",
        minutes=3,
        id="ingestion_rss",
        name="Ingesta RSS",
        replace_existing=True,
    )

    scheduler.add_job(
        _job_nlp,
        trigger="interval",
        minutes=6,
        id="nlp_pipeline",
        name="Pipeline NLP",
        replace_existing=True,
    )

    scheduler.add_job(
        _job_publishing,
        trigger="interval",
        minutes=8,
        id="publishing_pipeline",
        name="Generación y Publicación",
        replace_existing=True,
    )

    scheduler.add_job(
        _job_facebook_sync,
        trigger="interval",
        minutes=5,
        id="facebook_sync",
        name="Sincronización WordPress→Facebook",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("✓ Scheduler iniciado")
    return scheduler


if __name__ == "__main__":
    scheduler = start_scheduler()
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("NeuroDiario Scheduler detenido")
