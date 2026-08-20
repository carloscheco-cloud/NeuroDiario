from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List

from .config import StudyConfig


def _pct(n: int, total: int) -> str:
    return f"{(n / total * 100):.1f}%" if total else "0.0%"


def summarize(records: List[Dict]) -> Dict:
    analyzed = [r for r in records if isinstance(r.get("analysis"), dict)]
    sentiment = Counter(r["analysis"].get("sentiment", "unknown") for r in analyzed)
    stance = Counter(r["analysis"].get("stance", "unknown") for r in analyzed)
    narratives = Counter()
    actors = Counter()
    by_source = Counter(r.get("source_type", "unknown") for r in analyzed)
    by_name = Counter(r.get("source_name", "unknown") for r in analyzed)
    for row in analyzed:
        for item in row["analysis"].get("narratives", []):
            if isinstance(item, dict) and item.get("name"):
                narratives[item["name"]] += 1
        actors.update(a for a in row["analysis"].get("actors", []) if a)
    return {
        "total_records": len(records),
        "analyzed_records": len(analyzed),
        "sentiment": dict(sentiment),
        "stance": dict(stance),
        "narratives": narratives.most_common(20),
        "actors": actors.most_common(20),
        "source_types": dict(by_source),
        "source_names": by_name.most_common(20),
    }


def _table(rows: List[List[str]]) -> str:
    if not rows:
        return ""
    head, rest = rows[0], rows[1:]
    out = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    out.extend("| " + " | ".join(map(str, row)) + " |" for row in rest)
    return "\n".join(out)


def render_executive(study: StudyConfig, records: List[Dict]) -> str:
    s = summarize(records)
    total = s["analyzed_records"]
    narratives = [["Narrativa", "Menciones", "% evidencia"]] + [[n, str(c), _pct(c, total)] for n, c in s["narratives"][:5]]
    actors = [["Actor", "Menciones"]] + [[n, str(c)] for n, c in s["actors"][:8]]
    sentiment = [["Sentimiento", "Registros", "%"]] + [[k, str(v), _pct(v, total)] for k, v in sorted(s["sentiment"].items(), key=lambda x: -x[1])]
    questions = "\n".join(f"- {q}" for q in study.questions)
    return f"""# NeuroData Executive Brief
## {study.title}

**Cliente potencial / objetivo:** {study.client}  
**País:** {study.country}  
**Período:** {study.period_start} — {study.period_end}  
**Registros recolectados:** {s['total_records']}  
**Registros analizados:** {total}

> Este documento mide conversación pública observable en las fuentes recolectadas. No es una encuesta representativa de toda la población dominicana.

## 1. Termómetro de la conversación

{_table(sentiment)}

## 2. Cinco narrativas dominantes

{_table(narratives)}

## 3. Actores con mayor presencia

{_table(actors)}

## 4. Fuentes del estudio

{_table([["Tipo de fuente", "Registros"]] + [[k, str(v)] for k, v in s['source_types'].items()])}

## 5. Preguntas que guía NeuroData

{questions}

## 6. Lo que reserva el estudio Premium

- Evolución temporal detallada y eventos que cambian la conversación.
- Mapa de narrativas favorables, críticas y emergentes.
- Mapa de actores y amplificación por fuente.
- Claims que requieren verificación documental.
- Comparación medios vs. conversación ciudadana.
- Radio/audio y transcripción selectiva cuando exista acceso legítimo a las fuentes.
- Señales de licencia social, riesgo reputacional y oportunidades de comunicación.
- Anexo de evidencia trazable por URL, fecha y fuente.
"""


def render_premium(study: StudyConfig, records: List[Dict]) -> str:
    s = summarize(records)
    executive = render_executive(study, records)
    claims = []
    for row in records:
        for claim in (row.get("analysis") or {}).get("claims", []):
            if claim.get("claim"):
                claims.append((claim["claim"], bool(claim.get("needs_verification")), row.get("url")))
    claim_rows = [["Claim detectado", "Verificar", "Fuente"]] + [[c, "Sí" if v else "No", u or ""] for c, v, u in claims[:40]]
    source_rows = [["Fuente / canal", "Registros"]] + [[n, str(c)] for n, c in s["source_names"]]
    return executive + f"""

---
# Análisis Premium

## 7. Cobertura por fuente / canal

{_table(source_rows)}

## 8. Narrativas ampliadas

{_table([["Narrativa", "Menciones"]] + [[n, str(c)] for n, c in s['narratives'][:20]])}

## 9. Actores ampliados

{_table([["Actor", "Menciones"]] + [[n, str(c)] for n, c in s['actors'][:20]])}

## 10. Claims detectados para verificación

{_table(claim_rows)}

## 11. Evidencia y metodología

Cada hallazgo debe poder rastrearse al registro fuente conservado en el dataset JSONL del estudio. La clasificación es asistida por IA y debe revisarse antes de publicación comercial cuando implique reputación, cumplimiento, acusaciones o decisiones de alto impacto.
"""


def write_report(path: Path, content: str, summary: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.with_suffix(".summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
