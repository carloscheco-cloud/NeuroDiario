"""
NeuroDiario - Auto Scheduler (con CLUSTERING como único camino de generación)

Cambios vs versión anterior:
- El job de publicación viejo (uno-por-artículo) se REEMPLAZA por el
  pipeline de clustering (agrupa duplicados, genera UN artículo por noticia).
- Intervalos ajustados al ritmo real de las fuentes para no apilar basura:
    · Ingesta RSS:  cada 20 min (antes 3)
    · NLP:          cada 20 min (antes 6)
    · Clustering:   3 veces al día (7am, 1pm, 7pm RD) — no cada 8 min
    · Social sync:  cada 10 min (Facebook + Telegram) — UNO por ciclo (escalonado)
    · Newsletter:   domingos 8am RD
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


def _job_clustering():
    """
    Nuevo job de generación: agrupa noticias por similaridad y genera
    UN artículo por cluster (los N mejores por prioridad). Reemplaza al
    viejo _job_publishing que generaba uno-por-artículo y apilaba fallidos.
    """
    logger.info("=" * 60)
    logger.info("JOB: Generación con CLUSTERING")
    logger.info("=" * 60)
    try:
        # clustering_pipeline.py vive en la raíz del proyecto
        from clustering_pipeline import procesar
        publicados = procesar(publicar=True)
        logger.info(f"Clustering publicó {publicados} artículos en este ciclo")
    except Exception as e:
        logger.error(f"ERROR EN CLUSTERING: {e}", exc_info=True)


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
    """
    Distribuye artículos publicados en WordPress a Facebook y Telegram.

    MODO ESCALONADO: procesa UN solo artículo por ciclo (cada 10 minutos).
    Así, si publicas 20 artículos de golpe en WordPress, se distribuyen
    a redes sociales de uno en uno cada ~10 minutos.
    """
    logger.info("=" * 60)
    logger.info("JOB: Sincronización WordPress → Facebook + Telegram (escalonado)")
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

            logger.info(f"  Social sync: {len(pending)} artículo(s) en cola — procesando 1 ahora...")

            # ── CAMBIO CLAVE: solo procesamos el primero de la lista ──
            record = pending[0]

            try:
                wp_url = f"{wp_base}/wp-json/wp/v2/posts/{record.wordpress_post_id}"
                response = requests.get(wp_url, auth=auth, timeout=10)
                if response.status_code != 200:
                    logger.warning(f"  No se pudo obtener WP post {record.wordpress_post_id}")
                    return
                wp_post = response.json()
                if wp_post.get("status", "") != "publish":
                    logger.info(f"  WP post {record.wordpress_post_id} aún no está publicado — esperando.")
                    return

                logger.info(f"  ✓ WP post {record.wordpress_post_id} publicado — distribuyendo...")
                record.status = "published"

                image_candidates = []
                db_image_url = None
                if record.source_article_id:
                    source = db.query(Article).filter(
                        Article.id == record.source_article_id
                    ).first()
                    if source and source.image_url:
                        db_image_url = source.image_url
                        image_candidates.append(db_image_url)

                wp_image_url = _get_wordpress_image_url(wp_base, auth, record.wordpress_post_id)
                if wp_image_url and wp_image_url not in image_candidates:
                    image_candidates.append(wp_image_url)

                if not image_candidates:
                    logger.info("  🖼 Sin imagen en BD ni WordPress — se usará fallback con marca")

                image_url = image_candidates[0] if image_candidates else None
                wordpress_url = wp_post.get("link", f"{wp_base}/?p={record.wordpress_post_id}")

                if page_token and page_id and record.facebook_post_id is None:
                    try:
                        fb_post_id, fb_working_url = post_to_facebook_with_image(
                            title=record.title,
                            wordpress_url=wordpress_url,
                            page_id=page_id,
                            page_token=page_token,
                            image_url=image_candidates,
                        )
                        if fb_post_id:
                            record.facebook_post_id = fb_post_id
                            record.facebook_posted_at = datetime.utcnow()
                            logger.info(f"  📘 Facebook: publicado — ID {fb_post_id}")
                            if fb_working_url and fb_working_url != db_image_url:
                                if record.source_article_id and source and source.image_url != fb_working_url:
                                    source.image_url = fb_working_url
                                    logger.info(f"  🖼 BD actualizada con imagen que funcionó")
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
            editorial = generate_editorial_summary(articles, youtube_url=youtube_url)

            now = datetime.now()
            week_label = f"{now.day} de {MESES_ES[now.month]} de {now.year}"
            pdf_path = generate_weekly_pdf(articles, week_label=week_label)

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
    logger.info("NeuroDiario Scheduler — MODO PRODUCCIÓN (con Clustering)")
    logger.info("  Ingesta RSS:    cada 20 minutos")
    logger.info("  NLP:            cada 20 minutos")
    logger.info("  Clustering:     7am, 1pm, 7pm (hora RD)")
    logger.info("  Social sync:    cada 10 minutos — 1 artículo por ciclo (escalonado)")
    logger.info("  Newsletter:     domingos 8am RD")
    logger.info("=" * 60)

    scheduler = BackgroundScheduler(timezone="America/Santo_Domingo")

    scheduler.add_job(
        _job_ingestion,
        trigger="interval",
        minutes=20,
        id="ingestion_rss",
        name="Ingesta RSS",
        replace_existing=True,
    )

    scheduler.add_job(
        _job_nlp,
        trigger="interval",
        minutes=20,
        id="nlp_pipeline",
        name="Pipeline NLP",
        replace_existing=True,
    )

    # Clustering 3 veces al día (mañana, mediodía, noche hora RD)
    scheduler.add_job(
        _job_clustering,
        trigger="cron",
        hour="7,13,19",
        minute=0,
        id="clustering_generation",
        name="Generación con Clustering",
        replace_existing=True,
    )

    scheduler.add_job(
        _job_social_sync,
        trigger="interval",
        minutes=10,
        id="social_sync",
        name="Sincronización WordPress→Facebook+Telegram (escalonado)",
        replace_existing=True,
    )

    scheduler.add_job(
        _job_newsletter,
        trigger="cron",
        day_of_week="sun",
        hour=8,
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
