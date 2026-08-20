from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from .config import StudyConfig
from .reporting import DEFAULT_RELEVANCE_THRESHOLD
from .storage import write_jsonl


DEFAULT_SOURCE_QUOTAS = {
    "Diario Libre": 16,
    "Listín Diario": 12,
    "El Nuevo Diario": 12,
    "El Día": 10,
    "El Caribe": 8,
    "Acento": 8,
    "Hoy": 7,
    "CDN": 5,
    "Noticias SIN": 2,
}

NARRATIVE_ALIASES = {
    "seguridad hídrica": "agua y seguridad hídrica",
    "medido ambiente y contaminación": "medio ambiente y contaminación",
    "cuidado del medio ambiente": "medio ambiente y contaminación",
    "oposición a la minería": "oposición y movilización social",
    "inversión y desarrollo económico": "empleo y desarrollo económico",
    "desarrollo económico": "empleo y desarrollo económico",
    "seguridad jurídica": "inversión y seguridad jurídica",
}

ACTOR_ALIASES = {
    "comunidad de San Juan": "comunidades de San Juan",
}


def _year(record: Dict) -> str:
    text = " ".join(str(record.get(k) or "") for k in ("published_at", "url"))
    match = re.search(r"\b(20\d{2}|19\d{2})\b", text)
    return match.group(1) if match else "unknown"


