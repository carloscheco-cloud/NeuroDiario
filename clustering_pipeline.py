"""
NeuroDiario - Pipeline de publicación con CLUSTERING (deduplicación)

MÓDULO NUEVO Y SEPARADO. No modifica el publishing_pipeline existente.

Flujo:
  1. Agrupa los artículos crudos recientes en clusters (deduplicator_clusters).
  2. Ordena los clusters por: primero multi-medio (tendencias), luego por
     prioridad de categoría (política > sociedad > economía > internacional > ...).
  3. Toma los N mejores (por defecto 25).
  4. Para cada cluster, lee el raw_content de sus artículos y llama a
     create_article() del generador (que sintetiza varias fuentes en UNO).
  5. Publica en WordPress y registra el GeneratedArticle, marcando TODOS los
     artículos del cluster como usados (para que no se re-procesen).

Se activa/desactiva con el feature flag USE_CLUSTERING. Con False, no hace nada
(sigues usando tu publishing_pipeline normal).

Uso manual (prueba, no publica hasta poner --publicar):
    python clustering_pipeline.py            → simula: muestra qué generaría
    python clustering_pipeline.py --publicar → genera y publica de verdad
"""

import argparse
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ── Feature flag ──
USE_CLUSTERING = True

# ── Parámetros ──
MAX_ARTICULOS_POR_CICLO = 20
VENTANA_HORAS = 24

# Prioridad de categorías (menor número = más prioritaria)
PRIORIDAD_CATEGORIA = {
    "politica": 1,
    "sociedad": 2,
    "economia": 3,
    "internacional": 4,
    "deportes": 5,
    "salud": 6,
    "tecnologia": 7,
    "cultura": 8,
    "educacion": 9,
    "general": 10,
}


def _prioridad_cat(categoria: str) -> int:
    return PRIORIDAD_CATEGORIA.get((categoria or "general").lower(), 99)


def _ordenar_clusters(clusters):
    """
    Ordena los clusters para publicación:
      1. Más medios distintos primero (tendencias reales arriba).
      2. Dentro de eso, por prioridad de categoría.
      3. Dentro de eso, clusters más grandes primero.
    """
    from deduplicator_clusters import _fuentes_distintas

    def clave(cluster):
        n_medios = _fuentes_distintas(cluster)
        cat = cluster[0]["category"]
        return (-n_medios, _prioridad_cat(cat), -len(cluster))

    return sorted(clusters, key=clave)


def _cargar_raw_content(article_ids):
    """
    Lee el raw_content SOLO de los artículos que vamos a publicar.
    Devuelve {id: raw_content}. Ligero: solo los ~25 clusters elegidos.
    """
    from neurodiario.db.database import get_db
    from neurodiario.db.models import Article

    contenidos = {}
    with get_db() as db:
        filas = (
            db.query(Article.id, Article.raw_content, Article.clean_content)
            .filter(Article.id.in_(article_ids))
            .all()
        )
        for art_id, raw, clean in filas:
            contenidos[art_id] = clean or raw or ""
    return contenidos


