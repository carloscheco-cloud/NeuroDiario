"""
media_analyzer.py — NeuroData: Laboratorio de Inteligencia Mediatica
=====================================================================
Modulo de analisis de cobertura mediatica de medios dominicanos.

Funciones principales:
  1. Buscar articulos de un medio sobre un tema usando Serper.dev (Google Search)
  2. Almacenar resultados en PostgreSQL
  3. Clasificar sentimiento con Claude Haiku
  4. Generar estadisticas de cobertura

Uso desde Railway Shell:
  python3 media_analyzer.py setup          # Crear tablas en PostgreSQL
  python3 media_analyzer.py search         # Buscar articulos (interactivo)
  python3 media_analyzer.py analyze        # Clasificar sentimiento pendiente
  python3 media_analyzer.py report         # Generar reporte de resultados
  python3 media_analyzer.py full           # Ejecutar todo el pipeline completo
  python3 media_analyzer.py demo           # Demo rapido: INTRANT en Diario Libre

Variables de entorno requeridas (ya configuradas en Railway):
  DATABASE_URL, SERPER_API_KEY, ANTHROPIC_API_KEY
"""

import os
import sys
import json
import time
import logging
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras
import requests
import anthropic

# ─── Configuracion ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("media_analyzer")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# Pausa entre llamadas a Serper (segundos) para respetar rate limits
SERPER_DELAY = 1.5
# Pausa entre llamadas a Claude Haiku para clasificacion
CLAUDE_DELAY = 0.5
# Maximo de resultados por query de Serper (cuenta gratuita: max 10)
SERPER_MAX_RESULTS = 10

# ─── Medios Dominicanos ──────────────────────────────────────────────────────

MEDIOS_RD = {
    "diariolibre": {
        "nombre": "Diario Libre",
        "dominio": "diariolibre.com",
        "grupo": "Grupo Omnimedia",
        "tipo": "digital_impreso",
        "fundado": 2001,
    },
    "listindiario": {
        "nombre": "Listín Diario",
        "dominio": "listindiario.com",
        "grupo": "Grupo Listín",
        "tipo": "digital_impreso",
        "fundado": 1889,
    },
    "elcaribe": {
        "nombre": "El Caribe",
        "dominio": "elcaribe.com.do",
        "grupo": "Grupo Corripio",
        "tipo": "digital_impreso",
        "fundado": 1948,
    },
    "hoy": {
        "nombre": "Hoy Digital",
        "dominio": "hoy.com.do",
        "grupo": "Grupo Corripio",
        "tipo": "digital_impreso",
        "fundado": 1981,
    },
    "acento": {
        "nombre": "Acento",
        "dominio": "acento.com.do",
        "grupo": "Independiente",
        "tipo": "digital",
        "fundado": 2010,
    },
    "elnuevodiario": {
        "nombre": "El Nuevo Diario",
        "dominio": "elnuevodiario.com.do",
        "grupo": "Independiente",
        "tipo": "digital",
        "fundado": 1981,
    },
    "ndigital": {
        "nombre": "N Digital",
        "dominio": "ndigital.com.do",
        "grupo": "Independiente",
        "tipo": "digital",
        "fundado": 2015,
    },
    "cdn": {
        "nombre": "CDN",
        "dominio": "cdn.com.do",
        "grupo": "Grupo Corripio",
        "tipo": "tv_digital",
        "fundado": 1996,
    },
    "noticiassin": {
        "nombre": "Noticias SIN",
        "dominio": "noticiassin.com",
        "grupo": "Grupo SIN",
        "tipo": "tv_digital",
        "fundado": 2003,
    },
    "eldia": {
        "nombre": "El Día",
        "dominio": "eldia.com.do",
        "grupo": "Grupo Ávila",
        "tipo": "digital_impreso",
        "fundado": 2002,
    },
}

# ─── Instituciones y actores politicos clave ──────────────────────────────────

