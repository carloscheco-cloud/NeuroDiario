# Decisiones de Diseño

## 1. REST API en lugar de XML-RPC para WordPress

**Contexto**: el hosting (GreenGeeks) bloquea XML-RPC por seguridad.  
**Decisión**: migrar a WordPress REST API con HTTPBasicAuth (Application Passwords).  
**Consecuencia**: más verboso (buscar/crear categorías y tags), pero más confiable y compatible. La dependencia `python-wordpress-xmlrpc` en requirements.txt es legacy.

## 2. Claude Haiku para generación (no Sonnet/Opus)

**Contexto**: se generan hasta 75 artículos/día (25 × 3 ciclos).  
**Decisión**: usar Claude Haiku (~$0.28 por 20 artículos) para mantener costos bajos.  
**Consecuencia**: calidad editorial suficiente para noticias con prompt detallado. Modelo configurable si se quiere más calidad.

## 3. Clasificación híbrida (fuente → Haiku → keywords)

**Contexto**: el clasificador original por keywords tenía un bug donde "ley" contaba dentro de "leyenda", y casi todo caía en "politica".  
**Decisión**: tres capas: confiar en secciones específicas de fuentes (deportes, economía = gratis), consultar Haiku para fuentes genéricas, keywords como último recurso.  
**Consecuencia**: clasificación precisa sin gastar en API para secciones que ya están clasificadas por el medio.

## 4. Clustering TF-IDF en lugar de embeddings semánticos para deduplicación

**Contexto**: sentence-transformers consume mucha memoria (~1.5GB). Railway tiene límite de 4GB.  
**Decisión**: usar TF-IDF + cosine similarity (scikit-learn, ligero) para `deduplicator_clusters.py`. `topic_cluster.py` con sentence-transformers existe pero no se usa en el scheduler activo.  
**Consecuencia**: menos preciso semánticamente, pero funcional y dentro del límite de memoria.

## 5. Distribución social escalonada (1 artículo cada 12 minutos)

**Contexto**: publicar 25 artículos simultáneamente en redes sociales satura el feed.  
**Decisión**: procesar solo 1 artículo por ciclo del job social_sync.  
**Consecuencia**: distribución natural a lo largo de ~5 horas. Si el sistema se detiene, los pendientes se procesan al reiniciar.

## 6. Base de datos como bus de datos entre módulos

**Contexto**: los módulos podrían comunicarse directamente vía funciones.  
**Decisión**: usar PostgreSQL como intermediario: ingesta guarda → NLP lee y actualiza → clustering lee y genera → social sync lee y actualiza.  
**Consecuencia**: cada módulo es independiente, puede ejecutarse por separado, y el estado persiste entre reinicios.

## 7. Imágenes de fuentes oficiales primero

**Contexto**: las fotos de medios dominicanos llevan marcas de agua y tienen derechos de autor.  
**Decisión**: buscar primero en sitios oficiales (gobierno, congreso, partidos), luego en Google excluyendo medios, y Pexels como fallback.  
**Consecuencia**: imágenes sin marcas de agua, identidad de personas confiable, y respeto a derechos de autor.

## 8. Clustering separado del paquete principal

**Contexto**: `clustering_pipeline.py` y `deduplicator_clusters.py` están en la raíz, fuera de `neurodiario/`.  
**Decisión**: módulos separados para iteración rápida sin afectar el paquete principal.  
**Consecuencia**: imports menos limpios (`from clustering_pipeline import procesar`). Candidatos a integrar en el paquete en el futuro.
