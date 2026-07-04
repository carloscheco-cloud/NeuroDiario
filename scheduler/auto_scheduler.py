"""
NeuroDiario - Auto Scheduler
Flujo de producción normal para ~100 artículos diarios.
Intervalos:
- Cada 3 min:  Ingesta RSS
- Cada 6 min:  Procesamiento NLP
- Cada 8 min:  Generación + Publicación (10 artículos por ciclo)
- Cada 5 min:  Sincronización WordPress → Facebook + Telegram
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


def _job_social_sync():
    """
    Consulta WordPress para detectar artículos que pasaron de draft a published,
    actualiza el status en la BD y los publica en Facebook + Telegram.
    """
    logger.info("=" * 60)
    logger.info("JOB: Sincronización WordPress → Facebook + Telegram")
    logger.info("=" * 60)
    try:
        from neurodiario.config.settings import settings
        from neurodiario.db.database import get_db
        from neurodiario.db.models import GeneratedArticle, Article
        from neurodiario.publisher.facebook_image_generator import post_to_facebook_with_image
        from neurodiario.publisher.telegram_publisher import post_to_telegram
        import requests

        # ── Configuración Facebook ──
        page_token = getattr(settings, 'FACEBOOK_PAGE_TOKEN', None)
        page_id = getattr(settings, 'FACEBOOK_PAGE_ID', None)

        # ── Configuración Telegram ──
        telegram_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        telegram_channel = getattr(settings, 'TELEGRAM_CHANNEL_ID', None)

        if not page_token or not page_id:
            logger.warning("  📘 Facebook sync: faltan FACEBOOK_PAGE_TOKEN o FACEBOOK_PAGE_ID")

        if not telegram_token or not telegram_channel:
            logger.warning("  📱 Telegram sync: faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHANNEL_ID")

        if not (page_token and page_id) and not (telegram_token and telegram_channel):
            return

        wp_base = settings.WORDPRESS_URL.rstrip('/')
        auth = (settings.WORDPRESS_USER, settings.WORDPRESS_PASSWORD)

        with get_db() as db:
            pending = db.query(GeneratedArticle).filter(
                GeneratedArticle.status == "draft",
                GeneratedArticle.wordpress_post_id != None,   # noqa: E711
                GeneratedArticle.facebook_post_id == None,    # noqa: E711
            ).all()

            if not pending:
                logger.info("  Social sync: sin artículos pendientes.")
                return

            logger.info(f"  Social sync: verificando {len(pending)} artículo(s) en WordPress...")

            for record in pending:
                try:
                    # Consultar WordPress para ver si fue aprobado
                    wp_url = f"{wp_base}/wp-json/wp/v2/posts/{record.wordpress_post_id}"
                    response = requests.get(wp_url, auth=auth, timeout=10)

                    if response.status_code != 200:
                        logger.debug(f"  WP post {record.wordpress_post_id}: HTTP {response.status_code}")
                        continue

                    wp_post = response.json()
                    wp_status = wp_post.get("status", "")

                    if wp_status != "publish":
                        logger.debug(f"  WP post {record.wordpress_post_id}: aún en '{wp_status}' — saltando")
                        continue

                    logger.info(f"  ✓ WP post {record.wordpress_post_id} publicado — distribuyendo...")

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
                        wordpress_url = wp_post.get("link", f"{wp_base}/?p={record.wordpress_post_id}")
                    except Exception:
                        wordpress_url = f"{wp_base}/?p={record.wordpress_post_id}"

                    # ── FACEBOOK ──
                    if page_token and page_id:
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
                            logger.error(f"  📘 Facebook: falló el post {record.wordpress_post_id}")

                    # ── TELEGRAM ──
                    if telegram_token and telegram_channel:
                        tg_message_id = post_to_telegram(
                            title=record.title,
                            wordpress_url=wordpress_url,
                            channel_id=telegram_channel,
                            bot_token=telegram_token,
                            image_url=image_url,
                        )
                        if tg_message_id:
                            logger.info(f"  📱 Telegram: publicado — message_id {tg_message_id}")
                        else:
                            logger.error(f"  📱 Telegram: falló el post {record.wordpress_post_id}")

                except Exception as e:
                    logger.error(f"  Error procesando WP post {record.wordpress_post_id}: {e}")

            db.commit()

    except Exception as e:
        logger.error(f"ERROR EN SOCIAL SYNC: {e}", exc_info=True)


def start_scheduler() -> BackgroundScheduler:
    logger.info("=" * 60)
    logger.info("NeuroDiario Scheduler — MODO PRODUCCIÓN")
    logger.info("  Ingesta RSS:    cada 3 minutos")
    logger.info("  NLP:            cada 6 minutos")
    logger.info("  Publicación:    cada 8 minutos (10 artículos)")
    logger.info("  Social sync:    cada 5 minutos (Facebook + Telegram)")
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
        _job_social_sync,
        trigger="interval",
        minutes=5,
        id="social_sync",
        name="Sincronización WordPress→Facebook+Telegram",
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
