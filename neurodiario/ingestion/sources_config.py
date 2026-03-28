"""
Configuración de fuentes RSS de medios dominicanos.
Define qué periódicos monitorear y sus metadatos.
"""

# Timeout para requests HTTP (segundos)
FETCH_TIMEOUT = 15

# Artículos máximos por fuente en cada ciclo
MAX_ARTICLES_PER_SOURCE = 50

# Lista de fuentes RSS activas
SOURCES = [
    {
        "name": "Hoy",
        "url": "https://hoy.com.do/feed/",
        "category": "general",
        "language": "es",
        "active": True,
    },
    {
        "name": "Diario Libre - Portada",
        "url": "https://www.diariolibre.com/rss/portada.xml",
        "category": "general",
        "language": "es",
        "active": True,
    },
    {
        "name": "Diario Libre - Política",
        "url": "https://www.diariolibre.com/rss/politica.xml",
        "category": "politica",
        "language": "es",
        "active": True,
    },
    {
        "name": "Diario Libre - Deportes",
        "url": "https://www.diariolibre.com/rss/deportes.xml",
        "category": "deportes",
        "language": "es",
        "active": True,
    },
    {
        "name": "El Nacional",
        "url": "https://elnacional.com.do/feed/",
        "category": "general",
        "language": "es",
        "active": True,
    },
]
