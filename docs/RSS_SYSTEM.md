# Sistema RSS

## Fuentes Configuradas

Definidas en `neurodiario/ingestion/sources_config.py`:

### Medios Dominicanos (prioridad máxima, hasta 30 artículos por fuente)

| Fuente | URL del Feed | Categoría |
|--------|-------------|-----------|
| Diario Libre | diariolibre.com/rss/portada.xml | general |
| Diario Libre - Política | diariolibre.com/rss/politica.xml | politica |
| Diario Libre - Economía | diariolibre.com/rss/economia.xml | economia |
| Diario Libre - Deportes | diariolibre.com/rss/deportes.xml | deportes |
| El Nacional | elnacional.com.do/rss/home.xml | general |
| N Digital | n.com.do/feed/ | general |
| El Día | eldia.com.do/feed/ | general |

### Medios Internacionales (hasta 10 artículos, filtrados por relevancia)

| Fuente | URL del Feed | Categoría | Estado |
|--------|-------------|-----------|--------|
| BBC Mundo | feeds.bbci.co.uk/mundo/rss.xml | internacional | Activa |
| El País América | feeds.elpais.com/... | internacional | Activa |
| AS - Fútbol | feeds.as.com/.../futbol/... | deportes | Activa |
| Bloomberg | feeds.bloomberg.com/economics/news.rss | economia | Desactivada (403) |

## Configuración Global

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `FETCH_TIMEOUT` | 15 seg | Timeout para descargar feeds |
| `MAX_ARTICLES_PER_SOURCE` | 30 | Máximo por defecto (sobreescribible por fuente) |

## Filtro de Relevancia

Las fuentes internacionales solo pasan si el contenido contiene keywords relevantes para República Dominicana. La lista incluye:

- País y gentilicio: "república dominicana", "dominicano", "santo domingo", "haiti"
- Economía global: "petróleo", "dólar", "inflación", "fmi", "remesas", "turismo"
- Clima: "huracán", "tormenta tropical", "sismo", "inundación"
- Deportes: "béisbol", "mlb", "grandes ligas", "licey", "escogido"
- Migración: "migrante", "deportación", "estados unidos"

## Extracción de Imágenes del RSS

`RSSFetcher._extract_image()` intenta tres métodos:
1. `media_content` (Diario Libre, El Nacional)
2. `enclosures` con tipo image/*
3. `media_thumbnail`

## Headers HTTP

Se usa un User-Agent de Chrome real para evitar bloqueos de Cloudflare (requerido por N Digital):

```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36
```

## Agregar Nueva Fuente

Editar `sources_config.py` y agregar un diccionario con las claves: `name`, `url`, `category`, `language`, `active`, `max_articles`. Si es fuente dominicana, agregarla también a `FUENTES_DOMINICANAS` en `pipeline.py`.
