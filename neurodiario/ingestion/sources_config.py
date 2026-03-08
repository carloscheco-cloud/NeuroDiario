"""
Configuración de fuentes de noticias dominicanas.
Define los feeds RSS y metadatos de cada medio de comunicación.
"""

SOURCES = [
    {
        "name": "Listín Diario",
        "url": "https://listindiario.com/rss",
        "category": "general",
        "country": "DO",
        "language": "es",
        "active": True,
    },
    {
        "name": "Diario Libre",
        "url": "https://www.diariolibre.com/rss",
        "category": "general",
        "country": "DO",
        "language": "es",
        "active": True,
    },
    {
        "name": "El Caribe",
        "url": "https://www.elcaribe.com.do/rss",
        "category": "general",
        "country": "DO",
        "language": "es",
        "active": True,
    },
    {
        "name": "Hoy Digital",
        "url": "https://hoy.com.do/rss",
        "category": "general",
        "country": "DO",
        "language": "es",
        "active": True,
    },
    {
        "name": "Acento",
        "url": "https://acento.com.do/rss",
        "category": "opinion",
        "country": "DO",
        "language": "es",
        "active": True,
    },
]

# Categorías válidas para clasificación
VALID_CATEGORIES = [
    "politica",
    "economia",
    "deportes",
    "cultura",
    "tecnologia",
    "salud",
    "educacion",
    "internacional",
    "opinion",
    "general",
]

# Tiempo máximo de espera por fuente (segundos)
FETCH_TIMEOUT = 30

# Número máximo de artículos por fuente en cada ciclo
MAX_ARTICLES_PER_SOURCE = 50
