# Despliegue

## Railway (Producción)

NeuroDiario corre como un servicio Docker en Railway Pro.

### Componentes en Railway

| Servicio | Tipo | Descripción |
|---------|------|-------------|
| NeuroDiario | Web Service (Docker) | Aplicación Python con scheduler |
| PostgreSQL | Database | BD gestionada por Railway |

### Dockerfile

Basado en `python:3.11-slim`, optimizado para el límite de 4GB de Railway:

1. Instala gcc/g++ para compilar dependencias C
2. Instala dependencias Python + modelo spaCy `es_core_news_lg`
3. Limpieza agresiva: elimina tests, __pycache__, .pyc, .pyo
4. Elimina docs, tests, .git del código de aplicación
5. Ejecuta `python -m scheduler.auto_scheduler`

### Autodeploy

El repositorio GitHub `carloscheco-cloud/NeuroDiario` está conectado a Railway. Cada push a `main` dispara un nuevo build y deploy.

### Variables de Entorno

Todas las variables sensibles se configuran en Railway Dashboard > Variables. Railway inyecta automáticamente `DATABASE_URL` para el servicio PostgreSQL.

## Docker Local

```bash
# Build
docker build -t neurodiario .

# Run (con archivo .env)
docker run --env-file .env neurodiario
```

## Monitoreo

El sistema no tiene un endpoint de health check expuesto. El monitoreo se hace vía:
- Logs de Railway (streaming en tiempo real)
- Script `db_stats` para diagnóstico de BD
- Verificación de publicaciones en WordPress, Facebook y Telegram
