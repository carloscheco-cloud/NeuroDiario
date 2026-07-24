"""
Importa imágenes existentes de articles.image_url hacia media_assets.

No descarga imágenes.
No sube imágenes a WordPress.
No toca publicaciones.
Solo registra URLs ya conocidas como activos multimedia reutilizables.
"""

import argparse
from urllib.parse import urlparse

from neurodiario.db.database import get_db
from neurodiario.db.models import Article, MediaAsset


def detect_provider(url: str) -> str:
    netloc = urlparse(url or "").netloc.lower()

    if "diariolibre.com" in netloc:
        return "diario_libre"
    if "elnacional.com.do" in netloc:
        return "el_nacional"
    if "n.com.do" in netloc:
        return "n_digital"
    if "bbc.co.uk" in netloc or "bbci.co.uk" in netloc:
        return "bbc"
    if "elpais.com" in netloc:
        return "el_pais"
    if "asmedia" in netloc or "as.com" in netloc:
        return "as"

    return netloc or "unknown"


def import_existing_images(limit: int = 200, dry_run: bool = True) -> dict:
    stats = {
        "scanned": 0,
        "inserted": 0,
        "skipped_existing": 0,
        "skipped_empty": 0,
    }

    with get_db() as db:
        articles = (
            db.query(Article)
            .filter(Article.image_url.isnot(None))
            .order_by(Article.id.desc())
            .limit(limit)
            .all()
        )

        for article in articles:
            stats["scanned"] += 1

            image_url = (article.image_url or "").strip()
            if not image_url:
                stats["skipped_empty"] += 1
                continue

            exists = (
                db.query(MediaAsset.id)
                .filter(MediaAsset.source_url == image_url)
                .first()
            )

            if exists:
                stats["skipped_existing"] += 1
                continue

            provider = detect_provider(image_url)

            asset = MediaAsset(
                entity_name=None,
                entity_type=None,
                topic=article.category or "general",
                context=article.title,
                media_type="image",
                usage_type="featured_image",
                source_provider=provider,
                source_url=image_url,
                wordpress_media_id=None,
                wordpress_url=None,
                priority=40,
                quality_score=0.0,
                is_active=True,
                is_approved=False,
                notes=f"Importado desde Article ID {article.id}",
                extra_metadata={
                    "article_id": article.id,
                    "article_title": article.title,
                    "article_url": article.url,
                    "import_source": "articles.image_url",
                },
            )

            if dry_run:
                print(f"DRY_RUN insertaría: article_id={article.id} provider={provider} url={image_url[:120]}")
            else:
                db.add(asset)
                stats["inserted"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Importar imágenes existentes a media_assets")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--execute", action="store_true", help="Ejecuta inserción real. Sin esto solo simula.")
    args = parser.parse_args()

    stats = import_existing_images(
        limit=args.limit,
        dry_run=not args.execute,
    )

    print("RESULTADO")
    for key, value in stats.items():
        print(f"{key}={value}")

    if not args.execute:
        print("Modo simulación. Para insertar usa --execute")


if __name__ == "__main__":
    main()
