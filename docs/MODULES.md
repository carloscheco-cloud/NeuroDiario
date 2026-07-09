# Módulos

## neurodiario/config/settings.py

**Responsabilidad**: centraliza la configuración de la aplicación cargando variables de entorno.  
**Entradas**: variables de entorno (vía `os.getenv`)  
**Salidas**: instancia singleton `settings` con atributos tipados  
**Dependencias**: `python-dotenv`  
**Relación**: usado por todos los demás módulos

## neurodiario/db/models.py

**Responsabilidad**: define los modelos ORM (Source, Article, Trend, GeneratedArticle)  
**Entradas**: ninguna  
**Salidas**: clases ORM para SQLAlchemy  
**Dependencias**: `sqlalchemy`  
**Relación**: usado por `database.py` y todos los módulos que acceden a datos

## neurodiario/db/database.py

**Responsabilidad**: gestión de conexiones, sesiones, y operaciones comunes de BD  
**Entradas**: `DATABASE_URL` vía settings  
**Salidas**: sesiones de BD, funciones helper (save_article, get_unprocessed_articles, etc.)  
**Dependencias**: `sqlalchemy`, `settings`, `models`  
**Relación**: usado por pipelines, scheduler, y módulos de publicación

## neurodiario/ingestion/sources_config.py

**Responsabilidad**: lista de fuentes RSS con parámetros de configuración  
**Entradas**: ninguna (configuración estática)  
**Salidas**: lista `SOURCES`, constantes `FETCH_TIMEOUT`, `MAX_ARTICLES_PER_SOURCE`  
**Dependencias**: ninguna  
**Relación**: consumido por `RSSFetcher`

## neurodiario/ingestion/rss_fetcher.py

**Responsabilidad**: descarga y normalización de feeds RSS  
**Entradas**: lista de fuentes (SOURCES)  
**Salidas**: lista de diccionarios con artículos normalizados  
**Dependencias**: `feedparser`, `requests`, `sources_config`  
**Relación**: alimenta a `ArticleParser` y `database.save_article()`

## neurodiario/ingestion/article_parser.py

**Responsabilidad**: descarga HTML completo y extrae texto del artículo  
**Entradas**: diccionario de artículo con URL  
**Salidas**: artículo enriquecido con raw_html, raw_content, word_count  
**Dependencias**: `newspaper3k`, `beautifulsoup4`, `requests`  
**Relación**: llamado después de `RSSFetcher`, antes de guardar en BD

## neurodiario/ingestion/deduplicator.py

**Responsabilidad**: detecta artículos duplicados por URL exacta o similitud de título  
**Entradas**: URL y título del artículo, sesión de BD  
**Salidas**: booleano (es duplicado o no)  
**Dependencias**: `difflib.SequenceMatcher`, `sqlalchemy`  
**Relación**: usado durante la ingesta antes de guardar

## neurodiario/nlp/text_cleaner.py

**Responsabilidad**: limpieza y normalización de texto en español  
**Entradas**: texto crudo  
**Salidas**: texto limpio (sin HTML, URLs, emails, caracteres especiales)  
**Dependencias**: `re`, `unicodedata`  
**Relación**: primer paso del pipeline NLP

## neurodiario/nlp/entity_extractor.py

**Responsabilidad**: extracción de entidades nombradas (NER)  
**Entradas**: texto limpio  
**Salidas**: diccionario de entidades por tipo (persona, organización, lugar, etc.)  
**Dependencias**: `spacy` (es_core_news_lg)  
**Relación**: segundo paso del pipeline NLP, alimenta detección de tendencias

## neurodiario/nlp/classifier.py

**Responsabilidad**: clasificación temática de artículos con enfoque híbrido  
**Entradas**: texto, título, categoría de fuente  
**Salidas**: tupla (categoría, confianza)  
**Dependencias**: `anthropic` (opcional), `re`  
**Relación**: tercer paso del pipeline NLP

## neurodiario/nlp/topic_cluster.py

