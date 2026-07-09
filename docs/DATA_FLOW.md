# Flujo de Datos

## Viaje de una Noticia

```mermaid
flowchart TD
    A["🌐 Feed RSS<br>(ej: Diario Libre)"] --> B["📥 RSSFetcher<br>feedparser + requests"]
    B --> C["📄 ArticleParser<br>newspaper3k → BS4"]
    C --> D{"🔍 ¿Duplicado?<br>URL + título 80%"}
    D -- "Sí" --> X1["🗑 Descartado"]
    D -- "No" --> E{"🇩🇴 ¿Relevante<br>para RD?"}
    E -- "No (int.)" --> X2["🗑 Filtrado"]
    E -- "Sí" --> F["💾 PostgreSQL<br>articles<br>processed=false"]
    
    F --> G["🧹 TextCleaner<br>HTML, URLs, chars"]
    G --> H["👤 EntityExtractor<br>spaCy NER"]
    H --> I["📊 Classifier<br>fuente → Haiku → keywords"]
    I --> J["💾 PostgreSQL<br>processed=true<br>category, entities"]
    
    J --> K["📦 Clustering TF-IDF<br>cosine similarity 0.32"]
    K --> L["🏆 Ranking<br>medios × categoría"]
    L --> M["✍️ Claude Haiku<br>artículo 450-650 palabras"]
    M --> N["🖼 Serper → Pexels<br>imagen 3 niveles"]
    N --> O["📰 WordPress<br>REST API + imagen"]
    O --> P["💾 PostgreSQL<br>generated_articles<br>status=published"]
    
    P --> Q["📘 Facebook<br>imagen BBC 1200×630"]
    P --> R["📱 Telegram<br>sendPhoto + caption"]
    P --> S["📧 Newsletter<br>Mailchimp (domingos)"]

    style A fill:#e3f2fd
    style F fill:#f3e8fd
    style J fill:#f3e8fd
    style O fill:#fff3e0
    style P fill:#f3e8fd
    style Q fill:#e8f0fe
    style R fill:#e8f5e9
    style S fill:#fce8e6
```

## Transformaciones de Datos

| Etapa | Entrada | Transformación | Salida |
|-------|---------|---------------|--------|
| RSS | Feed XML | Parseo + normalización | Dict: title, url, summary, source, image |
| Parse | Dict con URL | Descarga HTML → extracción de texto | + raw_html, raw_content, word_count |
| Dedup | URL + título | Comparación exacta + SequenceMatcher | Booleano (pasa/no pasa) |
| Filtro | Dict completo | Keywords RD en título + contenido | Booleano (pasa/no pasa) |
| Clean | raw_content | Regex: HTML, URLs, emails, chars | clean_content |
| NER | clean_content | spaCy pipeline | entities: {persona: [], org: [], lugar: []} |
| Classify | texto + título + fuente | Híbrido 3 capas | (categoría, confianza) |
| Cluster | título + summary | TF-IDF + cosine similarity | Clusters de artículos similares |
| Generar | Cluster de artículos | Claude Haiku + system prompt | Artículo HTML + footer + compartir |
| Imagen | Título + categoría | Claude query → Serper → Pexels | URL de imagen + HTML |
| Publicar | Artículo + imagen | WordPress REST API | wordpress_post_id |
| Facebook | Título + imagen + URL | Pillow compositing + Graph API | facebook_post_id |
| Telegram | Título + imagen + URL | Bot API sendPhoto | telegram_message_id |