INSTITUCIONES_RD = {
    "INTRANT": {
        "nombre_completo": "Instituto Nacional de Tránsito y Transporte Terrestre",
        "creado": 2017,
        "predecesor": "AMET/OTTT",
        "sector": "transporte",
    },
    "CAASD": {
        "nombre_completo": "Corporación del Acueducto y Alcantarillado de Santo Domingo",
        "creado": 1973,
        "sector": "agua",
    },
    "EDESUR": {
        "nombre_completo": "Empresa Distribuidora de Electricidad del Sur",
        "creado": 1999,
        "sector": "energia",
    },
    "EDENORTE": {
        "nombre_completo": "Empresa Distribuidora de Electricidad del Norte",
        "creado": 1999,
        "sector": "energia",
    },
    "DGII": {
        "nombre_completo": "Dirección General de Impuestos Internos",
        "creado": 1997,
        "sector": "fiscal",
    },
    "Procuraduria": {
        "nombre_completo": "Procuraduría General de la República",
        "creado": 1844,
        "sector": "justicia",
    },
    "Policia Nacional": {
        "nombre_completo": "Policía Nacional de República Dominicana",
        "creado": 1936,
        "sector": "seguridad",
    },
    "MINERD": {
        "nombre_completo": "Ministerio de Educación",
        "creado": 1844,
        "sector": "educacion",
    },
    "Salud Publica": {
        "nombre_completo": "Ministerio de Salud Pública",
        "creado": 1942,
        "sector": "salud",
    },
    "DGA": {
        "nombre_completo": "Dirección General de Aduanas",
        "creado": 1953,
        "sector": "comercio",
    },
}

PERIODOS_PRESIDENCIALES = {
    "Hipolito Mejia": {"inicio": 2000, "fin": 2004, "partido": "PRD"},
    "Leonel Fernandez II": {"inicio": 2004, "fin": 2008, "partido": "PLD"},
    "Leonel Fernandez III": {"inicio": 2008, "fin": 2012, "partido": "PLD"},
    "Danilo Medina I": {"inicio": 2012, "fin": 2016, "partido": "PLD"},
    "Danilo Medina II": {"inicio": 2016, "fin": 2020, "partido": "PLD"},
    "Luis Abinader I": {"inicio": 2020, "fin": 2024, "partido": "PRM"},
    "Luis Abinader II": {"inicio": 2024, "fin": 2028, "partido": "PRM"},
}


# ─── Base de Datos ────────────────────────────────────────────────────────────

def get_db_connection():
    """Obtiene conexion a PostgreSQL usando DATABASE_URL de Railway."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL no configurada. Verifica variables de entorno en Railway.")
    return psycopg2.connect(DATABASE_URL)


def setup_database():
    """Crea las tablas necesarias para el analisis de medios."""
    logger.info("Creando tablas de NeuroData en PostgreSQL...")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS nd_media_searches (
            id              SERIAL PRIMARY KEY,
            medio_key       VARCHAR(50) NOT NULL,
            medio_dominio   VARCHAR(100) NOT NULL,
            keyword         VARCHAR(200) NOT NULL,
            year_start      INTEGER NOT NULL,
            year_end        INTEGER NOT NULL,
            total_results   INTEGER DEFAULT 0,
            searched_at     TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS nd_media_articles (
            id              SERIAL PRIMARY KEY,
            medio_key       VARCHAR(50) NOT NULL,
            medio_dominio   VARCHAR(100) NOT NULL,
            keyword         VARCHAR(200) NOT NULL,
            title           TEXT NOT NULL,
            snippet         TEXT,
            url             TEXT NOT NULL UNIQUE,
            article_date    DATE,
            year            INTEGER,
            month           INTEGER,
            section         VARCHAR(100),
            fetched_at      TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS nd_sentiment_analysis (
            id              SERIAL PRIMARY KEY,
            article_id      INTEGER REFERENCES nd_media_articles(id) ON DELETE CASCADE,
            keyword         VARCHAR(200) NOT NULL,
            sentiment       VARCHAR(20) NOT NULL,
            sentiment_score FLOAT,
            tone_detail     VARCHAR(50),
            actors_mentioned TEXT,
            frame           VARCHAR(100),
            analyzed_at     TIMESTAMP DEFAULT NOW(),
            model_used      VARCHAR(50) DEFAULT 'claude-haiku'
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS nd_coverage_stats (
            id              SERIAL PRIMARY KEY,
            medio_key       VARCHAR(50) NOT NULL,
            keyword         VARCHAR(200) NOT NULL,
            period_label    VARCHAR(100) NOT NULL,
            year_start      INTEGER NOT NULL,
            year_end        INTEGER NOT NULL,
            total_articles  INTEGER DEFAULT 0,
            positive_count  INTEGER DEFAULT 0,
            negative_count  INTEGER DEFAULT 0,
            neutral_count   INTEGER DEFAULT 0,
            avg_sentiment   FLOAT,
            computed_at     TIMESTAMP DEFAULT NOW(),
            UNIQUE(medio_key, keyword, period_label)
        );
    """)

    # Indices para consultas rapidas
    cur.execute("CREATE INDEX IF NOT EXISTS idx_nda_medio_keyword ON nd_media_articles(medio_key, keyword);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_nda_year ON nd_media_articles(year);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_nda_url ON nd_media_articles(url);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ndsa_article ON nd_sentiment_analysis(article_id);")

    conn.commit()
    cur.close()
    conn.close()

    logger.info("Tablas creadas exitosamente:")
    logger.info("  - nd_media_searches    (registro de busquedas realizadas)")
    logger.info("  - nd_media_articles    (articulos encontrados)")
    logger.info("  - nd_sentiment_analysis (clasificacion de sentimiento)")
    logger.info("  - nd_coverage_stats    (estadisticas agregadas)")


