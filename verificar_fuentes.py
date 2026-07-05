"""
NeuroDiario - Verificador de fuentes RSS

Le pega a cada feed de sources_config y reporta, fuente por fuente:
  - Si responde (HTTP status)
  - Cuántas entradas trae el feed
  - Si el título de la primera entrada se lee bien
  - Cualquier error de conexión o parseo

Solo lectura. No toca la base de datos. Se puede correr con el scheduler pausado.

Uso:
    python verificar_fuentes.py
"""

import sys
import time
import requests
import feedparser


BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}


def verificar():
    from neurodiario.ingestion.sources_config import SOURCES, FETCH_TIMEOUT

    print("\n" + "=" * 70)
    print("  VERIFICADOR DE FUENTES RSS — NeuroDiario")
    print("=" * 70)

    ok = 0
    fallidas = 0
    inactivas = 0

    for source in SOURCES:
        name = source.get("name", "?")
        url = source.get("url", "")
        activa = source.get("active", True)

        estado_activa = "" if activa else "  (INACTIVA en config)"
        if not activa:
            inactivas += 1

        try:
            r = requests.get(url, headers=BROWSER_HEADERS, timeout=FETCH_TIMEOUT)
            status = r.status_code

            if status != 200:
                print(f"  ✗ {name:<28} HTTP {status}{estado_activa}")
                if activa:
                    fallidas += 1
                continue

            feed = feedparser.parse(r.content)
            n_entries = len(feed.entries)
            bozo = " (parseo con warnings)" if feed.bozo else ""

            if n_entries == 0:
                print(f"  ⚠ {name:<28} responde pero 0 entradas{bozo}{estado_activa}")
                if activa:
                    fallidas += 1
                continue

            primera = feed.entries[0].get("title", "")[:45]
            marca = "✓" if activa else "·"
            print(f"  {marca} {name:<28} {n_entries:>3} entradas{bozo}{estado_activa}")
            print(f"      └ ej: {primera}...")
            if activa:
                ok += 1

        except requests.exceptions.Timeout:
            print(f"  ✗ {name:<28} TIMEOUT (>{FETCH_TIMEOUT}s){estado_activa}")
            if activa:
                fallidas += 1
        except Exception as e:
            print(f"  ✗ {name:<28} ERROR: {type(e).__name__}{estado_activa}")
            if activa:
                fallidas += 1

        time.sleep(0.3)

    print("\n" + "-" * 70)
    print(f"  Activas funcionando: {ok}   |   Activas con problema: {fallidas}   |   Inactivas: {inactivas}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    verificar()
