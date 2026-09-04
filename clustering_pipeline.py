"""
NeuroDiario - Pipeline de publicación con CLUSTERING (deduplicación)

MÓDULO NUEVO Y SEPARADO. No modifica el publishing_pipeline existente.

Flujo:
  1. Agrupa los artículos crudos recientes en clusters (deduplicator_clusters).
  2. Ordena los clusters por: primero multi-medio (tendencias), luego por
     prioridad de categoría (política > sociedad > economía > internacional > ...).
  3. Revisa un pool ampliado de candidatos (por defecto 24) para poder completar
     una tanda final de 12 sin exceder 5 imágenes genéricas de NeuroDiario.
  4. Para cada cluster, lee el raw_content de sus artículos y llama a
     create_article() del generador (que sintetiza varias fuentes en UNO).
  5. Publica en WordPress y registra el GeneratedArticle, marcando TODOS los
     artículos del cluster como usados (para que no se re-procesen).

Regla visual de tanda:
  - BATCH_SIZE = 12 noticias objetivo.
  - MAX_GENERIC_IMAGES = 5 imágenes genéricas de marca como máximo.
  - Una nota luctuosa con plantilla de memoria NO cuenta como genérica.
  - Si se alcanza el límite de 5 genéricas, se siguen revisando candidatos del
    pool hasta encontrar noticias con imagen real. Si no hay suficientes, se
    publica una tanda menor antes que violar el límite.

Se activa/desactiva con el feature flag USE_CLUSTERING. Con False, no hace nada
(sigues usando tu publishing_pipeline normal).

Uso manual (prueba, no publica hasta poner --publicar):
    python clustering_pipeline.py            → simula: muestra qué evaluaría
    python clustering_pipeline.py --publicar → genera y publica de verdad
"""

import argparse
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ── Feature flag ──
USE_CLUSTERING = True

# ── Parámetros de tanda ──
BATCH_SIZE = 12
MAX_GENERIC_IMAGES = 5
CANDIDATE_POOL_SIZE = 24
VENTANA_HORAS = 24

# Compatibilidad con referencias antiguas del módulo.
MAX_ARTICULOS_POR_CICLO = BATCH_SIZE

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
    Lee el raw_content SOLO de los artículos que vamos a evaluar/publicar.
    Devuelve {id: raw_content}.
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


def _es_generica_de_marca(generated: dict, topic: str, sources_text: str) -> bool:
    """Determina si la imagen elegida consume uno de los 5 cupos genéricos.

    El generador marca las imágenes de marca con ``image_is_branded``. Las
    plantillas luctuosas también son de marca, pero son una pieza editorial
    específica y no deben consumir el cupo de imágenes genéricas.
    """
    if not generated.get("image_is_branded", False):
        return False

    try:
        from neurodiario.generator.article_generator import es_nota_luctuosa

        if es_nota_luctuosa(topic, sources_text):
            return False
    except Exception as exc:
        logger.warning("No se pudo validar si la nota es luctuosa: %s", exc)

    return True