# ─── Serper.dev: Busqueda de articulos ────────────────────────────────────────

def search_serper(query: str, num: int = 10, gl: str = "do", hl: str = "es") -> Dict:
    """
    Ejecuta una busqueda en Google via Serper.dev.
    Retorna el JSON completo de respuesta.
    """
    if not SERPER_API_KEY:
        raise ValueError("SERPER_API_KEY no configurada.")

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "q": query,
        "gl": gl,
        "hl": hl,
        "num": min(num, SERPER_MAX_RESULTS),
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_date_from_url(url: str) -> Optional[date]:
    """
    Intenta extraer la fecha del articulo desde la URL.
    Patrones comunes en medios RD:
      /2024/03/15/titulo-del-articulo
      /2023/11/13/caso-intrant/2522054
    """
    patterns = [
        r'/(\d{4})/(\d{1,2})/(\d{1,2})/',
        r'/(\d{4})-(\d{1,2})-(\d{1,2})/',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            try:
                y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 2000 <= y <= 2030 and 1 <= m <= 12 and 1 <= d <= 31:
                    return date(y, m, d)
            except ValueError:
                continue
    return None


def extract_section_from_url(url: str) -> Optional[str]:
    """
    Extrae la seccion del articulo desde la URL.
    Ej: /actualidad/justicia/2023/... -> actualidad/justicia
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    parts = path.split("/")

    # Buscar las partes antes de la fecha (4 digitos = año)
    section_parts = []
    for part in parts:
        if re.match(r'^\d{4}$', part):
            break
        if part and not re.match(r'^\d+$', part):
            section_parts.append(part)

    if section_parts:
        return "/".join(section_parts[:2])  # Maximo 2 niveles
    return None


def search_media_articles(
    medio_key: str,
    keyword: str,
    year_start: int,
    year_end: int,
) -> List[Dict]:
    """
    Busca articulos de un medio sobre un tema en un rango de anios.
    Hace una query por anio para granularidad.
    Retorna lista de articulos encontrados.
    """
    medio = MEDIOS_RD.get(medio_key)
    if not medio:
        raise ValueError(f"Medio '{medio_key}' no reconocido. Opciones: {list(MEDIOS_RD.keys())}")

    dominio = medio["dominio"]
    all_articles = []
    seen_urls = set()

    for year in range(year_start, year_end + 1):
        # Buscar por semestre para maximizar resultados (max 10 por query en cuenta gratuita)
        semesters = [
            (f"{year}-01-01", f"{year}-06-30", "S1"),
            (f"{year}-07-01", f"{year}-12-31", "S2"),
        ]
        for date_start, date_end, sem_label in semesters:
            query = f'site:{dominio} "{keyword}" after:{date_start} before:{date_end}'
            logger.info(f"  Buscando: {medio['nombre']} | {keyword} | {year}-{sem_label}...")

            try:
                result = search_serper(query, num=10)
            except Exception as e:
                logger.error(f"  Error en Serper para {year}-{sem_label}: {e}")
                time.sleep(SERPER_DELAY)
                continue

            organic = result.get("organic", [])
            count = len(organic)

            logger.info(f"    -> {count} resultados")

            for item in organic:
                url = item.get("link", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                article_date = extract_date_from_url(url)
                section = extract_section_from_url(url)

                article = {
                    "medio_key": medio_key,
                    "medio_dominio": dominio,
                    "keyword": keyword,
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": url,
                    "article_date": article_date,
                    "year": article_date.year if article_date else year,
                    "month": article_date.month if article_date else None,
                    "section": section,
                }
                all_articles.append(article)

            time.sleep(SERPER_DELAY)

    logger.info(f"  Total unico: {len(all_articles)} articulos de {medio['nombre']} sobre '{keyword}' ({year_start}-{year_end})")
    return all_articles


def save_articles_to_db(articles: List[Dict], medio_key: str, keyword: str, year_start: int, year_end: int) -> int:
    """Guarda articulos en PostgreSQL. Ignora duplicados por URL."""
    if not articles:
        return 0

    conn = get_db_connection()
    cur = conn.cursor()
    saved = 0

    # Registrar la busqueda
    cur.execute("""
        INSERT INTO nd_media_searches (medio_key, medio_dominio, keyword, year_start, year_end, total_results)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (medio_key, articles[0]["medio_dominio"], keyword, year_start, year_end, len(articles)))

    for art in articles:
        try:
            cur.execute("""
                INSERT INTO nd_media_articles
                    (medio_key, medio_dominio, keyword, title, snippet, url, article_date, year, month, section)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
            """, (
                art["medio_key"], art["medio_dominio"], art["keyword"],
                art["title"], art["snippet"], art["url"],
                art["article_date"], art["year"], art["month"], art["section"],
            ))
            if cur.rowcount > 0:
                saved += 1
        except Exception as e:
            logger.warning(f"  Error guardando articulo: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"  Guardados: {saved} articulos nuevos (de {len(articles)} encontrados)")
    return saved


# ─── Claude Haiku: Clasificacion de sentimiento ──────────────────────────────

SENTIMENT_SYSTEM_PROMPT = """Eres un analista de medios de comunicacion de Republica Dominicana.
Tu trabajo es clasificar el sentimiento y tono de titulares y fragmentos de noticias
respecto a la institucion o actor mencionado.

REGLAS:
- Clasifica el sentimiento hacia la INSTITUCION o ACTOR indicado, no el tono general de la noticia.
- Una noticia sobre un accidente de transito NO es negativa contra el INTRANT a menos que critique su gestion.
- Una noticia sobre un logro o programa es POSITIVA.
- Una noticia sobre quejas, denuncias, corrupcion o fallos es NEGATIVA.
- Una noticia puramente informativa sin juicio es NEUTRA.

Responde SOLO con un JSON valido, sin texto adicional, sin backticks:
{
  "sentiment": "POSITIVO" | "NEGATIVO" | "NEUTRO",
  "score": float entre -1.0 (muy negativo) y 1.0 (muy positivo),
  "tone": "elogio" | "critica" | "denuncia" | "informativo" | "alarma" | "logro" | "queja_ciudadana",
  "actors": "lista de personas o instituciones mencionadas",
  "frame": "gestion" | "corrupcion" | "servicio_publico" | "politica" | "legal" | "social" | "infraestructura"
}"""


def classify_sentiment(title: str, snippet: str, keyword: str) -> Optional[Dict]:
    """
    Usa Claude Haiku para clasificar el sentimiento de un articulo
    respecto a la institucion/keyword indicada.
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY no configurada.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_msg = f"""Analiza este articulo sobre "{keyword}":

TITULO: {title}
FRAGMENTO: {snippet or 'No disponible'}

Clasifica el sentimiento HACIA "{keyword}" segun las reglas."""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            system=SENTIMENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = response.content[0].text.strip()

        # Limpiar posibles backticks
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        result = json.loads(text)
        return result
    except json.JSONDecodeError as e:
        logger.warning(f"  Error parseando JSON de Claude: {e} | Texto: {text[:200]}")
        return None
    except Exception as e:
        logger.error(f"  Error llamando Claude Haiku: {e}")
        return None


def analyze_pending_articles(limit: int = 50) -> int:
    """
    Clasifica el sentimiento de articulos que aun no han sido analizados.
    Retorna la cantidad de articulos clasificados.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT a.id, a.title, a.snippet, a.keyword
        FROM nd_media_articles a
        LEFT JOIN nd_sentiment_analysis s ON a.id = s.article_id
        WHERE s.id IS NULL
        ORDER BY a.id
        LIMIT %s
    """, (limit,))

    pending = cur.fetchall()
    if not pending:
        logger.info("No hay articulos pendientes de clasificacion.")
        cur.close()
        conn.close()
        return 0

    logger.info(f"Clasificando sentimiento de {len(pending)} articulos con Claude Haiku...")
    classified = 0

    for art in pending:
        result = classify_sentiment(art["title"], art["snippet"], art["keyword"])
        if result:
            try:
                cur.execute("""
                    INSERT INTO nd_sentiment_analysis
                        (article_id, keyword, sentiment, sentiment_score, tone_detail, actors_mentioned, frame)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    art["id"],
                    art["keyword"],
                    result.get("sentiment", "NEUTRO"),
                    result.get("score", 0.0),
                    result.get("tone", "informativo"),
                    result.get("actors", ""),
                    result.get("frame", ""),
                ))
                conn.commit()
                classified += 1
                logger.info(f"  [{classified}/{len(pending)}] {result['sentiment']:>8} ({result.get('score', 0):+.1f}) | {art['title'][:70]}...")
            except Exception as e:
                logger.warning(f"  Error guardando clasificacion: {e}")
                conn.rollback()
        else:
            logger.warning(f"  No se pudo clasificar: {art['title'][:70]}...")

        time.sleep(CLAUDE_DELAY)

    cur.close()
    conn.close()
    logger.info(f"Clasificacion completada: {classified}/{len(pending)} articulos.")
    return classified


