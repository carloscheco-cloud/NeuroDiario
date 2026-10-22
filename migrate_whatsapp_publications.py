"""Crea únicamente el registro de WhatsApp; se puede ejecutar más de una vez."""
from neurodiario.db.database import get_engine
from neurodiario.db.models import WhatsAppPublication


def migrate(engine=None):
    WhatsAppPublication.__table__.create(bind=engine if engine is not None else get_engine(), checkfirst=True)


if __name__ == "__main__":
    migrate()
    print("Registro de WhatsApp preparado. Los artículos y envíos de Telegram se conservan.")
