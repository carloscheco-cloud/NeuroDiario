# Estructura del Proyecto

## Directorio Raíz

| Archivo/Carpeta | Descripción |
|----------------|-------------|
| `Dockerfile` | Imagen Docker para Railway (Python 3.11-slim, optimizada para 4GB) |
| `requirements.txt` | Dependencias Python con versiones fijadas |
| `.env.example` | Plantilla de variables de entorno con descripciones |
| `.gitignore` | Exclusiones de Git (env, cache, logs, modelos, IDEs) |
| `dockerignore` | Exclusiones de Docker build (debería ser `.dockerignore`) |
| `scheduler/` | Scheduler principal (auto_scheduler.py) |
| `clustering_pipeline.py` | Pipeline activo de generación con clustering |
| `deduplicator_clusters.py` | Motor de agrupamiento TF-IDF + cosine similarity |
| `neurodiario/` | Paquete principal de la aplicación |

## Scripts de Utilidad

| Script | Descripción |
|--------|-------------|
| `verificar_fuentes.py` | Verifica conectividad de cada fuente RSS (solo lectura) |
| `limpiar_base_datos.py` | Limpieza total de BD (dry-run por defecto) |
| `limpiar_wordpress.py` | Limpieza total de WordPress (dry-run por defecto) |
| `limpiar_failed.py` | Limpieza de GeneratedArticles fallidos |
| `migrate_facebook_fields.py` | Migración: agrega columnas Facebook |
| `migrate_telegram_fields.py` | Migración: agrega columnas Telegram |
| `relleno_source_id.py` | Repara source_id en artículos históricos |

## Paquete `neurodiario/`

```
neurodiario/
├── config/          → Configuración centralizada
├── db/              → Modelos ORM y acceso a PostgreSQL
├── ingestion/       → Recolección de noticias (RSS, parseo, dedup)
├── nlp/             → Procesamiento de lenguaje natural
├── generator/       → Generación de artículos con Claude AI
├── publisher/       → Publicación (WordPress, Facebook, Telegram, newsletter)
│   └── assets/      → Recursos estáticos (favicon, fuente)
├── scheduler/       → Pipelines de orquestación (legacy)
├── tools/           → Herramientas de diagnóstico
└── tests/           → Suite de pruebas con pytest
```

## Convención de Nombres

- Módulos Python: `snake_case` (excepto `Db_stats` que debería ser `db_stats`)
- Clases: `PascalCase` (RSSFetcher, ArticleParser, TextCleaner)
- Funciones públicas: `snake_case` (fetch_articles, clean_text)
- Funciones internas: `_snake_case` con prefijo underscore
- Constantes: `UPPER_SNAKE_CASE` (SOURCES, SYSTEM_PROMPT)
