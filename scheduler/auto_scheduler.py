"""
NeuroDiario - Auto Scheduler COMPLETO (Fase 1)
Ejecuta automáticamente los pipelines de ingesta, NLP y PUBLICACIÓN.

Flujo completo:
- Cada 15 min: Ingesta RSS
- Cada 20 min: Procesamiento NLP
- Cada 30 min: Generación con Claude + Publicación en WordPress

Uso:
    python scheduler/auto_scheduler.py
"""
import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler

from neurodiario.scheduler.pipeline import run_ingestion_pipeline
from neurodiario.scheduler.nlp_pipeline import run_nlp_pipeline
from neurodiario.scheduler.publishing_pipeline import run_publishing_pipeline

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Wrappers con log descriptivo
# ---------------------------------------------------------------------------
def _job_ingestion():
    """Ejecuta ingesta de RSS feeds."""
    logger.info("=" * 60)
    logger.info("JOB: Ingesta RSS")
    logger.info("=" * 60)
    try:
        run_ingestion_pipeline()
    except Exception as e:
        logger.error(f"Error en ingesta RSS: {e}", exc_info=True)


def _job_nlp():
    """Ejecuta pipeline NLP."""
    logger.info("=" * 60)
    logger.info("JOB: Pipeline NLP")
    logger.info("=" * 60)
    try:
        run_nlp_pipeline(batch_size=50)
    except Exception as e:
        logger.error(f"Error en pipeline NLP: {e}", exc_info=True)


def _job_publishing():
    """Ejecuta pipeline de generación y publicación."""
    logger.info("=" * 60)
    logger.info("JOB: Generación y Publicación")
    logger.info("=" * 60)
    try:
        # Publicar 2-3 artículos cada 30 min = ~96 artículos/día
        published = run_publishing_pipeline(max_articles=2)
        logger.info(f"Publicados: {published} artículos")
    except Exception as e:
        logger.error(f"Error en publicación: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
def start_scheduler() -> BackgroundScheduler:
    """
    Crea, configura e inicia el BackgroundScheduler.

    Returns:
        La instancia del scheduler ya iniciada.
    """
    logger.info("Iniciando NeuroDiario Scheduler COMPLETO")
    logger.info("Pipelines activos:")
    logger.info("  - Ingesta RSS: cada 15 minutos")
    logger.info("  - Procesamiento NLP: cada 20 minutos")
    logger.info("  - Publicación: cada 30 minutos (noticias actuales)")
    logger.info("=" * 60)

    scheduler = BackgroundScheduler()

    # Tarea 1: Ingesta RSS cada 15 minutos
    scheduler.add_job(
        _job_ingestion,
        trigger="interval",
        minutes=15,
        id="ingestion_rss",
        name="Ingesta RSS",
        replace_existing=True,
    )

    # Tarea 2: Pipeline NLP cada 20 minutos
    scheduler.add_job(
        _job_nlp,
        trigger="interval",
        minutes=20,
        id="nlp_pipeline",
        name="Pipeline NLP",
        replace_existing=True,
    )

    # Tarea 3: Publicación cada 30 minutos (noticias más actuales)
    scheduler.add_job(
        _job_publishing,
        trigger="interval",
        minutes=30,
        id="publishing_pipeline",
        name="Generación y Publicación",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("✓ NeuroDiario Scheduler iniciado exitosamente")
    logger.info("")

    return scheduler


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    scheduler = start_scheduler()
    
    try:
        # Mantener el proceso vivo mientras el scheduler corre en background
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("NeuroDiario Scheduler detenido")
