# NeuroDiario

Sistema automatizado de periodismo asistido por inteligencia artificial para medios dominicanos.
Recolecta noticias de fuentes RSS locales, las analiza con NLP, detecta tendencias y genera
artículos originales usando Claude AI, publicándolos directamente en WordPress.

## Descripción

NeuroDiario actúa como una redacción digital autónoma: monitorea los principales medios
dominicanos cada dos horas, identifica los temas más relevantes del día y produce contenido
periodístico de calidad editorial, listo para publicar.

## Características

- **Ingesta automática** de feeds RSS de medios dominicanos (Listín Diario, Diario Libre, etc.)
- **Procesamiento NLP** con spaCy: extracción de entidades, clasificación temática y detección de tendencias
- **Generación de contenido** con Claude AI: resúmenes, análisis y boletines diarios
- **Publicación automática** en WordPress vía XML-RPC
- **Scheduler programado** con APScheduler (zona horaria America/Santo_Domingo)
- **Base de datos PostgreSQL** con SQLAlchemy para trazabilidad completa

## Requisitos

- Python 3.10+
- PostgreSQL 14+
- WordPress con XML-RPC habilitado
- Clave de API de Anthropic (Claude)

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/NeuroDiario.git
cd NeuroDiario

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Descargar modelo de spaCy en español
python -m spacy download es_core_news_lg

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 6. Inicializar la base de datos
python -c "from neurodiario.db.database import init_db; init_db()"
```

## Configuración

Copia `.env.example` a `.env` y completa los valores:

| Variable | Descripción |
|----------|-------------|
| `WORDPRESS_URL` | URL de tu sitio WordPress |
| `WORDPRESS_USER` | Usuario de WordPress |
| `WORDPRESS_PASSWORD` | Contraseña de WordPress |
| `DATABASE_URL` | URL de conexión PostgreSQL |
| `ANTHROPIC_API_KEY` | Clave de API de Anthropic |
| `CLAUDE_MODEL` | Modelo de Claude (por defecto: `claude-opus-4-6`) |
| `DEBUG` | Modo debug (`True`/`False`) |

## Uso

### Ejecutar el pipeline completo una vez

```python
from neurodiario.scheduler.pipeline import Pipeline

pipeline = Pipeline()
pipeline.run_once()
```

### Iniciar el scheduler continuo

```python
from neurodiario.scheduler.pipeline import Pipeline

pipeline = Pipeline()
pipeline.start()  # Bloqueante, ejecuta indefinidamente
```

### Usar módulos individualmente

```python
from neurodiario.ingestion.rss_fetcher import RSSFetcher
from neurodiario.nlp.classifier import ArticleClassifier

# Obtener artículos
fetcher = RSSFetcher()
articles = fetcher.fetch_articles()

# Clasificar artículos
classifier = ArticleClassifier()
for article in articles:
    category, confidence = classifier.classify(
        article["raw_content"],
        article["title"]
    )
    print(f"{article['title'][:50]} → {category} ({confidence:.0%})")
```

## Estructura del Proyecto

```
neurodiario/
├── ingestion/          # Recolección de noticias RSS
│   ├── rss_fetcher.py
│   ├── article_parser.py
│   └── sources_config.py
├── nlp/                # Procesamiento de lenguaje natural
│   ├── text_cleaner.py
│   ├── entity_extractor.py
│   ├── classifier.py
│   └── trend_detector.py
├── generator/          # Generación de artículos con Claude AI
│   └── article_generator.py
├── publisher/          # Publicación en WordPress
│   └── wordpress_publisher.py
├── scheduler/          # Orquestación del pipeline
│   └── pipeline.py
├── db/                 # Modelos y conexión a PostgreSQL
│   ├── models.py
│   └── database.py
├── config/             # Configuración centralizada
│   └── settings.py
└── tests/              # Suite de pruebas
    ├── test_ingestion.py
    └── test_nlp.py
docs/
├── ARQUITECTURA.md     # Diseño técnico detallado
└── ROADMAP.md          # Plan de desarrollo
```

## Tests

```bash
# Ejecutar todos los tests
pytest neurodiario/tests/ -v

# Ejecutar con cobertura
pytest neurodiario/tests/ --cov=neurodiario --cov-report=html
```

## Roadmap

Ver [docs/ROADMAP.md](docs/ROADMAP.md) para el plan de desarrollo completo.

**Versión actual:** v0.1.0 — Estructura base
**Próximo hito:** v0.2.0 — Ingesta funcional en producción

## Arquitectura

Ver [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) para el diseño técnico detallado,
incluyendo diagramas de flujo y decisiones de diseño.

## Contribuir

1. Haz fork del repositorio
2. Crea una rama: `git checkout -b feature/mi-feature`
3. Haz commit de tus cambios con mensajes descriptivos
4. Abre un Pull Request con descripción detallada

## Licencia

MIT License — Ver LICENSE para detalles.
