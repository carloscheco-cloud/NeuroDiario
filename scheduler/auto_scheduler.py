"""
NeuroDiario - Auto Scheduler DEBUG MODE
CONFIGURACIÓN TEMPORAL PARA DEBUGGING - JOBS CADA 5 MINUTOS

Flujo acelerado:
- Cada 5 min: Ingesta RSS
- Cada 5 min: Procesamiento NLP  
- Cada 5 min: Generación con Claude + Publicación en WordPress

ADVERTENCIA: Esto es solo para debugging. Cambiar a intervalos normales después.
"""
import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler

from neurodiario.scheduler.pipeline import run_ingestion_pipeline
from neurodiario.scheduler.nlp_pipeline import run_nlp_pipeline

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
        # DEBUGGING: Importar aquí para ver si falla
        logger.info("DEBUG: Importando publishing_pipeline...")
        from neurodiario.scheduler.publishing_pipeline import run_publishing_pipeline
        logger.info("DEBUG: Import exitoso")
        
        # Publicar 2 artículos
        logger.info("DEBUG: Llamando a run_publishing_pipeline...")
        published = run_publishing_pipeline(max_articles=2)
        logger.info(f"DEBUG: Función retornó: {published}")
        logger.info(f"Publicados: {published} artículos")
    except Exception as e:
        logger.error(f"ERROR EN PUBLICACIÓN: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
def start_scheduler() -> BackgroundScheduler:
    """
    Crea, configura e inicia el BackgroundScheduler.

    Returns:
        La instancia del scheduler ya iniciada.
    """
    logger.info("=" * 60)
    logger.info("⚠️  MODO DEBUG ACTIVADO - INTERVALOS DE 5 MINUTOS")
    logger.info("=" * 60)
    logger.info("Pipelines activos:")
    logger.info("  - Ingesta RSS: cada 5 minutos")
    logger.info("  - Procesamiento NLP: cada 5 minutos")
    logger.info("  - Publicación: cada 5 minutos")
    logger.info("=" * 60)

    scheduler = BackgroundScheduler()

    # MODO DEBUG: Todo cada 5 minutos
    scheduler.add_job(
        _job_ingestion,
        trigger="interval",
        minutes=5,
        id="ingestion_rss",
        name="Ingesta RSS",
        replace_existing=True,
    )

    scheduler.add_job(
        _job_nlp,
        trigger="interval",
        minutes=5,
        id="nlp_pipeline",
        name="Pipeline NLP",
        replace_existing=True,
    )

    scheduler.add_job(
        _job_publishing,
        trigger="interval",
        minutes=5,
        id="publishing_pipeline",
        name="Generación y Publicación",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("✓ Scheduler iniciado en MODO DEBUG")
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
