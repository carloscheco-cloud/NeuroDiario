"""
Pipeline NLP de NeuroDiario — Módulo 2.

Orquesta el procesamiento de lenguaje natural sobre artículos ya ingestados:
  1. Obtiene artículos no procesados desde la BD.
  2. Limpia y normaliza el texto con TextCleaner.
  3. Extrae entidades nombradas con EntityExtractor.
  4. Clasifica el artículo por tema con ArticleClassifier.
  5. Persiste los resultados en la BD y marca el artículo como procesado.

Uso directo:
    python -m neurodiario.scheduler.nlp_pipeline
    python neurodiario/scheduler/nlp_pipeline.py
"""

import logging
from datetime import datetime
from typing import List

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

        return processed_count


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
