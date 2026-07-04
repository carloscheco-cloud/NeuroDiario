"""
Configuracion de fuentes RSS - NeuroDiario
Dominicanas: 30 articulos max (prioridad total)
Internacionales: 10 articulos max (solo las relevantes para RD pasan el filtro)
"""
FETCH_TIMEOUT = 15
# Dominicanas: limite alto porque todas pasan el filtro
# Internacionales: limite bajo porque solo las relevantes pasan
MAX_ARTICLES_PER_SOURCE = 30  # se sobreescribe por fuente abajo
SOURCES = [
    # ─────────────────────────────────────────────
    # MEDIOS DOMINICANOS — prioridad maxima
    # ─────────────────────────────────────────────
    {
        "name": "Diario Libre",
        "url": "https://www.diariolibre.com/rss/portada.xml",
        "category": "general",
        "language": "es",
        "active": True,
        "max_articles": 30,
    },
    {
        "name": "Diario Libre - Politica",
        "url": "https://www.diariolibre.com/rss/politica.xml",
        "category": "politica",
        "language": "es",
        "active": True,
        "max_articles": 30,
    },
    {
        "name": "Diario Libre - Economia",
        "url": "https://www.diariolibre.com/rss/economia.xml",
        "category": "economia",
        "language": "es",
        "active": True,
        "max_articles": 30,
    },
    {
        "name": "Diario Libre - Deportes",
        "url": "https://www.diariolibre.com/rss/deportes.xml",
        "category": "deportes",
        "language": "es",
        "active": True,
        "max_articles": 30,
    },
    {
        "name": "El Nacional",
        # URL corregida — /feed/ entraba en loop infinito de redirects
        "url": "https://elnacional.com.do/rss/home.xml",
        "category": "general",
        "language": "es",
        "active": True,
        "max_articles": 30,
    },
    {
        "name": "N Digital",
        # Requiere User-Agent de browser — Cloudflare bloquea bots
        # El header se aplica en RSSFetcher.fetch_feed()
        "url": "https://n.com.do/feed/",
        "category": "general",
        "language": "es",
        "active": True,
        "max_articles": 30,
    },
    {
        "name": "El Dia",
        "url": "https://eldia.com.do/feed/",
        "category": "general",
        "language": "es",
        "active": True,
        "max_articles": 30,
    },
    # ─────────────────────────────────────────────
    # INTERNACIONALES — limite reducido
    # Solo las relevantes para RD pasan el filtro
    # ─────────────────────────────────────────────
    {
        "name": "BBC Mundo",
        "url": "https://feeds.bbci.co.uk/mundo/rss.xml",
        "category": "internacional",
        "language": "es",
        "active": True,
        "max_articles": 10,
    },
    {
        "name": "El Pais America",
        "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/america/portada",
        "category": "internacional",
        "language": "es",
        "active": True,
        "max_articles": 10,
    },
    {
        "name": "Bloomberg",
        "url": "https://feeds.bloomberg.com/economics/news.rss",
        "category": "economia",
        "language": "en",
        "active": False,  # Da 403 consistentemente — desactivado
        "max_articles": 5,
    },
]
