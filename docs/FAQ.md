# Preguntas Frecuentes

## ¿Cuántos artículos genera NeuroDiario por día?

Hasta 75 (25 artículos × 3 ciclos a las 7am, 1pm y 7pm). En la práctica, depende de cuántos clusters válidos se formen con las noticias del momento.

## ¿Cuánto cuesta operar NeuroDiario?

- **Claude Haiku**: ~$0.28 por 20 artículos generados
- **Railway Pro**: plan del servicio + PostgreSQL
- **Serper.dev**: depende del plan (1000 búsquedas/mes en free)
- **Pexels**: gratuito con atribución
- **Mailchimp**: free tier para audiencias pequeñas

## ¿Por qué se usa Claude Haiku y no un modelo más avanzado?

Costo-eficiencia. Con 75 artículos/día, un modelo más caro escalaría el gasto rápidamente. Haiku produce calidad editorial suficiente con el system prompt detallado.

## ¿Por qué los artículos no aparecen en redes sociales inmediatamente?

La distribución social es escalonada: se publica 1 artículo cada 12 minutos para evitar saturar el feed. Si se generan 25 artículos, tardan ~5 horas en distribuirse completamente.

## ¿Cómo se evitan los artículos duplicados?

Dos mecanismos: primero, la ingesta verifica por URL exacta y similitud de título (80%). Segundo, el clustering agrupa noticias similares de múltiples fuentes y genera UN solo artículo por historia.

## ¿Qué pasa si una fuente RSS deja de funcionar?

El sistema continúa con las demás fuentes. El error se registra en los logs. Se puede verificar con `python verificar_fuentes.py`. Para desactivar una fuente, cambiar `"active": False` en `sources_config.py`.

## ¿El sistema necesita una máquina local para funcionar?

No. Corre autónomamente en Railway (Docker + PostgreSQL). El mantenimiento se puede hacer desde Railway Shell.

## ¿Cómo reseteo todo y empiezo de cero?

```bash
python limpiar_base_datos.py --apply    # Borra BD (pide BORRAR)
python limpiar_wordpress.py --apply     # Borra WordPress (pide BORRAR)
```
