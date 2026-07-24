"""
Modulo de configuracion centralizada de NeuroDiario.
Carga variables de entorno desde .env y las expone como atributos tipados.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables desde .env en la raiz del proyecto
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_env_path)


class Settings:
    """Configuracion global de la aplicacion cargada desde variables de entorno."""

    # -- WordPress -------------------------------------------------------------
    WORDPRESS_URL: str = os.getenv("WORDPRESS_URL", "https://neurodiario.com")
    WORDPRESS_USER: str = os.getenv("WORDPRESS_USER", "neurodiario")
    WORDPRESS_PASSWORD: str = os.getenv("WORDPRESS_PASSWORD", "")

    # -- Base de datos ---------------------------------------------------------
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///neurodiario.db",
    )

    # -- OpenAI ---------------------------------------------------------------
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Se mantiene por compatibilidad, pero NeuroDiario migrara a OpenAI.

    # -- Facebook -------------------------------------------------------------
    FACEBOOK_PAGE_TOKEN: str = os.getenv("FACEBOOK_PAGE_TOKEN", "")
    FACEBOOK_PAGE_ID: str = os.getenv("FACEBOOK_PAGE_ID", "")

    # -- Telegram -------------------------------------------------------------
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHANNEL_ID: str = os.getenv("TELEGRAM_CHANNEL_ID", "")

    # -- Imagenes -------------------------------------------------------------
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")

    # -- Media Intelligence Engine -------------------------------------------
    # Apagado por defecto: primero diagnóstico, luego activación controlada.
    MEDIA_ENGINE_USE_FEATURED: bool = os.getenv(
        "MEDIA_ENGINE_USE_FEATURED",
        "False",
    ).lower() in ("true", "1", "yes")

    # -- Aplicacion -----------------------------------------------------------
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Santo_Domingo")

    # -- Pipeline -------------------------------------------------------------
    FETCH_INTERVAL_HOURS: int = int(os.getenv("FETCH_INTERVAL_HOURS", "2"))
    MAX_ARTICLES_PER_CYCLE: int = int(os.getenv("MAX_ARTICLES_PER_CYCLE", "100"))
    TREND_WINDOW_HOURS: int = int(os.getenv("TREND_WINDOW_HOURS", "24"))
    INGESTION_INTERVAL_MINUTES: int = int(os.getenv("INGESTION_INTERVAL_MINUTES", "15"))
    NLP_INTERVAL_MINUTES: int = int(os.getenv("NLP_INTERVAL_MINUTES", "20"))

    # -- NLP ------------------------------------------------------------------
    SPACY_MODEL: str = os.getenv("SPACY_MODEL", "es_core_news_lg")

    def validate(self) -> list:
        """
        Valida que las variables criticas esten configuradas.

        Returns:
            Lista de nombres de variables faltantes.
        """
        required = {
            "WORDPRESS_URL": self.WORDPRESS_URL,
            "WORDPRESS_USER": self.WORDPRESS_USER,
            "WORDPRESS_PASSWORD": self.WORDPRESS_PASSWORD,
            "DATABASE_URL": self.DATABASE_URL,
            "OPENAI_API_KEY": self.OPENAI_API_KEY,
        }
        return [name for name, value in required.items() if not value]

    def __repr__(self):
        return (
            f"Settings(debug={self.DEBUG}, wordpress={self.WORDPRESS_URL}, "
            f"model={self.OPENAI_MODEL})"
        )


# Instancia unica usada en toda la aplicacion
settings = Settings()
