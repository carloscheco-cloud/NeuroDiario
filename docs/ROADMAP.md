# Roadmap de NeuroDiario

## Estado Actual: v0.1.0 — Estructura Base

La estructura del proyecto está definida con todos los módulos base implementados.
El pipeline completo está diseñado pero requiere integración y pruebas end-to-end.

---

## v0.2.0 — Ingesta Funcional
**Objetivo:** Pipeline de recolección de noticias operativo en producción.

- [ ] Implementar `RSSFetcher.save_to_db()` con lógica de upsert por URL
- [ ] Añadir selectores CSS específicos por dominio en `sources_config.py`
- [ ] Implementar rate limiting y reintentos en `ArticleParser`
- [ ] Ampliar lista de fuentes dominicanas (meta: 15+ medios)
- [ ] Añadir soporte para fuentes sin RSS (scraping directo)
- [ ] Dashboard básico de monitoreo de ingesta
- [ ] Dockerizar la aplicación (Dockerfile + docker-compose.yml)

**Criterio de éxito:** > 200 artículos nuevos por día en la BD.

---

## v0.3.0 — NLP Robusto
**Objetivo:** Procesamiento NLP preciso para noticias en español dominicano.

- [ ] Fine-tuning del modelo spaCy con corpus dominicano
- [ ] Clasificador ML entrenado con datos reales (reemplaza heurística de keywords)
- [ ] Detección de sentimiento por artículo
- [ ] Extracción de citas textuales y atribución a fuentes
- [ ] Pipeline NLP asíncrono con `asyncio` para mayor rendimiento
- [ ] Implementar `EntityExtractor` con `nlp.pipe()` para lotes grandes
- [ ] Métricas de calidad del clasificador (precisión, recall, F1)

**Criterio de éxito:** Clasificación correcta > 85% en conjunto de validación.

---

## v0.4.0 — Generación con IA Avanzada
**Objetivo:** Artículos generados de alta calidad periodística.

- [ ] Implementar `generate_summary()` y `generate_analysis()` en producción
- [ ] Sistema de prompts versionados y evaluables
- [ ] Generación de títulos SEO optimizados
- [ ] Detección automática de noticias falsas o sensacionalistas
- [ ] Generación multiformat: artículo, hilo de Twitter, post de Instagram
- [ ] Caché de respuestas para temas recurrentes
- [ ] Evaluación humana de calidad (formulario de revisión editorial)

**Criterio de éxito:** Score editorial > 7/10 en revisión humana.

---

## v0.5.0 — Publicación Automatizada
**Objetivo:** Pipeline de publicación en WordPress completamente automatizado.

- [ ] Implementar `WordPressPublisher.publish()` en producción
- [ ] Implementar `get_categories()` y `update_post()`
- [ ] Sistema de aprobación humana antes de publicar (modo staging)
- [ ] Imágenes automáticas con DALL-E o Unsplash API
- [ ] Soporte para múltiples sitios WordPress
- [ ] Notificaciones por email/Slack al publicar

**Criterio de éxito:** Publicación automática de 3+ artículos diarios sin intervención.

---

## v1.0.0 — Producción
**Objetivo:** Sistema estable, monitoreado y escalable.

- [ ] CI/CD completo (GitHub Actions)
- [ ] Tests de integración end-to-end
- [ ] Monitoreo con Prometheus + Grafana
- [ ] Alertas automáticas por fallos en el pipeline
- [ ] Documentación de API interna
- [ ] Sistema de análisis de rendimiento de artículos (vistas, engagement)
- [ ] Panel de administración web
- [ ] Soporte multiidioma (inglés para audiencia diáspora)

**Criterio de éxito:** Sistema en producción con uptime > 99% durante 30 días.

---

## Backlog Futuro

- Análisis de redes sociales (Twitter/X, Instagram) como fuentes adicionales
- API REST pública para consumo de datos por terceros
- App móvil con resúmenes personalizados
- Modelo de suscripción premium con análisis exclusivos
- Colaboración con periodistas dominicanos para validación editorial
- Expansión a otros mercados caribeños (Puerto Rico, Cuba, Haití)

---

## Contribuciones

Para contribuir al proyecto:
1. Revisa los issues abiertos en GitHub
2. Asigna el issue a tu usuario antes de empezar
3. Crea una rama con el formato `feature/descripcion-corta`
4. Abre un PR con descripción detallada y tests
5. El PR debe pasar todos los tests y revisión de código

---

*Última actualización: Marzo 2026*