def _score(record: Dict) -> float:
    try:
        return float((record.get("analysis") or {}).get("relevance_score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _rank(records: List[Dict]) -> List[Dict]:
    return sorted(
        records,
        key=lambda row: (
            _score(row),
            int(row.get("full_text_chars") or len(row.get("text") or "")),
            str(row.get("published_at") or ""),
            str(row.get("id") or ""),
        ),
        reverse=True,
    )


def _allocate(counts: Dict[str, int], quota: int) -> Dict[str, int]:
    if not counts or quota <= 0:
        return {}
    total = sum(counts.values())
    if total <= quota:
        return dict(counts)
    raw = {key: quota * value / total for key, value in counts.items()}
    out = {key: min(counts[key], int(raw[key])) for key in counts}
    remaining = quota - sum(out.values())
    order = sorted(
        counts,
        key=lambda key: (raw[key] - int(raw[key]), counts[key], key),
        reverse=True,
    )
    for key in order:
        if remaining <= 0:
            break
        if out[key] < counts[key]:
            out[key] += 1
            remaining -= 1
    return out


def _is_relevant(record: Dict, threshold: float) -> bool:
    return isinstance(record.get("analysis"), dict) and _score(record) >= threshold


def select_signal_sample(
    study: StudyConfig,
    records: List[Dict],
    sample_size: int = 80,
    relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
) -> Tuple[List[Dict], Dict]:
    relevant = [
        row for row in records
        if row.get("source_type") == "media_article" and _is_relevant(row, relevance_threshold)
    ]
    config = (study.report or {}).get("signal_brief", {})
    quotas = config.get("source_quotas") or (
        DEFAULT_SOURCE_QUOTAS if study.slug == "goldquest-proyecto-romero" else {}
    )
    quotas = {str(k): int(v) for k, v in quotas.items() if int(v) > 0}
    if not quotas or sum(quotas.values()) != sample_size:
        source_counts = Counter(row.get("source_name") or "unknown" for row in relevant)
        quotas = _allocate(dict(source_counts), sample_size)

    by_source = defaultdict(list)
    for row in relevant:
        by_source[row.get("source_name") or "unknown"].append(row)

    selected: List[Dict] = []
    selected_ids = set()
    for source, quota in quotas.items():
        pool = by_source.get(source, [])
        if not pool:
            continue
        by_year = defaultdict(list)
        for row in pool:
            by_year[_year(row)].append(row)
        year_alloc = _allocate(
            {year: len(items) for year, items in by_year.items()},
            min(quota, len(pool)),
        )
        source_selected: List[Dict] = []
        for year in sorted(year_alloc):
            source_selected.extend(_rank(by_year[year])[: year_alloc[year]])
        if len(source_selected) < quota:
            used = {row.get("id") for row in source_selected}
            remainder = [row for row in _rank(pool) if row.get("id") not in used]
            source_selected.extend(remainder[: quota - len(source_selected)])
        for row in source_selected:
            if row.get("id") in selected_ids:
                continue
            selected.append(row)
            selected_ids.add(row.get("id"))

    if len(selected) < sample_size:
        remainder = [row for row in _rank(relevant) if row.get("id") not in selected_ids]
        selected.extend(remainder[: sample_size - len(selected)])
    selected = selected[:sample_size]

    metadata = {
        "method": "estratificada_por_medio_y_periodo_priorizando_relevancia",
        "sample_size": len(selected),
        "universe_relevant_media": len(relevant),
        "relevance_threshold": relevance_threshold,
        "source_quotas": quotas,
        "selected_by_source": dict(sorted(Counter(row.get("source_name") or "unknown" for row in selected).items())),
        "selected_by_year": dict(sorted(Counter(_year(row) for row in selected).items())),
    }
    return selected, metadata


def _canon_narrative(name: str) -> str:
    name = (name or "").strip()
    return NARRATIVE_ALIASES.get(name, name)


def _canon_actor(name: str) -> str:
    name = (name or "").strip()
    return ACTOR_ALIASES.get(name, name)


def summarize_signal(records: List[Dict]) -> Dict:
    sentiment = Counter()
    stance = Counter()
    narratives = Counter()
    actors = Counter()
    sources = Counter()
    years = Counter()
    for row in records:
        analysis = row.get("analysis") or {}
        sentiment[analysis.get("sentiment", "unknown")] += 1
        stance[analysis.get("stance", "unknown")] += 1
        sources[row.get("source_name") or "unknown"] += 1
        years[_year(row)] += 1
        narratives.update({
            _canon_narrative(item.get("name"))
            for item in analysis.get("narratives", [])
            if isinstance(item, dict) and item.get("name")
        })
        actors.update({
            _canon_actor(name)
            for name in analysis.get("actors", [])
            if name
        })
    return {
        "sample_size": len(records),
        "sentiment": dict(sentiment),
        "stance": dict(stance),
        "narratives": narratives.most_common(12),
        "actors": actors.most_common(12),
        "sources": dict(sorted(sources.items())),
        "years": dict(sorted(years.items())),
    }


def _pct(value: int, total: int) -> str:
    return f"{(value / total * 100):.1f}%" if total else "0.0%"


def _table(rows: List[List[str]]) -> str:
    head, rest = rows[0], rows[1:]
    out = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    out.extend("| " + " | ".join(map(str, row)) + " |" for row in rest)
    return "\n".join(out)


def _representative_claims(records: List[Dict]) -> List[Dict]:
    output = []
    seen = set()
    for stance in ("critico", "favorable"):
        taken = 0
        for row in [r for r in _rank(records) if (r.get("analysis") or {}).get("stance") == stance]:
            for item in (row.get("analysis") or {}).get("claims", []):
                claim = str(item.get("claim") or "").strip()
                if not claim or claim.lower() in seen:
                    continue
                seen.add(claim.lower())
                output.append({
                    "stance": stance,
                    "claim": claim,
                    "needs_verification": bool(item.get("needs_verification")),
                    "source_name": row.get("source_name"),
                    "published_at": row.get("published_at"),
                    "url": row.get("url"),
                })
                taken += 1
                if taken >= 3:
                    break
            if taken >= 3:
                break
    return output


def render_signal_brief(study: StudyConfig, records: List[Dict], metadata: Dict) -> Tuple[str, Dict]:
    summary = summarize_signal(records)
    total = summary["sample_size"]

    stance_rows = [["Postura hacia el proyecto", "Piezas", "%"]]
    for name, value in sorted(summary["stance"].items(), key=lambda item: -item[1]):
        stance_rows.append([name.capitalize(), str(value), _pct(value, total)])
    sentiment_rows = [["Sentimiento", "Piezas", "%"]]
    for name, value in sorted(summary["sentiment"].items(), key=lambda item: -item[1]):
        sentiment_rows.append([name.capitalize(), str(value), _pct(value, total)])
    narrative_rows = [["Narrativa", "Piezas", "%"]] + [
        [name, str(value), _pct(value, total)] for name, value in summary["narratives"][:6]
    ]
    actor_rows = [["Actor", "Piezas"]] + [[name, str(value)] for name, value in summary["actors"][:7]]
    source_rows = [["Medio", "Piezas"]] + [
        [name, str(value)] for name, value in sorted(summary["sources"].items(), key=lambda item: -item[1])
    ]
    year_rows = [["Año", "Piezas"]] + [[year, str(value)] for year, value in summary["years"].items()]

    claims = _representative_claims(records)
    claim_rows = [["Tipo", "Claim observado", "Fuente"]] + [
        [
            "Crítico" if item["stance"] == "critico" else "Favorable",
            item["claim"],
            f"{item['source_name']} · {item['published_at']}",
        ]
        for item in claims
    ]

    top_narratives = [name for name, _ in summary["narratives"][:5]]
    top_actors = [name for name, _ in summary["actors"][:5]]
    critical = summary["stance"].get("critico", 0)
    favorable = summary["stance"].get("favorable", 0)
    neutral = summary["stance"].get("neutral", 0)

    content = f"""# NeuroData Executive Signal Brief
## Proyecto Romero: señales de la narrativa mediática en República Dominicana

**Preparado para:** {study.client}  
**Mercado:** {study.country}  
**Período monitoreado:** {study.period_start} — {study.period_end}  
**Muestra presentada:** {total} piezas periodísticas de alta relevancia

> **Executive Signal Brief** — una lectura de señales. No es todavía el estudio integral de NeuroData.

---

## 1. Cinco señales que merecen atención ejecutiva

**1. Existe una presión crítica material en la cobertura.** En la muestra, {critical} piezas adoptan postura crítica, {favorable} favorable y {neutral} neutral hacia el proyecto.

**2. El centro narrativo no es únicamente “minería sí / minería no”.** Las narrativas de mayor presencia incluyen {", ".join(top_narratives[:3])}.

**3. El argumento económico existe, pero compite con marcos ambientales, sociales e institucionales.** Empleo, inversión y desarrollo aparecen junto a agua, medio ambiente, movilización y confianza.

**4. Proyecto Romero es una conversación multi-actor.** Entre los actores de mayor presencia aparecen {", ".join(top_actors[:4])}.

**5. La señal transversal es la confianza.** La aceptación de claims técnicos o económicos depende de la credibilidad que distintos públicos asignen a empresa, instituciones, autoridades y evidencia científica.

---

## 2. Termómetro de postura

{_table(stance_rows)}

### Sentimiento general de la cobertura

{_table(sentiment_rows)}

> Postura y sentimiento no son lo mismo: una pieza puede utilizar lenguaje neutral y, al mismo tiempo, presentar una posición crítica o favorable hacia el proyecto.

---

## 3. El mapa de tensión narrativa

La cobertura observada puede leerse como una competencia entre dos grandes familias de marcos:

**Riesgo / licencia social**  
Agua · Medio ambiente · Contaminación · Agricultura · Movilización social · Confianza institucional

**Oportunidad / desarrollo**  
Empleo · Inversión · Desarrollo regional · Seguridad jurídica · Participación · Ciencia y mitigación

El hallazgo preliminar no es que una de estas familias haya desaparecido. Es que ambas compiten por definir **qué significa Proyecto Romero**: riesgo para recursos y confianza, o vehículo de desarrollo sujeto a garantías creíbles.

---

## 4. Narrativas con mayor presencia

{_table(narrative_rows)}

> “Mención” significa que la narrativa fue identificada en una pieza; no implica aprobación de esa narrativa por parte del medio.

---

## 5. Actores que ocupan el centro de la conversación

{_table(actor_rows)}

La presencia del Gobierno, GoldQuest, comunidades, autoridades ambientales y organizaciones sociales convierte el tema en una conversación institucional y territorial, no exclusivamente corporativa.

---

## 6. Cobertura de la muestra

### Distribución por medio

{_table(source_rows)}

### Distribución temporal

{_table(year_rows)}

La muestra fue construida para ofrecer una lectura ejecutiva manejable sin agotar el universo de evidencia disponible.

---

## 7. Claims en tensión

{_table(claim_rows)}

Estos claims son **señales narrativas**, no hechos validados por NeuroData. El estudio Premium puede rastrear su frecuencia, origen, amplificación y contraste documental.

---

## 8. Cómo llegó NeuroData a estas conclusiones

Este brief no se construyó a partir de una lectura manual aislada ni de una búsqueda puntual. NeuroData utilizó un flujo reproducible de adquisición, extracción, control de calidad y análisis asistido por inteligencia artificial.

**1. Diseño de búsqueda.** Se definieron términos y variantes relacionadas con GoldQuest y Proyecto Romero, junto con un período de análisis y una lista de medios dominicanos. Las búsquedas se ejecutaron por ventanas temporales para reducir sesgos de recencia.

**2. Descubrimiento automatizado.** Python ejecutó consultas estructuradas sobre Google mediante Serper.dev, combinando términos del estudio con filtros por dominio (`site:`). El objetivo fue identificar URLs públicas potencialmente relevantes.

**3. Scraping y extracción del contenido.** Un módulo propio en Python visitó las páginas públicas recuperadas y extrajo el cuerpo visible de cada artículo usando `requests` y `BeautifulSoup`. El sistema conservó URL, medio, fecha, titular, snippet original y texto completo. Cuando existía una variante pública alternativa, como AMP, podía utilizarse como respaldo. NeuroData no intenta saltar autenticación, paywalls ni controles de acceso.

**4. Control de calidad.** Antes del análisis se identificaron duplicados, páginas de hemeroteca/listado, piezas con evidencia insuficiente y falsos positivos. Las estadísticas excluyen piezas con `relevance_score < {metadata.get('relevance_threshold', 0.5):.2f}`.

**5. Análisis con IA.** La capa de inteligencia utilizó OpenAI Responses API con Structured Outputs para producir una estructura consistente por pieza: relevancia, sentimiento, postura, tono, narrativas, actores, claims, emociones y términos de evidencia. La IA interpreta el texto recolectado; no sustituye la verificación documental.

**6. Muestra de este brief.** Para este Executive Signal Brief se tomó una muestra curada de **{total} piezas periodísticas** de alta relevancia, estratificada por medio y período y priorizando registros con mejor evidencia. Esta muestra forma parte de un universo de monitoreo más amplio que NeuroData conserva para análisis posteriores.

**7. Trazabilidad.** Cada conclusión puede regresar al registro fuente: medio, fecha, URL, texto extraído, versión del análisis y modelo utilizado.

> **Alcance:** esta edición observa únicamente la **capa mediática**. No debe interpretarse como encuesta de opinión pública ni como medición representativa de toda la población dominicana.

---

## 9. Lo que este brief deliberadamente no responde

Este documento muestra **qué señales aparecen en la prensa**. No responde todavía, con la profundidad necesaria:

- qué piensa la conversación ciudadana frente a lo publicado por los medios;
- qué videos y comentarios de YouTube amplifican o contradicen esas narrativas;
- qué programas de radio y comunicadores están moviendo el tema;
- cuáles narrativas están creciendo semana a semana;
- dónde existen brechas entre el discurso de GoldQuest, el discurso institucional y las preocupaciones sociales;
- qué claims se repiten, quién los origina y qué tan verificables son;
- qué actores funcionan como amplificadores, puentes o focos de riesgo.

---

## 10. NeuroData Premium: de señales a inteligencia accionable

**Executive Signal Brief** responde: **¿qué estamos viendo?**

**NeuroData Premium Narrative Intelligence** responde: **¿por qué está ocurriendo, quién lo impulsa, dónde está el riesgo y qué oportunidades de comunicación existen?**

La siguiente capa incorpora:

**Prensa completa + YouTube + comentarios en redes sociales + radio + evolución temporal + actores + claims + amplificación + riesgo reputacional + oportunidades de comunicación.**

Y una capa continua puede convertir el estudio en **NeuroData Radar**, un sistema de monitoreo para detectar cambios de volumen, narrativa y amplificación antes de que una señal se convierta en crisis.

> **La pregunta que queda abierta después de este brief es la más valiosa:** ¿la narrativa mediática coincide realmente con lo que está pensando y diciendo la gente?
"""

    output = {
        "study": study.slug,
        "client": study.client,
        "brief": "executive_signal",
        "sample": metadata,
        "summary": summary,
        "representative_claims": claims,
    }
    return content, output


def write_signal_brief(directory: Path, content: str, data: Dict, sample: List[Dict]) -> Dict[str, str]:
    md_path = directory / "report.signal-brief.md"
    json_path = directory / "report.signal-brief.json"
    sample_path = directory / "signal-brief.sample.jsonl"
    md_path.write_text(content, encoding="utf-8")
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(sample_path, sample)
    return {"report": str(md_path), "data": str(json_path), "sample": str(sample_path)}
