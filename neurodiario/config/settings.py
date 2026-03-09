"""
Módulo de configuración centralizada de NeuroDiario.
Carga variables de entorno desde .env y las expone como atributos tipados.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables desde .env en la raíz del proyecto
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_env_path)


class Settings:
    """Configuración global de la aplicación cargada desde variables de entorno."""

    # ── WordPress ──────────────────────────────────────────────────────────────
    WORDPRESS_URL: str = os.getenv("WORDPRESS_URL", "https://neurodiario.com")
    WORDPRESS_USER: str = os.getenv("WORDPRESS_USER", "neurodiario")
    WORDPRESS_APP_PASSWORD: str = os.getenv("WORDPRESS_APP_PASSWORD", "AQUI_EL_APPLICATION_PASSWORD")
    WORDPRESS_PASSWORD: str = os.getenv("WORDPRESS_PASSWORD", "")

    # ── Base de datos ──────────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost/neurodiario",
    )

    # ── Claude / Anthropic ─────────────────────────────────────────────────────
    CLAUDE_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", os.getenv("CLAUDE_API_KEY", ""))
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")

    # ── Aplicación ─────────────────────────────────────────────────────────────
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Santo_Domingo")

    # ── Pipeline ───────────────────────────────────────────────────────────────
    FETCH_INTERVAL_HOURS: int = int(os.getenv("FETCH_INTERVAL_HOURS", "2"))
    MAX_ARTICLES_PER_CYCLE: int = int(os.getenv("MAX_ARTICLES_PER_CYCLE", "100"))
    TREND_WINDOW_HOURS: int = int(os.getenv("TREND_WINDOW_HOURS", "24"))
    INGESTION_INTERVAL_MINUTES: int = int(os.getenv("INGESTION_INTERVAL_MINUTES", "15"))
    NLP_INTERVAL_MINUTES: int = int(os.getenv("NLP_INTERVAL_MINUTES", "20"))

    # ── NLP ────────────────────────────────────────────────────────────────────
    SPACY_MODEL: str = os.getenv("SPACY_MODEL", "es_core_news_lg")

    def validate(self) -> list:
        """
        Valida que las variables críticas estén configuradas.

        Returns:
            Lista de nombres de variables faltantes (vacía si todo está bien).
        """
        required = {
            "WORDPRESS_URL": self.WORDPRESS_URL,
            "WORDPRESS_USER": self.WORDPRESS_USER,
            "WORDPRESS_PASSWORD": self.WORDPRESS_PASSWORD,
            "DATABASE_URL": self.DATABASE_URL,
            "CLAUDE_API_KEY": self.CLAUDE_API_KEY,
        }
        return [name for name, value in required.items() if not value]

    def __repr__(self):
        return (
            f"Settings(debug={self.DEBUG}, wordpress={self.WORDPRESS_URL}, "
            f"model={self.CLAUDE_MODEL})"
        )


# Instancia única usada en toda la aplicación
settings = Settings()