# ─── Reportes y estadisticas ─────────────────────────────────────────────────

def generate_report(medio_key: Optional[str] = None, keyword: Optional[str] = None):
    """
    Genera un reporte de cobertura mediatica con los datos almacenados.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Filtros
    where_clauses = []
    params = []
    if medio_key:
        where_clauses.append("a.medio_key = %s")
        params.append(medio_key)
    if keyword:
        where_clauses.append("a.keyword = %s")
        params.append(keyword)

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # ── Resumen general ──
    print("\n" + "=" * 70)
    print("  NEURODATA — REPORTE DE INTELIGENCIA MEDIATICA")
    print("=" * 70)
    print(f"  Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if medio_key:
        medio = MEDIOS_RD.get(medio_key, {})
        print(f"  Medio: {medio.get('nombre', medio_key)} ({medio.get('grupo', 'N/A')})")
    if keyword:
        print(f"  Tema:  {keyword}")
    print("=" * 70)

    # ── Total de articulos por medio ──
    cur.execute(f"""
        SELECT a.medio_key, COUNT(*) as total
        FROM nd_media_articles a
        {where_sql}
        GROUP BY a.medio_key
        ORDER BY total DESC
    """, params)
    rows = cur.fetchall()

    if not rows:
        print("\n  No hay datos almacenados para estos filtros.")
        print("  Ejecuta primero: python3 media_analyzer.py search")
        cur.close()
        conn.close()
        return

    print(f"\n  ARTICULOS ENCONTRADOS POR MEDIO:")
    print("  " + "-" * 50)
    for row in rows:
        nombre = MEDIOS_RD.get(row["medio_key"], {}).get("nombre", row["medio_key"])
        print(f"    {nombre:<25} {row['total']:>6} articulos")

    # ── Distribucion por anio ──
    cur.execute(f"""
        SELECT a.year, COUNT(*) as total
        FROM nd_media_articles a
        {where_sql}
        GROUP BY a.year
        ORDER BY a.year
    """, params)
    rows = cur.fetchall()

    if rows:
        print(f"\n  DISTRIBUCION POR AÑO:")
        print("  " + "-" * 50)
        max_count = max(r["total"] for r in rows) if rows else 1
        for row in rows:
            if row["year"]:
                bar_len = int((row["total"] / max_count) * 30)
                bar = "█" * bar_len
                print(f"    {row['year']}  {bar} {row['total']}")

    # ── Sentimiento (si hay clasificaciones) ──
    cur.execute(f"""
        SELECT s.sentiment, COUNT(*) as total,
               ROUND(AVG(s.sentiment_score)::numeric, 2) as avg_score
        FROM nd_sentiment_analysis s
        JOIN nd_media_articles a ON s.article_id = a.id
        {where_sql}
        GROUP BY s.sentiment
        ORDER BY total DESC
    """, params)
    sent_rows = cur.fetchall()

    if sent_rows:
        total_classified = sum(r["total"] for r in sent_rows)
        print(f"\n  ANALISIS DE SENTIMIENTO ({total_classified} articulos clasificados):")
        print("  " + "-" * 50)

        for row in sent_rows:
            pct = (row["total"] / total_classified * 100) if total_classified > 0 else 0
            emoji = {"POSITIVO": "🟢", "NEGATIVO": "🔴", "NEUTRO": "⚪"}.get(row["sentiment"], "❓")
            print(f"    {emoji} {row['sentiment']:<10} {row['total']:>5} ({pct:5.1f}%)  score promedio: {row['avg_score']:+.2f}")

        # Sentimiento por anio
        cur.execute(f"""
            SELECT a.year, s.sentiment, COUNT(*) as total
            FROM nd_sentiment_analysis s
            JOIN nd_media_articles a ON s.article_id = a.id
            {where_sql}
            GROUP BY a.year, s.sentiment
            ORDER BY a.year, s.sentiment
        """, params)
        yearly_sent = cur.fetchall()

        if yearly_sent:
            print(f"\n  SENTIMIENTO POR AÑO:")
            print("  " + "-" * 60)
            print(f"    {'AÑO':<6} {'POS':>5} {'NEG':>5} {'NEU':>5} {'TOTAL':>6} {'% NEG':>7}")
            print("  " + "-" * 60)

            # Agrupar por anio
            by_year = {}
            for row in yearly_sent:
                y = row["year"]
                if y not in by_year:
                    by_year[y] = {"POSITIVO": 0, "NEGATIVO": 0, "NEUTRO": 0}
                by_year[y][row["sentiment"]] = row["total"]

            for y in sorted(by_year.keys()):
                if y is None:
                    continue
                d = by_year[y]
                total = d["POSITIVO"] + d["NEGATIVO"] + d["NEUTRO"]
                pct_neg = (d["NEGATIVO"] / total * 100) if total > 0 else 0
                print(f"    {y:<6} {d['POSITIVO']:>5} {d['NEGATIVO']:>5} {d['NEUTRO']:>5} {total:>6} {pct_neg:>6.1f}%")

    # ── Tono detallado ──
    cur.execute(f"""
        SELECT s.tone_detail, COUNT(*) as total
        FROM nd_sentiment_analysis s
        JOIN nd_media_articles a ON s.article_id = a.id
        {where_sql}
        GROUP BY s.tone_detail
        ORDER BY total DESC
        LIMIT 10
    """, params)
    tone_rows = cur.fetchall()

    if tone_rows:
        print(f"\n  TONOS DETECTADOS:")
        print("  " + "-" * 50)
        for row in tone_rows:
            print(f"    {row['tone_detail'] or 'N/A':<25} {row['total']:>5}")

    # ── Frames narrativos ──
    cur.execute(f"""
        SELECT s.frame, COUNT(*) as total
        FROM nd_sentiment_analysis s
        JOIN nd_media_articles a ON s.article_id = a.id
        {where_sql}
        GROUP BY s.frame
        ORDER BY total DESC
        LIMIT 10
    """, params)
    frame_rows = cur.fetchall()

    if frame_rows:
        print(f"\n  MARCOS NARRATIVOS:")
        print("  " + "-" * 50)
        for row in frame_rows:
            print(f"    {row['frame'] or 'N/A':<25} {row['total']:>5}")

    # ── Secciones donde aparece ──
    cur.execute(f"""
        SELECT a.section, COUNT(*) as total
        FROM nd_media_articles a
        {where_sql}
        AND a.section IS NOT NULL
        GROUP BY a.section
        ORDER BY total DESC
        LIMIT 10
    """, params)
    section_rows = cur.fetchall()

    if section_rows:
        print(f"\n  SECCIONES DEL MEDIO DONDE APARECE:")
        print("  " + "-" * 50)
        for row in section_rows:
            print(f"    {row['section']:<30} {row['total']:>5}")

    print("\n" + "=" * 70)
    print("  Generado por NeuroData — NeuroNoticia Group")
    print("=" * 70 + "\n")

    cur.close()
    conn.close()


# ─── Pipeline completo ───────────────────────────────────────────────────────

def run_search_interactive():
    """Modo interactivo para configurar una busqueda."""
    print("\n  NEURODATA — Busqueda de Cobertura Mediatica")
    print("  " + "-" * 45)

    # Seleccionar medio(s)
    print("\n  Medios disponibles:")
    for i, (key, info) in enumerate(MEDIOS_RD.items(), 1):
        print(f"    {i:>2}. {info['nombre']:<25} ({info['grupo']})")
    print(f"    {len(MEDIOS_RD)+1:>2}. ** TODOS LOS MEDIOS **")

    try:
        choice = input("\n  Selecciona medio (numero): ").strip()
        choice = int(choice)
        if choice == len(MEDIOS_RD) + 1:
            medios_selected = list(MEDIOS_RD.keys())
        else:
            medios_selected = [list(MEDIOS_RD.keys())[choice - 1]]
    except (ValueError, IndexError):
        print("  Seleccion invalida. Usando 'diariolibre'.")
        medios_selected = ["diariolibre"]

    # Keyword
    keyword = input("  Tema/institucion a buscar: ").strip()
    if not keyword:
        keyword = "INTRANT"
        print(f"  Usando tema por defecto: {keyword}")

    # Rango de anios
    try:
        y_start = int(input("  Año inicio (ej: 2017): ").strip())
    except ValueError:
        y_start = 2017
    try:
        y_end = int(input("  Año fin (ej: 2026): ").strip())
    except ValueError:
        y_end = 2026

    print(f"\n  Configuracion:")
    print(f"    Medios:  {', '.join(medios_selected)}")
    print(f"    Tema:    {keyword}")
    print(f"    Periodo: {y_start}-{y_end}")

    confirm = input("\n  ¿Ejecutar? (s/n): ").strip().lower()
    if confirm != "s":
        print("  Cancelado.")
        return

    # Ejecutar busquedas
    total_found = 0
    total_saved = 0
    for medio_key in medios_selected:
        nombre = MEDIOS_RD[medio_key]["nombre"]
        print(f"\n{'─' * 50}")
        print(f"  Buscando en {nombre}...")
        print(f"{'─' * 50}")

        articles = search_media_articles(medio_key, keyword, y_start, y_end)
        saved = save_articles_to_db(articles, medio_key, keyword, y_start, y_end)
        total_found += len(articles)
        total_saved += saved

    print(f"\n  RESUMEN: {total_found} articulos encontrados, {total_saved} nuevos guardados.")
    print(f"  Ejecuta 'python3 media_analyzer.py analyze' para clasificar sentimiento.")


def run_demo():
    """
    Demo rapido: busca INTRANT en Diario Libre (2017-2026),
    clasifica sentimiento y genera reporte.
    """
    print("\n" + "=" * 60)
    print("  NEURODATA — DEMO: Cobertura del INTRANT en Diario Libre")
    print("=" * 60)

    medio_key = "diariolibre"
    keyword = "INTRANT"
    y_start = 2017
    y_end = 2026

    # Paso 1: Buscar
    print(f"\n  PASO 1/3: Buscando articulos...")
    articles = search_media_articles(medio_key, keyword, y_start, y_end)
    saved = save_articles_to_db(articles, medio_key, keyword, y_start, y_end)

    # Paso 2: Clasificar (maximo 30 para el demo)
    print(f"\n  PASO 2/3: Clasificando sentimiento con Claude Haiku...")
    classified = analyze_pending_articles(limit=30)

    # Paso 3: Reporte
    print(f"\n  PASO 3/3: Generando reporte...")
    generate_report(medio_key=medio_key, keyword=keyword)


def run_full_pipeline(
    medios: Optional[List[str]] = None,
    keyword: str = "INTRANT",
    year_start: int = 2017,
    year_end: int = 2026,
    classify_limit: int = 100,
):
    """
    Pipeline completo: buscar -> clasificar -> reportar.
    Para uso programatico (no interactivo).
    """
    if medios is None:
        medios = ["diariolibre"]

    # Buscar
    for medio_key in medios:
        articles = search_media_articles(medio_key, keyword, year_start, year_end)
        save_articles_to_db(articles, medio_key, keyword, year_start, year_end)

    # Clasificar
    analyze_pending_articles(limit=classify_limit)

    # Reportar
    generate_report(keyword=keyword)


# ─── Utilidades ──────────────────────────────────────────────────────────────

def show_db_stats():
    """Muestra estadisticas generales de la base de datos de NeuroData."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT COUNT(*) as total FROM nd_media_articles")
    total_articles = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) as total FROM nd_sentiment_analysis")
    total_classified = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) as total FROM nd_media_searches")
    total_searches = cur.fetchone()["total"]

    cur.execute("""
        SELECT medio_key, keyword, COUNT(*) as total
        FROM nd_media_articles
        GROUP BY medio_key, keyword
        ORDER BY total DESC
    """)
    breakdown = cur.fetchall()

    print(f"\n  NEURODATA — Estado de la Base de Datos")
    print(f"  " + "-" * 40)
    print(f"    Busquedas realizadas:    {total_searches}")
    print(f"    Articulos almacenados:   {total_articles}")
    print(f"    Sentimiento clasificado: {total_classified}")
    print(f"    Pendientes:              {total_articles - total_classified}")

    if breakdown:
        print(f"\n  Desglose:")
        for row in breakdown:
            nombre = MEDIOS_RD.get(row["medio_key"], {}).get("nombre", row["medio_key"])
            print(f"    {nombre:<25} | {row['keyword']:<20} | {row['total']:>5} articulos")

    cur.close()
    conn.close()


