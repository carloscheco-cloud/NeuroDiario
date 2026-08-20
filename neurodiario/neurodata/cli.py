from __future__ import annotations

import argparse
import json

from .config import load_study
from .pipeline import NeuroDataPipeline


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="NeuroData reusable narrative intelligence engine")
    p.add_argument("--study", required=True, help="Path to study JSON configuration")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("validate")
    collect = sub.add_parser("collect")
    collect.add_argument("--sources", default="media,youtube")

    enrich = sub.add_parser("enrich")
    enrich.add_argument("--limit", type=int)

    sub.add_parser("audit")

    social = sub.add_parser("import-social")
    social.add_argument("--file", required=True)
    social.add_argument("--platform", required=True)
    social.add_argument("--source-url")

    analyze = sub.add_parser("analyze")
    analyze.add_argument("--limit", type=int)

    report = sub.add_parser("report")
    report.add_argument("--tier", choices=["executive", "premium"], default="executive")
    return p


def main() -> int:
    args = parser().parse_args()
    study = load_study(args.study)
    pipeline = NeuroDataPipeline(study)
    if args.command == "validate":
        print(json.dumps({"ok": True, "study": study.slug}, ensure_ascii=False))
    elif args.command == "collect":
        count = pipeline.collect([s.strip() for s in args.sources.split(",") if s.strip()])
        print(f"{count} records added")
    elif args.command == "enrich":
        stats = pipeline.enrich(args.limit)
        print(json.dumps(stats, ensure_ascii=False))
    elif args.command == "audit":
        audit = pipeline.audit()
        compact = {
            "study": audit["study"],
            "total": audit["total"],
            "usable": audit["usable"],
            "review": audit["review"],
            "by_year": audit["by_year"],
            "review_records": audit["review_records"],
        }
        print(json.dumps(compact, ensure_ascii=False, indent=2))
    elif args.command == "import-social":
        count = pipeline.import_social(args.file, args.platform, args.source_url)
        print(f"{count} social records added")
    elif args.command == "analyze":
        count = pipeline.analyze(args.limit)
        print(f"{count} records analyzed")
    elif args.command == "report":
        print(pipeline.report(args.tier))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
