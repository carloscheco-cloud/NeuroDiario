from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterable, List


def output_root() -> Path:
    return Path(os.getenv("NEURODATA_OUTPUT_DIR", "data/neurodata"))


def study_dir(slug: str) -> Path:
    path = output_root() / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def merge_records(path: Path, incoming: Iterable[Dict], key: str = "id") -> int:
    existing = read_jsonl(path)
    by_id = {str(row.get(key)): row for row in existing if row.get(key)}
    added = 0
    for row in incoming:
        row_id = str(row.get(key, ""))
        if not row_id:
            continue
        if row_id not in by_id:
            added += 1
        by_id[row_id] = row
    write_jsonl(path, by_id.values())
    return added