def procesar(publicar: bool = False):
    if not USE_CLUSTERING:
        logger.info("Clustering desactivado (USE_CLUSTERING=False). Nada que hacer.")
        return 0

    from deduplicator_clusters import _cargar_articulos, _agrupar, _fuentes_distintas, _medio_base, SIMILARITY_THRESHOLD
    from neurodiario.config.settings import settings
    from neurodiario.generator.article_generator import ArticleGenerator

    modo = "PUBLICAR" if publicar else "SIMULACIÓN (no publica)"
    print("\n" + "=" * 70)
    print("  PIPELINE DE PUBLICACIÓN CON CLUSTERING")
    print(f"  Modo: {modo} | Umbral: {SIMILARITY_THRESHOLD} | Máx: {MAX_ARTICULOS_POR_CICLO}")
    print("=" * 70)

    # 1. Cargar y agrupar
    articulos, _ = _cargar_articulos(VENTANA_HORAS)
    if not articulos:
        print("  Sin artículos para procesar.")
        return 0

    clusters = _agrupar(articulos, SIMILARITY_THRESHOLD)
    clusters = _ordenar_clusters(clusters)
    seleccionados = clusters[:MAX_ARTICULOS_POR_CICLO]

    print(f"\n  {len(articulos)} artículos → {len(clusters)} clusters")
    print(f"  Se procesarán los {len(seleccionados)} mejores.\n")

    if not publicar:
        # Solo mostrar qué se generaría
        for idx, c in enumerate(seleccionados, 1):
            n_medios = _fuentes_distintas(c)
            medios = ", ".join(sorted(set(_medio_base(a["source_name"]) for a in c)))
            marca = "🔥" if n_medios >= 2 else "  "
            print(f"  {marca} [{idx}] ({c[0]['category']}) {c[0]['title'][:55]}")
            print(f"       {n_medios} medio(s), {len(c)} art.: {medios}")
        print("\n  (Simulación — no se generó ni publicó nada.)")
        print(f"  Para publicar de verdad: python clustering_pipeline.py --publicar")
        print("=" * 70 + "\n")
        return 0

    # 2. Publicar de verdad
    generator = ArticleGenerator(api_key=settings.CLAUDE_API_KEY, model=settings.CLAUDE_MODEL)
    from neurodiario.publisher.wordpress_publisher import WordPressPublisher
    publisher = WordPressPublisher(
        url=settings.WORDPRESS_URL,
        username=settings.WORDPRESS_USER,
        password=settings.WORDPRESS_PASSWORD,
    )

    publicados = 0
    for idx, cluster in enumerate(seleccionados, 1):
        try:
            article_ids = [a["id"] for a in cluster]
            contenidos = _cargar_raw_content(article_ids)

            # Armar el trend y la lista de articles que espera create_article
            categoria = cluster[0]["category"]
            topic = cluster[0]["title"]
            articles_para_gen = []
            for a in cluster:
                articles_para_gen.append({
                    "title": a["title"],
                    "url": a["url"],
                    "source": _medio_base(a["source_name"]),
                    "raw_content": contenidos.get(a["id"], ""),
                })

            trend = {"topic": topic, "category": categoria}

            logger.info(f"[{idx}/{len(seleccionados)}] Generando: {topic[:60]}")
            generated = generator.create_article(trend, articles_para_gen)

            # Publicar en WordPress como publish (no draft)
            wp_article = {
                "title": generated["title"],
                "content": generated["content"],
                "categories": [categoria.title()],
                "tags": generated.get("tags", []),
                "status": "publish",
                "image_url": generated.get("image_url"),
            }
            post_id = publisher.publish(wp_article)

            if post_id:
                _registrar_generado(generated, categoria, article_ids, post_id)
                publicados += 1
                logger.info(f"  ✓ Publicado en WordPress (ID {post_id})")
            else:
                logger.error(f"  ✗ Falló publicación en WordPress")

        except Exception as e:
            logger.error(f"  ✗ Error en cluster {idx}: {e}", exc_info=True)

    print(f"\n  ✓ Publicados: {publicados}/{len(seleccionados)}")
    print("=" * 70 + "\n")
    return publicados


def _registrar_generado(generated, categoria, article_ids, wp_post_id):
    """
    Registra el GeneratedArticle y marca TODOS los artículos del cluster
    como usados (asocia el primero como source_article_id principal).
    Esto evita que los artículos del cluster se vuelvan a procesar.
    """
    from neurodiario.db.database import get_db
    from neurodiario.db.models import GeneratedArticle

    with get_db() as db:
        # Un GeneratedArticle por cluster; source_article_id = primer artículo.
        record = GeneratedArticle(
            title=generated["title"],
            content=generated["content"],
            category=categoria,
            tags=generated.get("tags", []),
            status="published",
            wordpress_post_id=wp_post_id,
            source_article_id=article_ids[0],
            published_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(record)
        db.flush()

        # Marcar los DEMÁS artículos del cluster como usados creando registros
        # ligeros que los excluyen del futuro (status='clustered').
        for extra_id in article_ids[1:]:
            dup = GeneratedArticle(
                title="[agrupado en otro artículo]",
                content="",
                category=categoria,
                status="clustered",
                source_article_id=extra_id,
                created_at=datetime.utcnow(),
            )
            db.add(dup)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--publicar", action="store_true", help="Generar y publicar de verdad")
    args = parser.parse_args()
    procesar(publicar=args.publicar)
