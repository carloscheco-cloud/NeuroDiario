"""
NeuroDiario - Auto Scheduler
Flujo de producción normal para ~100 artículos diarios.
Intervalos:
- Cada 3 min:  Ingesta RSS
- Cada 6 min:  Procesamiento NLP
- Cada 8 min:  Generación + Publicación (10 artículos por ciclo)
- Cada 5 min:  Sincronización WordPress → Facebook + Telegram
- Domingos 8am RD: Newsletter Semanal
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


def _get_wordpress_image_url(wp_base: str, auth: tuple, wp_post_id: int):
    import requests
    try:
        wp_url = f"{wp_base}/wp-json/wp/v2/posts/{wp_post_id}?_fields=featured_media"
        r = requests.get(wp_url, auth=auth, timeout=10)
        if r.status_code != 200:
            return None
        media_id = r.json().get("featured_media", 0)
        if not media_id:
            return None
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
                GeneratedArticle.wordpress_post_id != None,   # noqa
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

                    # ── Recolectar TODAS las URLs de imagen disponibles como candidatas ──
                    # Se pasan como lista a Facebook: si la primera falla al descargar,
                    # el generador intenta la siguiente automáticamente.
                    image_candidates = []

                    # 1) Imagen guardada en la BD del artículo fuente
                    db_image_url = None
                    if record.source_article_id:
                        source = db.query(Article).filter(
                            Article.id == record.source_article_id
                        ).first()
                        if source and source.image_url:
                            db_image_url = source.image_url
                            image_candidates.append(db_image_url)

                    # 2) Imagen destacada de WordPress (como respaldo adicional)
                    wp_image_url = _get_wordpress_image_url(wp_base, auth, record.wordpress_post_id)
                    if wp_image_url and wp_image_url not in image_candidates:
                        image_candidates.append(wp_image_url)

                    if not image_candidates:
                        logger.info("  🖼 Sin imagen en BD ni WordPress — se usará fallback con marca")

                    # Para Telegram mantenemos una sola URL (la mejor disponible)
                    image_url = image_candidates[0] if image_candidates else None

                    wordpress_url = wp_post.get("link", f"{wp_base}/?p={record.wordpress_post_id}")

                    if page_token and page_id and record.facebook_post_id is None:
                        try:
                            # post_to_facebook_with_image ahora devuelve (post_id, url_que_funciono)
                            fb_post_id, fb_working_url = post_to_facebook_with_image(
                                title=record.title,
                                wordpress_url=wordpress_url,
                                page_id=page_id,
                                page_token=page_token,
                                image_url=image_candidates,   # lista de candidatas
                            )
                            if fb_post_id:
                                record.facebook_post_id = fb_post_id
                                record.facebook_posted_at = datetime.utcnow()
                                logger.info(f"  📘 Facebook: publicado — ID {fb_post_id}")
                                # Si Facebook usó una URL distinta a la que teníamos en BD,
                                # actualizamos la BD para que Telegram/otros usen la que sí sirve.
                                if fb_working_url and fb_working_url != db_image_url:
                                    if record.source_article_id and source and source.image_url != fb_working_url:
                                        source.image_url = fb_working_url
                                        logger.info(f"  🖼 BD actualizada con imagen que funcionó: {fb_working_url[:60]}...")
                            else:
                                logger.error(f"  📘 Facebook: falló WP post {record.wordpress_post_id}")
                        except Exception as e:
                            logger.error(f"  📘 Facebook: excepción — {e}")

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


def _job_newsletter():
    """
    Genera y envía el newsletter semanal cada domingo a las 8am RD (12 UTC).
    Contenido: 5 mejores artículos + resumen editorial Claude + reporte PDF.
    """
    logger.info("=" * 60)
    logger.info("JOB: Newsletter Semanal")
    logger.info("=" * 60)
    try:
        from neurodiario.config.settings import settings
        from neurodiario.db.database import get_db
        from neurodiario.publisher.newsletter_generator import (
            get_top_articles_of_week,
            generate_editorial_summary,
            generate_weekly_pdf,
            MESES_ES,
        )
        from neurodiario.publisher.newsletter_sender import send_weekly_newsletter
        from datetime import datetime

        wp_base = settings.WORDPRESS_URL.rstrip("/")
        youtube_url = getattr(settings, "YOUTUBE_WEEKLY_URL", "")

        with get_db() as db:
            logger.info("  📧 Obteniendo mejores artículos de la semana...")
            articles = get_top_articles_of_week(db, limit=5)

            if not articles:
                logger.warning("  📧 Sin artículos publicados esta semana — newsletter cancelado")
                return

            logger.info(f"  📧 {len(articles)} artículos seleccionados")

            logger.info("  📧 Generando resumen editorial con Claude...")
            editorial = generate_editorial_summary(articles, youtube_url=youtube_url)

            now = datetime.now()
            week_label = f"{now.day} de {MESES_ES[now.month]} de {now.year}"

            logger.info("  📧 Generando reporte PDF...")
            pdf_path = generate_weekly_pdf(articles, week_label=week_label)

            logger.info("  📧 Enviando newsletter via Mailchimp...")
            success = send_weekly_newsletter(
                articles=articles,
                editorial_summary=editorial,
                pdf_path=pdf_path,
                youtube_url=youtube_url,
                wp_base=wp_base,
            )

            if success:
                logger.info("  📧 ✓ Newsletter semanal enviado exitosamente")
            else:
                logger.error("  📧 ✗ Error enviando newsletter")

    except Exception as e:
        logger.error(f"ERROR EN NEWSLETTER: {e}", exc_info=True)


def start_scheduler() -> BackgroundScheduler:
    logger.info("=" * 60)
    logger.info("NeuroDiario Scheduler — MODO PRODUCCIÓN")
    logger.info("  Ingesta RSS:    cada 3 minutos")
    logger.info("  NLP:            cada 6 minutos")
    logger.info("  Publicación:    cada 8 minutos (10 artículos)")
    logger.info("  Social sync:    cada 5 minutos (Facebook + Telegram)")
    logger.info("  Newsletter:     domingos 8am RD")
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

    scheduler.add_job(
        _job_newsletter,
        trigger="cron",
        day_of_week="sun",
        hour=12,    # 12 UTC = 8am RD (UTC-4)
        minute=0,
        id="newsletter_semanal",
        name="Newsletter Semanal",
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
