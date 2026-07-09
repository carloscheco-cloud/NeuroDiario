# Base de Datos

## Motor

PostgreSQL (gestionado por Railway) con SQLAlchemy 2.0 ORM. La conexión se configura en `neurodiario/db/database.py` como singleton con pool de conexiones.

| Parámetro | Valor |
|-----------|-------|
| Driver | psycopg2-binary |
| Pool size | 5 |
| Max overflow | 10 |
| Pool pre-ping | True (verifica conexión antes de usar) |
| Echo | Activado solo en modo DEBUG |

## Tablas

### `sources` — Fuentes de noticias

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | Integer PK | Identificador único |
| `name` | String(200) | Nombre del medio (ej: "Diario Libre") |
| `url` | String(500) UK | URL del feed RSS |
| `category` | String(100) | Categoría de la fuente (default: "general") |
| `language` | String(10) | Idioma (default: "es") |
| `active` | Boolean | Si la fuente está activa (default: True) |
| `created_at` | DateTime | Fecha de creación |

### `articles` — Artículos crudos del RSS

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | Integer PK | Identificador único |
| `title` | String(500) | Título del artículo |
| `url` | String(1000) UK | URL original |
| `summary` | Text | Resumen del RSS o generado |
| `raw_html` | Text | HTML completo de la página |
| `raw_content` | Text | Texto plano extraído |
| `clean_content` | Text | Texto limpio post-NLP |
| `word_count` | Integer | Conteo de palabras |
| `image_url` | String(1000) | URL de imagen del RSS |
| `category` | String(100) | Categoría asignada por NLP |
| `category_confidence` | Float | Confianza de la clasificación |
| `entities` | JSON | Entidades extraídas (personas, orgs, lugares) |
| `processed` | Boolean | Si ya pasó por NLP (default: False) |
| `published_at` | DateTime | Fecha de publicación original |
| `fetched_at` | DateTime | Fecha de descarga |
| `source_id` | Integer FK → sources.id | Fuente de origen |

### `generated_articles` — Artículos generados por Claude

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | Integer PK | Identificador único |
| `title` | String(500) | Título del artículo generado |
| `content` | Text | Contenido HTML generado |
| `article_type` | String(50) | Tipo (default: "summary") |
| `category` | String(100) | Categoría |
| `tags` | JSON | Lista de tags |
| `status` | String(50) | Estado: draft, published, failed, processing, clustered |
| `wordpress_post_id` | Integer | ID del post en WordPress |
| `published_at` | DateTime | Fecha de publicación |
| `created_at` | DateTime | Fecha de creación |
| `facebook_post_id` | String(200) | ID del post en Facebook |
| `facebook_posted_at` | DateTime | Fecha de publicación en Facebook |
| `telegram_message_id` | String(50) | ID del mensaje en Telegram |
| `telegram_posted_at` | DateTime | Fecha de publicación en Telegram |
| `model_used` | String(100) | Modelo de Claude utilizado |
| `prompt_tokens` | Integer | Tokens del prompt |
| `completion_tokens` | Integer | Tokens de la respuesta |
| `source_article_id` | Integer FK → articles.id | Artículo fuente principal |

### `trends` — Tendencias detectadas

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | Integer PK | Identificador único |
| `topic` | String(500) | Tema de la tendencia |
| `article_count` | Integer | Número de artículos |
| `sources` | JSON | Lista de medios que cubren el tema |
| `created_at` | DateTime | Fecha de detección |

## Relaciones

```
Source  ──1:N──>  Article  ──1:N──>  GeneratedArticle
```

- Un `Source` puede tener muchos `Article`
- Un `Article` puede tener muchos `GeneratedArticle` (el principal como fuente, los demás como `clustered`)
- `Trend` es independiente (sin FK)

## Funciones de Acceso

Definidas en `neurodiario/db/database.py`:

| Función | Descripción |
|---------|-------------|
| `init_db()` | Crea todas las tablas si no existen |
| `get_db()` | Context manager para sesiones (auto-commit/rollback) |
| `save_article(dict)` | Guarda artículo, resuelve source_id automáticamente |
| `article_exists(url)` | Verifica existencia por URL |
| `get_unprocessed_articles(limit)` | Artículos con processed=False |
| `save_trend(topic, count, sources)` | Guarda tendencia detectada |
| `get_generated_articles_by_topic_today(topic)` | Verifica si ya se generó hoy |
| `health_check()` | Verifica conexión con SELECT 1 |
