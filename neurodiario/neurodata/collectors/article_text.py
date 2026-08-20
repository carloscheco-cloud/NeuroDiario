from __future__ import annotations

import re
import time
from typing import Dict, Iterable, List

import requests
from bs4 import BeautifulSoup


class ArticleTextEnricher:
    """Enriquece registros de prensa con el texto visible del artículo.

    Solo trabaja con URLs públicas ya descubiertas por el estudio. Si una página
    bloquea el acceso, requiere autenticación o no puede extraerse con fiabilidad,
    conserva el snippet original y registra el fallo sin interrumpir el lote.
    """

    def __init__(self, delay: float = 0.8, timeout: int = 20, max_chars: int = 18000):
        self.delay = delay
        self.timeout = timeout
        self.max_chars = max_chars
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; NeuroData/1.0; "
                "+https://neurodiario.com)"
            )
        })

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"\s+", " ", text or " ").strip()
        return text

    def _extract(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        for node in soup(["script", "style", "noscript", "svg", "form", "nav", "footer", "aside"]):
            node.decompose()

        candidates: List[str] = []
        article = soup.find("article")
        if article:
            candidates = [self._clean(p.get_text(" ", strip=True)) for p in article.find_all("p")]

        text = " ".join(p for p in candidates if len(p) >= 30)
        if len(text) < 500:
            selectors = [
                "main p",
                "[itemprop='articleBody'] p",
                ".article-body p",
                ".entry-content p",
                ".post-content p",
                ".story-body p",
                ".content-body p",
            ]
            paragraphs: List[str] = []
            for selector in selectors:
                nodes = soup.select(selector)
                if nodes:
                    paragraphs = [self._clean(n.get_text(" ", strip=True)) for n in nodes]
                    joined = " ".join(p for p in paragraphs if len(p) >= 30)
                    if len(joined) >= 500:
                        text = joined
                        break

        if len(text) < 500:
            paragraphs = [self._clean(p.get_text(" ", strip=True)) for p in soup.find_all("p")]
            text = " ".join(p for p in paragraphs if len(p) >= 40)

        return self._clean(text)[: self.max_chars]

    def enrich_record(self, record: Dict) -> Dict:
        if record.get("source_type") != "media_article" or not record.get("url"):
            return record
        if record.get("full_text_chars", 0) >= 500:
            return record

        enriched = dict(record)
        enriched.setdefault("search_snippet", record.get("text", ""))
        try:
            response = self.session.get(record["url"], timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type.lower():
                raise ValueError(f"unsupported content type: {content_type}")
            text = self._extract(response.text)
            if len(text) < 300:
                raise ValueError("article body too short")
            enriched["text"] = text
            enriched["full_text_chars"] = len(text)
            enriched["text_source"] = "public_article_page"
            enriched["enrichment_status"] = "ok"
        except Exception as exc:
            enriched["full_text_chars"] = len(enriched.get("text", "") or "")
            enriched["text_source"] = "serper_snippet"
            enriched["enrichment_status"] = "failed"
            enriched["enrichment_error"] = str(exc)[:300]
        finally:
            time.sleep(self.delay)
        return enriched

    def enrich_many(self, records: Iterable[Dict], limit: int | None = None) -> List[Dict]:
        output: List[Dict] = []
        processed = 0
        for record in records:
            if limit is not None and processed >= limit:
                output.append(record)
                continue
            if record.get("source_type") == "media_article" and record.get("url"):
                output.append(self.enrich_record(record))
                processed += 1
            else:
                output.append(record)
        return output
