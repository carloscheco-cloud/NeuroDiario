"""
Migración: Agrega columnas de Facebook a generated_articles.

Ejecutar UNA SOLA VEZ en Railway con:
    python migrate_facebook_fields.py

Agrega:
    - facebook_post_id  (VARCHAR 200)
    - facebook_posted_at (TIMESTAMP)
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_migration():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("❌ Variable DATABASE_URL no encontrada en el entorno.")
        sys.exit(1)

    # Railway usa postgres://, SQLAlchemy necesita postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)

    migrations = [
        {
            "name": "facebook_post_id",
            "sql": "ALTER TABLE generated_articles ADD COLUMN IF NOT EXISTS facebook_post_id VARCHAR(200);",
        },
        {
            "name": "facebook_posted_at",
            "sql": "ALTER TABLE generated_articles ADD COLUMN IF NOT EXISTS facebook_posted_at TIMESTAMP;",
        },
    ]

    with engine.connect() as conn:
        for m in migrations:
            try:
                conn.execute(text(m["sql"]))
                conn.commit()
                logger.info(f"  ✓ Columna '{m['name']}' agregada (o ya existía).")
            except Exception as e:
                logger.error(f"  ✗ Error agregando '{m['name']}': {e}")
                sys.exit(1)

    logger.info("\n✅ Migración completada exitosamente.")
    logger.info("Ahora puedes subir models.py y publishing_pipeline.py a GitHub.")


if __name__ == "__main__":
    run_migration()
