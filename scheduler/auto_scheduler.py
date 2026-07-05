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


def _get_wordpress_image_url(wp_base: str, auth: tuple, wp_post_id: int) -> str | None:
    """
    Obtiene la URL de la imagen destacada de un post de WordPress.
    Retorna la URL de la imagen o None si no tiene.
    """
    import requests
    try:
        # Obtener el post con el featured_media
        wp_url = f"{wp_base}/wp-json/wp/v2/posts/{wp_post_id}?_fields=featured_media"
        r = requests.get(wp_url, auth=auth, timeout=10)
        if r.status_code != 200:
            return None
        media_id = r.json().get("featured_media", 0)
        if not media_id:
            return None

        # Obtener la URL de la imagen del media
        media_url = f"{wp_base}/wp-json/wp/v2/media/{media_id}?_fields=source_url"
        r2 = requests.get(media_url, auth=auth, timeout=10)
        if r2.status_code != 200:
            return None
        image_url = r2.json().get("source_url")
        if image_url:
            logger.info(f"  🖼 Imagen obtenida de WordPress: {image_url[:60]}...")
        return image_url
    except Exception as e:
        logger.warning(f"  🖼 No se pudo obtener imagen de WordPress: {e}")
        return None


def _job_social_sync():
    """
    Consulta WordPress para detectar artículos aprobados
    y los publica en Facebook + Telegram de forma independiente.
    Si el artículo no tiene image_url en la BD, la obtiene de WordPress.
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
        from datetime import datetime

        page_token = getattr(settings, 'FACEBOOK_PAGE_TOKEN', None)
        page_id = getattr(settings, 'FACEBOOK_PAGE_ID', None)
        telegram_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        telegram_channel = getattr(settings, 'TELEGRAM_CHANNEL_ID', None)

        wp_base = settings.WORDPRESS_URL.rstrip('/')
        auth = (settings.WORDPRESS_USER, settings.WORDPRESS_PASSWORD)

        with get_db() as db:
            pending = db.query(GeneratedArticle).filter(
                GeneratedArticle.status == "draft",
                GeneratedArticle.wordpress_post_id != None,   # noqa: E711
            ).all()

            pending = [
                r for r in pending
                if (page_token and page_id and r.facebook_post_id is None)
                or (telegram_token and telegram_channel and r.telegram_message_id is None)
            ]

            if not pending:
                logger.info("  Social sync: sin artículos pendientes.")
                return

            logger.info(f"  Social sync: {len(pending)} artículo(s) para distribuir...")

            for record in pending:
                try:
                    wp_url = f"{wp_base}/wp-json/wp/v2/posts/{record.wordpress_post_id}"
                    response = requests.get(wp_url, auth=auth, timeout=10)

                    if response.status_code != 200:
                        continue

                    wp_post = response.json()
                    if wp_post.get("status", "") != "publish":
                        continue

                    logger.info(f"  ✓ WP post {record.wordpress_post_id} publicado — distribuyendo...")
                    record.status = "published"

                    # Obtener image_url — primero desde la BD, si no desde WordPress
                    image_url = None
                    if record.source_article_id:
                        source = db.query(Article).filter(
                            Article.id == record.source_article_id
                        ).first()
                        if source:
                            image_url = source.image_url

                    if not image_url:
                        logger.info(f"  🖼 Sin imagen en BD — buscando en WordPress...")
                        image_url = _get_wordpress_image_url(
                            wp_base, auth, record.wordpress_post_id
                        )

                    wordpress_url = wp_post.get("link", f"{wp_base}/?p={record.wordpress_post_id}")

                    # ── FACEBOOK (independiente) ──
                    if page_token and page_id and record.facebook_post_id is None:
                        try:
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
                                logger.error(f"  📘 Facebook: falló WP post {record.wordpress_post_id}")
                        except Exception as e:
                            logger.error(f"  📘 Facebook: excepción — {e}")

                    # ── TELEGRAM (independiente) ──
                    if telegram_token and telegram_channel and record.telegram_message_id is None:
                        try:
                            tg_message_id = post_to_telegram(
                                title=record.title,
                                wordpress_url=wordpress_url,
                                channel_id=telegram_channel,
                                bot_token=telegram_token,
                                image_url=image_url,
                            )
                            if tg_message_id:
                                record.telegram_message_id = tg_message_id
                                record.telegram_posted_at = datetime.utcnow()
                                logger.info(f"  📱 Telegram: publicado — message_id {tg_message_id}")
                            else:
                                logger.error(f"  📱 Telegram: falló WP post {record.wordpress_post_id}")
                        except Exception as e:
                            logger.error(f"  📱 Telegram: excepción — {e}")

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
