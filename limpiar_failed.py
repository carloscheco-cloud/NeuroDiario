"""
NeuroDiario - Limpieza de GeneratedArticle en 'failed' y 'processing'

Borra los registros huérfanos "[generando...]" que dejó el pipeline viejo,
para empezar limpio con el nuevo auto_scheduler (clustering).

SEGURO: solo toca status 'failed' y 'processing'. NO borra draft, published,
ni clustered. NO toca la tabla Article (los crudos quedan intactos).

Por defecto simula. Con --apply borra de verdad.

Uso:
    python limpiar_failed.py            → simulación (no borra)
    python limpiar_failed.py --apply    → borra de verdad
"""

import sys
import logging

logging.basicConfig(level=logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def run(apply_changes: bool = False):
    from neurodiario.db.database import get_db
    from neurodiario.db.models import GeneratedArticle

    estados = ["failed", "processing"]
    print("\n" + "=" * 56)
    print("  LIMPIEZA DE GeneratedArticle (failed / processing)")
    print(f"  Modo: {'BORRADO REAL' if apply_changes else 'SIMULACIÓN'}")
    print("=" * 56)

    with get_db() as db:
        n = db.query(GeneratedArticle.id).filter(
            GeneratedArticle.status.in_(estados)
        ).count()
        print(f"\n  Registros a borrar (failed + processing): {n}")

        if not apply_changes:
            print("\n  (simulación) No se borró nada.")
            print("  Para borrar: python limpiar_failed.py --apply")
            print("=" * 56 + "\n")
            return

        borrados = db.query(GeneratedArticle).filter(
            GeneratedArticle.status.in_(estados)
        ).delete(synchronize_session=False)
        db.commit()
        print(f"\n  ✓ Borrados: {borrados}")

    print("=" * 56 + "\n")


if __name__ == "__main__":
    run(apply_changes="--apply" in sys.argv)
