"""
Sincroniza imágenes aprobadas del Media Engine hacia la librería de WordPress.

Uso seguro:
  python -m neurodiario.media.sync_to_wordpress --limit 5

Uso real:
  python -m neurodiario.media.sync_to_wordpress --limit 5 --execute
"""

import argparse
import mimetypes
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests

from neurodiario.config.settings import settings
from neurodiario.db.database import get_db
from neurodiario.db.models import MediaAsset


def _filename_from_url(url: str, asset_id: int) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name or f"media_asset_{asset_id}.jpg"
    name = name.split("?")[0].strip()

    if "." not in name:
        name = f"{name}.jpg"

    return name[:140]


def _download_image(url: str, asset_id: int) -> tuple[str, str]:
    headers = {
        "User-Agent": "NeuroDiario Media Engine/1.0",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }

    response = requests.get(url, headers=headers, timeout=25)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()

    if not content_type.startswith("image/"):
        raise ValueError(f"URL no devolvió imagen. content-type={content_type}")

    filename = _filename_from_url(url, asset_id)
    suffix = Path(filename).suffix or mimetypes.guess_extension(content_type) or ".jpg"

    fd, tmp_path = tempfile.mkstemp(prefix=f"nd_media_{asset_id}_", suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(response.content)

    return tmp_path, filename


def _upload_to_wordpress(file_path: str, filename: str, title: str) -> tuple[int, str]:
    wp_base = settings.WORDPRESS_URL.rstrip("/")
    endpoint = f"{wp_base}/wp-json/wp/v2/media"

    content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": content_type,
    }

    with open(file_path, "rb") as f:
        response = requests.post(
            endpoint,
            headers=headers,
            data=f,
            auth=(settings.WORDPRESS_USER, settings.WORDPRESS_PASSWORD),
            timeout=40,
        )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"WordPress rechazó media upload: {response.status_code} {response.text[:300]}"
        )

    payload = response.json()
    return payload.get("id"), payload.get("source_url")


def sync(limit: int = 5, execute: bool = False) -> int:
    updated = 0

    with get_db() as db:
        assets = (
            db.query(MediaAsset)
            .filter(MediaAsset.is_active == True)
            .filter(MediaAsset.is_approved == True)
            .filter(MediaAsset.wordpress_media_id.is_(None))
            .filter(MediaAsset.source_url.isnot(None))
            .order_by(MediaAsset.usage_count.asc(), MediaAsset.id.desc())
            .limit(limit)
            .all()
        )

        print(f"assets_found={len(assets)} execute={execute}")

        for asset in assets:
            print(
                f"\nASSET id={asset.id} topic={asset.topic} "
                f"provider={asset.source_provider} url={asset.source_url[:120]}"
            )

            if not execute:
                print("  DRY_RUN: no se descargó ni subió")
                continue

            tmp_path = None
            try:
                tmp_path, filename = _download_image(asset.source_url, asset.id)
                media_id, wp_url = _upload_to_wordpress(
                    tmp_path,
                    filename,
                    asset.context or f"NeuroDiario media asset {asset.id}",
                )

                if not media_id:
                    raise RuntimeError("WordPress no devolvió media ID")

                asset.wordpress_media_id = media_id
                asset.wordpress_url = wp_url
                asset.updated_at = __import__("datetime").datetime.utcnow()
                asset.notes = (asset.notes or "") + " | synced_to_wordpress"
                db.commit()

                updated += 1
                print(f"  OK media_id={media_id} wp_url={wp_url}")

            except Exception as exc:
                db.rollback()
                print(f"  ERROR {exc}")

            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

    print(f"\nupdated={updated}")
    return updated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    sync(limit=args.limit, execute=args.execute)


if __name__ == "__main__":
    main()
