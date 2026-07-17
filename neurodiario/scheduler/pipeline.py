"""
Modulo de orquestacion del pipeline de NeuroDiario.
Coordina la ingesta, procesamiento, generacion y publicacion de articulos.
"""

import logging
from datetime import datetime
from typing import Optional

from tqdm import tqdm

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# FUENTES DOMINICANAS — articulos de estas fuentes siempre pasan
# ─────────────────────────────────────────────────────────────
FUENTES_DOMINICANAS = {
    "diario libre", "diario libre - política", "diario libre - politica",
    "diario libre - economía", "diario libre - economia",
    "diario libre - deportes", "diario libre - entretenimiento",
    "el nacional", "n digital", "el día", "el dia",
    "hoy", "listín diario", "listin diario", "el caribe",
    "acento", "cdn", "la información", "la informacion",
}

# ─────────────────────────────────────────────────────────────
# PALABRAS CLAVE — noticias internacionales relevantes para RD
# ─────────────────────────────────────────────────────────────
KEYWORDS_RELEVANTES_RD = [
    # Pais y gentilicio
    "república dominicana", "republica dominicana", "dominicano", "dominicana",
    "santo domingo", "santiago", "haiti", "haitiano", "haitiana",
    # Economia global que impacta RD
    "petróleo", "petroleo", "combustible", "gasolina", "dólar", "dolar",
    "inflación", "inflacion", "fmi", "banco mundial", "bid",
    "aranceles", "trump", "economía global", "economia global",
    "remesas", "turismo", "caribe",
    # Clima y desastres
    "huracán", "huracan", "tormenta tropical", "ciclón", "ciclon",
    "sismo", "terremoto", "inundación", "inundacion",
    # Deportes dominicanos
    "béisbol", "beisbol", "mlb", "pelotero", "grandes ligas",
    "licey", "escogido", "águilas", "aguilas", "estrellas",
    # Migracion
    "migrante", "migración", "migracion", "deportación", "deportacion",
    "eeuu", "estados unidos", "washington",
    # Organismos internacionales relevantes para RD
    "cepal", "onu", "bid", "usaid",
]


def es_relevante_para_rd(title: str, content: str, source_name: str) -> bool:
    """
    Determina si un articulo internacional es relevante para Republica Dominicana.

    Las fuentes dominicanas siempre pasan (retorna True).
    Las fuentes internacionales pasan solo si contienen palabras clave relevantes.

    Args:
        title: Titulo del articulo
        content: Contenido del articulo
        source_name: Nombre de la fuente RSS

    Returns:
        True si el articulo debe guardarse, False si debe descartarse
    """
    # Fuentes dominicanas siempre pasan
    if source_name.lower() in FUENTES_DOMINICANAS:
        return True

    # Para fuentes internacionales, verificar palabras clave
    texto = f"{title} {content}".lower()
    for keyword in KEYWORDS_RELEVANTES_RD:
        if keyword in texto:
            return True

    return False


class Pipeline:
    """Orquesta el flujo completo de NeuroDiario de extremo a extremo."""

    def __init__(self, config=None):
        if config is None:
            from neurodiario.config.settings import settings
            config = settings

        self.config = config
        self.scheduler = BlockingScheduler(timezone="America/Santo_Domingo")
        self._setup_jobs()

    def _setup_jobs(self):
        self.scheduler.add_job(
            self.run_ingestion,
            trigger=CronTrigger(hour="*/2"),
            id="ingestion",
            name="Ingesta de noticias RSS",
            replace_existing=True,
        )

        for hour in [7, 12, 18]:
            self.scheduler.add_job(
                self.run_generation_and_publish,
                trigger=CronTrigger(hour=hour, minute=0),
                id=f"generate_publish_{hour}h",
                name=f"Generacion y publicacion {hour}:00",
                replace_existing=True,
            )

        logger.info("Jobs del scheduler configurados correctamente")

    def run_ingestion(self):
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

            logger.info(f"Ingesta completada: {saved} articulos nuevos guardados")
        except Exception as e:
            logger.error(f"Error en ingesta: {e}", exc_info=True)

    def run_nlp(self, articles: list) -> list:
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
        logger.info(f"[{datetime.now()}] Iniciando generacion y publicacion...")
        try:
            from neurodiario.db.database import get_db
            from neurodiario.nlp.trend_detector import TrendDetector
            from neurodiario.generator.article_generator import ArticleGenerator
            from neurodiario.publisher.wordpress_publisher import WordPressPublisher

            with get_db() as db:
                articles = []

            articles = self.run_nlp(articles)
            detector = TrendDetector()
            trends = detector.detect(articles)
            generator = ArticleGenerator(api_key=self.config.OPENAI_API_KEY, model=self.config.OPENAI_MODEL)
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

            logger.info("Generacion y publicacion completadas exitosamente")
        except Exception as e:
            logger.error(f"Error en generacion/publicacion: {e}", exc_info=True)

    def start(self):
        logger.info("Iniciando scheduler de NeuroDiario...")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler detenido por el usuario")

    def run_once(self):
        logger.info("Ejecutando pipeline completo en modo unico...")
        self.run_ingestion()
        self.run_generation_and_publish()


