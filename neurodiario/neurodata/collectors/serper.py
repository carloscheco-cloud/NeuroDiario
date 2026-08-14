from __future__ import annotations

import hashlib
import os
import time
from datetime import date
from typing import Dict, Iterable, List, Tuple

import requests

from ..config import StudyConfig

DEFAULT_MEDIA = {
    "Diario Libre": "diariolibre.com",
    "Listín Diario": "listindiario.com",
    "El Caribe": "elcaribe.com.do",
    "Hoy": "hoy.com.do",
    "Acento": "acento.com.do",
    "El Nuevo Diario": "elnuevodiario.com.do",
    "N Digital": "ndigital.com.do",
    "CDN": "cdn.com.do",
    "Noticias SIN": "noticiassin.com",
    "El Día": "eldia.com.do",
}


def _month_windows(start: date, end: date, months: int) -> Iterable[Tuple[date, date]]:
    cursor = start
    while cursor <= end:
        total = cursor.year * 12 + cursor.month - 1 + months
        next_date = date(total // 12, total % 12 + 1, 1)
        window_end = min(end, date.fromordinal(next_date.toordinal() - 1))
        yield cursor, window_end
        cursor = next_date


def _record_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


class SerperCollector:
    endpoint = "https://google.serper.dev/search"

    def __init__(self, api_key: str | None = None, delay: float = 1.0):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")
        self.delay = delay

    def _search(self, query: str, num: int = 10) -> Dict:
        if not self.api_key:
            raise RuntimeError("SERPER_API_KEY is not configured")
        response = requests.post(
            self.endpoint,
            headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
            json={"q": query, "gl": "do", "hl": "es", "num": min(num, 10)},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def build_query(domain: str, terms: List[str], start: date, end: date) -> str:
        term_expr = " OR ".join(f'"{term}"' for term in terms)
        return f"site:{domain} ({term_expr}) after:{start.isoformat()} before:{end.isoformat()}"

    def collect(self, study: StudyConfig) -> List[Dict]:
        cfg = study.sources.get("media", {})
        if cfg is False or cfg.get("enabled", True) is False:
            return []
        domains = cfg.get("domains", DEFAULT_MEDIA)
        months = int(cfg.get("window_months", 6))
        max_queries = int(cfg.get("max_queries", 300))
        results_per_query = int(cfg.get("results_per_query", 10))
        start = date.fromisoformat(study.period_start)
        end = date.fromisoformat(study.period_end)
        records: List[Dict] = []
        query_count = 0

        for media_name, domain in domains.items():
            for window_start, window_end in _month_windows(start, end, months):
                if query_count >= max_queries:
                    return records
                query = self.build_query(domain, study.search_terms, window_start, window_end)
                payload = self._search(query, num=results_per_query)
                query_count += 1
                for item in payload.get("organic", []):
                    url = item.get("link", "").strip()
                    if not url:
                        continue
                    text = " ".join(filter(None, [item.get("title", ""), item.get("snippet", "")]))
                    records.append({
                        "id": _record_id(url),
                        "study": study.slug,
                        "source_type": "media_article",
                        "platform": "web",
                        "source_name": media_name,
                        "domain": domain,
                        "url": url,
                        "title": item.get("title", ""),
                        "text": item.get("snippet", ""),
                        "published_at": item.get("date"),
                        "search_query": query,
                        "matched_terms": [t for t in study.search_terms if t.lower() in text.lower()],
                    })
                time.sleep(self.delay)
        return records
