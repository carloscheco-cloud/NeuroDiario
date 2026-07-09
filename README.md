<p align="center">
  <img src="neurodiario/publisher/assets/favicon_nd.png" alt="NeuroDiario Logo" width="100"/>
</p>

<h1 align="center">NeuroDiario</h1>

<p align="center">
  <strong>La Inteligencia Informativa de República Dominicana</strong>
</p>

<p align="center">
  <em>Plataforma autónoma de periodismo digital impulsada por inteligencia artificial.<br>
  Recolecta, analiza, genera y publica noticias — 24/7, sin intervención humana.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="Python 3.11"/>
  <img src="https://img.shields.io/badge/Claude_AI-Haiku-blueviolet?logo=anthropic" alt="Claude AI"/>
  <img src="https://img.shields.io/badge/PostgreSQL-15+-blue?logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/WordPress-REST_API-21759b?logo=wordpress" alt="WordPress"/>
  <img src="https://img.shields.io/badge/deploy-Railway-0B0D0E?logo=railway" alt="Railway"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"/>
</p>

---

## Tabla de Contenido

- [Descripción](#descripción)
- [Características](#características)
- [Arquitectura](#arquitectura)
- [Flujo del Pipeline](#flujo-del-pipeline)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Componentes Principales](#componentes-principales)
- [Base de Datos](#base-de-datos)
- [Scheduler](#scheduler)
- [Integración con Claude AI](#integración-con-claude-ai)
- [WordPress](#wordpress)
- [Distribución Social](#distribución-social)
- [Generación de Imágenes](#generación-de-imágenes)
- [Newsletter Semanal](#newsletter-semanal)
- [Sistema de Logs](#sistema-de-logs)
- [Manejo de Errores](#manejo-de-errores)
- [Dependencias](#dependencias)
- [Tecnologías](#tecnologías)
- [Seguridad](#seguridad)
- [Testing](#testing)
- [Desarrollo](#desarrollo)
- [Roadmap](#roadmap)
- [Contribuir](#contribuir)
- [Licencia](#licencia)
- [Observaciones del Arquitecto](#observaciones-del-arquitecto)

---

## Descripción

NeuroDiario es una plataforma de periodismo autónomo que opera como una redacción digital completa. Monitorea los principales medios de comunicación dominicanos e internacionales relevantes para República Dominicana, agrupa noticias duplicadas mediante clustering semántico, genera artículos originales con Claude AI, y los distribuye automáticamente a WordPress, Facebook, Telegram y un newsletter semanal vía Mailchimp.

El sistema corre de forma autónoma en Railway (Docker + PostgreSQL), sin requerir una máquina local. Produce tres ciclos de publicación diarios (7am, 1pm, 7pm hora Santo Domingo) con hasta 25 artículos por ciclo.

---

## Características

- **Ingesta RSS automatizada** de 10+ fuentes dominicanas e internacionales, con ejecución cada 20 minutos
- **Filtro de relevancia** para noticias internacionales: solo pasan las relacionadas con República Dominicana
- **Deduplicación por URL y similitud de título** (SequenceMatcher con umbral 0.80)
- **Pipeline NLP completo**: limpieza de texto, extracción de entidades (spaCy), clasificación temática híbrida (categoría de fuente + Claude Haiku + keywords como fallback)
- **Clustering semántico** de noticias con TF-IDF + cosine similarity para agrupar la misma noticia de múltiples fuentes
- **Generación de artículos** con Claude AI (Haiku): redacción periodística original con estilo Bloomberg/BBC
- **Búsqueda inteligente de imágenes**: Serper.dev (fuentes oficiales primero, luego Google Images excluyendo medios locales) + Pexels como fallback
- **Publicación automatizada en WordPress** vía REST API con imagen destacada, categorías y tags
- **Distribución social escalonada**: un artículo cada 12 minutos a Facebook (con imagen generada estilo BBC) y Telegram
- **Newsletter semanal** vía Mailchimp con resumen editorial generado por Claude + PDF adjunto (ReportLab)
- **Detección de tendencias**: identifica breaking stories por velocidad de crecimiento y cobertura multi-medio
- **Scripts de mantenimiento**: limpieza de BD, limpieza de WordPress, verificación de fuentes, diagnóstico de BD

---

## Arquitectura

```mermaid
graph TD
    subgraph Ingesta["📥 Ingesta (cada 20 min)"]
        RSS[Feeds RSS<br>10+ fuentes] --> Fetcher[RSSFetcher<br>feedparser + requests]
        Fetcher --> Parser[ArticleParser<br>newspaper3k + BS4]
        Parser --> Dedup[Deduplicator<br>URL + título]
        Dedup --> Filter[Filtro de Relevancia<br>solo RD-relevante]
    end

    subgraph NLP["🧠 NLP (cada 20 min)"]
        Filter --> Cleaner[TextCleaner<br>limpieza + normalización]
        Cleaner --> NER[EntityExtractor<br>spaCy es_core_news_lg]
        NER --> Classifier[ArticleClassifier<br>híbrido: fuente + Haiku + keywords]
    end

    subgraph Generacion["✍️ Generación (7am, 1pm, 7pm)"]
        Classifier --> Clustering[Clustering TF-IDF<br>cosine similarity]
        Clustering --> Ranker[Ranking por<br>medios + categoría]
        Ranker --> Claude[Claude Haiku<br>generación de artículo]
        Claude --> ImageSearch[Búsqueda de imagen<br>Serper → Pexels]
    end

    subgraph Publicacion["📤 Publicación"]
        ImageSearch --> WP[WordPress<br>REST API]
        WP --> Facebook[Facebook<br>Graph API + imagen BBC]
        WP --> Telegram[Telegram<br>Bot API]
        WP --> Newsletter[Newsletter semanal<br>Mailchimp]
    end

    subgraph Datos["💾 Datos"]
        DB[(PostgreSQL<br>sources · articles<br>generated_articles · trends)]
    end

    Filter --> DB
    Classifier --> DB
    Claude --> DB
    WP --> DB

    style Ingesta fill:#e8f0fe,stroke:#1a73e8
    style NLP fill:#e8f5e9,stroke:#34a853
    style Generacion fill:#fef7e0,stroke:#f9ab00
    style Publicacion fill:#fce8e6,stroke:#ea4335
    style Datos fill:#f3e8fd,stroke:#a142f4
```

> Para documentación detallada de la arquitectura, ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Flujo del Pipeline

El sistema opera en cinco fases automatizadas:

**1. Ingesta RSS** (cada 20 minutos): `RSSFetcher` descarga feeds de 10+ medios → `ArticleParser` extrae contenido completo con newspaper3k/BeautifulSoup → `Deduplicator` filtra duplicados por URL y título similar → filtro de relevancia para fuentes internacionales → guardado en PostgreSQL.

**2. Procesamiento NLP** (cada 20 minutos): `TextCleaner` normaliza el texto → `EntityExtractor` identifica personas, organizaciones y lugares con spaCy → `ArticleClassifier` asigna categoría temática (híbrido: confía en secciones específicas de fuentes, usa Claude Haiku para fuentes genéricas, y keywords como fallback).

**3. Clustering y Generación** (7am, 1pm, 7pm): `deduplicator_clusters` agrupa artículos por similitud TF-IDF + coseno → ordena clusters por cobertura multi-medio y prioridad de categoría → toma los 25 mejores → `ArticleGenerator` llama a Claude Haiku para sintetizar cada cluster en un artículo original → busca imagen con Serper.dev/Pexels.

**4. Publicación en WordPress**: sube imagen destacada a la Media Library → crea post con categorías y tags vía REST API → publica con status `publish`.

**5. Distribución social** (cada 12 minutos, escalonado): para cada artículo publicado sin distribuir, genera imagen estilo BBC con Pillow → publica en Facebook vía Graph API `/photos` → publica en Telegram vía Bot API `sendPhoto`. Newsletter semanal los domingos a las 8am.

> Para el flujo detallado paso a paso, ver [docs/PIPELINE.md](docs/PIPELINE.md) y [docs/DATA_FLOW.md](docs/DATA_FLOW.md).

---

## Instalación

### Requisitos Previos

- Python 3.11+
- PostgreSQL 14+
- WordPress con REST API habilitada y autenticación básica (Application Passwords)
- Clave de API de Anthropic (Claude)

### Instalación Local

```bash
# 1. Clonar el repositorio
git clone https://github.com/carloscheco-cloud/NeuroDiario.git
cd NeuroDiario

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Descargar modelo de spaCy en español (grande)
python -m spacy download es_core_news_lg

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales (ver sección Configuración)

# 6. Inicializar la base de datos
python -c "from neurodiario.db.database import init_db; init_db()"
```

### Despliegue en Railway (Producción)

El proyecto incluye un `Dockerfile` optimizado para el límite de 4GB de Railway:

```bash
# El CMD del Dockerfile ejecuta automáticamente el scheduler:
CMD ["python", "-m", "scheduler.auto_scheduler"]
```

Railway autodeploy está conectado al repositorio GitHub. Cada push a `main` dispara un nuevo despliegue.

> Para instrucciones detalladas, ver [docs/INSTALLATION.md](docs/INSTALLATION.md) y [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Configuración

Copia `.env.example` a `.env` y configura las variables:

| Variable | Descripción | Ejemplo | Requerida |
|----------|------------|---------|-----------|
| `WORDPRESS_URL` | URL del sitio WordPress | `https://neurodiario.com` | ✅ |
| `WORDPRESS_USER` | Usuario de WordPress | `neurodiario` | ✅ |
| `WORDPRESS_PASSWORD` | Application Password de WordPress | `xxxx xxxx xxxx` | ✅ |
| `DATABASE_URL` | URL de conexión PostgreSQL | `postgresql://user:pass@host/db` | ✅ |
| `ANTHROPIC_API_KEY` | Clave de API de Anthropic | `sk-ant-...` | ✅ |
| `CLAUDE_MODEL` | Modelo de Claude a usar | `claude-haiku-4-5-20251001` | No |
| `SERPER_API_KEY` | Clave de Serper.dev para Google Images | `...` | No |
| `PEXELS_API_KEY` | Clave de Pexels (fallback de imágenes) | `...` | No |
| `FACEBOOK_PAGE_TOKEN` | Token permanente de Facebook Page | `...` | No |
| `FACEBOOK_PAGE_ID` | ID de la página de Facebook | `1042274052307538` | No |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | `...` | No |
| `TELEGRAM_CHANNEL_ID` | ID del canal de Telegram | `-1004336394332` | No |
| `SPACY_MODEL` | Modelo spaCy para NER | `es_core_news_lg` | No |
| `DEBUG` | Modo debug (SQL echo) | `False` | No |
| `LOG_LEVEL` | Nivel de logging | `INFO` | No |
| `TIMEZONE` | Zona horaria | `America/Santo_Domingo` | No |

> Para la tabla completa de variables, ver [docs/ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md).

---

## Uso

### Ejecutar el scheduler completo (producción)

```bash
python -m scheduler.auto_scheduler
```

Esto inicia todos los jobs automáticos: ingesta, NLP, clustering, distribución social y newsletter.

### Ejecutar solo la ingesta RSS

```bash
python -m neurodiario.scheduler.pipeline
```

### Ejecutar solo el pipeline NLP

```bash
python -m neurodiario.scheduler.nlp_pipeline
```

### Analizar clusters sin publicar (simulación)

```bash
python clustering_pipeline.py
```

### Publicar con clustering

```bash
python clustering_pipeline.py --publicar
```

### Analizar agrupamiento de noticias

```bash
python deduplicator_clusters.py --horas 24 --top 20
```

### Verificar fuentes RSS

```bash
python verificar_fuentes.py
```

### Diagnóstico de base de datos

```bash
python -m neurodiario.tools.Db_stats
```

### Limpieza de base de datos (con confirmación)

```bash
python limpiar_base_datos.py            # Simulación
python limpiar_base_datos.py --apply    # Borra (pide BORRAR)
```

### Limpieza de WordPress

```bash
python limpiar_wordpress.py             # Simulación
python limpiar_wordpress.py --apply     # Borra permanente (pide BORRAR)
```

---

## Estructura del Proyecto

```
NeuroDiario/
├── Dockerfile                      # Imagen Docker para Railway (Python 3.11-slim)
├── requirements.txt                # Dependencias Python
├── .env.example                    # Plantilla de variables de entorno
├── .gitignore                      # Exclusiones de Git
├── dockerignore                    # Exclusiones de Docker
│
├── scheduler/
│   └── auto_scheduler.py           # 🎯 SCHEDULER PRINCIPAL — orquesta todos los jobs
│
├── clustering_pipeline.py          # Pipeline de generación con clustering (activo)
├── deduplicator_clusters.py        # Agrupador TF-IDF de noticias similares
│
├── neurodiario/                    # Paquete principal de la aplicación
│   ├── config/
│   │   └── settings.py             # Configuración centralizada desde env vars
│   │
│   ├── db/
│   │   ├── models.py               # Modelos ORM: Source, Article, GeneratedArticle, Trend
│   │   └── database.py             # Motor SQLAlchemy, sesiones, helpers de BD
│   │
│   ├── ingestion/
│   │   ├── sources_config.py       # Lista de fuentes RSS con límites por fuente
│   │   ├── rss_fetcher.py          # Descarga y normalización de feeds RSS
│   │   ├── article_parser.py       # Extracción de contenido (newspaper3k + BS4)
│   │   └── deduplicator.py         # Deduplicación por URL y similitud de título
│   │
│   ├── nlp/
│   │   ├── text_cleaner.py         # Limpieza HTML, URLs, normalización de texto
│   │   ├── entity_extractor.py     # NER con spaCy: personas, orgs, lugares
│   │   ├── classifier.py           # Clasificación híbrida: fuente + Haiku + keywords
│   │   ├── topic_cluster.py        # Clustering DBSCAN/KMeans con sentence-transformers
│   │   ├── trend_detector.py       # Detección de tendencias por entidad y por cluster
│   │   ├── trend_ranker.py         # Ranking de tendencias por score compuesto
│   │   ├── source_ranker.py        # Score de calidad por dominio de fuente
│   │   ├── angle_detector.py       # Detección del ángulo periodístico por keywords
│   │   └── story_detector.py       # Detección de breaking stories por velocidad
│   │
│   ├── generator/
│   │   └── article_generator.py    # Generación con Claude + búsqueda de imágenes
│   │
│   ├── publisher/
│   │   ├── wordpress_publisher.py  # Publicación vía WordPress REST API
│   │   ├── facebook_image_generator.py  # Generación de imagen BBC + publicación FB
│   │   ├── telegram_publisher.py   # Publicación en canal de Telegram
│   │   ├── newsletter_generator.py # Generación de newsletter semanal + PDF
│   │   ├── newsletter_sender.py    # Envío vía Mailchimp API
│   │   └── assets/
│   │       ├── favicon_nd.png      # Favicon de NeuroDiario
│   │       └── DejaVuSans-Bold.ttf # Fuente para imágenes de Facebook
│   │
│   ├── scheduler/
│   │   ├── pipeline.py             # Pipeline de ingesta + clase Pipeline (legacy)
│   │   ├── nlp_pipeline.py         # Pipeline NLP independiente
│   │   └── publishing_pipeline.py  # Pipeline de publicación individual (legacy)
│   │
│   ├── tools/
│   │   └── Db_stats                # Diagnóstico de base de datos (solo lectura)
│   │
│   └── tests/
│       ├── test_ingestion.py       # Tests de ingesta, parser y deduplicación
│       ├── test_nlp.py             # Tests de limpieza, clasificación y tendencias
│       └── test_trends.py          # Tests de clustering y detección de tendencias
│
├── limpiar_base_datos.py           # Limpieza total de BD (dry-run por defecto)
├── limpiar_failed.py               # Limpieza de GeneratedArticles fallidos
├── limpiar_wordpress.py            # Limpieza total de WordPress (dry-run por defecto)
├── migrate_facebook_fields.py      # Migración: columnas Facebook en generated_articles
├── migrate_telegram_fields.py      # Migración: columnas Telegram en generated_articles
├── relleno_source_id.py            # Repara source_id en artículos históricos
├── verificar_fuentes.py            # Verificador de conectividad de fuentes RSS
│
└── docs/
    ├── ARQUITECTURA.md             # (Obsoleto — reemplazado por esta documentación)
    └── ROADMAP.md                  # (Obsoleto — reemplazado por docs/ROADMAP.md)
```

---

## Componentes Principales

> Para documentación detallada de cada módulo, ver [docs/MODULES.md](docs/MODULES.md).

### Ingesta (`neurodiario/ingestion/`)
Recolecta noticias de 10+ fuentes RSS dominicanas e internacionales. Descarga el contenido completo de cada artículo con newspaper3k (fallback a BeautifulSoup), detecta duplicados, filtra internacionales por relevancia para RD, y persiste en PostgreSQL.

### NLP (`neurodiario/nlp/`)
Procesa los artículos crudos: limpia HTML y caracteres especiales, extrae entidades nombradas con spaCy (`es_core_news_lg`), y clasifica temáticamente con un enfoque híbrido de tres capas (categoría de fuente → Claude Haiku → keywords).

### Generación (`neurodiario/generator/`)
Usa Claude AI (modelo Haiku) para generar artículos periodísticos originales en español, con prompt especializado estilo Bloomberg/BBC. Busca imágenes relevantes en tres niveles: fuentes oficiales dominicanas (Serper.dev), Google Images general excluyendo medios locales, y Pexels como fallback.

### Publicación (`neurodiario/publisher/`)
Publica en WordPress vía REST API con imagen destacada. Genera imágenes estilo BBC para Facebook con Pillow. Distribuye a Telegram con Bot API. Envía newsletter semanal con Mailchimp incluyendo resumen editorial y PDF adjunto.

### Scheduler (`scheduler/auto_scheduler.py`)
Orquesta todo el sistema con APScheduler: ingesta cada 20min, NLP cada 20min, clustering a las 7/13/19h, distribución social cada 12min, newsletter los domingos 8am. Todo en zona horaria `America/Santo_Domingo`.

---

## Base de Datos

PostgreSQL con SQLAlchemy ORM. Cuatro tablas:

```mermaid
erDiagram
    Source ||--o{ Article : "1:N"
    Article ||--o{ GeneratedArticle : "1:N"

    Source {
        int id PK
        string name
        string url UK
        string category
        string language
        boolean active
        datetime created_at
    }

    Article {
        int id PK
        string title
        string url UK
        text summary
        text raw_html
        text raw_content
        text clean_content
        int word_count
        string image_url
        string category
        float category_confidence
        json entities
        boolean processed
        datetime published_at
        datetime fetched_at
        int source_id FK
    }

    GeneratedArticle {
        int id PK
        string title
        text content
        string article_type
        string category
        json tags
        string status
        int wordpress_post_id
        datetime published_at
        datetime created_at
        string facebook_post_id
        datetime facebook_posted_at
        string telegram_message_id
        datetime telegram_posted_at
        string model_used
        int prompt_tokens
        int completion_tokens
        int source_article_id FK
    }

    Trend {
        int id PK
        string topic
        int article_count
        json sources
        datetime created_at
    }
```

**Estados de `GeneratedArticle.status`**: `draft`, `published`, `failed`, `processing`, `clustered`.

> Para más detalles, ver [docs/DATABASE.md](docs/DATABASE.md).

---

## Scheduler

El scheduler principal es `scheduler/auto_scheduler.py`, ejecutado como proceso Docker:

| Job | Frecuencia | Descripción |
|-----|-----------|-------------|
| Ingesta RSS | Cada 20 minutos | Descarga feeds, parsea, filtra, guarda en BD |
| Pipeline NLP | Cada 20 minutos | Limpia, extrae entidades, clasifica artículos sin procesar |
| Clustering + Generación | 7:00, 13:00, 19:00 (RD) | Agrupa noticias, genera y publica hasta 25 artículos |
| Distribución Social | Cada 12 minutos | Publica 1 artículo en Facebook + Telegram (escalonado) |
| Newsletter Semanal | Domingos 8:00 AM (RD) | Genera resumen editorial + PDF, envía vía Mailchimp |

> Para más detalles, ver [docs/SCHEDULER.md](docs/SCHEDULER.md).

---

## Integración con Claude AI

Claude AI interviene en tres puntos del pipeline:

1. **Clasificación temática** (`classifier.py`): cuando la categoría de la fuente es genérica (`general`, `internacional`), usa Claude Haiku con un prompt de 10 tokens max para clasificar en una de las 10 categorías válidas. Modelo: `claude-haiku-4-5-20251001`.

2. **Generación de artículos** (`article_generator.py`): genera artículos periodísticos originales de 450-650 palabras con un system prompt detallado de estilo editorial. Soporta dos modos: `generate_from_single_article()` y `create_article()` (sintetiza múltiples fuentes). Modelo configurable, default: `claude-haiku-4-5-20251001`.

3. **Query de imagen** (`article_generator.py`): genera una query de 4-6 palabras para buscar la imagen más relevante en Google Images. Modelo: mismo del generador.

4. **Newsletter editorial** (`newsletter_generator.py`): genera el resumen editorial semanal para los suscriptores. Modelo: `claude-haiku-4-5-20251001`.

> Para más detalles, ver [docs/CLAUDE_AI.md](docs/CLAUDE_AI.md).

---

## WordPress

Integración exclusivamente vía **REST API** (`/wp-json/wp/v2/`) con autenticación HTTPBasicAuth (Application Passwords). Funcionalidades:

- **Subida de imágenes** a Media Library con asignación como `featured_media`
- **Creación de posts** con título, contenido HTML, categorías, tags y status
- **Creación automática** de categorías y tags inexistentes
- **Actualización de contenido** post-publicación (para URLs de compartir)

> Para más detalles, ver [docs/WORDPRESS.md](docs/WORDPRESS.md).

---

## Distribución Social

### Facebook
Genera imágenes estilo BBC (1200×630px) con Pillow: foto de fondo + overlay oscuro + título + barra de marca NeuroDiario. Publica vía Graph API `/photos` con caption. Intenta múltiples URLs candidatas hasta encontrar una que descargue exitosamente. Fallback: gradiente navy con textura de red neuronal.

### Telegram
Publica en canal `@NeuroDiario` vía Bot API. Intenta primero `sendPhoto` con imagen; si falla, usa `sendMessage` con preview. Formato HTML en caption con título en negrita y enlace al artículo.

### WhatsApp Canal

Canal oficial: [whatsapp.com/channel/0029VbDCDigJP21BALwA9a1t](https://whatsapp.com/channel/0029VbDCDigJP21BALwA9a1t)

La distribución a WhatsApp opera **fuera del código Python**, mediante una automatización en Make.com:

| Componente | Detalle |
|-----------|---------|
| Herramienta | Make.com — Scenario "WhatsApp Canal v2" (ID: 5610516) |
| Frecuencia | Cada 15 minutos |
| Fuente | RSS de neurodiario.com (`/feed/`, 1 artículo por ciclo) |
| Extracción imagen | Text Parser Match Pattern extrae `src="([^"]+)"` del campo `<description>` del RSS |
| Envío | HTTP POST a `https://gate.whapi.cloud/messages/image` |
| Canal destino | `120363412361118712@newsletter` |
| Plugin requerido | "Featured Images in RSS" (WordPress) — embebe la imagen en el `<description>` del feed |

> **Hoja de ruta:** Cuando Meta lance su API oficial para canales de WhatsApp, esta integración migrará directamente hacia ella y se integrará al código Python del repositorio.

---

## Generación de Imágenes

Estrategia de tres niveles para encontrar imágenes relevantes:

1. **Nivel 1 — Fuentes oficiales**: Serper.dev con filtro `site:` hacia 15+ dominios gubernamentales y de partidos políticos dominicanos (presidencia.gob.do, senadord.gob.do, etc.)
2. **Nivel 2 — Google Images general**: Serper.dev excluyendo 17 dominios de medios dominicanos comerciales (para evitar marcas de agua)
3. **Nivel 3 — Pexels**: fallback con CDN abierto, casi nunca falla la descarga

Se recolectan múltiples URLs candidatas en orden de prioridad. Facebook intenta descargar cada una hasta que alguna funcione.

> Para más detalles, ver [docs/IMAGE_GENERATION.md](docs/IMAGE_GENERATION.md).

---

## Newsletter Semanal

Cada domingo a las 8am (hora RD), el sistema:

1. Obtiene los 5 mejores artículos publicados en la semana (priorizados por categoría)
2. Genera un resumen editorial con Claude Haiku
3. Genera un PDF con ReportLab (banner, tabla de noticias, distribución por categoría)
4. Envía vía Mailchimp API: crea campaña, agrega contenido HTML, y envía

---

## Sistema de Logs

Logging estándar de Python (`logging`) configurado en `auto_scheduler.py`:

- Formato: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Nivel por defecto: `INFO`
- Cada módulo usa `logger = logging.getLogger(__name__)` para trazabilidad
- Separadores visuales (`=` * 60) al inicio de cada job para facilitar lectura
- Emojis indicadores: ✓ éxito, ✗ fallo, 🖼 imagen, 📘 Facebook, 📱 Telegram, 📧 newsletter

> Para más detalles, ver [docs/LOGGING.md](docs/LOGGING.md).

---

## Manejo de Errores

- **try/except** en cada operación externa (HTTP, BD, APIs) con logging del error
- **Rollback automático** en sesiones de BD vía context manager `get_db()`
- **Fallbacks en cascada**: newspaper3k → BeautifulSoup; Serper → Pexels; sendPhoto → sendMessage
- **Auto-limpieza de artículos atascados** en estado `processing` por más de 30 minutos
- **Tope de seguridad en clustering**: clusters > 8 artículos se desarman (señal de representante genérico)
- **Validación de imágenes**: verifica Content-Type, tamaño mínimo (3KB), dimensiones mínimas (300×200)
- **Dry-run por defecto** en scripts de limpieza con confirmación `BORRAR`

> Para más detalles, ver [docs/ERROR_HANDLING.md](docs/ERROR_HANDLING.md).

---

## Dependencias

| Librería | Versión | Propósito |
|----------|---------|-----------|
| `anthropic` | 0.39.0 | Cliente API de Claude para generación de contenido |
| `sqlalchemy` | 2.0.23 | ORM para PostgreSQL |
| `psycopg2-binary` | 2.9.9 | Driver PostgreSQL |
| `spacy` | 3.7.2 | NLP: extracción de entidades nombradas |
| `sentence-transformers` | 2.7.0 | Embeddings semánticos para clustering |
| `scikit-learn` | 1.3.2 | DBSCAN, KMeans, TF-IDF |
| `feedparser` | 6.0.10 | Parser de feeds RSS/Atom |
| `beautifulsoup4` | 4.12.2 | Extracción de texto HTML |
| `newspaper3k` | 0.2.8 | Extracción inteligente de artículos web |
| `requests` | 2.31.0 | Cliente HTTP |
| `apscheduler` | 3.10.4 | Scheduler de tareas programadas |
| `reportlab` | latest | Generación de PDFs |
| `python-dotenv` | 1.0.0 | Carga de variables de entorno |
| `Pillow` | (dep. transitiva) | Generación de imágenes para Facebook |

---

## Tecnologías

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.11 |
| Base de datos | PostgreSQL + SQLAlchemy ORM |
| IA / LLM | Claude AI (Anthropic API) — modelo Haiku |
| NLP | spaCy (`es_core_news_lg`), sentence-transformers, scikit-learn, NLTK |
| Ingesta | feedparser, newspaper3k, BeautifulSoup4, lxml |
| Imágenes | Serper.dev (Google Images), Pexels API, Pillow |
| CMS | WordPress REST API |
| Redes Sociales | Facebook Graph API, Telegram Bot API |
| Email | Mailchimp API v3 |
| PDF | ReportLab |
| Scheduling | APScheduler |
| Despliegue | Docker, Railway (Pro) |
| Control de versión | GitHub (autodeploy) |

---

## Seguridad

- **Variables sensibles** (API keys, contraseñas, tokens) se cargan exclusivamente desde variables de entorno, nunca hardcodeadas en código
- `.env` está en `.gitignore` y nunca se commitea
- WordPress usa Application Passwords con HTTPBasicAuth sobre HTTPS (XML-RPC está bloqueado)
- Token de Facebook debe ser un Page Access Token permanente (obtenido vía `GET /me/accounts`)
- El Dockerfile elimina archivos innecesarios (docs, tests, .git) del contenedor de producción
- Scripts de limpieza tienen tres capas de seguridad: dry-run por defecto, flag `--apply`, confirmación `BORRAR`
- Las imágenes de medios dominicanos comerciales están bloqueadas para evitar problemas de derechos de autor

> Para más detalles, ver [docs/SECURITY.md](docs/SECURITY.md).

---

## Testing

```bash
# Ejecutar todos los tests
pytest neurodiario/tests/ -v

# Tests por módulo
pytest neurodiario/tests/test_ingestion.py -v
pytest neurodiario/tests/test_nlp.py -v
pytest neurodiario/tests/test_trends.py -v

# Con cobertura
pytest neurodiario/tests/ --cov=neurodiario --cov-report=html
```

Los tests cubren: ingesta RSS, parseo de artículos, deduplicación, limpieza de texto, clasificación temática, detección de tendencias, y clustering.

> Para más detalles, ver [docs/TESTING.md](docs/TESTING.md).

---

## Desarrollo

### Agregar una nueva fuente RSS

Editar `neurodiario/ingestion/sources_config.py`:

```python
{
    "name": "Nuevo Medio",
    "url": "https://nuevomedio.com/feed/",
    "category": "general",
    "language": "es",
    "active": True,
    "max_articles": 30,
}
```

### Agregar una nueva categoría

1. Agregar a `CATEGORIAS_VALIDAS` en `classifier.py`
2. Agregar keywords correspondientes a `CATEGORY_KEYWORDS`
3. Agregar prioridad en `PRIORIDAD_CATEGORIA` de `clustering_pipeline.py`

> Para guía completa de desarrollo, ver [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Roadmap

### Funcionalidades Existentes ✅
- Pipeline completo de ingesta, NLP, generación, publicación y distribución
- Clustering semántico para deduplicación
- Distribución a Facebook, Telegram, newsletter
- Scripts de mantenimiento y diagnóstico

### Mejoras Sugeridas (no implementadas)
- CI/CD con GitHub Actions
- Monitoreo con health check endpoints
- Caché de respuestas de Claude para temas recurrentes
- Dashboard web de administración
- Detección de noticias falsas
- Fine-tuning del modelo spaCy con corpus dominicano
- API REST pública
- Análisis de rendimiento de artículos (vistas, engagement)

> Para el roadmap detallado, ver [docs/ROADMAP.md](docs/ROADMAP.md).

---

## Contribuir

1. Haz fork del repositorio
2. Crea una rama: `git checkout -b feature/mi-feature`
3. Asegúrate de que los tests pasen: `pytest neurodiario/tests/ -v`
4. Haz commit con mensajes descriptivos en español
5. Abre un Pull Request con descripción detallada

> Para la guía completa, ver [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

---

## Licencia

MIT License

---

## Observaciones del Arquitecto

### Deuda Técnica

1. **README desactualizado vs código real**: el README original menciona XML-RPC y `WordPressPublisher(XML-RPC)`, pero el código actual usa exclusivamente REST API. Se corrige en esta documentación.

2. **Archivo `dockerignore` sin punto**: el archivo debería ser `.dockerignore` (con punto al inicio) para que Docker lo reconozca automáticamente.

3. **Dos rutas de publicación coexistentes**: `publishing_pipeline.py` (artículo por artículo) y `clustering_pipeline.py` (con agrupamiento) existen en paralelo. Solo `clustering_pipeline.py` está conectado al scheduler activo. `publishing_pipeline.py` es código legacy que podría eliminarse o marcarse claramente como deprecado.

4. **Clase `Pipeline` en `pipeline.py` no se usa en producción**: el scheduler activo (`auto_scheduler.py`) usa `run_ingestion_pipeline()` directamente, no la clase `Pipeline`. La clase tiene un método `run_generation_and_publish()` que genera digests (no artículos completos), pero nunca se invoca.

5. **Tests referencian `VALID_CATEGORIES` que no existe**: `test_ingestion.py` importa `VALID_CATEGORIES` de `sources_config.py`, pero esa variable no existe en el módulo. Los tests fallarían al ejecutarse.

6. **Tests esperan `NotImplementedError` que no se lanza**: `test_ingestion.py` espera que `save_to_db()` lance `NotImplementedError`, pero el método está implementado (guarda artículos). El test de `ArticleClassifier` con `method="ml"` también espera `NotImplementedError` que el código actual no lanza.

7. **Modelo `Trend` poco utilizado**: la tabla `trends` está definida en el ORM y `save_trend()` existe, pero la ruta activa de producción (clustering) no guarda trends en la BD.

8. **`requirements.txt` incluye `python-wordpress-xmlrpc`**: esta librería ya no se usa (el código migró a REST API) y debería eliminarse.

9. **`neurodiario/publisher/__init__.py` solo exporta `WordPressPublisher`**: los módulos de Facebook, Telegram y newsletter no están exportados en el `__init__.py` del paquete.

### Posibles Refactorizaciones

- Consolidar las dos rutas de publicación en una sola
- Mover `clustering_pipeline.py` y `deduplicator_clusters.py` dentro del paquete `neurodiario/`
- Renombrar `Db_stats` a `db_stats.py` (convención snake_case)
- Agregar type hints completos en los módulos del publisher
- Implementar retry con backoff exponencial para llamadas a APIs externas
- Agregar health check endpoint para monitoreo externo
