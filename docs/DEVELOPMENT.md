# Desarrollo

## Entorno de Desarrollo

```bash
# Clonar y preparar
git clone https://github.com/carloscheco-cloud/NeuroDiario.git
cd NeuroDiario
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download es_core_news_lg
cp .env.example .env
```

## Agregar una Nueva Fuente RSS

1. Editar `neurodiario/ingestion/sources_config.py`:
```python
{
    "name": "Nuevo Medio",
    "url": "https://nuevomedio.com/feed/",
    "category": "general",
    "language": "es",
    "active": True,
    "max_articles": 30,
}
```

2. Si es fuente dominicana, agregarla a `FUENTES_DOMINICANAS` en `neurodiario/scheduler/pipeline.py`

3. Verificar conectividad: `python verificar_fuentes.py`

## Agregar una Nueva Categoría

1. Agregar a `CATEGORIAS_VALIDAS` en `neurodiario/nlp/classifier.py`
2. Agregar keywords a `CATEGORY_KEYWORDS` en el mismo archivo
3. Agregar prioridad a `PRIORIDAD_CATEGORIA` en `clustering_pipeline.py`
4. Agregar ángulo y keywords en `neurodiario/nlp/angle_detector.py` si aplica

## Modificar el Prompt de Generación

Editar `SYSTEM_PROMPT` en `neurodiario/generator/article_generator.py`. El prompt actual define: estilo editorial, estructura del artículo, formato HTML, restricciones, y output format.

## Probar Localmente sin Publicar

```bash
# Solo ingesta
python -m neurodiario.scheduler.pipeline

# Solo NLP
python -m neurodiario.scheduler.nlp_pipeline

# Clustering en simulación (no publica)
python clustering_pipeline.py

# Diagnóstico de BD
python -m neurodiario.tools.Db_stats
```

## Flujo de Trabajo con Railway

1. Hacer cambios locales
2. Probar en Railway Shell: `python3 -c "..."`  (más confiable que heredoc)
3. Push a GitHub: `git push origin main`
4. Railway autodeploy se activa automáticamente

## Convenciones de Código

- Docstrings en español con formato descriptivo
- Type hints cuando sea posible
- Logging con `logger = logging.getLogger(__name__)`
- Constantes en UPPER_SNAKE_CASE al inicio del módulo
- Funciones internas con prefijo `_`
