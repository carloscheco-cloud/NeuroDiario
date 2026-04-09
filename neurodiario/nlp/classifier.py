"""
Modulo de clasificacion tematica de articulos.
Asigna categorias (politica, economia, deportes, etc.) a cada articulo.
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# PALABRAS CLAVE POR CATEGORIA
# Mas especificas para evitar colisiones entre categorias
# El titulo pesa el doble que el cuerpo
# ─────────────────────────────────────────────────────────────
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "politica": [
        "gobierno", "presidente", "congreso", "senado", "diputado",
        "partido politico", "elecciones", "ministro", "decreto", "ley",
        "constitución", "abinader", "legislativo", "ejecutivo", "judicial",
        "gobernador", "alcalde", "ayuntamiento", "procurador", "fiscal",
        "poder ejecutivo", "poder legislativo", "poder judicial",
        "pld", "prm", "fuerza del pueblo", "reforma", "politica dominicana",
        "canciller", "cancillería", "diplomacia dominicana",
    ],
    "economia": [
        "economía dominicana", "peso dominicano", "dólar", "inflación",
        "pib dominicano", "banco central", "inversión extranjera",
        "exportaciones dominicanas", "importaciones", "empleo dominicano",
        "desempleo", "hacienda", "presupuesto nacional", "deuda publica",
        "zona franca", "turismo dominicano", "remesas", "tipo de cambio",
        "banreservas", "popular", "bhd", "reservas internacionales",
        "crecimiento económico", "recaudaciones", "dgii", "aduanas",
    ],
    "deportes": [
        "béisbol dominicano", "lidom", "grandes ligas", "mlb",
        "pelotero dominicano", "home run", "pitcher", "lanzador", "bateador",
        "yankees", "dodgers", "medias rojas", "padres", "astros",
        "clásico mundial", "clasico mundial", "licey", "escogido",
        "águilas cibaeñas", "estrellas orientales", "toros del este",
        "baloncesto dominicano", "lnb", "atletismo dominicano",
        "boxeo", "campeón mundial", "campeonato dominicano",
        "futbol dominicano", "selección dominicana", "deporte dominicano",
    ],
    "salud": [
        "salud dominicana", "hospital dominicano", "médico", "enfermedad",
        "vacuna", "paciente", "ministerio de salud", "epidemia", "dengue",
        "covid", "tratamiento médico", "sns", "seguro médico", "idss",
        "aborto", "maternidad", "salud publica", "farmacia", "medicamento",
    ],
    "tecnologia": [
        "tecnología", "internet dominicano", "digital", "software",
        "aplicacion", "startup dominicana", "inteligencia artificial",
        "ciberseguridad", "datos", "innovación tecnológica",
        "indotel", "telecomunicaciones", "banda ancha", "fibra optica",
    ],
    "cultura": [
        "cultura dominicana", "arte dominicano", "música dominicana",
        "cine dominicano", "teatro dominicano", "festival dominicano",
        "literatura dominicana", "merengue", "bachata", "patrimonio dominicano",
        "artista dominicano", "carnaval dominicano", "gastronomia dominicana",
        "cultura popular", "folclore dominicano",
    ],
    "educacion": [
        "educación dominicana", "escuela dominicana", "universidad dominicana",
        "estudiante", "docente dominicano", "minerd", "maestro dominicano",
        "aula", "currículo", "beca dominicana", "uasd", "pucmm", "intec",
        "año escolar", "tanda extendida", "jornada escolar",
    ],
    "internacional": [
        "guerra", "conflicto armado", "bombardeo", "ataque militar",
        "iran", "israel", "ucrania", "rusia", "oriente proximo", "medio oriente",
        "onu", "oea", "otan", "biden", "trump", "xi jinping",
        "haiti", "venezuela", "cuba", "colombia", "mexico", "argentina",
        "estados unidos", "europa", "asia", "africa",
        "refugiados", "paz", "tratado internacional", "cumbre mundial",
        "banco mundial", "fmi", "g20", "g7",
    ],
    "sociedad": [
        "crimen", "homicidio", "robo", "seguridad ciudadana",
        "feminicidio", "violencia", "accidente", "catástrofe",
        "inundación dominicana", "damnificados", "coe", "defensa civil",
        "comunidad dominicana", "barrio", "pobreza", "desigualdad",
        "migracion dominicana", "deportados", "haitiano en rd",
    ],
}


class ArticleClassifier:
    """Clasifica articulos de noticias por tematica."""

    def __init__(self, method: str = "keyword"):
        self.method = method
        self._model = None

    def classify(self, text: str, title: str = "") -> Tuple[str, float]:
        if self.method == "keyword":
            return self._classify_by_keywords(text, title)
        raise NotImplementedError(f"Metodo '{self.method}' no implementado aun")

    def classify_article(self, title: str, content: str) -> Tuple[str, float]:
        return self.classify(text=content, title=title)

    def classify_batch(self, articles: List[Dict]) -> List[Dict]:
        for article in articles:
            category, confidence = self.classify(
                article.get("raw_content", ""),
                article.get("title", ""),
            )
            article["category"] = category
            article["category_confidence"] = confidence
        return articles

    def _classify_by_keywords(self, text: str, title: str) -> Tuple[str, float]:
        """
        Clasifica usando conteo de palabras clave por categoria.
        El titulo pesa 3 veces mas que el cuerpo para mayor precision.
        Las frases de dos palabras tienen mas peso que palabras sueltas.
        """
        # Titulo tiene peso x3 para mayor precision
        combined = f"{title} {title} {title} {text}".lower()
        scores: Dict[str, int] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            for kw in keywords:
                count = combined.count(kw.lower())
                # Frases de mas de una palabra tienen peso doble
                weight = 2 if len(kw.split()) > 1 else 1
                score += count * weight
            scores[category] = score

        if not any(scores.values()):
            return "general", 0.0

        best_category = max(scores, key=lambda k: scores[k])
        total = sum(scores.values())
        confidence = scores[best_category] / total if total > 0 else 0.0

        return best_category, round(confidence, 3)
