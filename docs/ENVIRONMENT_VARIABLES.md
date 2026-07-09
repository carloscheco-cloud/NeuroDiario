# Variables de Entorno

## Tabla Completa

| Variable | Descripción | Default | Requerida |
|----------|------------|---------|-----------|
| **WordPress** | | | |
| `WORDPRESS_URL` | URL del sitio WordPress | `https://neurodiario.com` | ✅ |
| `WORDPRESS_USER` | Usuario de WordPress | `neurodiario` | ✅ |
| `WORDPRESS_PASSWORD` | Application Password | _(vacío)_ | ✅ |
| **Base de Datos** | | | |
| `DATABASE_URL` | URL conexión PostgreSQL | `sqlite:///neurodiario.db` | ✅ |
| **Claude AI** | | | |
| `ANTHROPIC_API_KEY` | Clave API Anthropic (prioritaria) | _(vacío)_ | ✅ |
| `CLAUDE_API_KEY` | Alias alternativo de API key | _(vacío)_ | ✅* |
| `CLAUDE_MODEL` | Modelo de Claude | `claude-sonnet-4-20250514` | No |
| **Facebook** | | | |
| `FACEBOOK_PAGE_TOKEN` | Token permanente de Facebook Page | _(vacío)_ | No |
| `FACEBOOK_PAGE_ID` | ID de la página de Facebook | _(vacío)_ | No |
| **Telegram** | | | |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | _(vacío)_ | No |
| `TELEGRAM_CHANNEL_ID` | ID del canal de Telegram | _(vacío)_ | No |
| **Imágenes** | | | |
| `SERPER_API_KEY` | Clave de Serper.dev (Google Images) | _(vacío)_ | No |
| `PEXELS_API_KEY` | Clave de Pexels (fallback) | _(vacío)_ | No |
| **Aplicación** | | | |
| `DEBUG` | Modo debug (True/False) | `False` | No |
| `LOG_LEVEL` | Nivel de logging | `INFO` | No |
| `TIMEZONE` | Zona horaria | `America/Santo_Domingo` | No |
| **Pipeline** | | | |
| `FETCH_INTERVAL_HOURS` | Intervalo de ingesta (horas) | `2` | No |
| `MAX_ARTICLES_PER_CYCLE` | Máx artículos por ciclo | `100` | No |
| `TREND_WINDOW_HOURS` | Ventana de tendencias (horas) | `24` | No |
| `INGESTION_INTERVAL_MINUTES` | Intervalo ingesta (minutos) | `15` | No |
| `NLP_INTERVAL_MINUTES` | Intervalo NLP (minutos) | `20` | No |
| **NLP** | | | |
| `SPACY_MODEL` | Modelo spaCy | `es_core_news_lg` | No |
| **Newsletter** | | | |
| `MAILCHIMP_API_KEY` | Clave API Mailchimp | _(vacío)_ | No |
| `MAILCHIMP_AUDIENCE_ID` | ID de audiencia Mailchimp | _(vacío)_ | No |

\* Se usa `ANTHROPIC_API_KEY` prioritariamente. `CLAUDE_API_KEY` es un alias de respaldo.

## Nota sobre Railway

Railway inyecta `DATABASE_URL` con formato `postgres://`. El código de migración lo convierte a `postgresql://` que SQLAlchemy requiere. El módulo principal `database.py` usa `DATABASE_URL` directamente.
