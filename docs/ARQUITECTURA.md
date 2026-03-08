# Arquitectura de NeuroDiario

## Visión General

NeuroDiario es un sistema automatizado de periodismo asistido por IA para el mercado dominicano. El sistema recolecta noticias de medios locales, las analiza con NLP, detecta tendencias y genera artículos periodísticos usando Claude AI, publicándolos automáticamente en WordPress.

```
┌─────────────────────────────────────────────────────────────────┐
│                        NEURODIARIO                              │
│                   Pipeline de Noticias IA                       │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   INGESTION     │───▶│      NLP        │───▶│   GENERATOR     │
│                 │    │                 │    │                 │
│ • RSSFetcher    │    │ • TextCleaner   │    │ • ArticleGen    │
│ • ArticleParser │    │ • EntityExtract │    │   (Claude AI)   │
│ • SourcesConfig │    │ • Classifier    │    │                 │
└─────────────────┘    │ • TrendDetector │    └────────┬────────┘
         │             └─────────────────┘             │
         │                                             ▼
         ▼                                   ┌─────────────────┐
┌─────────────────┐                          │   PUBLISHER     │
│   DATABASE      │◀─────────────────────────│                 │
│                 │                          │ • WordPressPub  │
│ • Article       │                          │   (XML-RPC)     │
│ • Source        │                          └─────────────────┘
│ • GenArticle    │
└─────────────────┘
         ▲
         │
┌─────────────────┐
│   SCHEDULER     │
│                 │
│ • Pipeline      │
│ • APScheduler   │
│   (cron jobs)   │
└─────────────────┘
```

## Módulos

### `ingestion/` — Recolección de Noticias

| Archivo | Responsabilidad |
|---------|-----------------|
| `sources_config.py` | Lista de medios dominicanos y sus feeds RSS |
| `rss_fetcher.py` | Descarga y normaliza entradas de feeds RSS |
| `article_parser.py` | Extrae el texto completo de cada artículo |

**Flujo:**
1. `RSSFetcher.fetch_articles()` → itera sobre `SOURCES` activas
2. Para cada fuente llama a `feedparser.parse()`
3. Normaliza cada entrada al formato interno
4. `ArticleParser.parse_batch()` descarga el HTML y extrae el texto con BeautifulSoup

### `nlp/` — Procesamiento de Lenguaje Natural

| Archivo | Responsabilidad |
|---------|-----------------|
| `text_cleaner.py` | Limpieza y normalización de texto |
| `entity_extractor.py` | NER con spaCy (personas, orgs, lugares) |
| `classifier.py` | Clasificación temática por palabras clave o ML |
| `trend_detector.py` | Detección de temas recurrentes en ventana temporal |

**Flujo:**
1. `TextCleaner.clean()` elimina HTML, URLs, caracteres especiales
2. `EntityExtractor.extract()` identifica entidades con `es_core_news_lg`
3. `ArticleClassifier.classify()` asigna categoría y confianza
4. `TrendDetector.detect()` agrupa entidades frecuentes en las últimas 24h

### `generator/` — Generación con IA

| Archivo | Responsabilidad |
|---------|-----------------|
| `article_generator.py` | Genera texto periodístico con Claude API |

**Tipos de contenido generado:**
- `generate_summary()` — Resumen de múltiples noticias sobre un tema
- `generate_analysis()` — Análisis profundo con contexto y perspectivas
- `generate_digest()` — Boletín diario de tendencias

### `publisher/` — Publicación en WordPress

| Archivo | Responsabilidad |
|---------|-----------------|
| `wordpress_publisher.py` | Publica artículos vía XML-RPC |

### `scheduler/` — Orquestación

| Archivo | Responsabilidad |
|---------|-----------------|
| `pipeline.py` | Coordina el pipeline completo con APScheduler |

**Schedule:**
- **Cada 2 horas:** Ingesta de RSS y parseo
- **7:00 AM:** Generación y publicación del resumen matutino
- **12:00 PM:** Generación y publicación del resumen del mediodía
- **6:00 PM:** Generación y publicación del resumen vespertino

### `db/` — Base de Datos

| Archivo | Responsabilidad |
|---------|-----------------|
| `models.py` | Modelos ORM (Source, Article, GeneratedArticle) |
| `database.py` | Motor SQLAlchemy, sesiones y health check |

### `config/` — Configuración

| Archivo | Responsabilidad |
|---------|-----------------|
| `settings.py` | Variables de entorno centralizadas |

## Diagrama de Datos

```
Source ──────┐
             │ 1:N
             ▼
           Article ──────────────────┐
             │                       │ 1:N
             │ (NLP enrichment)      ▼
             │                 GeneratedArticle
             │                       │
             ▼                       │ (published to)
         [PostgreSQL]          WordPress Post
```

## Tecnologías

| Capa | Tecnología |
|------|-----------|
| Ingesta RSS | feedparser, BeautifulSoup4, lxml |
| NLP | spaCy (es_core_news_lg), sentence-transformers |
| ML | scikit-learn |
| Generación IA | Claude (Anthropic API) |
| Base de datos | PostgreSQL + SQLAlchemy |
| Publicación | wordpress-xmlrpc |
| Scheduler | APScheduler |
| Testing | pytest |

## Variables de Entorno Requeridas

Ver `.env.example` en la raíz del proyecto.

## Decisiones de Diseño

1. **Carga perezosa de modelos:** spaCy y el cliente WordPress se inicializan solo cuando se necesitan, para reducir el tiempo de arranque.
2. **Context manager para BD:** `get_db()` garantiza commit/rollback automático y cierre de sesión.
3. **Clasificación por capas:** Primero por palabras clave (rápido, sin GPU), con opción de escalar a modelo ML.
4. **Pipeline modular:** Cada fase puede ejecutarse de forma independiente para facilitar el desarrollo y las pruebas.
