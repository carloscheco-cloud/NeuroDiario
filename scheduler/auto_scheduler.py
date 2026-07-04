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
    Busca en WordPress posts publicados en los últimos 30 minutos,
    cruza con la BD, y publica en Facebook los que no tienen facebook_post_id.
    """
    logger.info("=" * 60)
    logger.info("JOB: Sincronización WordPress → Facebook")
    logger.info("=" * 60)
    try:
        from neurodiario.config.settings import settings
        from neurodiario.db.database import get_db
        from neurodiario.db.models import GeneratedArticle
        from neurodiario.publisher.facebook_image_generator import post_to_facebook_with_image
        from datetime import datetime, timedelta
        import requests

        page_token = getattr(settings, 'FACEBOOK_PAGE_TOKEN', None)
        page_id = getattr(settings, 'FACEBOOK_PAGE_ID', None)

        if not page_token or not page_id:
            logger.warning("  📘 Facebook sync: faltan FACEBOOK_PAGE_TOKEN o FACEBOOK_PAGE_ID")
            return

        wp_base = settings.WORDPRESS_URL.rstrip('/')
        auth = (settings.WORDPRESS_USER, settings.WORDPRESS_PASSWORD)

        # Buscar en WordPress posts publicados en los últimos 30 minutos
        after = (datetime.utcnow() - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S")
        wp_resp = requests.get(
            f"{wp_base}/wp-json/wp/v2/posts",
            params={
                "status": "publish",
                "after": after,
                "per_page": 10,
                "orderby": "date",
                "order": "desc",
            },
            auth=auth,
            timeout=15,
        )

        if wp_resp.status_code != 200:
            logger.warning(f"  📘 WordPress respondió {wp_resp.status_code}")
            return

        recent_posts = wp_resp.json()

        if not recent_posts:
            logger.info("  📘 Facebook sync: no hay posts publicados en los últimos 30 min.")
            return

        logger.info(f"  📘 Facebook sync: {len(recent_posts)} post(s) publicados recientemente en WordPress...")

        with get_db() as db:
            for wp_post in recent_posts:
                wp_post_id = wp_post.get("id")
                try:
                    # Buscar en BD por wordpress_post_id
                    record = db.query(GeneratedArticle).filter(
                        GeneratedArticle.wordpress_post_id == wp_post_id,
                        GeneratedArticle.facebook_post_id == None,  # noqa: E711
                    ).first()

                    if not record:
                        logger.debug(f"  WP post {wp_post_id}: no está en BD o ya fue posteado en FB")
                        continue

                    logger.info(f"  ✓ WP post {wp_post_id} — enviando a Facebook...")

                    # Actualizar status en BD
                    record.status = "published"

                    # Permalink limpio
                    wordpress_url = wp_post.get("link", f"{wp_base}/?p={wp_post_id}")
                    logger.info(f"  🔗 URL: {wordpress_url}")

                    # Imagen destacada de WordPress
                    image_url = None
                    try:
                        featured_media_id = wp_post.get("featured_media", 0)
                        if featured_media_id:
                            media_resp = requests.get(
                                f"{wp_base}/wp-json/wp/v2/media/{featured_media_id}",
                                auth=auth,
                                timeout=10,
                            )
                            if media_resp.status_code == 200:
                                image_url = media_resp.json().get("source_url")
                                logger.info(f"  🖼 Imagen: {image_url}")
                    except Exception as e:
                        logger.warning(f"  🖼 No se pudo obtener imagen: {e}")

                    # Publicar en Facebook
                    fb_post_id = post_to_facebook_with_image(
                        title=record.title,
                        wordpress_url=wordpress_url,
                        page_id=page_id,
                        page_token=page_token,
                        image_url=image_url,
                    )

                    if fb_post_id:
                        record.facebook_post_id = fb_post_id
                        record.facebook_posted_at = datetime.utcnow()
                        logger.info(f"  📘 Facebook: publicado — ID {fb_post_id}")
                    else:
                        logger.error(f"  📘 Facebook: falló post {wp_post_id}")

                except Exception as e:
                    logger.error(f"  Error procesando WP post {wp_post_id}: {e}")

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
