"""
Angle Detector — detecta el ángulo periodístico de una noticia.

Utiliza un enfoque basado en keywords para identificar el ángulo dominante
de un texto y devuelve el ángulo junto a una puntuación de confianza.
"""

ANGLES = [
    "economia",
    "politica",
    "corrupcion",
    "seguridad",
    "crisis",
    "deportes",
    "internacional",
]

# Keywords asociados a cada ángulo (en minúsculas, sin tildes para mayor cobertura)
_ANGLE_KEYWORDS: dict[str, list[str]] = {
    "economia": [
        "economia", "economico", "economica", "pib", "inflacion", "peso",
        "dolar", "banco", "inversion", "mercado", "precio", "impuesto",
        "presupuesto", "deuda", "exportacion", "importacion", "comercio",
        "empresa", "negocio", "finanzas", "empleo", "desempleo", "salario",
    ],
    "politica": [
        "politica", "gobierno", "presidente", "congreso", "senado", "diputado",
        "partido", "eleccion", "voto", "ministro", "decreto", "ley", "reforma",
        "oposicion", "candidato", "campana", "prrd", "pld", "fuerza del pueblo",
    ],
    "corrupcion": [
        "corrupcion", "soborno", "fraude", "malversacion", "lavado", "dinero",
        "investigacion", "fiscal", "imputado", "detenido", "arresto", "juicio",
        "tribunal", "acusado", "expediente", "irregular", "desfalco",
    ],
    "seguridad": [
        "seguridad", "policia", "crimen", "homicidio", "robo", "violencia",
        "narcotrafico", "droga", "pnp", "militar", "operativo", "delito",
        "prision", "carcel", "apresado", "disparos", "muertes", "victima",
    ],
    "crisis": [
        "crisis", "emergencia", "escasez", "apagon", "desabastecimiento",
        "protesta", "manifestacion", "huelga", "colapso", "caos", "desastre",
        "catastrofe", "inundacion", "huracan", "tormenta",
    ],
    "deportes": [
        "deportes", "beisbol", "futbol", "liga", "campeonato", "torneo",
        "jugador", "equipo", "partido", "gol", "bateo", "pitcher", "pelotero",
        "olimpico", "atletismo", "boxeo", "serie del caribe",
    ],
    "internacional": [
        "internacional", "estados unidos", "eeuu", "onu", "haiti",
        "america latina", "europa", "mundo", "global", "exterior",
        "cancilleria", "diplomacia", "tratado", "embajada", "extranjero",
    ],
}


def detect_angle(text: str) -> dict:
    """
    Detecta el ángulo periodístico de un texto mediante keywords.

    Args:
        text: Texto del artículo a analizar.

    Returns:
        Diccionario con claves:
            - 'angle' (str): ángulo detectado (uno de ANGLES o 'general').
            - 'confidence' (float): proporción de hits del ángulo ganador
              sobre el total de hits; 0.0 si no se encontraron keywords.
    """
    if not text:
        return {"angle": "general", "confidence": 0.0}

    text_lower = text.lower()

    scores: dict[str, int] = {
        angle: sum(1 for kw in keywords if kw in text_lower)
        for angle, keywords in _ANGLE_KEYWORDS.items()
    }

    total_hits = sum(scores.values())
    if total_hits == 0:
        return {"angle": "general", "confidence": 0.0}

    best_angle = max(scores, key=scores.__getitem__)
    confidence = round(scores[best_angle] / total_hits, 3)

    return {"angle": best_angle, "confidence": confidence}
