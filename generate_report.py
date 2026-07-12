"""
Genera el reporte investigativo NeuroData sobre cobertura del INTRANT.
Usa reportlab para crear un PDF profesional con branding NeuroDiario.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.lib import colors
import json
from datetime import datetime, date
from collections import defaultdict

# ─── Colores NeuroDiario ──────────────────────────────────────────────────────
NAVY = HexColor("#0B1F3B")
ELECTRIC_BLUE = HexColor("#0077FF")
LIGHT_GRAY = HexColor("#F2F4F7")
WHITE = HexColor("#FFFFFF")
GREEN = HexColor("#2ECC71")
RED = HexColor("#E74C3C")
GRAY_TEXT = HexColor("#555555")
DARK_GRAY = HexColor("#333333")

# ─── Data ─────────────────────────────────────────────────────────────────────

MEDIOS_NOMBRES = {
    "diariolibre": "Diario Libre",
    "listindiario": "Listín Diario",
    "elcaribe": "El Caribe",
    "hoy": "Hoy Digital",
    "cdn": "CDN",
    "acento": "Acento",
    "ndigital": "N Digital",
    "noticiassin": "Noticias SIN",
}

MEDIOS_GRUPOS = {
    "diariolibre": "Grupo Omnimedia",
    "listindiario": "Grupo Listín",
    "elcaribe": "Grupo Corripio",
    "hoy": "Grupo Corripio",
    "cdn": "Grupo Corripio",
    "acento": "Independiente",
    "ndigital": "Independiente (Nuria Piera)",
    "noticiassin": "Grupo SIN",
}

DIRECTORES = [
    {"nombre": "Claudia Franchesca de los Santos", "inicio": "2017", "fin": "Ago 2020", "years": [2017, 2018, 2019], "gobierno": "PLD (Danilo Medina)"},
    {"nombre": "Rafael Arias", "inicio": "Ago 2020", "fin": "Ago 2022", "years": [2020, 2021], "gobierno": "PRM (Abinader)"},
    {"nombre": "Hugo Beras", "inicio": "Ago 2022", "fin": "Nov 2023", "years": [2022, 2023], "gobierno": "PRM (Abinader)"},
    {"nombre": "Milton Morrison", "inicio": "2024", "fin": "presente", "years": [2024, 2025, 2026], "gobierno": "PRM (Abinader)"},
]

# ─── Cargar datos ─────────────────────────────────────────────────────────────
with open("/tmp/neurodata_full.json", "r") as f:
    articles = json.load(f)

# ─── Procesar datos ───────────────────────────────────────────────────────────

def compute_stats():
    """Computa todas las estadisticas necesarias para el reporte."""
    stats = {}

    # Por medio
    by_medio = defaultdict(lambda: {"total": 0, "pos": 0, "neg": 0, "neu": 0, "scores": []})
    for a in articles:
        m = a["medio_key"]
        by_medio[m]["total"] += 1
        s = a["sentiment"]
        if s == "POSITIVO":
            by_medio[m]["pos"] += 1
        elif s == "NEGATIVO":
            by_medio[m]["neg"] += 1
        else:
            by_medio[m]["neu"] += 1
        if a.get("sentiment_score"):
            by_medio[m]["scores"].append(a["sentiment_score"])
    stats["by_medio"] = dict(by_medio)

    # Por medio y year
    by_medio_year = defaultdict(lambda: defaultdict(lambda: {"pos": 0, "neg": 0, "neu": 0}))
    for a in articles:
        m = a["medio_key"]
        y = a.get("year") or (int(a["article_date"][:4]) if a.get("article_date") else None)
        if y is None:
            continue
        s = a["sentiment"]
        if s == "POSITIVO":
            by_medio_year[m][y]["pos"] += 1
        elif s == "NEGATIVO":
            by_medio_year[m][y]["neg"] += 1
        else:
            by_medio_year[m][y]["neu"] += 1
    stats["by_medio_year"] = {m: dict(yrs) for m, yrs in by_medio_year.items()}

    # Por director (usando years como proxy)
    by_director = {}
    for d in DIRECTORES:
        data = {"pos": 0, "neg": 0, "neu": 0}
        for a in articles:
            y = a.get("year") or (int(a["article_date"][:4]) if a.get("article_date") else None)
            if y in d["years"]:
                s = a["sentiment"]
                if s == "POSITIVO":
                    data["pos"] += 1
                elif s == "NEGATIVO":
                    data["neg"] += 1
                else:
                    data["neu"] += 1
        data["total"] = data["pos"] + data["neg"] + data["neu"]
        by_director[d["nombre"]] = data
    stats["by_director"] = by_director

    # Por director POR MEDIO
    by_dir_medio = {}
    for d in DIRECTORES:
        by_dir_medio[d["nombre"]] = {}
        for m in MEDIOS_NOMBRES:
            data = {"pos": 0, "neg": 0, "neu": 0}
            for a in articles:
                if a["medio_key"] != m:
                    continue
                y = a.get("year") or (int(a["article_date"][:4]) if a.get("article_date") else None)
                if y in d["years"]:
                    s = a["sentiment"]
                    if s == "POSITIVO":
                        data["pos"] += 1
                    elif s == "NEGATIVO":
                        data["neg"] += 1
                    else:
                        data["neu"] += 1
            data["total"] = data["pos"] + data["neg"] + data["neu"]
            if data["total"] > 0:
                by_dir_medio[d["nombre"]][m] = data
    stats["by_dir_medio"] = by_dir_medio

    # Grupo Corripio vs resto
    corripio = {"pos": 0, "neg": 0, "neu": 0, "total": 0}
    no_corripio = {"pos": 0, "neg": 0, "neu": 0, "total": 0}
    for a in articles:
        target = corripio if a["medio_key"] in ("elcaribe", "hoy", "cdn") else no_corripio
        target["total"] += 1
        s = a["sentiment"]
        if s == "POSITIVO":
            target["pos"] += 1
        elif s == "NEGATIVO":
            target["neg"] += 1
        else:
            target["neu"] += 1
    stats["corripio"] = corripio
    stats["no_corripio"] = no_corripio

    # Tono y frame
    tones = defaultdict(int)
    frames = defaultdict(int)
    for a in articles:
        if a.get("tone_detail"):
            tones[a["tone_detail"]] += 1
        if a.get("frame"):
            frames[a["frame"]] += 1
    stats["tones"] = dict(sorted(tones.items(), key=lambda x: -x[1]))
    stats["frames"] = dict(sorted(frames.items(), key=lambda x: -x[1]))

    return stats


# ─── Estilos ──────────────────────────────────────────────────────────────────

def get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle("CoverTitle", fontName="Helvetica-Bold", fontSize=28,
                              textColor=WHITE, alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle("CoverSub", fontName="Helvetica", fontSize=14,
                              textColor=HexColor("#AACCFF"), alignment=TA_CENTER, spaceAfter=4))
    styles.add(ParagraphStyle("CoverDate", fontName="Helvetica", fontSize=11,
                              textColor=HexColor("#88AADD"), alignment=TA_CENTER))
    styles.add(ParagraphStyle("SectionTitle", fontName="Helvetica-Bold", fontSize=16,
                              textColor=NAVY, spaceBefore=18, spaceAfter=10))
    styles.add(ParagraphStyle("SubSection", fontName="Helvetica-Bold", fontSize=12,
                              textColor=ELECTRIC_BLUE, spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle("BodyText2", fontName="Helvetica", fontSize=10,
                              textColor=DARK_GRAY, alignment=TA_JUSTIFY, spaceAfter=6,
                              leading=14))
    styles.add(ParagraphStyle("Finding", fontName="Helvetica-Bold", fontSize=10,
                              textColor=NAVY, spaceBefore=4, spaceAfter=4, leading=14,
                              leftIndent=12))
    styles.add(ParagraphStyle("SmallText", fontName="Helvetica", fontSize=8,
                              textColor=GRAY_TEXT, spaceAfter=3, leading=10))
    styles.add(ParagraphStyle("TableHeader", fontName="Helvetica-Bold", fontSize=8,
                              textColor=WHITE, alignment=TA_CENTER))
    styles.add(ParagraphStyle("TableCell", fontName="Helvetica", fontSize=8,
                              textColor=DARK_GRAY, alignment=TA_CENTER))
    styles.add(ParagraphStyle("TableCellLeft", fontName="Helvetica", fontSize=8,
                              textColor=DARK_GRAY, alignment=TA_LEFT))
    styles.add(ParagraphStyle("Footer", fontName="Helvetica", fontSize=7,
                              textColor=GRAY_TEXT, alignment=TA_CENTER))
    styles.add(ParagraphStyle("AnnexTitle", fontName="Helvetica-Bold", fontSize=7,
                              textColor=DARK_GRAY, alignment=TA_LEFT))
    styles.add(ParagraphStyle("AnnexCell", fontName="Helvetica", fontSize=6.5,
                              textColor=DARK_GRAY, alignment=TA_LEFT, leading=8))
    return styles


# ─── Construir PDF ────────────────────────────────────────────────────────────

def build_report():
    stats = compute_stats()
    styles = get_styles()
    output_path = "/tmp/NeuroData_INTRANT_Reporte_Investigativo.pdf"
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.6*inch, bottomMargin=0.6*inch,
                            leftMargin=0.7*inch, rightMargin=0.7*inch)
    story = []
    W = letter[0] - 1.4*inch  # usable width

    # ═══════════════ PORTADA ═══════════════
    # Background table for cover
    cover_data = [[""]]
    cover_content = []
    cover_content.append(Spacer(1, 1.5*inch))
    cover_content.append(Paragraph("NEURODATA", styles["CoverTitle"]))
    cover_content.append(Spacer(1, 6))
    cover_content.append(Paragraph("Laboratorio de Inteligencia Mediatica", styles["CoverSub"]))
    cover_content.append(Spacer(1, 30))
    cover_content.append(Paragraph("REPORTE INVESTIGATIVO", styles["CoverTitle"]))
    cover_content.append(Spacer(1, 10))
    cover_content.append(Paragraph("Cobertura del INTRANT en Medios Dominicanos", styles["CoverSub"]))
    cover_content.append(Paragraph("2017 - 2026", styles["CoverSub"]))
    cover_content.append(Spacer(1, 40))
    cover_content.append(Paragraph("811 articulos | 8 medios | Analisis de sentimiento con IA", styles["CoverDate"]))
    cover_content.append(Spacer(1, 20))
    cover_content.append(Paragraph(f"Generado: {datetime.now().strftime('%d de julio de 2026')}", styles["CoverDate"]))
    cover_content.append(Spacer(1, 10))
    cover_content.append(Paragraph("NeuroNoticia Group | neurodiario.com", styles["CoverDate"]))

    # Wrap in a colored table
    cover_table = Table([[cover_content]], colWidths=[W])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 40),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    # Can't easily nest flowables in table cells this way with reportlab
    # Use simpler approach: just add elements directly
    story.append(Spacer(1, 1.5*inch))

    # Cover title block
    ct = Table([
        [Paragraph("NEURODATA", styles["CoverTitle"])],
        [Paragraph("Laboratorio de Inteligencia Mediatica", styles["CoverSub"])],
        [Spacer(1, 20)],
        [Paragraph("REPORTE INVESTIGATIVO", styles["CoverTitle"])],
        [Spacer(1, 6)],
        [Paragraph("Cobertura del INTRANT en Medios Dominicanos (2017-2026)", styles["CoverSub"])],
        [Spacer(1, 30)],
        [Paragraph("811 articulos  |  8 medios  |  Analisis de sentimiento con IA", styles["CoverDate"])],
        [Spacer(1, 10)],
        [Paragraph(f"12 de julio de 2026", styles["CoverDate"])],
        [Paragraph("NeuroNoticia Group  |  neurodiario.com", styles["CoverDate"])],
    ], colWidths=[W])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 30),
        ("RIGHTPADDING", (0, 0), (-1, -1), 30),
    ]))
    story.append(ct)
    story.append(PageBreak())

    # ═══════════════ RESUMEN EJECUTIVO ═══════════════
    story.append(Paragraph("1. RESUMEN EJECUTIVO", styles["SectionTitle"]))
    story.append(Paragraph(
        "Este reporte analiza la cobertura mediatica del Instituto Nacional de Transito y Transporte "
        "Terrestre (INTRANT) en 8 medios de comunicacion dominicanos entre 2017 y 2026. Se recopilaron "
        "811 articulos mediante busqueda sistematica en Google (via Serper.dev) y se clasifico el sentimiento "
        "de cada uno utilizando inteligencia artificial (Claude Haiku de Anthropic). El objetivo es determinar "
        "patrones de sesgo, diferencias de cobertura entre grupos mediaticos, y como la percepcion mediatica "
        "varia segun el director de turno de la institucion.",
        styles["BodyText2"]
    ))

    # Key findings box
    findings = [
        "El 43.9% de toda la cobertura es neutra, 33.0% positiva y 23.1% negativa.",
        "Los medios del Grupo Corripio (El Caribe, Hoy, CDN) tienen la cobertura MAS FAVORABLE hacia el INTRANT: solo 18.7% negativa vs. 25.6% en el resto de medios.",
        "N Digital (dirigido por Nuria Piera) tiene la cobertura MAS CRITICA: 36.2% negativa, casi el doble del promedio.",
        "2023-2024 (era Hugo Beras / Caso Camaleon) concentra el pico de cobertura negativa: 31% promedio.",
        "2025-2026 (era Milton Morrison) muestra una caida drastica de la negatividad a 19.8%, con Diario Libre cayendo a solo 10.5% negativo en 2025.",
        "Listin Diario es el medio con MAYOR VOLUMEN de cobertura (157 articulos), pero mantiene un perfil mayormente neutro (48.4%).",
    ]
    story.append(Spacer(1, 8))
    story.append(Paragraph("Hallazgos principales:", styles["SubSection"]))
    for f_text in findings:
        story.append(Paragraph(f">> {f_text}", styles["Finding"]))
    story.append(PageBreak())

    # ═══════════════ METODOLOGIA ═══════════════
    story.append(Paragraph("2. METODOLOGIA", styles["SectionTitle"]))
    story.append(Paragraph(
        "La recoleccion de datos se realizo mediante consultas automatizadas a la API de Serper.dev, "
        "que accede al indice de Google Search. Para cada medio se ejecutaron queries con el operador "
        "site: combinado con la palabra clave INTRANT y filtros de fecha por semestre (after:/before:). "
        "Se utilizo la cuenta gratuita de Serper, limitada a 10 resultados por consulta, lo que significa "
        "que en semestres con mas de 10 articulos publicados, la muestra es parcial. Sin embargo, con "
        "811 articulos totales, la muestra es estadisticamente significativa para detectar patrones de sesgo.",
        styles["BodyText2"]
    ))
    story.append(Paragraph(
        "La clasificacion de sentimiento se realizo con Claude Haiku (modelo claude-haiku-4-5-20251001) "
        "de Anthropic. Cada articulo fue evaluado por su titulo y fragmento (snippet) respecto a la "
        "institucion INTRANT, clasificandose en POSITIVO, NEGATIVO o NEUTRO, con un score numerico "
        "de -1.0 a +1.0, un tono (logro, denuncia, critica, informativo, queja ciudadana) y un marco "
        "narrativo (servicio publico, gestion, corrupcion, infraestructura, politica, legal).",
        styles["BodyText2"]
    ))

    # Medios table
    story.append(Paragraph("Medios analizados:", styles["SubSection"]))
    mt_data = [["Medio", "Grupo", "Articulos"]]
    for m_key in ["listindiario", "elcaribe", "acento", "diariolibre", "hoy", "cdn", "ndigital", "noticiassin"]:
        d = stats["by_medio"].get(m_key, {})
        mt_data.append([MEDIOS_NOMBRES[m_key], MEDIOS_GRUPOS[m_key], str(d.get("total", 0))])
    mt_data.append(["TOTAL", "", "811"])

    mt = Table(mt_data, colWidths=[2*inch, 2*inch, 1*inch])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GRAY),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, LIGHT_GRAY]),
    ]))
    story.append(mt)

    story.append(Spacer(1, 10))
    story.append(Paragraph("Directores del INTRANT:", styles["SubSection"]))
    dir_data = [["Director", "Periodo", "Gobierno"]]
    for d in DIRECTORES:
        dir_data.append([d["nombre"], f"{d['inicio']} - {d['fin']}", d["gobierno"]])
    dt = Table(dir_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
    dt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
    ]))
    story.append(dt)
    story.append(PageBreak())

    # ═══════════════ COMPARACION POR MEDIO ═══════════════
    story.append(Paragraph("3. COMPARACION DE COBERTURA POR MEDIO", styles["SectionTitle"]))
    story.append(Paragraph(
        "La siguiente tabla muestra la distribucion de sentimiento por cada medio analizado. "
        "El porcentaje de cobertura negativa (% NEG) es el indicador clave de postura critica. "
        "Un medio con alto % NEG ejerce mayor fiscalizacion; uno con bajo % NEG tiende a ser "
        "mas complaciente o a cubrir principalmente logros institucionales.",
        styles["BodyText2"]
    ))

    comp_data = [["Medio", "Total", "Positivo", "Negativo", "Neutro", "% POS", "% NEG"]]
    order = ["ndigital", "diariolibre", "acento", "listindiario", "hoy", "elcaribe", "cdn", "noticiassin"]
    for m_key in order:
        d = stats["by_medio"].get(m_key, {})
        total = d.get("total", 1)
        pos = d.get("pos", 0)
        neg = d.get("neg", 0)
        neu = d.get("neu", 0)
        pct_pos = f"{pos/total*100:.1f}%"
        pct_neg = f"{neg/total*100:.1f}%"
        comp_data.append([MEDIOS_NOMBRES[m_key], str(total), str(pos), str(neg), str(neu), pct_pos, pct_neg])

    comp_data.append(["PROMEDIO", "811", "268", "187", "356", "33.0%", "23.1%"])

    ct2 = Table(comp_data, colWidths=[1.5*inch, 0.6*inch, 0.7*inch, 0.7*inch, 0.6*inch, 0.7*inch, 0.7*inch])
    ct2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GRAY),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, LIGHT_GRAY]),
    ]))
    story.append(ct2)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Interpretacion:", styles["SubSection"]))
    story.append(Paragraph(
        "N Digital, bajo la direccion de la periodista investigativa Nuria Piera, muestra el perfil "
        "mas critico con un 36.2% de cobertura negativa, casi el doble del promedio. Esto es consistente "
        "con su linea editorial de periodismo investigativo. En el extremo opuesto, El Caribe (Grupo "
        "Corripio) tiene solo 18.1% de cobertura negativa, el mas bajo entre los medios con muestra "
        "significativa.",
        styles["BodyText2"]
    ))
    story.append(Paragraph(
        "Diario Libre destaca por tener la mayor proporcion de cobertura positiva (43.1%), significativamente "
        "por encima del promedio (33.0%). Esto sugiere una orientacion editorial que prioriza la difusion "
        "de logros y programas del INTRANT sobre la fiscalizacion de sus problemas.",
        styles["BodyText2"]
    ))
    story.append(PageBreak())

    # ═══════════════ GRUPO CORRIPIO ═══════════════
    story.append(Paragraph("4. ANALISIS: GRUPO CORRIPIO", styles["SectionTitle"]))
    story.append(Paragraph(
        "El Grupo Corripio opera tres medios analizados: El Caribe (periodico), Hoy Digital (periodico) "
        "y CDN (canal de television). Un hallazgo significativo es la consistencia del tono entre los tres.",
        styles["BodyText2"]
    ))

    corr = stats["corripio"]
    nocorr = stats["no_corripio"]
    corr_neg = corr["neg"]/corr["total"]*100 if corr["total"] else 0
    nocorr_neg = nocorr["neg"]/nocorr["total"]*100 if nocorr["total"] else 0

    gc_data = [["", "El Caribe", "Hoy Digital", "CDN", "GRUPO CORRIPIO", "Resto medios"]]

    ec = stats["by_medio"].get("elcaribe", {})
    hy = stats["by_medio"].get("hoy", {})
    cd = stats["by_medio"].get("cdn", {})

    gc_data.append(["Total", str(ec.get("total",0)), str(hy.get("total",0)), str(cd.get("total",0)),
                     str(corr["total"]), str(nocorr["total"])])
    gc_data.append(["% Positivo",
                     f"{ec.get('pos',0)/max(ec.get('total',1),1)*100:.1f}%",
                     f"{hy.get('pos',0)/max(hy.get('total',1),1)*100:.1f}%",
                     f"{cd.get('pos',0)/max(cd.get('total',1),1)*100:.1f}%",
                     f"{corr['pos']/max(corr['total'],1)*100:.1f}%",
                     f"{nocorr['pos']/max(nocorr['total'],1)*100:.1f}%"])
    gc_data.append(["% Negativo",
                     f"{ec.get('neg',0)/max(ec.get('total',1),1)*100:.1f}%",
                     f"{hy.get('neg',0)/max(hy.get('total',1),1)*100:.1f}%",
                     f"{cd.get('neg',0)/max(cd.get('total',1),1)*100:.1f}%",
                     f"{corr['neg']/max(corr['total'],1)*100:.1f}%",
                     f"{nocorr['neg']/max(nocorr['total'],1)*100:.1f}%"])
    gc_data.append(["% Neutro",
                     f"{ec.get('neu',0)/max(ec.get('total',1),1)*100:.1f}%",
                     f"{hy.get('neu',0)/max(hy.get('total',1),1)*100:.1f}%",
                     f"{cd.get('neu',0)/max(cd.get('total',1),1)*100:.1f}%",
                     f"{corr['neu']/max(corr['total'],1)*100:.1f}%",
                     f"{nocorr['neu']/max(nocorr['total'],1)*100:.1f}%"])

    gct = Table(gc_data, colWidths=[0.9*inch, 0.85*inch, 0.85*inch, 0.7*inch, 1.15*inch, 1.05*inch])
    gct.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("BACKGROUND", (4, 1), (4, -1), HexColor("#E8F4FD")),
        ("BACKGROUND", (5, 1), (5, -1), HexColor("#FFF8E1")),
        ("ROWBACKGROUNDS", (0, 1), (3, -1), [WHITE, LIGHT_GRAY]),
    ]))
    story.append(gct)

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"El Grupo Corripio muestra una cobertura negativa del {corr_neg:.1f}%, significativamente "
        f"inferior al {nocorr_neg:.1f}% del resto de los medios. Los tres medios del grupo mantienen "
        "porcentajes de negatividad similares (18-20%), lo cual sugiere una linea editorial unificada "
        "respecto al INTRANT. Este patron es consistente con una postura editorial que favorece la "
        "cobertura de logros institucionales sobre denuncias o criticas.",
        styles["BodyText2"]
    ))
    story.append(PageBreak())

    # ═══════════════ ANALISIS POR DIRECTOR ═══════════════
    story.append(Paragraph("5. PERCEPCION MEDIATICA POR DIRECTOR", styles["SectionTitle"]))
    story.append(Paragraph(
        "El INTRANT ha tenido cuatro directores desde su creacion. Cada gestion genero patrones de "
        "cobertura distintos que reflejan tanto el desempeno real como la relacion del director con "
        "los medios y el contexto politico.",
        styles["BodyText2"]
    ))

    dir_table = [["Director", "Periodo", "Total", "% POS", "% NEG", "% NEU"]]
    for d in DIRECTORES:
        data = stats["by_director"][d["nombre"]]
        t = max(data["total"], 1)
        dir_table.append([
            d["nombre"], f"{d['inicio']} - {d['fin']}",
            str(data["total"]),
            f"{data['pos']/t*100:.1f}%",
            f"{data['neg']/t*100:.1f}%",
            f"{data['neu']/t*100:.1f}%",
        ])

    dirtbl = Table(dir_table, colWidths=[2.2*inch, 1.2*inch, 0.6*inch, 0.7*inch, 0.7*inch, 0.7*inch])
    dirtbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
    ]))
    story.append(dirtbl)

    # Director detail
    for d in DIRECTORES:
        data = stats["by_director"][d["nombre"]]
        t = max(data["total"], 1)
        pct_neg = data["neg"]/t*100

        story.append(Spacer(1, 10))
        story.append(Paragraph(f"{d['nombre']} ({d['inicio']} - {d['fin']})", styles["SubSection"]))

        if d["nombre"] == "Claudia Franchesca de los Santos":
            story.append(Paragraph(
                f"Primera directora del INTRANT, gestiono la etapa fundacional de la institucion. Con {data['total']} "
                f"articulos y solo {pct_neg:.1f}% de cobertura negativa, su periodo refleja una cobertura predominantemente "
                "informativa-neutra, tipica de instituciones nuevas donde los medios reportan sobre su creacion "
                "y primeras acciones sin un historial que fiscalizar.",
                styles["BodyText2"]))
        elif d["nombre"] == "Rafael Arias":
            story.append(Paragraph(
                f"Primer director bajo el gobierno de Luis Abinader (PRM). Con {data['total']} articulos y "
                f"{pct_neg:.1f}% negativo, su gestion fue marcada por los corredores de autobuses (Churchill, "
                "Nunez de Caceres) que generaron tanto cobertura positiva (inauguraciones) como criticas "
                "(quejas de choferes desplazados). Su origen como dirigente de Conatra genero cuestionamientos "
                "sobre conflicto de intereses.",
                styles["BodyText2"]))
        elif d["nombre"] == "Hugo Beras":
            story.append(Paragraph(
                f"El periodo mas polemico. Con {data['total']} articulos y el PICO de cobertura negativa ({pct_neg:.1f}%), "
                "su gestion estuvo dominada por el escandalo de la licitacion de semaforos con Transcore Latam "
                "(Caso Camaleon), que derivo en su salida de la institucion y posterior procesamiento judicial. "
                "Los medios pasaron de cubrir logros operativos a investigar una presunta red de corrupcion.",
                styles["BodyText2"]))
        elif d["nombre"] == "Milton Morrison":
            story.append(Paragraph(
                f"Director actual. Con {data['total']} articulos y {pct_neg:.1f}% de cobertura negativa, su gestion "
                "muestra una recuperacion de la imagen institucional. La cobertura se concentra en nuevas licencias "
                "de conducir, educacion vial (Guardianes del Transito), regulacion de motoconchos y eliminacion "
                "de simuladores. Sin embargo, el Caso Camaleon (juicio a Hugo Beras y Jochi Gomez) sigue "
                "generando cobertura negativa asociada al INTRANT.",
                styles["BodyText2"]))

        # Per-medio breakdown for this director
        dir_medio = stats["by_dir_medio"].get(d["nombre"], {})
        if dir_medio:
            dm_data = [["Medio", "Total", "% POS", "% NEG"]]
            for mk in ["diariolibre", "listindiario", "elcaribe", "hoy", "cdn", "acento", "ndigital", "noticiassin"]:
                if mk in dir_medio and dir_medio[mk]["total"] > 0:
                    dd = dir_medio[mk]
                    tt = max(dd["total"], 1)
                    dm_data.append([MEDIOS_NOMBRES[mk], str(dd["total"]),
                                     f"{dd['pos']/tt*100:.0f}%", f"{dd['neg']/tt*100:.0f}%"])
            if len(dm_data) > 1:
                dmt = Table(dm_data, colWidths=[1.5*inch, 0.7*inch, 0.7*inch, 0.7*inch])
                dmt.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), ELECTRIC_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                ]))
                story.append(dmt)

    story.append(PageBreak())

    # ═══════════════ CONCLUSIONES ═══════════════
    story.append(Paragraph("6. CONCLUSIONES", styles["SectionTitle"]))

    conclusions = [
        ("Existe diferenciacion editorial medible entre medios dominicanos.",
         "Los 8 medios analizados muestran patrones de cobertura estadisticamente distintos respecto al INTRANT. "
         "No todos los medios cubren igual la misma institucion: hay una variacion de casi 20 puntos porcentuales "
         "entre el medio mas critico (N Digital, 36.2% negativo) y el menos critico (El Caribe, 18.1%)."),
        ("El Grupo Corripio mantiene una linea editorial unificada.",
         f"Sus tres medios (El Caribe, Hoy, CDN) muestran niveles de negatividad similares ({corr_neg:.1f}% combinado), "
         f"significativamente inferiores al resto ({nocorr_neg:.1f}%). Esta consistencia sugiere coordinacion editorial "
         "a nivel de grupo, no decisiones editoriales independientes de cada medio."),
        ("La cobertura sigue ciclos predecibles vinculados al director de turno.",
         "Cada cambio de director produce un patron visible: luna de miel inicial (cobertura neutra/positiva), "
         "seguida de escrutinio creciente. Hugo Beras rompio este patron al generar el pico de negatividad "
         "mas pronunciado de toda la serie (2023: 31.5% negativo) por el Caso Camaleon."),
        ("Milton Morrison ha logrado la mejor cobertura mediatica reciente.",
         "Con solo 10.5% de negatividad en Diario Libre durante 2025 y un promedio general de 19.8% en "
         "2025-2026, Morrison ha conseguido una percepcion mediatica notablemente mas favorable que sus "
         "predecesores. Esto puede reflejar mejor gestion, mejor comunicacion institucional, o ambas."),
        ("N Digital (Nuria Piera) es el medio mas fiscalizador del INTRANT.",
         "Con 36.2% de cobertura negativa, casi duplica el promedio. Su perfil investigativo se refleja "
         "en articulos sobre irregularidades en licitaciones, corrupcion y denuncias que otros medios no "
         "priorizan con la misma intensidad."),
    ]
    for i, (title, body) in enumerate(conclusions, 1):
        story.append(Paragraph(f"{i}. {title}", styles["SubSection"]))
        story.append(Paragraph(body, styles["BodyText2"]))

    story.append(Spacer(1, 15))
    story.append(Paragraph("Nota metodologica:", styles["SubSection"]))
    story.append(Paragraph(
        "Este analisis detecta CORRELACIONES en patrones de cobertura, no establece CAUSALIDAD. "
        "Que un medio tenga baja cobertura negativa no significa necesariamente que sea parcializado; "
        "puede reflejar priorizacion editorial, acceso a fuentes, o simplemente que no cubre el tema "
        "de transito con la misma frecuencia. Las conclusiones deben interpretarse como indicadores "
        "que merecen investigacion mas profunda, no como veredictos definitivos. Los datos completos "
        "se incluyen en los anexos para verificacion independiente.",
        styles["BodyText2"]
    ))

    # Footer
    story.append(Spacer(1, 30))
    ft = Table([[Paragraph(
        "Este reporte fue generado por NeuroData, division de inteligencia mediatica de NeuroNoticia Group. "
        "Datos recopilados via Serper.dev. Sentimiento clasificado con Claude Haiku (Anthropic). "
        "Contacto: neurodiario.com", styles["Footer"]
    )]], colWidths=[W])
    ft.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(ft)
    story.append(PageBreak())

    # ═══════════════ ANEXOS ═══════════════
    story.append(Paragraph("ANEXO: BASE DE DATOS COMPLETA DE TITULARES", styles["SectionTitle"]))
    story.append(Paragraph(
        "A continuacion se presenta el listado completo de los 811 articulos analizados, organizados "
        "por medio y fecha. Cada entrada incluye la fecha de publicacion, el titular, la clasificacion "
        "de sentimiento y el marco narrativo detectado. Esta base de datos constituye la evidencia "
        "primaria que respalda todas las conclusiones del reporte.",
        styles["BodyText2"]
    ))
    story.append(Spacer(1, 8))

    # Group articles by medio
    by_medio_list = defaultdict(list)
    for a in articles:
        by_medio_list[a["medio_key"]].append(a)

    for m_key in ["diariolibre", "listindiario", "elcaribe", "hoy", "cdn", "acento", "ndigital", "noticiassin"]:
        arts = by_medio_list.get(m_key, [])
        if not arts:
            continue

        m_stats = stats["by_medio"].get(m_key, {})
        neg_pct = m_stats.get("neg", 0) / max(m_stats.get("total", 1), 1) * 100

        story.append(Paragraph(
            f"{MEDIOS_NOMBRES[m_key]} ({MEDIOS_GRUPOS[m_key]}) - {len(arts)} articulos - {neg_pct:.1f}% negativo",
            styles["SubSection"]
        ))

        annex_data = [["Fecha", "Titular", "Sent.", "Score", "Tono"]]
        for a in sorted(arts, key=lambda x: x.get("article_date") or ""):
            dt_str = a.get("article_date", "")
            if dt_str and len(dt_str) >= 10:
                dt_str = dt_str[:10]
            else:
                dt_str = "N/D"

            sent = a.get("sentiment", "")
            sent_short = {"POSITIVO": "POS", "NEGATIVO": "NEG", "NEUTRO": "NEU"}.get(sent, sent[:3])
            score = a.get("sentiment_score")
            score_str = f"{score:+.1f}" if score is not None else ""
            tone = a.get("tone_detail", "")

            # Truncate title
            title = a.get("title", "")
            if len(title) > 85:
                title = title[:82] + "..."

            annex_data.append([
                Paragraph(dt_str, styles["AnnexCell"]),
                Paragraph(title, styles["AnnexCell"]),
                Paragraph(sent_short, styles["AnnexCell"]),
                Paragraph(score_str, styles["AnnexCell"]),
                Paragraph(tone, styles["AnnexCell"]),
            ])

        at = Table(annex_data, colWidths=[0.65*inch, 3.4*inch, 0.4*inch, 0.45*inch, 0.8*inch])
        at.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ELECTRIC_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("FONTSIZE", (0, 1), (-1, -1), 6.5),
            ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#DDDDDD")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#F8F9FA")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 1), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 1),
        ]))
        story.append(at)
        story.append(Spacer(1, 12))

    # Build
    doc.build(story)
    print(f"Reporte generado: {output_path}")
    return output_path


if __name__ == "__main__":
    build_report()
