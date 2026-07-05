"""
NeuroDiario - Agrupador de noticias por similaridad (deduplicación de publicación)

MÓDULO NUEVO Y SEPARADO. No modifica el pipeline actual.

Objetivo:
    De los muchos artículos crudos que entran al día (a menudo la misma noticia
    contada por varias fuentes), agruparlos en "clusters" — cada cluster es una
    noticia única cubierta por N fuentes. Luego se priorizan los clusters que
    aparecen en más fuentes (señal de tendencia) y se toman los mejores.

Método:
    TF-IDF (scikit-learn) + similaridad de coseno sobre (título + resumen).
    Ligero: solo lee title y summary, no carga raw_content ni raw_html.

Esta primera versión SOLO REPORTA lo que agruparía. No genera ni publica nada.
Así puedes verificar que agrupa bien antes de conectarlo al pipeline.

Uso:
    python deduplicator_clusters.py                → analiza últimas 24h
    python deduplicator_clusters.py --horas 12     → analiza últimas 12h
    python deduplicator_clusters.py --top 20       → muestra top 20 clusters
"""

import argparse
import logging
from collections import defaultdict
from datetime import datetime, timedelta

logging.basicConfig(level=logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# ── Parámetros ajustables ──
# Umbral de similaridad de coseno para considerar dos noticias "la misma".
# Más alto = agrupa solo casi-idénticos. Más bajo = agrupa más agresivo.
# Con datos reales (151 artículos), 0.18 formaba clusters gigantes por
# representantes "pegajosos". 0.30-0.35 rompe eso manteniendo duplicados reales.
# Ajustar tras probar: si agrupa cosas distintas, súbelo; si separa duplicados, bájalo.
SIMILARITY_THRESHOLD = 0.32

# Tope de seguridad: ningún cluster real de noticias debería tener más de esto.
# Si un cluster supera este tamaño, es señal de representante pegajoso y se
# desarma (cada artículo queda solo). Evita el cluster-basura de 85 artículos.
MAX_CLUSTER_SIZE = 8

# Stopwords en español para que el TF-IDF ignore palabras vacías comunes
# (sin esto, "de/la/el" inflan la similaridad con ruido).
STOPWORDS_ES = [
    "de", "la", "el", "los", "las", "en", "y", "a", "que", "del", "se", "un",
    "una", "por", "para", "con", "su", "sus", "al", "lo", "como", "mas", "más",
    "esta", "este", "esto", "estos", "estas", "o", "e", "ni", "pero", "sino",
    "le", "les", "me", "te", "nos", "es", "son", "fue", "ser", "ha", "han",
    "hay", "tras", "sobre", "entre", "desde", "hasta", "durante", "segun", "según",
]

# Cuántos clusters mostrar por defecto
DEFAULT_TOP = 20

# Ventana de tiempo por defecto (horas hacia atrás)
DEFAULT_HORAS = 24


def _cargar_articulos(horas: int):
    """
    Lee artículos crudos recientes: solo id, title, summary, source_id, url.
    Ligero a propósito — no toca raw_content ni raw_html.
    Solo artículos que aún NO tienen un GeneratedArticle asociado
    (es decir, los que todavía no se han publicado).
    """
    from neurodiario.db.database import get_db
    from neurodiario.db.models import Article, GeneratedArticle, Source

    corte = datetime.utcnow() - timedelta(hours=horas)
    articulos = []
    fuentes = {}

    with get_db() as db:
        # Mapa de fuentes id -> nombre
        fuentes = {s.id: s.name for s in db.query(Source).all()}

        # IDs de artículos ya generados (para excluirlos)
        ya_generados = set(
            r[0] for r in db.query(GeneratedArticle.source_article_id)
            .filter(GeneratedArticle.source_article_id != None)  # noqa: E711
            .all()
        )

        filas = (
            db.query(Article.id, Article.title, Article.summary,
                     Article.source_id, Article.url, Article.category)
            .filter(Article.fetched_at >= corte)
            .all()
        )

        for art_id, title, summary, source_id, url, category in filas:
            if art_id in ya_generados:
                continue
            articulos.append({
                "id": art_id,
                "title": title or "",
                "summary": summary or "",
                "source_id": source_id,
                "source_name": fuentes.get(source_id, "(sin fuente)"),
                "url": url or "",
                "category": category or "general",
            })

    return articulos, fuentes


def _texto_comparacion(art: dict) -> str:
    """Combina título y resumen para vectorizar. El título pesa más (se repite)."""
    titulo = art["title"]
    resumen = art["summary"]
    # Repetir el título le da más peso en el TF-IDF
    return f"{titulo} {titulo} {resumen}".strip()


def _agrupar(articulos, umbral):
    """
    Agrupa artículos por similaridad de coseno usando TF-IDF.
    Devuelve lista de clusters; cada cluster es una lista de artículos.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    if len(articulos) < 2:
        return [[a] for a in articulos]

    textos = [_texto_comparacion(a) for a in articulos]

    # TF-IDF con stopwords en español básicas
    vectorizer = TfidfVectorizer(
        lowercase=True,
        max_df=0.85,        # ignora palabras en >85% de docs (muy comunes)
        min_df=1,
        ngram_range=(1, 2), # unigramas y bigramas (capta "santo domingo")
        stop_words=STOPWORDS_ES,  # ignora palabras vacías en español
    )
    try:
        matriz = vectorizer.fit_transform(textos)
    except ValueError:
        # vocabulario vacío (textos muy cortos); no agrupar
        return [[a] for a in articulos]

    sim = cosine_similarity(matriz)

    n = len(articulos)
    visitado = [False] * n
    clusters = []

    for i in range(n):
        if visitado[i]:
            continue
        # Nuevo cluster: i es el REPRESENTANTE.
        # Los demás entran solo si se parecen AL REPRESENTANTE (i),
        # no a cualquier miembro. Esto evita las cadenas gigantes
        # (A~B, B~C, C~D... arrastrando artículos inconexos).
        grupo = [i]
        visitado[i] = True
        for j in range(i + 1, n):
            if not visitado[j] and sim[i][j] >= umbral:
                grupo.append(j)
                visitado[j] = True

        # Tope de seguridad: si el cluster creció demasiado, el representante
        # es "pegajoso" (título genérico que se parece a todo). En ese caso
        # desarmamos el grupo — cada artículo queda como su propio cluster.
        if len(grupo) > MAX_CLUSTER_SIZE:
            for k in grupo:
                clusters.append([articulos[k]])
        else:
            clusters.append([articulos[k] for k in grupo])

    return clusters


def _medio_base(source_name: str) -> str:
    """
    Reduce el nombre de fuente a su medio base.
    'Diario Libre - Politica', 'Diario Libre - Deportes' -> 'Diario Libre'.
    Así las secciones del mismo periódico cuentan como UN solo medio.
    """
    if not source_name:
        return "(sin fuente)"
    # Cortar en el primer " - " (separador de sección)
    return source_name.split(" - ")[0].strip()


def _fuentes_distintas(cluster):
    """
    Cuenta cuántos MEDIOS distintos cubren un cluster.
    Las secciones del mismo periódico (Diario Libre - X) cuentan como uno.
    """
    return len(set(_medio_base(a["source_name"]) for a in cluster if a["source_id"]))


def analizar(horas: int, top: int, umbral: float):
    print("\n" + "=" * 70)
    print("  AGRUPADOR DE NOTICIAS — Análisis (solo reporte, no publica)")
    print(f"  Ventana: últimas {horas}h | Umbral similaridad: {umbral} | Top: {top}")
    print("=" * 70)

    articulos, fuentes = _cargar_articulos(horas)
    print(f"\n  Artículos sin publicar en la ventana: {len(articulos)}")

    if not articulos:
        print("  (Nada que agrupar — la base está vacía o todo ya fue generado.)")
        print("=" * 70 + "\n")
        return

    clusters = _agrupar(articulos, umbral)

    # Ordenar: primero los de más fuentes distintas, luego los de más artículos
    clusters.sort(key=lambda c: (_fuentes_distintas(c), len(c)), reverse=True)

    total_clusters = len(clusters)
    con_varias_fuentes = sum(1 for c in clusters if _fuentes_distintas(c) >= 2)

    print(f"  Noticias únicas detectadas (clusters): {total_clusters}")
    print(f"  De esas, cubiertas por 2+ fuentes:     {con_varias_fuentes}")
    print(f"  Reducción: {len(articulos)} artículos → {total_clusters} noticias únicas")

    print("\n" + "-" * 70)
    print(f"  TOP {top} CLUSTERS (por número de fuentes que los cubren)")
    print("-" * 70)

    for idx, cluster in enumerate(clusters[:top], 1):
        n_fuentes = _fuentes_distintas(cluster)
        n_arts = len(cluster)
        # El título representativo: el del primer artículo del cluster
        titulo = cluster[0]["title"][:60]
        cat = cluster[0]["category"]
        nombres_fuentes = sorted(set(_medio_base(a["source_name"]) for a in cluster))

        marca = "🔥" if n_fuentes >= 2 else "  "
        print(f"\n  {marca} [{idx}] {titulo}")
        print(f"       Categoría: {cat} | {n_fuentes} fuente(s), {n_arts} artículo(s)")
        if n_fuentes >= 2:
            print(f"       Fuentes: {', '.join(nombres_fuentes)}")

    print("\n" + "=" * 70)
    print(f"  Con el pipeline conectado, se generarían los primeros {top} clusters,")
    print(f"  cada uno como UN artículo que sintetiza sus fuentes.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agrupador de noticias por similaridad")
    parser.add_argument("--horas", type=int, default=DEFAULT_HORAS, help="Ventana en horas hacia atrás")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP, help="Cuántos clusters mostrar")
    parser.add_argument("--umbral", type=float, default=SIMILARITY_THRESHOLD, help="Umbral de similaridad 0-1")
    args = parser.parse_args()

    analizar(horas=args.horas, top=args.top, umbral=args.umbral)
