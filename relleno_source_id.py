"""
NeuroDiario - Relleno de source_id en artículos históricos

Los artículos guardados antes del fix de save_article quedaron sin source_id.
Este script los repara cruzando el DOMINIO de la URL de cada artículo con
la configuración de fuentes (sources_config).

MODO SEGURO:
- Por defecto corre en DRY-RUN (simulación): muestra qué haría, no toca nada.
- Solo con el argumento --apply modifica la base de datos.

Uso:
    python relleno_source_id.py            → simulación (no cambia nada)
    python relleno_source_id.py --apply    → aplica los cambios

Varias fuentes comparten dominio (las 4 de Diario Libre son diariolibre.com).
En esos casos se asigna la fuente PRINCIPAL de ese dominio. La categoría del
artículo ya vive en otro campo, así que no se pierde información.
"""

import logging
import sys
from collections import Counter
from urllib.parse import urlparse

logging.basicConfig(level=logging.WARNING)


# ── Mapa dominio → nombre de fuente principal ──
# Cuando varias fuentes comparten dominio, se elige la principal (sin sufijo).
DOMAIN_TO_SOURCE = {
    "diariolibre.com":  "Diario Libre",
    "elnacional.com.do": "El Nacional",
    "n.com.do":         "N Digital",
    "eldia.com.do":     "El Dia",
    "bbc.co.uk":        "BBC Mundo",
    "bbci.co.uk":       "BBC Mundo",
    "elpais.com":       "El Pais America",
    "bloomberg.com":    "Bloomberg",
}


def _domain_of(url: str) -> str:
    """Extrae el dominio base de una URL, sin www ni subdominios de más."""
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        # Reducir subdominios: feeds.bbci.co.uk -> bbci.co.uk, etc.
        parts = netloc.split(".")
        # Casos .com.do (3 partes finales) vs .com (2 partes)
        if len(parts) >= 3 and parts[-2] in ("com", "co", "org", "gob") and parts[-1] in ("do", "uk"):
            return ".".join(parts[-3:])
        return ".".join(parts[-2:]) if len(parts) >= 2 else netloc
    except Exception:
        return ""


def run(apply_changes: bool = False):
    from neurodiario.db.database import get_db
    from neurodiario.db.models import Article, Source

    mode = "APLICAR CAMBIOS" if apply_changes else "SIMULACIÓN (dry-run, no modifica nada)"
    print("\n" + "=" * 64)
    print("  RELLENO DE source_id EN ARTÍCULOS HISTÓRICOS")
    print(f"  Modo: {mode}")
    print("=" * 64)

    with get_db() as db:
        # 1) Resolver nombre de fuente -> id (crear las que falten)
        name_to_id = {}
        for domain, source_name in set((d, n) for d, n in DOMAIN_TO_SOURCE.items()):
            src = db.query(Source).filter(Source.name == source_name).first()
            if not src:
                if apply_changes:
                    src = Source(name=source_name, url=f"https://{domain}", category="general", language="es")
                    db.add(src)
                    db.flush()
                    print(f"  + Fuente creada: {source_name} (id={src.id})")
                    name_to_id[source_name] = src.id
                else:
                    print(f"  (simulación) se crearía la fuente: {source_name}")
                    name_to_id[source_name] = None
            else:
                name_to_id[source_name] = src.id

        # 2) Recorrer artículos sin source_id
        sin_fuente = db.query(Article).filter(Article.source_id == None).all()  # noqa: E711
        print(f"\n  Artículos sin source_id: {len(sin_fuente)}")

        asignados = Counter()
        no_reconocidos = Counter()
        cambios = 0

        for art in sin_fuente:
            dom = _domain_of(art.url or "")
            source_name = DOMAIN_TO_SOURCE.get(dom)

            if not source_name:
                no_reconocidos[dom or "(url vacía)"] += 1
                continue

            src_id = name_to_id.get(source_name)
            if src_id is None and not apply_changes:
                # en simulación la fuente aún no tiene id real, pero contamos igual
                asignados[source_name] += 1
                continue

            if apply_changes and src_id is not None:
                art.source_id = src_id
                cambios += 1
            asignados[source_name] += 1

        # 3) Reporte
        print("\n  ── Asignaciones por fuente ──")
        for name, count in asignados.most_common():
            print(f"    {name:<22} {count:>6}")

        if no_reconocidos:
            print("\n  ── Dominios NO reconocidos (quedan sin fuente) ──")
            for dom, count in no_reconocidos.most_common():
                print(f"    {dom:<30} {count:>6}")

        if apply_changes:
            db.commit()
            print(f"\n  ✓ Cambios aplicados: {cambios} artículos actualizados.")
        else:
            total_asignables = sum(asignados.values())
            print(f"\n  (simulación) Se asignarían {total_asignables} artículos.")
            print("  Para aplicar de verdad, corre:  python relleno_source_id.py --apply")

    print("=" * 64 + "\n")


if __name__ == "__main__":
    apply_flag = "--apply" in sys.argv
    run(apply_changes=apply_flag)
