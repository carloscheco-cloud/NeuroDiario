"""
Módulo de orquestación del pipeline de NeuroDiario.
Coordina la ingesta, procesamiento, generación y publicación de artículos
de forma programada usando APScheduler.
"""

import logging
from datetime import datetime
from typing import Optional

from tqdm import tqdm

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class Pipeline:
    """Orquesta el flujo completo de NeuroDiario de extremo a extremo."""

    def __init__(self, config=None):
        """
        Args:
            config: Objeto de configuración con credenciales y parámetros.
                    Si es None, carga desde neurodiario.config.settings.
        """
        if config is None:
            from neurodiario.config.settings import settings
            config = settings

        self.config = config
        self.scheduler = BlockingScheduler(timezone="America/Santo_Domingo")
        self._setup_jobs()

    def _setup_jobs(self):
        """Registra los trabajos programados en el scheduler."""
        # Ingesta cada 2 horas
        self.scheduler.add_job(
            self.run_ingestion,
            trigger=CronTrigger(hour="*/2"),
            id="ingestion",
            name="Ingesta de noticias RSS",
            replace_existing=True,
        )

        # Generación y publicación a las 7am y 12pm hora DR
        for hour in [7, 12, 18]:
            self.scheduler.add_job(
                self.run_generation_and_publish,
                trigger=CronTrigger(hour=hour, minute=0),
                id=f"generate_publish_{hour}h",
                name=f"Generación y publicación {hour}:00",
                replace_existing=True,
            )

        logger.info("Jobs del scheduler configurados correctamente")

    def run_ingestion(self):
        """
        Ejecuta la fase de ingesta: obtiene artículos RSS y los parsea.
        Se ejecuta automáticamente cada 2 horas.
        """
        logger.info(f"[{datetime.now()}] Iniciando ingesta de noticias...")
        try:
            from neurodiario.ingestion.rss_fetcher import RSSFetcher
            from neurodiario.ingestion.article_parser import ArticleParser
            from neurodiario.db.database import get_db

            fetcher = RSSFetcher()
            parser = ArticleParser()

            articles = fetcher.fetch_articles()
            articles = parser.parse_batch(articles)

            with get_db() as db:
                saved = fetcher.save_to_db(articles, db)

            logger.info(f"Ingesta completada: {saved} artículos nuevos guardados")
        except Exception as e:
            logger.error(f"Error en ingesta: {e}", exc_info=True)

    def run_nlp(self, articles: list) -> list:
        """
        Ejecuta el procesamiento NLP sobre los artículos: limpieza,
        extracción de entidades y clasificación.

        Args:
            articles: Lista de artículos crudos de la BD.

        Returns:
            Lista de artículos enriquecidos con datos NLP.
        """
        from neurodiario.nlp.text_cleaner import TextCleaner
        from neurodiario.nlp.entity_extractor import EntityExtractor
        from neurodiario.nlp.classifier import ArticleClassifier

        cleaner = TextCleaner()
        extractor = EntityExtractor()
        classifier = ArticleClassifier()

        for article in articles:
            article["clean_content"] = cleaner.clean(article.get("raw_content", ""))
            article["entities"] = extractor.extract(article["clean_content"])
            article["category"], article["category_confidence"] = classifier.classify(
                article["clean_content"], article.get("title", "")
            )

        return articles

    def run_generation_and_publish(self):
        """
        Ejecuta la fase de generación con IA y publicación en WordPress.
        Se ejecuta a las 7am, 12pm y 6pm hora dominicana.
        """
        logger.info(f"[{datetime.now()}] Iniciando generación y publicación...")
        try:
            from neurodiario.db.database import get_db
            from neurodiario.nlp.trend_detector import TrendDetector
            from neurodiario.generator.article_generator import ArticleGenerator
            from neurodiario.publisher.wordpress_publisher import WordPressPublisher

            # TODO: Obtener artículos sin procesar de la BD
            with get_db() as db:
                articles = []  # db.query(Article).filter_by(processed=False).all()

            articles = self.run_nlp(articles)

            detector = TrendDetector()
            trends = detector.detect(articles)

            generator = ArticleGenerator(api_key=self.config.CLAUDE_API_KEY)
            digest = generator.generate_digest(trends)

            publisher = WordPressPublisher(
                url=self.config.WORDPRESS_URL,
                username=self.config.WORDPRESS_USER,
                password=self.config.WORDPRESS_PASSWORD,
            )
            publisher.publish({
                "title": f"NeuroDiario - Resumen del {datetime.now().strftime('%d/%m/%Y')}",
                "content": digest,
                "categories": ["Resumen Diario"],
                "tags": [t["topic"] for t in trends[:5]],
                "status": "publish",
            })

            logger.info("Generación y publicación completadas exitosamente")
        except Exception as e:
            logger.error(f"Error en generación/publicación: {e}", exc_info=True)

    def start(self):
        """Inicia el scheduler en modo bloqueante."""
        logger.info("Iniciando scheduler de NeuroDiario...")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler detenido por el usuario")

    def run_once(self):
        """Ejecuta el pipeline completo una sola vez (útil para pruebas)."""
        logger.info("Ejecutando pipeline completo en modo único...")
        self.run_ingestion()
        self.run_generation_and_publish()


def run_ingestion_pipeline():
    """
    Ejecuta pipeline completo de ingesta.

    Flujo:
    1) Fetch RSS de todas las fuentes
    2) Parse de cada artículo
    3) Verificar duplicados
    4) Guardar en BD
    """
    from neurodiario.ingestion.rss_fetcher import RSSFetcher
    from neurodiario.ingestion.article_parser import ArticleParser
    from neurodiario.ingestion.deduplicator import is_duplicate
    from neurodiario.db.database import get_db, save_article, init_db

    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE DE INGESTA")
    logger.info("=" * 60)

    # Inicializar BD
    init_db()

    # 1) FETCH RSS
    logger.info("PASO 1: Obteniendo feeds RSS...")
    fetcher = RSSFetcher()
    rss_articles = fetcher.fetch_articles()

    if not rss_articles:
        logger.warning("No articles found in RSS feeds")
        return

    logger.info(f"✓ {len(rss_articles)} artículos encontrados en RSS")

    # 2) PARSE Y DEDUPLICACIÓN
    logger.info("PASO 2: Parseando artículos completos...")
    parser = ArticleParser()
    saved_count = 0
    skipped_count = 0

    with get_db() as db_session:
        for rss_article in tqdm(rss_articles, desc="Procesando"):
            url = rss_article.get('url')

            if not url:
                logger.warning(f"Artículo sin URL: {rss_article.get('title')}")
                continue

            # 3) VERIFICAR DUPLICADO
            if is_duplicate(url, rss_article.get('title', ''), db_session):
                logger.debug(f"Duplicado saltado: {url}")
                skipped_count += 1
                continue

            # 4) PARSE CONTENIDO COMPLETO
            parsed = parser.parse(rss_article)

            if not parsed.get('raw_content'):
                logger.warning(f"No se pudo parsear: {url}")
                continue

            # 5) GUARDAR EN BD
            if save_article(parsed):
                saved_count += 1
                logger.info(f"✓ Guardado: {parsed['title'][:60]}")

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETADO")
    logger.info(f"  Guardados: {saved_count}")
    logger.info(f"  Duplicados: {skipped_count}")
    logger.info("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    run_ingestion_pipeline()
