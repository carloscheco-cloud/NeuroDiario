# NeuroData Narrative Intelligence Engine v1

NeuroData convierte una investigación específica en una **configuración**, no en un script nuevo por cliente. El mismo motor sirve para empresas, instituciones, personas o temas públicos.

## Alcance v1

- Búsqueda de cobertura en medios dominicanos mediante Serper.dev.
- Enriquecimiento de artículos con el texto público visible de la página antes del análisis narrativo.
- Búsqueda de videos y comentarios públicos mediante YouTube Data API.
- Importación de comentarios sociales desde JSON, CSV o TXT/Markdown.
- Seudonimización de autores importados: NeuroData no necesita conservar el nombre del comentarista para analizar narrativas.
- Clasificación con OpenAI de relevancia, sentimiento, postura, tono, narrativas, actores, emociones y claims.
- Dataset trazable en JSONL.
- Reporte `executive` y `premium` en Markdown + resumen JSON.
- Primer estudio incluido: GoldQuest / Proyecto Romero.

La radio/audio continuo queda preparado como fase v2. La arquitectura prevista es: **escuchar/detectar relevancia → transcribir solo segmentos relevantes → analizar narrativa**. No se debe capturar ni redistribuir audio sin una fuente o permiso legítimo.

## Variables de entorno

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
NEURODATA_OPENAI_MODEL=gpt-4o-mini
SERPER_API_KEY=...
YOUTUBE_API_KEY=...
NEURODATA_OUTPUT_DIR=data/neurodata
```

## Validar el estudio GoldQuest

```bash
python -m neurodiario.neurodata.cli \
  --study studies/goldquest_proyecto_romero.json validate
```

## Recolectar prensa + YouTube

```bash
python -m neurodiario.neurodata.cli \
  --study studies/goldquest_proyecto_romero.json collect \
  --sources media,youtube
```

## Enriquecer artículos antes de analizarlos

Serper descubre cobertura usando títulos y snippets. Para un reporte cliente-facing, NeuroData intenta recuperar el cuerpo público visible de cada artículo antes de clasificar narrativas. Si una página bloquea el acceso o no puede extraerse con fiabilidad, se conserva el snippet y se registra el fallo.

```bash
python -m neurodiario.neurodata.cli \
  --study studies/goldquest_proyecto_romero.json enrich
```

Para probar primero una muestra:

```bash
python -m neurodiario.neurodata.cli \
  --study studies/goldquest_proyecto_romero.json enrich --limit 10
```

Los registros enriquecidos conservan `search_snippet` y añaden `text_source`, `full_text_chars` y `enrichment_status` para mantener trazabilidad.

## Importar comentarios de Facebook u otra red

CSV mínimo:

```csv
author,comment,likes,date
usuario1,"Me preocupa el agua",15,2026-05-04
usuario2,"La provincia necesita empleo",8,2026-05-04
```

Luego:

```bash
python -m neurodiario.neurodata.cli \
  --study studies/goldquest_proyecto_romero.json import-social \
  --file /ruta/comentarios.csv \
  --platform facebook \
  --source-url "https://facebook.com/..."
```

## Analizar

Ejecutar preferiblemente después del paso `enrich` para que los artículos disponibles se analicen con cuerpo completo y no solo con el snippet de búsqueda.

```bash
python -m neurodiario.neurodata.cli \
  --study studies/goldquest_proyecto_romero.json analyze --limit 500
```

## Reportes

```bash
python -m neurodiario.neurodata.cli \
  --study studies/goldquest_proyecto_romero.json report --tier executive

python -m neurodiario.neurodata.cli \
  --study studies/goldquest_proyecto_romero.json report --tier premium
```

Los archivos se guardan por defecto en:

```text
data/neurodata/goldquest-proyecto-romero/
  records.raw.jsonl
  records.analyzed.jsonl
  report.executive.md
  report.executive.summary.json
  report.premium.md
  report.premium.summary.json
```

## Filosofía del producto

El Executive Brief muestra el estado visible de la conversación y sirve como abrepuertas comercial. Premium agrega detalle de actores, narrativas, claims, evidencia y comparaciones. En una fase posterior, `NeuroData Radar` reutilizará el mismo dataset para monitoreo recurrente y alertas narrativas.

## Límites metodológicos

- El análisis de comentarios públicos no es una encuesta representativa.
- “Sentimiento negativo” no equivale a sesgo editorial.
- Una clasificación de IA debe revisarse antes de conclusiones reputacionales o legales.
- Claims detectados son afirmaciones para verificar, no hechos confirmados.
- El enriquecedor de texto trabaja únicamente con páginas públicas; no intenta saltarse autenticación, paywalls ni controles de acceso.
- Respetar términos de servicio, privacidad, licencias y derechos de cada fuente.
