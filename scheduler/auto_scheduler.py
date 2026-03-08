"""
NeuroDiario - Auto Scheduler
Ejecuta automáticamente los pipelines de ingesta y NLP usando APScheduler.

Uso:
    python scheduler/auto_scheduler.py
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
    logger.info("Ejecutando ingesta RSS")
    run_ingestion_pipeline()


def _job_nlp():
    logger.info("Ejecutando pipeline NLP")
    run_nlp_pipeline()


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


def start_scheduler() -> BackgroundScheduler:
    """Crea, configura e inicia el BackgroundScheduler.

    Returns:
        La instancia del scheduler ya iniciada.
    """
    logger.info("Iniciando scheduler")

    scheduler = BackgroundScheduler()

    # Tarea 1: ingesta RSS cada 15 minutos
    scheduler.add_job(
        _job_ingestion,
        trigger="interval",
        minutes=15,
        id="ingestion_rss",
        name="Ingesta RSS",
        replace_existing=True,
    )

    # Tarea 2: pipeline NLP cada 20 minutos
    scheduler.add_job(
        _job_nlp,
        trigger="interval",
        minutes=20,
        id="nlp_pipeline",
        name="Pipeline NLP",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("NeuroDiario Scheduler iniciado")

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
