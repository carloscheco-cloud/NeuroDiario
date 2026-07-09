# Manejo de Errores

## Estrategia General

Cada operación que involucra recursos externos (HTTP, BD, APIs) está envuelta en try/except. Los errores se registran con `logger.error()` y la ejecución continúa con el siguiente elemento.

## Errores de Base de Datos

- **Context manager `get_db()`**: hace commit automático al salir sin errores; rollback si ocurre excepción; close siempre.
- **Artículos duplicados**: `save_article()` verifica existencia por URL antes de insertar; retorna False sin lanzar excepción.
- **Pool de conexiones**: `pool_pre_ping=True` verifica la conexión antes de usarla, reconectando si la BD reinició.

## Errores de Ingesta

- **Feed con errores de parseo**: se continúa procesando las entradas disponibles (feed.bozo solo genera warning)
- **Descarga de artículos**: newspaper3k falla → fallback a requests + BeautifulSoup; si ambos fallan → raw_content queda vacío
- **Timeout**: 15 segundos para feeds, 20 segundos para contenido de artículos

## Errores de NLP

- **Modelo spaCy no encontrado**: `OSError` con mensaje indicando cómo instalar
- **Clasificación Haiku falla**: fallback a clasificación por keywords
- **TF-IDF vocabulario vacío**: retorna cada artículo como su propio cluster

## Errores de Generación

- **Claude API error**: `anthropic.APIError` capturado, se re-lanza para que el ciclo de clustering salte al siguiente cluster
- **Imagen no encontrada**: se publica sin imagen (artículo sin featured_media en WordPress)

## Errores de Publicación

- **WordPress**: error HTTP capturado, artículo se marca como `failed`
- **Facebook**: si la imagen generada falla, publica solo link vía `/feed`
- **Telegram**: si `sendPhoto` falla, usa `sendMessage` sin imagen

## Auto-limpieza

`PublishingPipeline.cleanup_stuck_processing()` marca como `failed` los artículos que llevan más de 30 minutos en estado `processing`.

## Tope de Seguridad en Clustering

Clusters con más de 8 artículos (`MAX_CLUSTER_SIZE`) se desarman: cada artículo queda como su propio cluster. Esto previene agrupamientos falsos causados por títulos genéricos.

## Scripts de Limpieza

Tres capas de seguridad:
1. **Dry-run por defecto**: solo reporta qué haría
2. **Flag `--apply`**: requerido para ejecutar cambios
3. **Confirmación `BORRAR`**: texto que debe escribirse para confirmar
