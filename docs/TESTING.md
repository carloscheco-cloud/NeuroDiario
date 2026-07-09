# Testing

## Suite de Pruebas

Los tests se encuentran en `neurodiario/tests/` y usan pytest con unittest.mock.

### test_ingestion.py

| Clase | Tests | Cobertura |
|-------|-------|-----------|
| `TestRSSFetcher` | Inicialización, fetch_articles, manejo de errores, normalización de entradas | `rss_fetcher.py` |
| `TestArticleParser` | Parseo sin URL, parseo batch, extracción de texto, manejo de errores de red | `article_parser.py` |
| `TestDeduplicator` | Normalización de títulos, similitud de cadenas | `deduplicator.py` |
| `TestSourcesConfig` | Estructura de fuentes, claves requeridas, categorías válidas | `sources_config.py` |

### test_nlp.py

| Clase | Tests | Cobertura |
|-------|-------|-----------|
| `TestTextCleaner` | Limpieza HTML, URLs, emails, espacios, batch, oraciones | `text_cleaner.py` |
| `TestArticleClassifier` | Clasificación política, deportes, texto vacío, batch, confianza | `classifier.py` |
| `TestTrendDetector` | Detección de entidades frecuentes, ventana temporal, categorías | `trend_detector.py` |

### test_trends.py

| Clase | Tests | Cobertura |
|-------|-------|-----------|
| `TestTopicClusterer` | KMeans, DBSCAN, formato de salida, keywords, entrada vacía | `topic_cluster.py` |
| `TestTrendDetector` | detect_trends, mín artículos, mín fuentes, múltiples clusters, ordenamiento | `trend_detector.py` |

## Ejecución

```bash
# Todos los tests
pytest neurodiario/tests/ -v

# Un archivo específico
pytest neurodiario/tests/test_nlp.py -v

# Con cobertura
pytest neurodiario/tests/ --cov=neurodiario --cov-report=html
```

## Notas Importantes

Los tests de `TopicClusterer` usan mocks para el modelo de sentence-transformers (no descargan el modelo real). Los tests de `ArticleClassifier` se ejecutan en modo `method="keyword"` para evitar llamadas a la API de Claude.

## Tests que Requieren Atención

- `TestSourcesConfig.test_valid_categories_not_empty` referencia `VALID_CATEGORIES` que no existe en `sources_config.py` (causaría ImportError)
- `TestRSSFetcher.test_save_to_db_not_implemented` espera `NotImplementedError` pero el método está implementado
- `TestArticleClassifier.test_unsupported_method_raises` espera `NotImplementedError` para method="ml" que el código actual no lanza
