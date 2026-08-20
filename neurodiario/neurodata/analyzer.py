from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .config import StudyConfig


_ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
        "sentiment": {"type": "string", "enum": ["positivo", "negativo", "neutral", "mixto"]},
        "stance": {"type": "string", "enum": ["favorable", "critico", "neutral", "incierto"]},
        "tone": {
            "type": "string",
            "enum": ["informativo", "elogio", "critica", "denuncia", "preocupacion", "sarcasmo", "pregunta", "movilizacion", "otro"],
        },
        "narratives": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "score": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["name", "score"],
            },
        },
        "actors": {"type": "array", "items": {"type": "string"}},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "claim": {"type": "string"},
                    "needs_verification": {"type": "boolean"},
                },
                "required": ["claim", "needs_verification"],
            },
        },
        "emotions": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
        "evidence_terms": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "relevance_score", "sentiment", "stance", "tone", "narratives",
        "actors", "claims", "emotions", "summary", "evidence_terms",
    ],
}


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

    def analyze(self, study: StudyConfig, record: Dict) -> Dict:
        body = (record.get("text") or "")[:12000]
        title = (record.get("title") or "")[:800]
        instructions = (
            "Eres NeuroData, un analista de inteligencia mediática y narrativa en República Dominicana. "
            "Analiza solamente evidencia observable. No inventes hechos ni atribuyas intenciones. "
            "Diferencia sentimiento general de postura hacia el objetivo. No infieras atributos sensibles. "
            "La relevancia debe medir qué tan directamente trata la evidencia sobre el objetivo del estudio. "
            "Si la pieza es ajena al objetivo, asigna relevance_score bajo y no fuerces narrativas."
        )
        prompt = f"""ESTUDIO: {study.title}
OBJETIVO ANALIZADO: {study.target}
PAÍS: {study.country}
NARRATIVAS DE INTERÉS: {', '.join(study.narratives) or 'descubrirlas'}
ACTORES DE INTERÉS: {', '.join(study.actors) or 'descubrirlos'}
PREGUNTAS: {' | '.join(study.questions)}
FUENTE: {record.get('source_type')} / {record.get('source_name')}
FECHA: {record.get('published_at')}
TÍTULO: {title}
CONTENIDO: {body}
"""
        response = self._client_instance().responses.create(
            model=self.model,
            instructions=instructions,
            input=prompt,
            max_output_tokens=1000,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "neurodata_narrative_analysis",
                    "strict": True,
                    "schema": _ANALYSIS_SCHEMA,
                }
            },
        )
        parsed = json.loads(response.output_text or "{}")
        enriched = dict(record)
        enriched["analysis"] = parsed
        enriched["analysis_model"] = self.model
        enriched["analysis_api"] = "responses"
        enriched["analysis_version"] = "neurodata-v1.1"
        return enriched

    def analyze_many(self, study: StudyConfig, records: List[Dict], limit: int | None = None) -> List[Dict]:
        selected = records[:limit] if limit else records
        return [self.analyze(study, record) for record in selected]
