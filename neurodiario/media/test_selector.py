"""
Prueba manual del selector multimedia.

Uso:
  python -m neurodiario.media.test_selector --topic politica
  python -m neurodiario.media.test_selector --entity "Luis Abinader"
"""

import argparse
from pprint import pprint

from neurodiario.media.selector import select_featured_image


def main():
    parser = argparse.ArgumentParser(description="Probar selector de media_assets")
    parser.add_argument("--entity", default=None)
    parser.add_argument("--topic", default=None)
    parser.add_argument("--mark-used", action="store_true")
    args = parser.parse_args()

    result = select_featured_image(
        entity_name=args.entity,
        topic=args.topic,
        mark_used=args.mark_used,
    )

    if not result:
        print("NO_MATCH")
        return

    pprint(result)


if __name__ == "__main__":
    main()
