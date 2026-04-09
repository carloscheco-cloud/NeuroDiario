"""
NeuroDiario - Auto Scheduler
Flujo de producción normal para ~100 artículos diarios.

Intervalos:
- Cada 15 min: Ingesta RSS
- Cada 20 min: Procesamiento NLP
- Cada 30 min: Generación + Publicación (10 artículos por ciclo)

10 artículos × 48 ciclos/día = ~480 artículos/día (margen amplio)
Ajusta max_articles según el volumen deseado.
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
        # 10 artículos por ciclo × 48 ciclos = ~480/día
        # Baja a 5 si quieres ~240/día, sube a 15 para ~720/día
        published = run_publishing_pipeline(max_articles=10)
        logger.info(f"Publicados en este ciclo: {published} artículos")
    except Exception as e:
        logger.error(f"ERROR EN PUBLICACIÓN: {e}", exc_info=True)


def start_scheduler() -> BackgroundScheduler:
    logger.info("=" * 60)
    logger.info("NeuroDiario Scheduler — MODO PRODUCCIÓN")
    logger.info("  Ingesta RSS:    cada 15 minutos")
    logger.info("  NLP:            cada 20 minutos")
    logger.info("  Publicación:    cada 30 minutos (10 artículos)")
    logger.info("  Meta diaria:    ~480 artículos")
    logger.info("=" * 60)

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        _job_ingestion,
        trigger="interval",
        minutes=15,
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

    scheduler.add_job(
        _job_publishing,
        trigger="interval",
        minutes=30,
        id="publishing_pipeline",
        name="Generación y Publicación",
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
