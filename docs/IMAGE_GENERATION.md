# Generación y Búsqueda de Imágenes

## Estrategia de Búsqueda (3 niveles)

### Nivel 1: Fuentes Oficiales (Serper.dev)

Busca en 15+ dominios gubernamentales y de partidos políticos dominicanos cuyas fotos de prensa se publican para uso de los medios. Query con filtro `site:`:

- Gobierno: presidencia.gob.do, mirex.gob.do, mepyd.gob.do, mitur.gob.do, etc.
- Congreso: senadord.gob.do, camaradediputados.gob.do, jce.gob.do
- Partidos: fuerzadelpueblo.org.do, prm.org.do, pldaldia.com

### Nivel 2: Google Images General (Serper.dev)

Búsqueda general excluyendo 17 dominios de medios dominicanos comerciales (sus fotos llevan marca de agua y tienen derechos de autor). Exclusiones vía `-site:` en el query.

### Nivel 3: Pexels (Fallback)

CDN abierto, casi nunca falla la descarga. Orientación landscape. Hasta 3 imágenes.

## Validación de Imágenes

Dominios bloqueados en la red de seguridad (además de la exclusión por query):
- Redes sociales: facebook, instagram, tiktok, youtube
- Medios dominicanos: 17 dominios comerciales

## Generación de Query

`_build_image_query()` usa Claude para generar una query de 4-6 palabras. Si falla, usa fallbacks por categoría (ej: "gobierno Republica Dominicana politica" para política).

## Imágenes para Facebook

`facebook_image_generator.py` genera imágenes 1200×630px estilo BBC:

1. Intenta descargar cada URL candidata hasta que una funcione
2. Redimensiona a 1200×630 con LANCZOS
3. Aplica overlay oscuro gradual
4. Dibuja barra navy inferior (90px) con línea azul
5. Renderiza título con wrapping inteligente (fuente grande → mediana si > 3 líneas)
6. Agrega favicon y "NeuroDiario" en la barra
7. Agrega "neurodiario.com" alineado a la derecha

Fallback: gradiente navy→azul con textura de red neuronal (puntos + líneas) generada proceduralmente.

## Múltiples Candidatas

El sistema recolecta múltiples URLs en orden de prioridad. Tanto Facebook como WordPress intentan cada candidata hasta encontrar una que descargue exitosamente. Esto resuelve el problema de imágenes que existen en Google pero que bloquean la descarga directa.
