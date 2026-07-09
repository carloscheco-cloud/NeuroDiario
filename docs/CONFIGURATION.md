# Configuración

## Archivo de Configuración

La configuración se centraliza en `neurodiario/config/settings.py` como una clase `Settings` que carga variables de entorno con valores por defecto.

## Instancia Global

```python
from neurodiario.config.settings import settings
```

`settings` es una instancia singleton usada en toda la aplicación.

## Validación

`settings.validate()` retorna una lista de variables requeridas que están vacías:

```python
missing = settings.validate()
if missing:
    print(f"Variables faltantes: {missing}")
```

Variables requeridas: `WORDPRESS_URL`, `WORDPRESS_USER`, `WORDPRESS_PASSWORD`, `DATABASE_URL`, `CLAUDE_API_KEY`.

## Categorías de Configuración

### WordPress
- `WORDPRESS_URL`: URL base del sitio (default: "https://neurodiario.com")
- `WORDPRESS_USER`: usuario con permisos de publicación
- `WORDPRESS_PASSWORD`: Application Password

### Base de Datos
- `DATABASE_URL`: URL de conexión PostgreSQL (default: "sqlite:///neurodiario.db")

### Claude AI
- `CLAUDE_API_KEY`: acepta `ANTHROPIC_API_KEY` o `CLAUDE_API_KEY` como alias
- `CLAUDE_MODEL`: modelo a usar (default: "claude-sonnet-4-20250514")

### Facebook / Telegram
- Tokens y IDs para distribución social (opcionales)

### Imágenes
- `SERPER_API_KEY` y `PEXELS_API_KEY` para búsqueda de imágenes

### Pipeline
- `FETCH_INTERVAL_HOURS`, `MAX_ARTICLES_PER_CYCLE`, `TREND_WINDOW_HOURS`
- `INGESTION_INTERVAL_MINUTES`, `NLP_INTERVAL_MINUTES`

### NLP
- `SPACY_MODEL`: modelo de spaCy (default: "es_core_news_lg")

Ver [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) para la tabla completa.