**Responsabilidad**: clustering semántico con embeddings (sentence-transformers)  
**Entradas**: lista de artículos  
**Salidas**: clusters con topic_id, keywords, artículos  
**Dependencias**: `sentence-transformers`, `scikit-learn`  
**Relación**: usado por `TrendDetector.detect_trends()`

## neurodiario/nlp/trend_detector.py

**Responsabilidad**: detección de tendencias por entidad y por cluster  
**Entradas**: artículos con entidades, o clusters de topic_cluster  
**Salidas**: lista de tendencias con topic, conteo, fuentes  
**Dependencias**: ninguna externa  
**Relación**: alimenta al generador de artículos y newsletter

## neurodiario/nlp/trend_ranker.py

**Responsabilidad**: ordena tendencias por score de importancia  
**Entradas**: lista de tendencias  
**Salidas**: tendencias ordenadas con campo `score`  
**Dependencias**: ninguna  
**Relación**: usado después de detect_trends

## neurodiario/nlp/source_ranker.py

**Responsabilidad**: asigna score de calidad a fuentes por dominio  
**Entradas**: lista de artículos con URLs  
**Salidas**: score promedio (0.0-1.0)  
**Dependencias**: `urllib.parse`  
**Relación**: módulo auxiliar

## neurodiario/nlp/angle_detector.py

**Responsabilidad**: detecta el ángulo periodístico (economía, política, etc.) vía keywords  
**Entradas**: texto del artículo  
**Salidas**: diccionario con ángulo y confianza  
**Dependencias**: ninguna  
**Relación**: módulo auxiliar

## neurodiario/nlp/story_detector.py

**Responsabilidad**: detecta breaking stories por velocidad de crecimiento  
**Entradas**: clusters con timestamps  
**Salidas**: clusters enriquecidos con velocity y is_breaking_story  
**Dependencias**: ninguna  
**Relación**: módulo auxiliar, no conectado al scheduler activo

## neurodiario/generator/article_generator.py

**Responsabilidad**: genera artículos periodísticos con Claude AI + busca imágenes  
**Entradas**: tendencia/artículo con datos de fuentes  
**Salidas**: diccionario con título, contenido HTML, imagen, tags  
**Dependencias**: `anthropic`, `requests`, settings  
**Relación**: llamado por clustering_pipeline, alimenta a WordPressPublisher

## neurodiario/publisher/wordpress_publisher.py

**Responsabilidad**: publica artículos en WordPress vía REST API  
**Entradas**: diccionario de artículo con título, contenido, categorías, tags, imagen  
**Salidas**: ID del post creado (o None si falla)  
**Dependencias**: `requests`  
**Relación**: llamado por clustering_pipeline y publishing_pipeline

## neurodiario/publisher/facebook_image_generator.py

**Responsabilidad**: genera imagen estilo BBC y publica en Facebook  
**Entradas**: título, URL de WordPress, imagen candidata(s)  
**Salidas**: tupla (post_id, URL de imagen que funcionó)  
**Dependencias**: `Pillow`, `requests`  
**Relación**: llamado por auto_scheduler._job_social_sync()

## neurodiario/publisher/telegram_publisher.py

**Responsabilidad**: publica en canal de Telegram  
**Entradas**: título, URL, channel_id, bot_token, imagen  
**Salidas**: message_id (o None)  
**Dependencias**: `requests`  
**Relación**: llamado por auto_scheduler._job_social_sync()

## neurodiario/publisher/newsletter_generator.py

**Responsabilidad**: genera contenido del newsletter semanal (editorial + PDF)  
**Entradas**: artículos de la semana  
**Salidas**: resumen editorial (HTML), PDF (ruta temporal)  
**Dependencias**: `anthropic`, `reportlab`  
**Relación**: llamado por auto_scheduler._job_newsletter()

## neurodiario/publisher/newsletter_sender.py

**Responsabilidad**: envía newsletter vía Mailchimp API  
**Entradas**: artículos, editorial, PDF, configuración  
**Salidas**: booleano de éxito  
**Dependencias**: `requests`  
**Relación**: llamado por auto_scheduler._job_newsletter()
