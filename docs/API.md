# API Interna

NeuroDiario no expone una API REST pública. Este documento describe la API interna de los módulos Python.

## Ingesta

```python
from neurodiario.ingestion import RSSFetcher, ArticleParser

# Obtener artículos de todas las fuentes activas
fetcher = RSSFetcher()
articles = fetcher.fetch_articles()  # -> List[Dict]

# Obtener artículos de una fuente específica
articles = fetcher.fetch_feed({"name": "...", "url": "...", "active": True})

# Parsear contenido completo
parser = ArticleParser(timeout=20)
enriched = parser.parse(article_dict)     # -> Dict con raw_html, raw_content, word_count
enriched_list = parser.parse_batch(articles)

# Deduplicación
from neurodiario.ingestion.deduplicator import is_duplicate
is_dup = is_duplicate(url, title, db_session)  # -> bool
```

## NLP

```python
from neurodiario.nlp import TextCleaner, EntityExtractor, ArticleClassifier

# Limpieza
cleaner = TextCleaner(remove_urls=True, lowercase=False)
clean = cleaner.clean(raw_text)            # -> str
summary = cleaner.get_summary(text, max_sentences=3)
normalized = cleaner.normalize_text(text)  # minúsculas, sin acentos, sin stopwords

# Entidades
extractor = EntityExtractor(model_name="es_core_news_lg")
entities = extractor.extract(clean_text)   # -> {"persona": [...], "organización": [...], ...}

# Clasificación
classifier = ArticleClassifier(method="hybrid", api_key="sk-ant-...")
category, confidence = classifier.classify(text, title, source_category="general")
```

## Generación

```python
from neurodiario.generator import ArticleGenerator

generator = ArticleGenerator(api_key="sk-ant-...", model="claude-haiku-4-5-20251001")

# Desde un solo artículo
result = generator.generate_from_single_article(
    title="...", content="...", source="Diario Libre",
    category="politica", url="...", published_at=datetime_obj
)
# -> {"title", "content", "excerpt", "category", "tags", "image_url", "image_candidates"}

# Desde múltiples fuentes (trend)
result = generator.create_article(
    trend={"topic": "...", "category": "politica"},
    articles=[{"title": "...", "url": "...", "source": "...", "raw_content": "..."}]
)
```

## Publicación

```python
from neurodiario.publisher import WordPressPublisher

publisher = WordPressPublisher(url="https://...", username="...", password="...")
post_id = publisher.publish({
    "title": "...", "content": "<p>...</p>",
    "categories": ["Política"], "tags": ["RD"],
    "status": "publish", "image_url": "https://..."
})

# Facebook
from neurodiario.publisher.facebook_image_generator import post_to_facebook_with_image
post_id, working_url = post_to_facebook_with_image(
    title="...", wordpress_url="...",
    page_id="...", page_token="...",
    image_url=["url1", "url2", "url3"]
)

# Telegram
from neurodiario.publisher.telegram_publisher import post_to_telegram
msg_id = post_to_telegram(
    title="...", wordpress_url="...",
    channel_id="...", bot_token="...", image_url="..."
)
```

## Base de Datos

```python
from neurodiario.db import get_db, init_db, Article, GeneratedArticle
from neurodiario.db.database import save_article, get_unprocessed_articles, health_check

init_db()  # Crea tablas si no existen
ok = health_check()  # Verifica conexión

with get_db() as db:
    articles = db.query(Article).filter(Article.processed == False).all()
```
