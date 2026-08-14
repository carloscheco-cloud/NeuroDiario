from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _normalize(rows: Iterable[Dict], study_slug: str, platform: str, source_url: str | None) -> List[Dict]:
    output: List[Dict] = []
    for index, row in enumerate(rows):
        text = str(row.get("text") or row.get("comment") or row.get("comentario") or "").strip()
        if not text:
            continue
        author = str(row.get("author") or row.get("user") or "").strip()
        raw_id = str(row.get("id") or f"{source_url or platform}:{index}:{text[:120]}")
        output.append({
            "id": _hash(raw_id),
            "study": study_slug,
            "source_type": "social_comment",
            "platform": platform,
            "source_name": row.get("source_name") or platform,
            "url": row.get("url") or source_url,
            "title": row.get("title") or "",
            "text": text,
            "published_at": row.get("published_at") or row.get("date"),
            "like_count": row.get("like_count") or row.get("likes") or 0,
            "author_hash": _hash(author) if author else None,
        })
    return output


def import_social_file(path: str | Path, study_slug: str, platform: str, source_url: str | None = None) -> List[Dict]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("comments", [])
    elif suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
    elif suffix in {".txt", ".md"}:
        rows = [{"text": line.strip()} for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        raise ValueError("Supported social imports: .json, .csv, .txt, .md")
    return _normalize(rows, study_slug, platform, source_url)
