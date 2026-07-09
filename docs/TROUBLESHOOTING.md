# Troubleshooting

## Ingesta

**Problema**: Feed de N Digital no devuelve artículos  
**Causa**: Cloudflare bloquea bots sin User-Agent de browser  
**Solución**: el sistema ya usa headers de Chrome. Si persiste, verificar con `python verificar_fuentes.py`

**Problema**: Artículos llegan sin raw_content  
**Causa**: newspaper3k y BeautifulSoup no pudieron extraer texto  
**Solución**: artículos sin contenido se guardan pero no generan artículos. Es normal para sitios con contenido dinámico (JavaScript).

## NLP

**Problema**: Error "Modelo es_core_news_lg no encontrado"  
**Solución**: `python -m spacy download es_core_news_lg`

**Problema**: Todo se clasifica como "politica"  
**Causa**: bug antiguo del clasificador por keywords (substrings). Resuelto con el clasificador híbrido actual.

## Publicación

**Problema**: WordPress devuelve 401  
**Causa**: URL con http:// en vez de https://, o Application Passwords no habilitadas  
**Solución**: verificar `WORDPRESS_URL` con https:// y que Application Passwords estén activas

**Problema**: Categorías de WordPress se crean con slug duplicado (ej: `politica-2`)  
**Causa**: ya existía una categoría con ese nombre/slug  
**Solución**: verificar las categorías en WordPress Admin y actualizar los menús

## Imágenes

**Problema**: Misma imagen repetida en diferentes artículos  
**Causa**: la query de imagen para Claude genera queries muy similares  
**Solución**: verificar la variedad de queries en los logs. El query se genera específicamente para cada título.

**Problema**: Artículos sin imagen destacada  
**Causa**: Serper y Pexels no encontraron imagen válida, o la descarga falló  
**Solución**: las imágenes son opcionales; el artículo se publica sin imagen destacada

## Facebook

**Problema**: Posts no se publican en Facebook  
**Causa**: token expirado (si se usó token de usuario de corta vida)  
**Solución**: obtener un Page Access Token permanente vía `GET /me/accounts`

## Railway

**Problema**: Container se reinicia por memoria  
**Causa**: sentence-transformers consume ~1.5GB. El clustering activo usa TF-IDF (ligero)  
**Solución**: el scheduler actual no carga sentence-transformers a menos que se use `topic_cluster.py`

**Problema**: Railway Shell no acepta heredoc  
**Solución**: usar `python3 -c "..."` en una sola línea, más confiable
