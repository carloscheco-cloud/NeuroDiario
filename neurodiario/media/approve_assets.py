"""
Aprueba o desaprueba assets multimedia por filtros.

Uso:
  python -m neurodiario.media.approve_assets --provider neurodiario.com --execute
  python -m neurodiario.media.approve_assets --topic politica --limit 20 --execute
  python -m neurodiario.media.approve_assets --all-pending --limit 50
"""

import argparse
from datetime import datetime

from neurodiario.db.database import get_db
from neurodiario.db.models import MediaAsset


def approve_assets(
    *,
    provider=None,
    topic=None,
    all_pending=False,
    limit=50,
    execute=False,
):
    with get_db() as db:
        query = db.query(MediaAsset).filter(
            MediaAsset.is_active == True,  # noqa: E712
            MediaAsset.is_approved == False,  # noqa: E712
        )

        if provider:
            query = query.filter(MediaAsset.source_provider == provider)

        if topic:
            query = query.filter(MediaAsset.topic == topic)

        if not provider and not topic and not all_pending:
            raise SystemExit("ERROR: usa --provider, --topic o --all-pending")

        assets = (
            query.order_by(
                MediaAsset.source_provider.asc(),
                MediaAsset.id.desc(),
            )
            .limit(limit)
            .all()
        )

        for asset in assets:
            print(
                f"{asset.id} | provider={asset.source_provider} | "
                f"topic={asset.topic} | approved={asset.is_approved} | "
                f"{(asset.context or '')[:90]}"
            )

            if execute:
                asset.is_approved = True
                asset.updated_at = datetime.utcnow()

        print("RESULTADO")
        print(f"matched={len(assets)}")
        print(f"updated={len(assets) if execute else 0}")

        if not execute:
            print("Modo simulación. Para aprobar usa --execute")


def main():
    parser = argparse.ArgumentParser(description="Aprobar media_assets por lote")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--topic", default=None)
    parser.add_argument("--all-pending", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    approve_assets(
        provider=args.provider,
        topic=args.topic,
        all_pending=args.all_pending,
        limit=args.limit,
        execute=args.execute,
    )


if __name__ == "__main__":
    main()
