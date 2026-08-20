from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

from .config import StudyConfig


class NarrativeAnalyzer:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("NEURODATA_OPENAI_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._client = None

    def _client_instance(self):
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    @staticmethod
    def _extract_json(text: str) -> Dict:
        text = text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    def analyze(self, study: StudyConfig, record: Dict) -> Dict:
        body = (record.get("text") or "")[:7000]
        title = (record.get("title") or "")[:800]
        system = """Eres NeuroData, un analista de inteligencia mediática y narrativa en República Dominicana.
Analiza evidencia observable. No inventes hechos ni atribuyas intenciones. Diferencia sentimiento general de postura hacia el objetivo. No infieras género, etnia, edad, religión u otros atributos sensibles. Devuelve SOLO JSON válido."""
        user = f"""ESTUDIO: {study.title}
OBJETIVO ANALIZADO: {study.target}
PAÍS: {study.country}
NARRATIVAS DE INTERÉS: {', '.join(study.narratives) or 'descubrirlas'}
ACTORES DE INTERÉS: {', '.join(study.actors) or 'descubrirlos'}
PREGUNTAS: {' | '.join(study.questions)}
FUENTE: {record.get('source_type')} / {record.get('source_name')}
TÍTULO: {title}
CONTENIDO: {body}

Devuelve este esquema:
{{
  "relevance_score": 0.0,
  "sentiment": "positivo|negativo|neutral|mixto",
  "stance": "favorable|critico|neutral|incierto",
  "tone": "informativo|elogio|critica|denuncia|preocupacion|sarcasmo|pregunta|movilizacion|otro",
  "narratives": [{{"name":"...","score":0.0}}],
  "actors": ["..."],
  "claims": [{{"claim":"...","needs_verification":true}}],
  "emotions": ["..."],
  "summary": "máximo 2 oraciones",
  "evidence_terms": ["frases o conceptos breves presentes en la evidencia"]
}}
"""
        response = self._client_instance().chat.completions.create(
            model=self.model,
            temperature=0,
            max_tokens=700,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        parsed = self._extract_json(response.choices[0].message.content or "{}")
        enriched = dict(record)
        enriched["analysis"] = parsed
        enriched["analysis_model"] = self.model
        return enriched

    def analyze_many(self, study: StudyConfig, records: List[Dict], limit: int | None = None) -> List[Dict]:
        selected = records[:limit] if limit else records
        return [self.analyze(study, record) for record in selected]
