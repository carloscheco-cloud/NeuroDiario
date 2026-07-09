# Scheduler

## Implementación

APScheduler (`BackgroundScheduler`) con zona horaria `America/Santo_Domingo`. Definido en `scheduler/auto_scheduler.py`.

## Jobs Configurados

| ID | Trigger | Frecuencia | Función | Descripción |
|----|---------|-----------|---------|-------------|
| `ingestion_rss` | interval | 20 min | `_job_ingestion()` | Descarga feeds RSS, parsea, filtra, guarda |
| `nlp_pipeline` | interval | 20 min | `_job_nlp()` | Limpia, extrae entidades, clasifica |
| `clustering_generation` | cron | 7:00, 13:00, 19:00 | `_job_clustering()` | Agrupa, genera y publica artículos |
| `social_sync` | interval | 12 min | `_job_social_sync()` | Facebook + Telegram (1 artículo/ciclo) |
| `newsletter_semanal` | cron | Domingos 8:00 | `_job_newsletter()` | Genera y envía newsletter vía Mailchimp |

## Ejecución

El scheduler se inicia con:

```bash
python -m scheduler.auto_scheduler
```

El Dockerfile lo ejecuta como CMD por defecto. El proceso permanece vivo con un bucle `while True: time.sleep(60)`.

## Manejo de Errores en Jobs

Cada job tiene su propio try/except con `exc_info=True` para trazabilidad completa. Un job que falla no afecta a los demás.

## Distribución Escalonada

El job `social_sync` procesa **solo un artículo por ciclo** (cada 12 minutos). Si se publican 25 artículos de golpe en WordPress, se distribuyen a redes sociales de uno en uno durante ~5 horas. Esto evita flooding de contenido en las redes.
