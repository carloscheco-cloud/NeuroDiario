from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class StudyConfig:
    slug: str
    client: str
    title: str
    target: str
    country: str = "República Dominicana"
    period_start: str = "2015-01-01"
    period_end: str = field(default_factory=lambda: date.today().isoformat())
    search_terms: List[str] = field(default_factory=list)
    narratives: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    sources: Dict[str, Any] = field(default_factory=dict)
    report: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        errors: List[str] = []
        for name in ("slug", "client", "title", "target", "period_start", "period_end"):
            if not getattr(self, name):
                errors.append(f"{name} is required")
        if not self.search_terms:
            errors.append("search_terms must contain at least one term")
        try:
            start = date.fromisoformat(self.period_start)
            end = date.fromisoformat(self.period_end)
            if start > end:
                errors.append("period_start must be <= period_end")
        except ValueError:
            errors.append("period_start and period_end must use YYYY-MM-DD")
        return errors

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "StudyConfig":
        study = payload.get("study", payload)
        return cls(
            slug=study.get("slug", ""),
            client=study.get("client", ""),
            title=study.get("title", ""),
            target=study.get("target", study.get("client", "")),
            country=study.get("country", "República Dominicana"),
            period_start=study.get("period_start", "2015-01-01"),
            period_end=study.get("period_end", date.today().isoformat()),
            search_terms=list(payload.get("search_terms", study.get("search_terms", []))),
            narratives=list(payload.get("narratives", [])),
            actors=list(payload.get("actors", [])),
            questions=list(payload.get("questions", [])),
            sources=dict(payload.get("sources", {})),
            report=dict(payload.get("report", {})),
        )


def load_study(path: str | Path) -> StudyConfig:
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        config = StudyConfig.from_dict(json.load(fh))
    errors = config.validate()
    if errors:
        raise ValueError("Invalid study config: " + "; ".join(errors))
    return config
