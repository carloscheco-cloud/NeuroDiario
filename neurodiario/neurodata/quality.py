from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

from .config import StudyConfig


_NON_ARTICLE_TITLE_PATTERNS = [
    re.compile(r"^noticias\s+del\s+\d", re.I),
    re.compile(r"^noticias\s+de\s+", re.I),
    re.compile(r"^domingo,\s+\d", re.I),
    re.compile(r"^lunes,\s+\d", re.I),
    re.compile(r"^martes,\s+\d", re.I),
    re.compile(r"^miercoles,\s+\d", re.I),
    re.compile(r"^miércoles,\s+\d", re.I),
    re.compile(r"^jueves,\s+\d", re.I),
    re.compile(r"^viernes,\s+\d", re.I),
    re.compile(r"^sabado,\s+\d", re.I),
    re.compile(r"^sábado,\s+\d", re.I),
]


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value).strip().lower()


def _year(record: Dict) -> str:
    candidates = [record.get("published_at") or "", record.get("url") or ""]
    for candidate in candidates:
        match = re.search(r"\b(20\d{2}|19\d{2})\b", candidate)
        if match:
            return match.group(1)
    return "unknown"


def audit_record(study: StudyConfig, record: Dict) -> Dict:
    title = record.get("title") or ""
    evidence = " ".join(
        part
        for part in [title, record.get("text") or "", record.get("search_snippet") or ""]
        if part
    )
    normalized = _normalize(evidence)
    term_hits = [term for term in study.search_terms if _normalize(term) in normalized]

    flags: List[str] = []
    if record.get("source_type") == "media_article":
        if record.get("enrichment_status") == "failed":
            flags.append("full_text_unavailable")
        if int(record.get("full_text_chars") or len(record.get("text") or "")) < 300:
            flags.append("short_evidence")
        if any(pattern.search(title.strip()) for pattern in _NON_ARTICLE_TITLE_PATTERNS):
            flags.append("non_article_landing")
    if not term_hits:
        flags.append("no_search_term_in_evidence")

    review_flags = {"non_article_landing", "no_search_term_in_evidence"}
    status = "review" if any(flag in review_flags for flag in flags) else "usable"

    return {
        "id": record.get("id"),
        "source_name": record.get("source_name"),
        "source_type": record.get("source_type"),
        "title": title,
        "url": record.get("url"),
        "published_at": record.get("published_at"),
        "year": _year(record),
        "full_text_chars": int(record.get("full_text_chars") or len(record.get("text") or "")),
        "term_hits": term_hits,
        "flags": flags,
        "qa_status": status,
    }


def audit_records(study: StudyConfig, records: Iterable[Dict]) -> Dict:
    rows = [audit_record(study, record) for record in records]
    by_year = Counter(row["year"] for row in rows)
    by_status = Counter(row["qa_status"] for row in rows)
    by_source = Counter(row.get("source_name") or "unknown" for row in rows)
    review = [row for row in rows if row["qa_status"] == "review"]
    return {
        "study": study.slug,
        "total": len(rows),
        "usable": by_status.get("usable", 0),
        "review": by_status.get("review", 0),
        "by_year": dict(sorted(by_year.items())),
        "by_source": dict(sorted(by_source.items())),
        "review_records": review,
    }


def write_audit(path: Path, audit: Dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
