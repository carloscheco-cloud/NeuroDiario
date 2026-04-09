"""
Configuración de fuentes RSS - NeuroDiario
Solo feeds verificados y activos.
Última verificación: 09/04/2026
"""

FETCH_TIMEOUT = 15
MAX_ARTICLES_PER_SOURCE = 30

SOURCES = [
    # ─────────────────────────────────
    # DIARIO LIBRE (4 secciones activas)
    # ─────────────────────────────────
    {
        "name": "Diario Libre",
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
        "name": "Diario Libre - Economía",
        "url": "https://www.diariolibre.com/rss/economia.xml",
        "category": "economia",
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

    # ─────────────────────────────────
    # OTROS MEDIOS DOMINICANOS ACTIVOS
    # ─────────────────────────────────
    {
        "name": "El Nacional",
        "url": "https://elnacional.com.do/feed/",
        "category": "general",
        "language": "es",
        "active": True,
    },
    {
        "name": "N Digital",
        "url": "https://n.com.do/feed/",
        "category": "general",
        "language": "es",
        "active": True,
    },
    {
        "name": "El Día",
        "url": "https://eldia.com.do/feed/",
        "category": "general",
        "language": "es",
        "active": True,
    },

    # ─────────────────────────────────
    # INTERNACIONALES ACTIVOS
    # ─────────────────────────────────
    {
        "name": "BBC Mundo",
        "url": "https://feeds.bbci.co.uk/mundo/rss.xml",
        "category": "internacional",
        "language": "es",
        "active": True,
    },
    {
        "name": "El País América",
        "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/america/portada",
        "category": "internacional",
        "language": "es",
        "active": True,
    },
    {
        "name": "Bloomberg",
        "url": "https://feeds.bloomberg.com/economics/news.rss",
        "category": "economia",
        "language": "en",
        "active": True,
    },
]