def procesar(publicar: bool = False):
    if not USE_CLUSTERING:
        logger.info("Clustering desactivado (USE_CLUSTERING=False). Nada que hacer.")
        return 0

    from deduplicator_clusters import (
        _cargar_articulos,
        _agrupar,
        _fuentes_distintas,
        _medio_base,
        SIMILARITY_THRESHOLD,
    )
    from neurodiario.config.settings import settings
    from neurodiario.generator.article_generator import ArticleGenerator

    modo = "PUBLICAR" if publicar else "SIMULACIÓN (no publica)"
    print("\n" + "=" * 70)
    print("  PIPELINE DE PUBLICACIÓN CON CLUSTERING")
    print(
        f"  Modo: {modo} | Umbral: {SIMILARITY_THRESHOLD} | "
        f"Tanda: {BATCH_SIZE} | Máx genéricas: {MAX_GENERIC_IMAGES} | "
        f"Pool: {CANDIDATE_POOL_SIZE}"
    )
    print("=" * 70)

    # 1. Cargar y agrupar
    articulos, _ = _cargar_articulos(VENTANA_HORAS)
    if not articulos:
        print("  Sin artículos para procesar.")
        return 0

    clusters = _agrupar(articulos, SIMILARITY_THRESHOLD)
    clusters = _ordenar_clusters(clusters)
    candidatos = clusters[:CANDIDATE_POOL_SIZE]

    print(f"\n  {len(articulos)} artículos → {len(clusters)} clusters")
    print(
        f"  Se evaluarán hasta {len(candidatos)} candidatos para completar "
        f"{BATCH_SIZE} publicaciones con <= {MAX_GENERIC_IMAGES} genéricas.\n"
    )

    if not publicar:
        # Solo mostrar el pool que se evaluaría.
        for idx, c in enumerate(candidatos, 1):
            n_medios = _fuentes_distintas(c)
            medios = ", ".join(sorted(set(_medio_base(a["source_name"]) for a in c)))
            marca = "🔥" if n_medios >= 2 else "  "
            print(f"  {marca} [{idx}] ({c[0]['category']}) {c[0]['title'][:55]}")
            print(f"       {n_medios} medio(s), {len(c)} art.: {medios}")
        print("\n  (Simulación — no se generó ni publicó nada.)")
        print("  La cuota visual se aplica después de resolver la imagen de cada candidato.")
        print("  Para publicar de verdad: python clustering_pipeline.py --publicar")
        print("=" * 70 + "\n")
        return 0

    # 2. Publicar de verdad con cuota global de imágenes genéricas.
    generator = ArticleGenerator(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
    from neurodiario.publisher.wordpress_publisher import WordPressPublisher

    publisher = WordPressPublisher(
        url=settings.WORDPRESS_URL,
        username=settings.WORDPRESS_USER,
        password=settings.WORDPRESS_PASSWORD,
    )

    publicados = 0
    genericas_publicadas = 0
    reales_publicadas = 0
    luctuosas_marca = 0
    omitidas_por_cuota = 0
    evaluados = 0

    for idx, cluster in enumerate(candidatos, 1):
        if publicados >= BATCH_SIZE:
            break

        try:
            evaluados += 1
            article_ids = [a["id"] for a in cluster]
            contenidos = _cargar_raw_content(article_ids)

            # Armar el trend y la lista de articles que espera create_article.
            categoria = cluster[0]["category"]
            topic = cluster[0]["title"]
            articles_para_gen = []
            for a in cluster:
                articles_para_gen.append(
                    {
                        "title": a["title"],
                        "url": a["url"],
                        "source": _medio_base(a["source_name"]),
                        "raw_content": contenidos.get(a["id"], ""),
                    }
                )

            trend = {"topic": topic, "category": categoria}

            logger.info(
                "[%s/%s | publicados %s/%s] Generando: %s",
                idx,
                len(candidatos),
                publicados,
                BATCH_SIZE,
                topic[:60],
            )
            generated = generator.create_article(trend, articles_para_gen)

            sources_text = generator._format_sources(articles_para_gen[:5])
            es_generica = _es_generica_de_marca(generated, topic, sources_text)

            # Si ya consumimos los 5 cupos genéricos, este candidato se omite y
            # se continúa con el siguiente del pool buscando una imagen real.
            if es_generica and genericas_publicadas >= MAX_GENERIC_IMAGES:
                omitidas_por_cuota += 1
                logger.warning(
                    "  ⏭ Cuota visual: se omite candidato con imagen genérica "
                    "(%s/%s ya usadas). Se busca reemplazo con imagen real.",
                    genericas_publicadas,
                    MAX_GENERIC_IMAGES,
                )
                continue

            # Publicar en WordPress como publish (no draft).
            image_url = generated.get("image_url")
            image_candidates = generated.get("image_candidates", []) or []
            if image_url and image_url not in image_candidates:
                image_candidates.insert(0, image_url)

            # Media Engine para clustering: usa imagen aprobada si el flag está activo.
            if getattr(settings, "MEDIA_ENGINE_USE_FEATURED", False):
                try:
                    from neurodiario.media.selector import select_featured_image

                    media_asset = select_featured_image(
                        entity_name=None,
                        topic=categoria,
                        mark_used=True,
                    )

                    if media_asset:
                        media_url = media_asset.get("wordpress_url") or media_asset.get("source_url")
                        media_id = media_asset.get("wordpress_media_id")

                        if media_id:
                            generated["image_media_id"] = media_id
                            image_url = None
                            logger.info(
                                "  🧠 Media Engine activo: usando WP media_id %s para categoría %s",
                                media_id,
                                categoria,
                            )
                        elif media_url:
                            image_url = media_url
                            image_candidates = [
                                media_url,
                                *[c for c in image_candidates if c != media_url],
                            ]
                            logger.info(
                                "  🧠 Media Engine activo: usando URL aprobada id=%s categoría=%s",
                                media_asset.get("id"),
                                categoria,
                            )
                    else:
                        logger.info("  🧠 Media Engine activo: sin imagen aprobada para %s", categoria)
                except Exception as media_error:
                    logger.warning(
                        "  ⚠ Media Engine falló; se conserva imagen normal: %s",
                        media_error,
                    )
            else:
                logger.info("  🧠 Media Engine activo: OFF")

            wp_article = {
                "title": generated["title"],
                "content": generated["content"],
                "categories": [categoria.title()],
                "tags": generated.get("tags", []),
                "status": "publish",
                "image_url": image_url,
                "image_candidates": image_candidates,
                "image_media_id": generated.get("image_media_id"),
            }
            post_id = publisher.publish(wp_article)

            if post_id:
                _registrar_generado(generated, categoria, article_ids, post_id)
                publicados += 1

                if es_generica:
                    genericas_publicadas += 1
                    tipo_imagen = "GENÉRICA"
                else:
                    # Las luctuosas de marca son específicas y no consumen la cuota.
                    if generated.get("image_is_branded", False):
                        luctuosas_marca += 1
                        tipo_imagen = "MARCA-ESPECÍFICA"
                    else:
                        reales_publicadas += 1
                        tipo_imagen = "REAL"

                logger.info(
                    "  ✓ Publicado en WordPress (ID %s) | imagen=%s | "
                    "balance real=%s genérica=%s/%s marca-específica=%s",
                    post_id,
                    tipo_imagen,
                    reales_publicadas,
                    genericas_publicadas,
                    MAX_GENERIC_IMAGES,
                    luctuosas_marca,
                )
            else:
                logger.error("  ✗ Falló publicación en WordPress")

        except Exception as e:
            logger.error("  ✗ Error en cluster %s: %s", idx, e, exc_info=True)

    # Resumen inequívoco para revisar mañana en logs.
    summary = (
        f"IMAGE_BATCH_SUMMARY target={BATCH_SIZE} published={publicados} "
        f"real={reales_publicadas} generic={genericas_publicadas} "
        f"brand_specific={luctuosas_marca} skipped_generic={omitidas_por_cuota} "
        f"evaluated={evaluados} pool={len(candidatos)}"
    )
    logger.info(summary)

    print(f"\n  ✓ Publicados: {publicados}/{BATCH_SIZE}")
    print(
        f"  Imágenes: {reales_publicadas} reales | "
        f"{genericas_publicadas} genéricas (máx {MAX_GENERIC_IMAGES}) | "
        f"{luctuosas_marca} marca-específica"
    )
    if omitidas_por_cuota:
        print(f"  Reemplazos buscados: {omitidas_por_cuota} candidato(s) genérico(s) omitido(s)")
    if publicados < BATCH_SIZE:
        logger.warning(
            "Tanda incompleta: %s/%s. Se respetó el máximo de %s genéricas; "
            "faltaron candidatos con imagen no genérica en el pool.",
            publicados,
            BATCH_SIZE,
            MAX_GENERIC_IMAGES,
        )
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