# ─── CLI ─────────────────────────────────────────────────────────────────────

def print_usage():
    print("""
  NEURODATA — Laboratorio de Inteligencia Mediatica
  NeuroNoticia Group

  Uso:
    python3 media_analyzer.py <comando>

  Comandos:
    setup     Crear tablas en PostgreSQL
    search    Buscar articulos (modo interactivo)
    analyze   Clasificar sentimiento de articulos pendientes
    report    Generar reporte con datos existentes
    full      Pipeline completo (buscar + clasificar + reportar)
    demo      Demo rapido: INTRANT en Diario Libre 2017-2026
    stats     Mostrar estadisticas de la base de datos
    help      Mostrar esta ayuda

  Ejemplos:
    python3 media_analyzer.py setup
    python3 media_analyzer.py demo
    python3 media_analyzer.py report

  Variables de entorno requeridas:
    DATABASE_URL      (auto-inyectada por Railway)
    SERPER_API_KEY    (configurada en Railway)
    ANTHROPIC_API_KEY (configurada en Railway)
""")


def main():
    if len(sys.argv) < 2:
        print_usage()
        return

    command = sys.argv[1].lower()

    if command == "setup":
        setup_database()

    elif command == "search":
        run_search_interactive()

    elif command == "analyze":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        analyze_pending_articles(limit=limit)

    elif command == "report":
        medio = sys.argv[2] if len(sys.argv) > 2 else None
        keyword = sys.argv[3] if len(sys.argv) > 3 else None
        generate_report(medio_key=medio, keyword=keyword)

    elif command == "full":
        run_full_pipeline()

    elif command == "demo":
        run_demo()

    elif command == "stats":
        show_db_stats()

    elif command == "help":
        print_usage()

    else:
        print(f"  Comando desconocido: '{command}'")
        print_usage()


if __name__ == "__main__":
    main()
