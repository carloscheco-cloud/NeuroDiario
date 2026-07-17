"""
Modulo de clasificacion tematica de articulos.
Asigna categorias (politica, economia, deportes, etc.) a cada articulo.

Estrategia (Opción 1 + corrección):
  1. Si la fuente declara una categoría ESPECÍFICA y confiable
     (deportes, economia, salud...), se usa directamente — gratis.
  2. Si la fuente es genérica (general/portada) o dudosa, se consulta
     a OpenAI para clasificar con precisión.
  3. Si Haiku no está disponible (sin API key o error), cae al método
     de palabras clave como respaldo.

Esto arregla el bug donde casi todo terminaba en "politica" por el
conteo ingenuo de substrings.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Categorías válidas del sistema
CATEGORIAS_VALIDAS = [
    "politica", "economia", "deportes", "salud", "tecnologia",
    "cultura", "educacion", "internacional", "sociedad", "general",
]

# Categorías de fuente en las que confiamos DIRECTAMENTE (sin Haiku).
# Son secciones específicas donde el medio ya clasificó bien.
CATEGORIAS_FUENTE_CONFIABLES = {
    "politica", "economia", "deportes", "salud",
    "tecnologia", "cultura", "educacion",
}

# Categorías de fuente GENÉRICAS o ambiguas → siempre verificar con Haiku.
CATEGORIAS_FUENTE_DUDOSAS = {"general", "internacional", "sociedad", "", None}


# ─────────────────────────────────────────────────────────────
# PALABRAS CLAVE (RESPALDO cuando Haiku no está disponible)
# ─────────────────────────────────────────────────────────────
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "politica": [
        "gobierno", "presidente", "congreso", "senado", "diputado",
        "partido politico", "elecciones", "ministro", "decreto",
        "constitución", "abinader", "legislativo", "ejecutivo",
        "gobernador", "alcalde", "ayuntamiento", "procurador",
        "pld", "prm", "fuerza del pueblo", "reforma fiscal",
        "canciller", "cancillería",
    ],
    "economia": [
        "economía dominicana", "peso dominicano", "inflación",
        "pib dominicano", "banco central", "inversión extranjera",
        "exportaciones", "importaciones", "desempleo", "hacienda",
        "presupuesto nacional", "zona franca", "remesas", "tipo de cambio",
        "banreservas", "reservas internacionales", "recaudaciones", "dgii",
    ],
    "deportes": [
        "béisbol", "lidom", "grandes ligas", "mlb", "pelotero",
        "home run", "pitcher", "lanzador", "bateador", "licey",
        "escogido", "águilas cibaeñas", "estrellas orientales",
        "baloncesto", "atletismo", "boxeo", "campeonato", "selección dominicana",
    ],
    "salud": [
        "hospital", "médico", "enfermedad", "vacuna", "paciente",
        "ministerio de salud", "epidemia", "dengue", "covid",
        "sns", "seguro médico", "medicamento", "salud publica",
    ],
    "tecnologia": [
        "tecnología", "internet", "software", "aplicacion", "startup",
        "inteligencia artificial", "ciberseguridad", "indotel",
        "telecomunicaciones", "banda ancha", "fibra optica",
    ],
    "cultura": [
        "arte", "música dominicana", "cine dominicano", "teatro",
        "festival", "literatura", "merengue", "bachata", "carnaval",
        "gastronomia", "folclore",
    ],
    "educacion": [
        "educación", "escuela", "universidad", "estudiante", "docente",
        "minerd", "maestro", "beca", "uasd", "pucmm", "año escolar",
        "tanda extendida",
    ],
    "internacional": [
        "guerra", "conflicto armado", "bombardeo", "iran", "israel",
        "ucrania", "rusia", "onu", "otan", "haiti", "venezuela", "cuba",
        "estados unidos", "refugiados", "tratado internacional", "fmi",
    ],
    "sociedad": [
        "crimen", "homicidio", "robo", "seguridad ciudadana", "feminicidio",
        "violencia", "accidente", "inundación", "damnificados", "coe",
        "defensa civil", "pobreza", "migracion", "deportados",
    ],
}


class ArticleClassifier:
    """Clasifica articulos de noticias por tematica."""

    def __init__(self, method: str = "hybrid", api_key: Optional[str] = None, model: Optional[str] = None):
        self.method = method
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._client = None

    def _get_client(self):
        if self._client is None and self.api_key:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def classify(self, text: str, title: str = "", source_category: Optional[str] = None) -> Tuple[str, float]:
        """
        Clasifica un artículo.
        - Si source_category es una sección confiable, se usa directo.
        - Si es dudosa/genérica, se consulta a Haiku.
        - Si Haiku falla, cae a palabras clave.
        """
        sc = (source_category or "").lower().strip()

        # 1. Confiar en secciones específicas de la fuente
        if sc in CATEGORIAS_FUENTE_CONFIABLES:
            return sc, 1.0

        # 2. Fuente dudosa/genérica → intentar Haiku
        if self.api_key:
            cat_haiku = self._classify_with_haiku(title, text)
            if cat_haiku:
                return cat_haiku, 0.95

        # 3. Respaldo: palabras clave
        return self._classify_by_keywords(text, title)

    def classify_article(self, title: str, content: str, source_category: Optional[str] = None) -> Tuple[str, float]:
        return self.classify(text=content, title=title, source_category=source_category)

    def classify_batch(self, articles: List[Dict]) -> List[Dict]:
        for article in articles:
            category, confidence = self.classify(
                article.get("raw_content", "") or article.get("clean_content", ""),
                article.get("title", ""),
                article.get("category"),  # categoría que trae la fuente
            )
            article["category"] = category
            article["category_confidence"] = confidence
        return articles

    def _classify_with_haiku(self, title: str, text: str) -> Optional[str]:
        """Clasifica con OpenAI. Devuelve la categoría o None si falla."""
        try:
            client = self._get_client()
            if not client:
                return None

            # Limitar el texto para no gastar tokens de más
            fragmento = (text or "")[:600]
            categorias_str = ", ".join(CATEGORIAS_VALIDAS)

            prompt = f"""Clasifica esta noticia dominicana en UNA sola categoría.