def run_ingestion_pipeline():
    """
    Ejecuta pipeline completo de ingesta.

    Flujo:
    1) Fetch RSS de todas las fuentes
    2) Parse de cada articulo
    3) Verificar duplicados
    4) Filtro de relevancia (internacionales deben ser relevantes para RD)
    5) Guardar en BD — primero dominicanas, luego internacionales relevantes
    """
    from neurodiario.ingestion.rss_fetcher import RSSFetcher
    from neurodiario.ingestion.article_parser import ArticleParser
    from neurodiario.ingestion.deduplicator import is_duplicate
    from neurodiario.db.database import get_db, save_article, init_db

    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE DE INGESTA")
    logger.info("=" * 60)

    init_db()

    # 1) FETCH RSS
    logger.info("PASO 1: Obteniendo feeds RSS...")
    fetcher = RSSFetcher()
    rss_articles = fetcher.fetch_articles()

    if not rss_articles:
        logger.warning("No articles found in RSS feeds")
        return

    logger.info(f"{len(rss_articles)} articulos encontrados en RSS")

    # 2) PARSE Y DEDUPLICACION
    logger.info("PASO 2: Parseando articulos completos...")
    parser = ArticleParser()
    saved_count = 0
    skipped_count = 0
    filtered_count = 0

    # Separar dominicanas e internacionales para priorizar dominicanas
    dominicanas = []
    internacionales = []

    with get_db() as db_session:
        for rss_article in tqdm(rss_articles, desc="Procesando"):
            url = rss_article.get('url')
            if not url:
                continue

            # 3) VERIFICAR DUPLICADO
            if is_duplicate(url, rss_article.get('title', ''), db_session):
                skipped_count += 1
                continue

            # 4) PARSE CONTENIDO COMPLETO
            parsed = parser.parse(rss_article)
            if not parsed.get('raw_content'):
                continue

            source_name = parsed.get('source_name', '').lower()

            # 4b) FILTRO DE RELEVANCIA
            if not es_relevante_para_rd(
                parsed.get('title', ''),
                parsed.get('raw_content', ''),
                source_name
            ):
                filtered_count += 1
                logger.debug(f"Filtrado por irrelevancia para RD: {parsed['title'][:60]}")
                continue

            # Separar por origen
            if source_name in FUENTES_DOMINICANAS:
                dominicanas.append(parsed)
            else:
                internacionales.append(parsed)

        # 5) GUARDAR EN BD — primero dominicanas, luego internacionales
        logger.info(f"Dominicanas: {len(dominicanas)} | Internacionales relevantes: {len(internacionales)}")

        for parsed in dominicanas + internacionales:
            if save_article(parsed):
                saved_count += 1
                logger.info(f"Guardado: {parsed['title'][:60]}")

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETADO")
    logger.info(f"  Guardados: {saved_count}")
    logger.info(f"  Duplicados: {skipped_count}")
    logger.info(f"  Filtrados por irrelevancia: {filtered_count}")
    logger.info("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    run_ingestion_pipeline()
