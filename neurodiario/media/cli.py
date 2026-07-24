"""
CLI interna para administrar Media Intelligence Engine.

Uso:
  python -m neurodiario.media.cli add --entity "Luis Abinader" --wp-url "https://..."
  python -m neurodiario.media.cli find --entity "Luis Abinader"
  python -m neurodiario.media.cli list
"""

import argparse

from neurodiario.db.database import get_db
from neurodiario.db.models import MediaAsset
from neurodiario.media.library import register_media_asset, find_best_asset


def cmd_add(args):
    asset = register_media_asset(
        entity_name=args.entity,
        entity_type=args.entity_type,
        topic=args.topic,
        context=args.context,
        media_type=args.media_type,
        usage_type=args.usage_type,
        source_provider=args.provider,
        source_url=args.source_url,
        wordpress_media_id=args.wp_id,
        wordpress_url=args.wp_url,
        priority=args.priority,
        quality_score=args.quality,
        is_approved=args.approved,
        notes=args.notes,
    )
    print(f"OK asset_id={asset.id} entity={asset.entity_name} wp_url={asset.wordpress_url}")


def cmd_find(args):
    asset = find_best_asset(
        entity_name=args.entity,
        topic=args.topic,
        media_type=args.media_type,
        usage_type=args.usage_type,
        approved_only=not args.include_unapproved,
    )

    if not asset:
        print("NO_MATCH")
        return

    print(f"id={asset.id}")
    print(f"entity_name={asset.entity_name}")
    print(f"entity_type={asset.entity_type}")
    print(f"topic={asset.topic}")
    print(f"media_type={asset.media_type}")
    print(f"usage_type={asset.usage_type}")
    print(f"wordpress_media_id={asset.wordpress_media_id}")
    print(f"wordpress_url={asset.wordpress_url}")
    print(f"priority={asset.priority}")
    print(f"quality_score={asset.quality_score}")
    print(f"usage_count={asset.usage_count}")
    print(f"is_approved={asset.is_approved}")


def cmd_list(args):
    with get_db() as db:
        query = db.query(MediaAsset).order_by(MediaAsset.id.desc())

        if args.entity:
            query = query.filter(MediaAsset.entity_name.ilike(f"%{args.entity.strip()}%"))

        rows = query.limit(args.limit).all()

        for asset in rows:
            print(
                f"{asset.id} | {asset.entity_name} | {asset.entity_type} | "
                f"{asset.media_type} | {asset.usage_type} | "
                f"approved={asset.is_approved} | uses={asset.usage_count} | "
                f"wp_id={asset.wordpress_media_id} | {asset.wordpress_url}"
            )


def main():
    parser = argparse.ArgumentParser(description="Media Intelligence Engine CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add")
    add.add_argument("--entity", required=True)
    add.add_argument("--entity-type", default="persona")
    add.add_argument("--topic", default=None)
    add.add_argument("--context", default=None)
    add.add_argument("--media-type", default="image")
    add.add_argument("--usage-type", default="featured_image")
    add.add_argument("--provider", default="manual")
    add.add_argument("--source-url", default=None)
    add.add_argument("--wp-id", type=int, default=None)
    add.add_argument("--wp-url", required=True)
    add.add_argument("--priority", type=int, default=50)
    add.add_argument("--quality", type=float, default=0.0)
    add.add_argument("--approved", action="store_true")
    add.add_argument("--notes", default=None)
    add.set_defaults(func=cmd_add)

    find = sub.add_parser("find")
    find.add_argument("--entity", default=None)
    find.add_argument("--topic", default=None)
    find.add_argument("--media-type", default="image")
    find.add_argument("--usage-type", default="featured_image")
    find.add_argument("--include-unapproved", action="store_true")
    find.set_defaults(func=cmd_find)

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--entity", default=None)
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
