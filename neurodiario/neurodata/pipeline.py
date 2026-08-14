from __future__ import annotations

from pathlib import Path
from typing import List

from .analyzer import NarrativeAnalyzer
from .collectors import SerperCollector, YouTubeCollector
from .config import StudyConfig
from .reporting import render_executive, render_premium, summarize, write_report
from .social_import import import_social_file
from .storage import merge_records, read_jsonl, study_dir, write_jsonl


class NeuroDataPipeline:
    def __init__(self, study: StudyConfig):
        self.study = study
        self.directory = study_dir(study.slug)
        self.raw_path = self.directory / "records.raw.jsonl"
        self.analyzed_path = self.directory / "records.analyzed.jsonl"

    def collect(self, sources: List[str] | None = None) -> int:
        sources = sources or ["media", "youtube"]
        records = []
        if "media" in sources:
            records.extend(SerperCollector().collect(self.study))
        if "youtube" in sources:
            records.extend(YouTubeCollector().collect(self.study))
        return merge_records(self.raw_path, records)

    def import_social(self, path: str, platform: str, source_url: str | None = None) -> int:
        rows = import_social_file(path, self.study.slug, platform, source_url)
        return merge_records(self.raw_path, rows)

    def analyze(self, limit: int | None = None) -> int:
        raw = read_jsonl(self.raw_path)
        existing = {r.get("id"): r for r in read_jsonl(self.analyzed_path)}
        pending = [r for r in raw if r.get("id") not in existing]
        if limit:
            pending = pending[:limit]
        if not pending:
            return 0
        analyzer = NarrativeAnalyzer()
        for record in pending:
            analyzed = analyzer.analyze(self.study, record)
            existing[record["id"]] = analyzed
            write_jsonl(self.analyzed_path, existing.values())
        return len(pending)

    def report(self, tier: str = "executive") -> Path:
        records = read_jsonl(self.analyzed_path)
        if tier == "premium":
            content = render_premium(self.study, records)
            filename = "report.premium.md"
        else:
            content = render_executive(self.study, records)
            filename = "report.executive.md"
        path = self.directory / filename
        write_report(path, content, summarize(records))
        return path
