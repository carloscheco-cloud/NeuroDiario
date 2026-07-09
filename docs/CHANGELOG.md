# Changelog

## [Actual] — Julio 2026

### Cambios Recientes
- Migración completa de publicación a clustering (deduplicación semántica)
- Distribución social escalonada (1 artículo cada 12 minutos)
- Imágenes: priorización de fuentes oficiales, exclusión de medios comerciales
- Múltiples URLs candidatas para imágenes (fallback en cascada)
- Newsletter semanal vía Mailchimp con PDF adjunto
- Integración con WhatsApp Canal vía Make.com (Scenario ID 5610516) + Whapi.Cloud — canal [whatsapp.com/channel/0029VbDCDigJP21BALwA9a1t](https://whatsapp.com/channel/0029VbDCDigJP21BALwA9a1t). Pendiente de migración a API oficial de Meta cuando esté disponible.

### Pipeline Activo
- Ingesta RSS: cada 20 minutos
- NLP: cada 20 minutos  
- Clustering + generación: 3 veces al día (7am, 1pm, 7pm RD)
- Social sync: cada 12 minutos
- Newsletter: domingos 8am RD

### Fuentes
- 7 feeds dominicanos activos
- 3 feeds internacionales activos (BBC Mundo, El País América, AS Fútbol)
- Bloomberg desactivado (403 consistente)

## [Histórico]

- Migración de XML-RPC a WordPress REST API
- Migración de `publishing_pipeline` individual a `clustering_pipeline`
- Agregación de columnas Facebook y Telegram a la BD
- Fix del bug de clasificación (substrings: "ley" dentro de "leyenda")
- Fix del status field: `publish` en WordPress, `published` en BD
- Implementación de filtro de relevancia para fuentes internacionales
- Agregación de AS.com fútbol para cobertura del Mundial 2026
