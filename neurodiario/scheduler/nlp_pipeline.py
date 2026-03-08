"""
Pipeline NLP de NeuroDiario — Módulos 2 y 4.

Orquesta el procesamiento de lenguaje natural sobre artículos ya ingestados:
  1. Obtiene artículos no procesados desde la BD.
  2. Limpia y normaliza el texto con TextCleaner.
  3. Extrae entidades nombradas con EntityExtractor.
  4. Clasifica el artículo por tema con ArticleClassifier.
  5. Persiste los resultados en la BD y marca el artículo como procesado.
  6. [Módulo 4] Agrupa artículos recientes en clusters temáticos (TopicClusterer).
  7. [Módulo 4] Detecta tendencias entre múltiples medios (TrendDetector).
  8. Guarda las tendencias en la BD y las muestra en consola.

Uso directo:
    python -m neurodiario.scheduler.nlp_pipeline
    python neurodiario/scheduler/nlp_pipeline.py
"""

import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


class NLPPipeline:
    """Orquesta el procesamiento NLP de artículos no procesados."""

    def __init__(self, batch_size: int = 50):
        """
        Args:
            batch_size: Número de artículos a procesar por ejecución.
        """
        self.batch_size = batch_size
        self._cleaner = None
        self._extractor = None
        self._classifier = None
        self._clusterer = None
        self._trend_detector = None

    # ------------------------------------------------------------------ #
    #  Carga perezosa de componentes NLP (evita importar spaCy al inicio) #
    # ------------------------------------------------------------------ #

    @property
    def cleaner(self):
        if self._cleaner is None:
            from neurodiario.nlp.text_cleaner import TextCleaner
            self._cleaner = TextCleaner(lowercase=False)
        return self._cleaner

    @property
    def extractor(self):
        if self._extractor is None:
            from neurodiario.nlp.entity_extractor import EntityExtractor
            self._extractor = EntityExtractor(model_name="es_core_news_sm")
        return self._extractor

    @property
    def classifier(self):
        if self._classifier is None:
            from neurodiario.nlp.classifier import ArticleClassifier
            self._classifier = ArticleClassifier(method="keyword")
        return self._classifier

    @property
    def clusterer(self):
        if self._clusterer is None:
            from neurodiario.nlp.topic_cluster import TopicClusterer
            self._clusterer = TopicClusterer()
        return self._clusterer

    @property
    def trend_detector(self):
        if self._trend_detector is None:
            from neurodiario.nlp.trend_detector import TrendDetector
            self._trend_detector = TrendDetector()
        return self._trend_detector

    # ------------------------------------------------------------------ #
    #  Procesamiento de un artículo individual                            #
    # ------------------------------------------------------------------ #

    def _process_article(self, article) -> dict:
        """
        Aplica el pipeline NLP completo a un artículo ORM.

        Args:
            article: Instancia de Article (SQLAlchemy ORM).

        Returns:
            Diccionario con los campos NLP calculados.
        """
        raw_text = article.raw_content or article.summary or ""

        # 1) Limpieza
        clean_text = self.cleaner.clean_text(raw_text)

        # 2) Resumen automático si no hay uno del RSS
        summary = article.summary
        if not summary and clean_text:
            summary = self.cleaner.get_summary(clean_text, max_sentences=3)

        # 3) Extracción de entidades
        entities = self.extractor.extract_entities(clean_text)

        # 4) Clasificación
        category, confidence = self.classifier.classify_article(
            title=article.title or "",
            content=clean_text,
        )

        return {
            "clean_content": clean_text,
            "summary": summary,
            "entities": entities,
            "category": category,
            "category_confidence": confidence,
        }

    # ------------------------------------------------------------------ #
    #  Punto de entrada principal                                          #
    # ------------------------------------------------------------------ #

    def run_nlp_pipeline(self) -> int:
        """
        Ejecuta el pipeline NLP sobre todos los artículos pendientes.

        Returns:
            Número de artículos procesados exitosamente.
        """
        from neurodiario.db.database import get_db, get_unprocessed_articles
        from neurodiario.db.models import Article

        logger.info("=" * 60)
        logger.info("INICIANDO PIPELINE NLP")
        logger.info(f"  Fecha    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"  Batch    : {self.batch_size} artículos")
        logger.info("=" * 60)

        articles = get_unprocessed_articles(limit=self.batch_size)
        if not articles:
            logger.info("No hay artículos pendientes de procesamiento NLP.")
            return 0

        logger.info(f"Artículos a procesar: {len(articles)}")
        processed_count = 0

        for article in articles:
            try:
                nlp_data = self._process_article(article)

                with get_db() as db:
                    db_article = db.query(Article).filter(Article.id == article.id).first()
                    if db_article is None:
                        logger.warning(f"Artículo ID {article.id} no encontrado en BD, omitiendo")
                        continue

                    db_article.clean_content = nlp_data["clean_content"]
                    if nlp_data["summary"]:
                        db_article.summary = nlp_data["summary"]
                    db_article.entities = nlp_data["entities"]
                    db_article.category = nlp_data["category"]
                    db_article.category_confidence = nlp_data["category_confidence"]
                    db_article.processed = True

                processed_count += 1
                logger.info(
                    f"  ✓ [{processed_count}/{len(articles)}] "
                    f"[{nlp_data['category']}] {article.title[:70]}"
                )
            except Exception as e:
                logger.error(f"  ✗ Error procesando artículo ID {article.id}: {e}", exc_info=True)

        logger.info("=" * 60)
        logger.info("PIPELINE NLP COMPLETADO")
        logger.info(f"  Procesados : {processed_count}")
        logger.info(f"  Fallidos   : {len(articles) - processed_count}")
        logger.info("=" * 60)

        # ------------------------------------------------------------------ #
        #  Módulo 4 — Detección de tendencias                                 #
        # ------------------------------------------------------------------ #
        trends = self._run_trend_detection()

        # ------------------------------------------------------------------ #
        #  Módulo 5 — Generación y publicación de artículos por tendencia     #
        # ------------------------------------------------------------------ #
        self._generate_and_publish(trends)

        return processed_count

    def _run_trend_detection(self) -> List[Dict]:
        """
        Módulo 4: Agrupa artículos recientes y detecta tendencias.

        Obtiene los últimos artículos procesados, construye clusters temáticos
        y filtra los que aparecen en múltiples medios con suficiente volumen.

        Returns:
            Lista de tendencias detectadas.
        """
        from neurodiario.db.database import get_db, save_trend
        from neurodiario.db.models import Article
        from sqlalchemy.orm import joinedload

        logger.info("=" * 60)
        logger.info("DETECTANDO TENDENCIAS")
        logger.info("=" * 60)

        # Obtener artículos recientes ya procesados, con su fuente cargada
        try:
            with get_db() as db:
                recent_orm = (
                    db.query(Article)
                    .options(joinedload(Article.source))
                    .filter(Article.processed == True)  # noqa: E712
                    .order_by(Article.fetched_at.desc())
                    .limit(200)
                    .all()
                )
                # Convertir a dicts mientras la sesión está activa
                article_dicts = [
                    {
                        "title": a.title or "",
                        "content": a.clean_content or a.raw_content or "",
                        "source_name": a.source.name if a.source else "Desconocido",
                        "url": a.url,
                    }
                    for a in recent_orm
                ]
        except Exception as exc:
            logger.error(f"Error obteniendo artículos para clustering: {exc}", exc_info=True)
            return []

        if not article_dicts:
            logger.info("No hay artículos procesados disponibles para clustering.")
            return []

        logger.info(f"Artículos disponibles para clustering: {len(article_dicts)}")

        # Paso 1: clustering temático
        try:
            clusters = self.clusterer.cluster_articles(article_dicts)
        except Exception as exc:
            logger.error(f"Error en clustering: {exc}", exc_info=True)
            return []

        if not clusters:
            logger.info("No se formaron clusters.")
            return []

        # Paso 2: detectar tendencias
        try:
            trends = self.trend_detector.detect_trends(clusters)
        except Exception as exc:
            logger.error(f"Error en detección de tendencias: {exc}", exc_info=True)
            return []

        # Paso 3: guardar tendencias en BD
        for trend in trends:
            save_trend(
                topic=trend["topic"],
                article_count=trend["article_count"],
                sources=trend["sources"],
            )

        # Paso 4: mostrar resultado en consola
        self._display_trends(trends)
        return trends

    @staticmethod
    def _display_trends(trends: List[Dict]) -> None:
        """Muestra las tendencias detectadas en consola con formato claro."""
        print("\n" + "=" * 40)
        print("DETECTANDO TENDENCIAS")
        print("=" * 40)

        if not trends:
            print("No se detectaron tendencias en este ciclo.")
        else:
            for trend in trends:
                sources_str = ", ".join(trend["sources"])
                print(f"\nTema: {trend['topic']}")
                print(f"Artículos: {trend['article_count']}")
                print(f"Medios: {sources_str}")

        print("\n" + "=" * 40 + "\n")

    def _generate_and_publish(self, trends: List[Dict]) -> None:
        """
        Módulo 5: Genera y publica un artículo por cada tendencia detectada.

        Para cada tendencia verifica si ya se generó un artículo hoy para ese
        tema. Si ya existe, lo salta para evitar duplicados en WordPress.

        Args:
            trends: Lista de tendencias retornadas por _run_trend_detection.
        """
        from neurodiario.db.database import get_db, get_generated_articles_by_topic_today
        from neurodiario.db.models import Article
        from neurodiario.generator.article_generator import ArticleGenerator
        from neurodiario.config.settings import settings

        if not trends:
            logger.info("No hay tendencias para generar artículos.")
            return

        logger.info("=" * 60)
        logger.info("GENERANDO ARTÍCULOS POR TENDENCIA")
        logger.info("=" * 60)

        # Obtener artículos procesados recientes como contexto para la generación
        try:
            with get_db() as db:
                recent_orm = (
                    db.query(Article)
                    .filter(Article.processed == True)  # noqa: E712
                    .order_by(Article.fetched_at.desc())
                    .limit(50)
                    .all()
                )
                article_dicts = [
                    {
                        "title": a.title or "",
                        "url": a.url,
                        "raw_content": a.clean_content or a.raw_content or "",
                    }
                    for a in recent_orm
                ]
        except Exception as exc:
            logger.error(f"Error obteniendo artículos para generación: {exc}", exc_info=True)
            return

        generator = ArticleGenerator(api_key=settings.CLAUDE_API_KEY)

        for trend in trends:
            topic = trend.get("topic", "")

            exists_today = get_generated_articles_by_topic_today(topic)

            if exists_today:
                logger.info(f"Saltando tendencia ya publicada hoy: {topic}")
                continue

            try:
                logger.info(f"Generando artículo para tendencia: {topic}")
                generator.create_article(trend, article_dicts)
                logger.info(f"Artículo generado para tema: {topic}")
            except Exception as exc:
                logger.error(
                    f"Error generando artículo para '{topic}': {exc}", exc_info=True
                )

        logger.info("=" * 60)


def run_nlp_pipeline(batch_size: int = 50) -> int:
    """
    Función de conveniencia para ejecutar el pipeline NLP desde cualquier contexto.

    Args:
        batch_size: Número máximo de artículos a procesar.

    Returns:
        Número de artículos procesados.
    """
    pipeline = NLPPipeline(batch_size=batch_size)
    return pipeline.run_nlp_pipeline()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    run_nlp_pipeline()
