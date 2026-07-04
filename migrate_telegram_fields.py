"""
Migración: Agrega columnas telegram_message_id y telegram_posted_at
a la tabla generated_articles.
Ejecutar una sola vez en Railway Shell:
    python migrate_telegram_fields.py
"""
import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL no está configurada.")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("Agregando columnas Telegram a generated_articles...")

try:
    cur.execute("""
        ALTER TABLE generated_articles
        ADD COLUMN IF NOT EXISTS telegram_message_id VARCHAR(50),
        ADD COLUMN IF NOT EXISTS telegram_posted_at TIMESTAMP;
    """)
    conn.commit()
    print("✓ Columnas agregadas exitosamente.")
except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")
finally:
    cur.close()
    conn.close()
