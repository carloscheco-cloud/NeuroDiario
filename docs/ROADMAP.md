# Roadmap

## Estado Actual

NeuroDiario opera como pipeline completo y autónomo: ingesta RSS, NLP, generación con clustering, publicación en WordPress, distribución a Facebook y Telegram, y newsletter semanal.

## Mejoras Sugeridas (no implementadas)

### Infraestructura
- CI/CD con GitHub Actions (tests automáticos en PR)
- Health check endpoint para monitoreo externo
- Alertas automáticas por fallos en el pipeline (Slack, email)
- Métricas de Prometheus para observabilidad

### Contenido
- Caché de respuestas de Claude para temas recurrentes
- Evaluación humana de calidad editorial (formulario de revisión)
- Detección de noticias falsas o sensacionalistas
- Contenido evergreen y series temáticas
- Generación multiformat: hilos de X, posts de Instagram

### NLP
- Fine-tuning del modelo spaCy con corpus dominicano
- Clasificador ML entrenado con datos reales
- Detección de sentimiento por artículo
- Extracción de citas textuales con atribución
- Pipeline NLP asíncrono con asyncio

### Publicación
- Dashboard web de administración
- Sistema de aprobación humana antes de publicar
- Análisis de rendimiento de artículos (vistas, engagement)
- Soporte para múltiples sitios WordPress

### Datos
- API REST pública para consumo por terceros
- Scraping de portales gubernamentales (transparencia, contratos)
- Análisis de redes sociales como fuentes
- Base de datos de funcionarios públicos

### Escalabilidad
- Expansión a otros mercados caribeños
- Soporte multiidioma (inglés para diáspora)
- App móvil con resúmenes personalizados
- Modelo de suscripción premium

> Estas mejoras están separadas de las funcionalidades existentes. Ninguna está implementada en el código actual.
