# Arquitectura de NeuroDiario

## Visión General

NeuroDiario es un sistema de periodismo autónomo que opera como un pipeline de procesamiento de datos de cinco etapas: ingesta, procesamiento NLP, generación de contenido, publicación y distribución. El sistema corre como un proceso Docker persistente en Railway, orquestado por APScheduler.

## Diagrama de Componentes

```mermaid
graph TD
    subgraph Externo["Servicios Externos"]
        RSS_Feeds["Feeds RSS<br>10+ medios"]
        ClaudeAPI["Anthropic API<br>Claude Haiku"]
        SerperAPI["Serper.dev<br>Google Images"]
        PexelsAPI["Pexels API"]
        WPAPI["WordPress<br>REST API"]
        FBAPI["Facebook<br>Graph API"]
        TGAPI["Telegram<br>Bot API"]
        MCAPI["Mailchimp<br>API v3"]
    end

    subgraph App["NeuroDiario (Docker Container)"]
        Scheduler["auto_scheduler.py<br>APScheduler"]
        
        subgraph Ingestion["Ingesta"]
            RSSFetcher --> ArticleParser
            ArticleParser --> Deduplicator
            Deduplicator --> RelevanceFilter["Filtro de Relevancia"]
        end
        
        subgraph NLP_Module["NLP"]
            TextCleaner --> EntityExtractor
            EntityExtractor --> Classifier["ArticleClassifier<br>(híbrido)"]
        end
        
        subgraph Generation["Generación"]
            DeduplicatorClusters["deduplicator_clusters<br>TF-IDF + cosine"]
            ClusteringPipeline["clustering_pipeline<br>ordenamiento + generación"]
            ArticleGenerator["ArticleGenerator<br>Claude + imágenes"]
        end
        
        subgraph Publishing["Publicación"]
            WPPublisher["WordPressPublisher"]
            FBImageGen["FacebookImageGenerator<br>Pillow"]
            TGPublisher["TelegramPublisher"]
            NewsletterGen["NewsletterGenerator"]
            NewsletterSender["NewsletterSender"]
        end
        
        DB[(PostgreSQL)]
    end

    RSS_Feeds --> RSSFetcher
    RelevanceFilter --> DB
    DB --> TextCleaner
    Classifier --> DB
    DB --> DeduplicatorClusters
    ClusteringPipeline --> ArticleGenerator
    ArticleGenerator --> ClaudeAPI
    ArticleGenerator --> SerperAPI
    ArticleGenerator --> PexelsAPI
    ArticleGenerator --> WPPublisher
    WPPublisher --> WPAPI
    WPPublisher --> DB
    DB --> FBImageGen
    FBImageGen --> FBAPI
    DB --> TGPublisher
    TGPublisher --> TGAPI
    DB --> NewsletterGen
    NewsletterGen --> ClaudeAPI
    NewsletterSender --> MCAPI
    Classifier -.-> ClaudeAPI

    Scheduler --> Ingestion
    Scheduler --> NLP_Module
    Scheduler --> Generation
    Scheduler --> Publishing
```

## Comunicación entre Componentes

Los módulos se comunican a través de la base de datos PostgreSQL como intermediario principal:

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant I as Ingesta
    participant DB as PostgreSQL
    participant N as NLP
    participant C as Clustering
    participant G as Generador
    participant P as Publisher
    participant R as Redes Sociales

    S->>I: Trigger cada 20 min
    I->>DB: INSERT articles (processed=false)
    S->>N: Trigger cada 20 min
    N->>DB: SELECT articles WHERE processed=false
    DB-->>N: Artículos sin procesar
    N->>DB: UPDATE articles SET processed=true, category, entities
    S->>C: Trigger 7am/1pm/7pm
    C->>DB: SELECT articles WHERE no GeneratedArticle
    DB-->>C: Artículos no publicados
    C->>G: Clusters ordenados
    G->>P: Artículo generado + imagen
    P->>DB: INSERT generated_articles (status=published)
    S->>R: Trigger cada 12 min
    R->>DB: SELECT generated_articles WHERE fb=null OR tg=null
    DB-->>R: Pendientes de distribución
    R->>DB: UPDATE facebook_post_id, telegram_message_id
```

## Principios de Diseño

1. **Modularidad**: cada fase del pipeline es independiente y ejecutable por separado.
2. **Carga perezosa**: los modelos pesados (spaCy, sentence-transformers) se inicializan solo cuando se necesitan.
3. **BD como bus de datos**: los módulos no se llaman entre sí directamente; la BD actúa como cola de trabajo.
4. **Fallbacks en cascada**: cada integración externa tiene alternativas (newspaper3k → BS4, Serper → Pexels, sendPhoto → sendMessage).
5. **Distribución escalonada**: un artículo por ciclo en redes sociales para evitar saturación.
6. **Dry-run por defecto**: todas las operaciones destructivas requieren confirmación explícita.

## Infraestructura

| Componente | Servicio | Detalles |
|-----------|---------|---------|
| Aplicación | Railway Pro | Docker container con Python 3.11-slim |
| Base de datos | Railway PostgreSQL | Gestionada, pool_size=5, max_overflow=10 |
| CMS | GreenGeeks | WordPress (PHP 8.2), REST API habilitada |
| CDN de imágenes | WordPress Media Library | Subida vía REST API |
| Código fuente | GitHub | Autodeploy a Railway en push a main |
