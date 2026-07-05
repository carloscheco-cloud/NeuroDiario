"""
Pipeline NLP de NeuroDiario — MODIFICADO PARA FASE 1 (Sin Clustering)

Orquesta el procesamiento de lenguaje natural sobre artículos ya ingestados:
  1. Obtiene artículos no procesados desde la BD.
  2. Limpia y normaliza el texto con TextCleaner.
  3. Extrae entidades nombradas con EntityExtractor.
  4. Clasifica el artículo por tema con ArticleClassifier (híbrido: fuente + Haiku).
  5. Persiste los resultados en la BD y marca el artículo como procesado.

FASE 1: Los módulos de clustering y trend detection están DESHABILITADOS.
Los artículos procesados quedan listos en la BD para publicación manual vía WordPress.

Uso directo:
    python -m neurodiario.scheduler.nlp_pipeline
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class NLPPipeline:
    """Orquesta el procesamiento NLP de artículos no procesados."""

    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self._cleaner = None
        self._extractor = None
        self._classifier = None

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
            from neurodiario.config.settings import settings
            self._extractor = EntityExtractor(model_name=settings.SPACY_MODEL)
        return self._extractor

    @property
    def classifier(self):
        if self._classifier is None:
            from neurodiario.nlp.classifier import ArticleClassifier
            from neurodiario.config.settings import settings
            # Híbrido: usa la categoría de la fuente cuando es confiable,
            # y Claude Haiku cuando la fuente es genérica/dudosa.
            self._classifier = ArticleClassifier(
                method="hybrid",
                api_key=getattr(settings, "CLAUDE_API_KEY", None),
                model=getattr(settings, "CLAUDE_MODEL", None),
            )
        return self._classifier

    def _process_article(self, article, source_category: str = None) -> dict:
        """
        Aplica el pipeline NLP completo a un artículo ORM.

        Args:
            article: Instancia de Article (SQLAlchemy ORM).
            source_category: Categoría declarada por la fuente RSS (si se conoce).

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

        # 4) Clasificación (pasando la categoría de la fuente para la ruta híbrida)
        category, confidence = self.classifier.classify_article(
            title=article.title or "",
            content=clean_text,
            source_category=source_category,
        )

        return {
            "clean_content": clean_text,
            "summary": summary,
            "entities": entities,
            "category": category,
            "category_confidence": confidence,
        }

    def run_nlp_pipeline(self) -> int:
        """
        Ejecuta el pipeline NLP sobre todos los artículos pendientes.

        Returns:
            Número de artículos procesados exitosamente.
        """
        from neurodiario.db.database import get_db, get_unprocessed_articles
        from neurodiario.db.models import Article, Source

        logger.info("=" * 60)
        logger.info("INICIANDO PIPELINE NLP - FASE 1 (SIN CLUSTERING)")
        logger.info(f"  Fecha    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"  Batch    : {self.batch_size} artículos")
        logger.info("=" * 60)

        articles = get_unprocessed_articles(limit=self.batch_size)
        if not articles:
            logger.info("No hay artículos pendientes de procesamiento NLP.")
            return 0

        # Mapa source_id -> categoría de la fuente, para la ruta híbrida
        with get_db() as db:
            fuentes_cat = {s.id: s.category for s in db.query(Source).all()}

        logger.info(f"Artículos a procesar: {len(articles)}")
        processed_count = 0

        for article in articles:
            try:
                source_category = fuentes_cat.get(article.source_id)
                nlp_data = self._process_article(article, source_category=source_category)

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

        logger.info("\n🚫 Módulos de Clustering y Trends deshabilitados (Fase 1)")
        logger.info(f"✓ {processed_count} artículos procesados y listos para publicación")

        return processed_count


def run_nlp_pipeline(batch_size: int = 50) -> int:
    """Función de conveniencia para ejecutar el pipeline NLP desde cualquier contexto."""
    pipeline = NLPPipeline(batch_size=batch_size)
    return pipeline.run_nlp_pipeline()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    run_nlp_pipeline()