Categorías válidas: {categorias_str}

Titular: {title}
Extracto: {fragmento}

Responde SOLO con el nombre exacto de la categoría, en minúsculas, sin explicación."""

            response = client.chat.completions.create(
                model=self.model,
                max_tokens=10,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            respuesta = (response.choices[0].message.content or "").strip().lower()

            # Validar que sea una categoría real
            for cat in CATEGORIAS_VALIDAS:
                if cat in respuesta:
                    return cat
            return None

        except Exception as e:
            logger.warning(f"Haiku no pudo clasificar ({e}); usando respaldo")
            return None

    def _classify_by_keywords(self, text: str, title: str) -> Tuple[str, float]:
        """
        RESPALDO: clasifica por palabras clave.
        Mejora vs versión anterior: usa límites de palabra para no contar
        substrings dentro de otras palabras (el bug de 'ley' dentro de otras).
        """
        import re
        combined = f"{title} {title} {title} {text}".lower()
        scores: Dict[str, int] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            for kw in keywords:
                # \b = límite de palabra: cuenta "ley" pero no dentro de "leyenda"
                patron = r"\b" + re.escape(kw.lower()) + r"\b"
                count = len(re.findall(patron, combined))
                weight = 2 if len(kw.split()) > 1 else 1
                score += count * weight
            scores[category] = score

        if not any(scores.values()):
            return "general", 0.0

        best_category = max(scores, key=lambda k: scores[k])
        total = sum(scores.values())
        confidence = scores[best_category] / total if total > 0 else 0.0
        return best_category, round(confidence, 3)
