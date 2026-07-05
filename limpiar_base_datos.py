"""
NeuroDiario - Limpieza total de la base de datos (empezar de cero)

Borra TODO el contenido de prueba:
  - GeneratedArticle (artículos generados por Claude)
  - Trend (tendencias detectadas)
  - Article (artículos crudos del RSS)
  - Source (fuentes/periódicos)

Las Source se regeneran solas cuando entra el primer artículo de cada
periódico (el database.py corregido las crea automáticamente).

SEGURIDAD (3 capas):
  1. Por defecto DRY-RUN: solo cuenta y reporta, no borra nada.
  2. Requiere --apply para borrar de verdad.
  3. Con --apply, pide escribir la palabra BORRAR para confirmar.

El orden de borrado respeta las llaves foráneas:
  GeneratedArticle -> Trend -> Article -> Source

Uso:
    python limpiar_base_datos.py            → simulación (no borra)
    python limpiar_base_datos.py --apply    → borra (pide confirmación)
"""

import logging
import sys

logging.basicConfig(level=logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def run(apply_changes: bool = False):
    from neurodiario.db.database import get_db
    from neurodiario.db.models import Article, GeneratedArticle, Trend, Source

    mode = "BORRADO REAL" if apply_changes else "SIMULACIÓN (dry-run, no borra nada)"
    print("\n" + "=" * 64)
    print("  LIMPIEZA TOTAL DE LA BASE DE DATOS")
    print(f"  Modo: {mode}")
    print("=" * 64)

    with get_db() as db:
        n_generated = db.query(GeneratedArticle.id).count()
        n_trends    = db.query(Trend.id).count()
        n_articles  = db.query(Article.id).count()
        n_sources   = db.query(Source.id).count()

        print("\n  Contenido actual:")
        print(f"    GeneratedArticle : {n_generated}")
        print(f"    Trend            : {n_trends}")
        print(f"    Article          : {n_articles}")
        print(f"    Source           : {n_sources}")
        total = n_generated + n_trends + n_articles + n_sources
        print(f"    ─────────────────────────")
        print(f"    TOTAL a borrar   : {total}")

        if not apply_changes:
            print("\n  (simulación) No se borró nada.")
            print("  Para borrar de verdad, corre:  python limpiar_base_datos.py --apply")
            print("=" * 64 + "\n")
            return

        # ── Confirmación interactiva ──
        print("\n  ⚠  ESTO BORRARÁ TODO EL CONTENIDO DE LA BASE DE DATOS.")
        print("  ⚠  Esta acción NO se puede deshacer.")
        respuesta = input("\n  Para confirmar, escribe la palabra BORRAR y presiona Enter: ").strip()

        if respuesta != "BORRAR":
            print("\n  ✗ Confirmación incorrecta. No se borró nada.")
            print("=" * 64 + "\n")
            return

        # ── Borrado en orden seguro (hijos primero) ──
        print("\n  Borrando...")
        d1 = db.query(GeneratedArticle).delete(synchronize_session=False)
        print(f"    GeneratedArticle borrados: {d1}")
        d2 = db.query(Trend).delete(synchronize_session=False)
        print(f"    Trend borrados: {d2}")
        d3 = db.query(Article).delete(synchronize_session=False)
        print(f"    Article borrados: {d3}")
        d4 = db.query(Source).delete(synchronize_session=False)
        print(f"    Source borrados: {d4}")
        db.commit()

        print("\n  ✓ Base de datos vaciada. Lista para empezar de cero.")
        print("    (Las Source se recrearán solas al entrar los primeros artículos.)")

    print("=" * 64 + "\n")


if __name__ == "__main__":
    apply_flag = "--apply" in sys.argv
    run(apply_changes=apply_flag)
