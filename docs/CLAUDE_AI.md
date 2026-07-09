# Integración con Claude AI

## Modelos Utilizados

| Uso | Modelo | Tokens máx |
|-----|--------|------------|
| Clasificación temática | `claude-haiku-4-5-20251001` | 10 |
| Generación de artículos | `claude-haiku-4-5-20251001` (configurable) | 2000-2500 |
| Query de imagen | Mismo del generador | 30 |
| Boletín diario | Mismo del generador | 2048 |
| Newsletter editorial | `claude-haiku-4-5-20251001` | 1000 |

El modelo se configura vía la variable `CLAUDE_MODEL`. El default en settings.py es `claude-sonnet-4-20250514`, pero el generador usa `claude-haiku-4-5-20251001` por defecto para optimizar costo.

## Punto 1: Clasificación Temática

**Archivo**: `neurodiario/nlp/classifier.py`  
**Método**: `_classify_with_haiku()`

Se activa solo cuando la categoría de la fuente es genérica (`general`, `internacional`, `sociedad`). El prompt:

```
Clasifica esta noticia dominicana en UNA sola categoría.
Categorías válidas: politica, economia, deportes, salud, tecnologia, cultura, educacion, internacional, sociedad, general
Titular: {title}
Extracto: {primeros 600 chars}
Responde SOLO con el nombre exacto de la categoría, en minúsculas, sin explicación.
```

Costo: ~10 tokens de respuesta. Se valida que la respuesta sea una categoría real.

## Punto 2: Generación de Artículos

**Archivo**: `neurodiario/generator/article_generator.py`  
**Métodos**: `generate_from_single_article()`, `create_article()`

### System Prompt

El system prompt define el estilo editorial de NeuroDiario:

- Redactor principal, estilo periodista senior dominicano
- Titulares: directos, máximo 12 palabras, sin clickbait
- Lead: quién, qué, cuándo, dónde, por qué en 2-3 oraciones
- Cuerpo: 450-650 palabras, párrafos cortos (máx 4 oraciones), mínimo 4 párrafos de desarrollo
- HTML limpio: `<p>`, `<strong>`, `<em>`, `<blockquote>`, `<h2>` — sin Markdown, sin `<h1>`
- Tono: neutral con criterio, contextualiza, sin frases vacías
- Prohibido: "Medio desconocido", mezclar idiomas en fechas, comenzar con "Según reportó..."

### Prompt de Artículo Individual

Incluye: título original, medio, categoría, fecha en español, URL, y contenido recortado a 3000 caracteres.

### Prompt de Artículo Multi-fuente

Incluye: hasta 5 fuentes con título, medio, URL y primeros 500 chars de contenido. Genera un artículo que sintetiza todas las fuentes.

## Punto 3: Query de Imagen

**Método**: `_build_image_query()`

Genera una query de 4-6 palabras para Google Images. El prompt incluye ejemplos concretos del contexto dominicano para guiar al modelo:

- "Abinader anuncia reforma fiscal" → "Luis Abinader presidente Republica Dominicana 2026"
- "Tigres del Licey ganan campeonato" → "Tigres Licey beisbol dominicano campeones"

Si falla, cae a queries genéricas por categoría.

## Punto 4: Newsletter Editorial

**Archivo**: `neurodiario/publisher/newsletter_generator.py`  
**Método**: `generate_editorial_summary()`

Genera el resumen editorial semanal para suscriptores. Tono profesional, dominicano, cercano. Máximo 500 palabras. HTML simple.

## Costo Estimado

Con Claude Haiku y ~25 artículos por ciclo (3 ciclos/día), el costo es de aproximadamente $0.28 por 20 artículos generados.
