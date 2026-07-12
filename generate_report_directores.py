"""
generate_report_directores.py — NeuroData
"Los Rostros del INTRANT: Como los Medios Tratan a Cada Director"
Reporte premium con branding NeuroDiario.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, PageBreak, NextPageTemplate
)
import json, os
from collections import defaultdict

# ─── Colors ──────────────────────────────────────────────────────────────────
NAVY = HexColor("#0B1F3B")
NAVY_L = HexColor("#122A4F")
BLUE = HexColor("#0077FF")
BLUE_L = HexColor("#3399FF")
BLUE_DIM = HexColor("#1A3A5C")
CYAN = HexColor("#88AADD")
WHITE = HexColor("#FFFFFF")
LGRAY = HexColor("#F2F4F7")
MGRAY = HexColor("#E0E4EA")
DGRAY = HexColor("#666666")
DARK = HexColor("#222222")
GREEN = HexColor("#27AE60")
RED = HexColor("#E74C3C")
AMBER = HexColor("#F39C12")
PURPLE = HexColor("#8E44AD")

W_PAGE, H_PAGE = letter
M = 0.7 * inch
WC = W_PAGE - 2 * M

# ─── Data ────────────────────────────────────────────────────────────────────
with open("/tmp/neurodata_full.json") as f:
    ALL = json.load(f)

MEDIOS = {
    "diariolibre": ("Diario Libre", "Omnimedia"),
    "listindiario": ("Listin Diario", "Listin"),
    "elcaribe": ("El Caribe", "Corripio"),
    "hoy": ("Hoy Digital", "Corripio"),
    "cdn": ("CDN", "Corripio"),
    "acento": ("Acento", "Independiente"),
    "ndigital": ("N Digital", "Independiente"),
    "noticiassin": ("Noticias SIN", "SIN"),
}

DIRS = [
    {"key": "Claudia Franchesca", "name": "Claudia Franchesca de los Santos",
     "period": "2017 - Ago 2020", "gov": "PLD (Danilo Medina)", "color": PURPLE},
    {"key": "Rafael Arias INTRANT", "name": "Rafael Arias",
     "period": "Ago 2020 - Ago 2022", "gov": "PRM (Abinader)", "color": DGRAY},
    {"key": "Hugo Beras", "name": "Hugo Beras",
     "period": "Ago 2022 - Nov 2023", "gov": "PRM (Abinader)", "color": RED},
    {"key": "Milton Morrison", "name": "Milton Morrison",
     "period": "2024 - presente", "gov": "PRM (Abinader)", "color": GREEN},
]

def pct(n, t): return f"{n/max(t,1)*100:.1f}%"

def get_dir_data(key):
    arts = [a for a in ALL if a["keyword"] == key]
    total = len(arts)
    pos = sum(1 for a in arts if a["sentiment"] == "POSITIVO")
    neg = sum(1 for a in arts if a["sentiment"] == "NEGATIVO")
    neu = total - pos - neg
    by_medio = defaultdict(lambda: {"t":0,"p":0,"n":0,"u":0})
    for a in arts:
        m = a["medio_key"]; by_medio[m]["t"] += 1
        if a["sentiment"] == "POSITIVO": by_medio[m]["p"] += 1
        elif a["sentiment"] == "NEGATIVO": by_medio[m]["n"] += 1
        else: by_medio[m]["u"] += 1
    by_year = defaultdict(lambda: {"t":0,"p":0,"n":0,"u":0})
    for a in arts:
        y = a.get("year")
        if y: by_year[y]["t"] += 1
        if a["sentiment"] == "POSITIVO": by_year[y]["p"] += 1
        elif a["sentiment"] == "NEGATIVO": by_year[y]["n"] += 1
        else: by_year[y]["u"] += 1
    tones = defaultdict(int)
    frames = defaultdict(int)
    for a in arts:
        if a.get("tone_detail"): tones[a["tone_detail"]] += 1
        if a.get("frame"): frames[a["frame"]] += 1
    return {"arts": arts, "total": total, "pos": pos, "neg": neg, "neu": neu,
            "by_medio": dict(by_medio), "by_year": dict(by_year),
            "tones": dict(sorted(tones.items(), key=lambda x: -x[1])),
            "frames": dict(sorted(frames.items(), key=lambda x: -x[1]))}

# ─── Page Templates ─────────────────────────────────────────────────────────
def cover_page(c, doc):
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, 0, W_PAGE, H_PAGE, fill=1, stroke=0)
    c.setStrokeColor(BLUE); c.setLineWidth(3)
    c.line(M, H_PAGE - 1.4*inch, W_PAGE - M, H_PAGE - 1.4*inch)

    # Logo attempt
    for p in ["/app/1000700578.png", "/mnt/project/1000700578.png", "/tmp/neurodiario_logo.png"]:
        if os.path.exists(p):
            try: c.drawImage(p, W_PAGE/2-50, H_PAGE-1.3*inch, 100, 100, preserveAspectRatio=True, mask='auto')
            except: pass
            break

    # NEURODATA badge
    bw, bh = 170, 32; bx = W_PAGE/2 - bw/2; by = H_PAGE - 2.1*inch
    c.setFillColor(BLUE); c.roundRect(bx, by, bw, bh, 16, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W_PAGE/2, by + 9, "NEURODATA")

    # Title
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(W_PAGE/2, H_PAGE - 2.9*inch, "Los Rostros del INTRANT")
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W_PAGE/2, H_PAGE - 3.25*inch, "Como los Medios Tratan a Cada Director")
    c.setFillColor(BLUE_L); c.setFont("Helvetica", 12)
    c.drawCentredString(W_PAGE/2, H_PAGE - 3.7*inch, "Analisis de Cobertura Personal en 8 Medios Dominicanos")

    # Director boxes - 4 columns
    dirs_info = [
        ("Claudia\nFranchesca", "23", "art.", PURPLE),
        ("Rafael\nArias", "1", "art.", DGRAY),
        ("Hugo\nBeras", "201", "art.", RED),
        ("Milton\nMorrison", "114", "art.", GREEN),
    ]
    bw2 = 110; gap = 12; total = 4*bw2 + 3*gap; sx = W_PAGE/2 - total/2; by2 = H_PAGE - 5.4*inch
    for i, (name, val, lab, col) in enumerate(dirs_info):
        x = sx + i*(bw2+gap)
        c.setStrokeColor(col); c.setLineWidth(2)
        c.setFillColor(NAVY_L); c.roundRect(x, by2, bw2, 80, 8, fill=1, stroke=1)
        c.setFillColor(col); c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(x+bw2/2, by2+50, val)
        c.setFillColor(CYAN); c.setFont("Helvetica", 7)
        lines = name.split("\n")
        for j, line in enumerate(lines):
            c.drawCentredString(x+bw2/2, by2+30-j*10, line)
        c.drawCentredString(x+bw2/2, by2+8, lab)

    c.setFillColor(CYAN); c.setFont("Helvetica", 9)
    c.drawCentredString(W_PAGE/2, H_PAGE - 6.0*inch, "339 articulos por nombre de director  |  8 medios  |  2017 - 2026")
    c.setFillColor(BLUE); c.setFont("Helvetica", 11)
    c.drawCentredString(W_PAGE/2, 2.0*inch, "Fecha del reporte: 13 de julio de 2026")
    cbw = 160; c.setFillColor(BLUE)
    c.roundRect(W_PAGE/2-cbw/2, 1.4*inch, cbw, 30, 15, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W_PAGE/2, 1.49*inch, "CONFIDENCIAL")
    c.setFillColor(CYAN); c.setFont("Helvetica", 8)
    c.drawCentredString(W_PAGE/2, 0.8*inch, "neurodiario.com  |  La Inteligencia Informativa de Republica Dominicana")
    c.restoreState()

def hf(c, doc):
    c.saveState()
    c.setFillColor(NAVY); c.rect(0, H_PAGE-0.4*inch, W_PAGE, 0.4*inch, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 7)
    c.drawString(M, H_PAGE-0.27*inch, "NEURODIARIO  |  NEURODATA")
    c.setFont("Helvetica", 7)
    c.drawRightString(W_PAGE-M, H_PAGE-0.27*inch, "Los Rostros del INTRANT  |  Julio 2026")
    c.setStrokeColor(BLUE); c.setLineWidth(2)
    c.line(M, H_PAGE-0.42*inch, W_PAGE-M, H_PAGE-0.42*inch)
    c.setFillColor(NAVY); c.rect(0, 0, W_PAGE, 0.45*inch, fill=1, stroke=0)
    c.setFillColor(CYAN); c.setFont("Helvetica", 6.5)
    c.drawString(M, 0.18*inch, "NeuroDiario  |  La Inteligencia Informativa de Republica Dominicana")
    c.drawRightString(W_PAGE-M, 0.18*inch, f"Pagina {doc.page}")
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(W_PAGE/2, 0.08*inch, "Documento confidencial. Prohibida su reproduccion sin autorizacion.")
    c.restoreState()

# ─── Styles ──────────────────────────────────────────────────────────────────
def ST():
    return {
        "sec": ParagraphStyle("S", fontName="Helvetica-Bold", fontSize=15, textColor=NAVY, spaceBefore=14, spaceAfter=8),
        "sub": ParagraphStyle("Su", fontName="Helvetica-Bold", fontSize=11, textColor=BLUE, spaceBefore=10, spaceAfter=5),
        "body": ParagraphStyle("B", fontName="Helvetica", fontSize=9.5, textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=5, leading=13),
        "find": ParagraphStyle("F", fontName="Helvetica-Bold", fontSize=9.5, textColor=NAVY, spaceBefore=3, spaceAfter=3, leading=13, leftIndent=8),
        "sm": ParagraphStyle("Sm", fontName="Helvetica", fontSize=7.5, textColor=DGRAY, spaceAfter=2, leading=10),
        "ax": ParagraphStyle("Ax", fontName="Helvetica", fontSize=6, textColor=DARK, leading=7.5),
    }

def hbox(text, bg=NAVY, fg=WHITE):
    p = Paragraph(text, ParagraphStyle("hb", fontName="Helvetica-Bold", fontSize=9, textColor=fg, alignment=TA_CENTER, leading=13))
    t = Table([[p]], colWidths=[WC-20])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),("TOPPADDING",(0,0),(-1,-1),10),
        ("BOTTOMPADDING",(0,0),(-1,-1),10),("LEFTPADDING",(0,0),(-1,-1),15),("RIGHTPADDING",(0,0),(-1,-1),15)]))
    return t

def dir_header(name, period, gov, color, total, neg_pct):
    """Header visual para cada director."""
    data = [[
        Paragraph(f"<b>{name}</b>", ParagraphStyle("dh", fontName="Helvetica-Bold", fontSize=12, textColor=WHITE)),
        Paragraph(f"{period}<br/>{gov}", ParagraphStyle("dp", fontName="Helvetica", fontSize=8, textColor=CYAN, leading=11)),
        Paragraph(f"<b>{total}</b> art.", ParagraphStyle("dt", fontName="Helvetica-Bold", fontSize=14, textColor=WHITE, alignment=TA_CENTER)),
        Paragraph(f"<b>{neg_pct}</b> neg.", ParagraphStyle("dn", fontName="Helvetica-Bold", fontSize=11, textColor=AMBER, alignment=TA_CENTER)),
    ]]
    t = Table(data, colWidths=[2.2*inch, 1.5*inch, 0.9*inch, 0.9*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY_L),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(0,0),12),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LINEBELOW",(0,0),(-1,-1),3,color),
    ]))
    return t

# ─── Build ───────────────────────────────────────────────────────────────────
def build():
    st = ST()
    out = "/tmp/NeuroData_Rostros_INTRANT.pdf"
    doc = BaseDocTemplate(out, pagesize=letter, topMargin=0.6*inch, bottomMargin=0.6*inch, leftMargin=M, rightMargin=M)
    doc.addPageTemplates([
        PageTemplate(id='Cover', frames=[Frame(0,0,W_PAGE,H_PAGE,id='c')], onPage=cover_page),
        PageTemplate(id='Content', frames=[Frame(M,0.55*inch,WC,H_PAGE-1.15*inch,id='f')], onPage=hf),
    ])

    story = []
    story.append(NextPageTemplate('Content'))
    story.append(PageBreak())

    # Collect data
    dd = {d["key"]: get_dir_data(d["key"]) for d in DIRS}

    # ═══════════════ 1. RESUMEN ═══════════════
    story.append(Paragraph("1  El Hallazgo Central", st["sec"]))
    story.append(Paragraph(
        "Buscamos el nombre de cada director del INTRANT en 8 medios dominicanos para medir cuanta "
        "atencion mediatica recibe cada uno y con que tono. El resultado revela una asimetria extraordinaria: "
        "Hugo Beras acumula mas cobertura personal que los otros tres directores COMBINADOS. Pero el dato "
        "mas revelador no es Beras — es Rafael Arias, que dirigio el INTRANT durante dos anos y solo aparece "
        "mencionado por nombre en 1 articulo de 8 medios.", st["body"]))

    story.append(Spacer(1, 8))
    story.append(hbox(
        "Hugo Beras: 201 articulos (59%)  |  Milton Morrison: 114 (34%)  |  "
        "Claudia Franchesca: 23 (7%)  |  Rafael Arias: 1 (0.3%)<br/>"
        "Un director acumula casi el 60% de toda la cobertura personal. La fama mediatica "
        "del INTRANT es, en gran medida, la fama de Hugo Beras y el Caso Camaleon."))

    story.append(Spacer(1, 10))
    # Comparison table
    ct = [["Director", "Periodo", "Articulos", "% POS", "% NEG", "% NEU", "Perfil"]]
    profiles = {
        "Hugo Beras": "Polemico",
        "Milton Morrison": "Favorable",
        "Claudia Franchesca": "Invisible",
        "Rafael Arias INTRANT": "Inexistente",
    }
    for d in DIRS:
        data = dd[d["key"]]
        t = max(data["total"],1)
        ct.append([d["name"], d["period"], str(data["total"]),
                   pct(data["pos"],t), pct(data["neg"],t), pct(data["neu"],t),
                   profiles[d["key"]]])
    ct.append(["TOTAL", "", "339", "", "", "", ""])

    t1 = Table(ct, colWidths=[2*inch, 1.1*inch, 0.6*inch, 0.55*inch, 0.55*inch, 0.55*inch, 0.8*inch])
    t1.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
        ("ALIGN",(2,0),(-1,-1),"CENTER"),("GRID",(0,0),(-1,-1),0.5,MGRAY),
        ("BACKGROUND",(0,-1),(-1,-1),LGRAY),("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),[WHITE,LGRAY]),
    ]))
    story.append(t1)
    story.append(PageBreak())

    # ═══════════════ 2. HUGO BERAS ═══════════════
    hb = dd["Hugo Beras"]
    story.append(Paragraph("2  Hugo Beras: El Director Mas Mediatico", st["sec"]))
    story.append(dir_header("Hugo Beras", "Ago 2022 - Nov 2023", "PRM (Abinader)",
                            RED, hb["total"], pct(hb["neg"], hb["total"])))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Hugo Beras es, por mucho, el director del INTRANT que mas atencion mediatica ha recibido. Con 201 "
        "articulos que mencionan su nombre, acumula el 59% de toda la cobertura personal de directores. "
        "La razon es clara: el Caso Camaleon, la investigacion por la licitacion de semaforos con Transcore "
        "Latam que derivo en su arresto, juicio y la mayor crisis de corrupcion del INTRANT.", st["body"]))

    story.append(Spacer(1, 6))
    story.append(hbox(
        f"De 201 articulos, {hb['neg']} son negativos ({pct(hb['neg'],hb['total'])}). "
        f"El tono dominante es 'denuncia' — Hugo Beras paso de funcionario a acusado en la narrativa mediatica.",
        bg=HexColor("#2C1515"), fg=RED))

    # By medio
    story.append(Spacer(1, 8))
    story.append(Paragraph("Cobertura por medio", st["sub"]))
    hm = [["Medio", "Grupo", "Total", "% POS", "% NEG"]]
    for mk in ["diariolibre","listindiario","hoy","acento","elcaribe","cdn","noticiassin"]:
        if mk in hb["by_medio"]:
            d = hb["by_medio"][mk]; t = max(d["t"],1); nm,gr = MEDIOS[mk]
            hm.append([nm, gr, str(d["t"]), pct(d["p"],t), pct(d["n"],t)])
    t2 = Table(hm, colWidths=[1.3*inch, 0.9*inch, 0.5*inch, 0.6*inch, 0.6*inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),RED),("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
        ("ALIGN",(2,0),(-1,-1),"CENTER"),("GRID",(0,0),(-1,-1),0.5,MGRAY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LGRAY]),
    ]))
    story.append(t2)

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Diario Libre lidera la cobertura de Hugo Beras con 65 articulos, seguido de Listin Diario (50) y "
        "Hoy Digital (31). Acento (28) mantiene un enfoque investigativo. El Grupo Corripio combinado "
        "(El Caribe + Hoy + CDN = 54) cubre extensamente el caso pero con matices: CDN tiene solo 10 "
        "articulos, significativamente menos que sus hermanos de grupo.", st["body"]))

    # Tones
    story.append(Paragraph("Tonos dominantes", st["sub"]))
    top_tones = list(hb["tones"].items())[:5]
    for tone, count in top_tones:
        story.append(Paragraph(f"<b>&gt;&gt;</b> {tone}: {count} articulos", st["find"]))

    story.append(PageBreak())

    # ═══════════════ 3. MILTON MORRISON ═══════════════
    mm = dd["Milton Morrison"]
    story.append(Paragraph("3  Milton Morrison: La Imagen Positiva", st["sec"]))
    story.append(dir_header("Milton Morrison", "2024 - presente", "PRM (Abinader)",
                            GREEN, mm["total"], pct(mm["neg"], mm["total"])))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Milton Morrison es el contrapunto perfecto de Hugo Beras. Con 114 articulos, tiene una cobertura "
        "personal sustancial pero con un tono radicalmente distinto. Donde Beras acumula denuncias y "
        "procesos judiciales, Morrison acumula inauguraciones, programas y reformas. Su perfil mediatico "
        "refleja una estrategia de comunicacion activa y una gestion orientada a generar noticias positivas.", st["body"]))

    story.append(Spacer(1, 6))
    story.append(hbox(
        f"De 114 articulos, {mm['pos']} son positivos ({pct(mm['pos'],mm['total'])}). "
        f"Solo {mm['neg']} son negativos ({pct(mm['neg'],mm['total'])}). "
        "Morrison es el director mejor tratado por los medios en la historia del INTRANT.",
        bg=HexColor("#152C1A"), fg=GREEN))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Cobertura por medio", st["sub"]))
    mt = [["Medio", "Grupo", "Total", "% POS", "% NEG"]]
    for mk in ["diariolibre","listindiario","acento","hoy","cdn","elcaribe","noticiassin"]:
        if mk in mm["by_medio"]:
            d = mm["by_medio"][mk]; t = max(d["t"],1); nm,gr = MEDIOS[mk]
            mt.append([nm, gr, str(d["t"]), pct(d["p"],t), pct(d["n"],t)])
    t3 = Table(mt, colWidths=[1.3*inch, 0.9*inch, 0.5*inch, 0.6*inch, 0.6*inch])
    t3.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),GREEN),("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
        ("ALIGN",(2,0),(-1,-1),"CENTER"),("GRID",(0,0),(-1,-1),0.5,MGRAY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LGRAY]),
    ]))
    story.append(t3)

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Diario Libre nuevamente lidera (32 articulos), seguido de Listin Diario (25) y Acento (23). "
        "Llama la atencion que Acento — el medio independiente — le dedica casi tanta cobertura como "
        "Listin Diario, sugiriendo que Morrison genera interes editorial mas alla de la cobertura oficial. "
        "La cobertura negativa que existe se concentra en temas heredados (Caso Camaleon/Dekolor) y "
        "cuestionamientos sobre una propiedad en Florida.", st["body"]))

    story.append(PageBreak())

    # ═══════════════ 4. CLAUDIA FRANCHESCA ═══════════════
    cf = dd["Claudia Franchesca"]
    story.append(Paragraph("4  Claudia Franchesca: La Directora Invisible", st["sec"]))
    story.append(dir_header("Claudia Franchesca de los Santos", "2017 - Ago 2020", "PLD (Danilo Medina)",
                            PURPLE, cf["total"], pct(cf["neg"], cf["total"])))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Claudia Franchesca de los Santos fue la primera directora del INTRANT y gestiono la institucion "
        "durante tres anos (2017-2020), incluyendo la pandemia de COVID-19. A pesar de liderar una "
        "institucion nueva con desafios enormes de transito, su nombre apenas aparece en 23 articulos "
        "de 6 medios. Para una funcionaria con ese nivel de responsabilidad, es un perfil extraordinariamente bajo.", st["body"]))

    story.append(Spacer(1, 6))
    story.append(hbox(
        f"23 articulos en 3 anos. Solo 1 negativo. {pct(cf['neu'],cf['total'])} neutro. "
        "Claudia Franchesca no fue ni elogiada ni criticada — simplemente no fue cubierta. "
        "La pregunta es: fue invisibilidad por merito (sin escandalos) o por genero?",
        bg=HexColor("#1A152C"), fg=HexColor("#BB99DD")))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Cobertura por medio", st["sub"]))
    cft = [["Medio", "Total", "% POS", "% NEG"]]
    for mk in ["diariolibre","listindiario","elcaribe"]:
        if mk in cf["by_medio"]:
            d = cf["by_medio"][mk]; t = max(d["t"],1); nm,_ = MEDIOS[mk]
            cft.append([nm, str(d["t"]), pct(d["p"],t), pct(d["n"],t)])
    t4 = Table(cft, colWidths=[1.5*inch, 0.6*inch, 0.6*inch, 0.6*inch])
    t4.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),PURPLE),("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
        ("ALIGN",(1,0),(-1,-1),"CENTER"),("GRID",(0,0),(-1,-1),0.5,MGRAY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LGRAY]),
    ]))
    story.append(t4)

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Diario Libre es el unico medio que le dio cobertura significativa (21 de 23 articulos). "
        "Listin Diario y El Caribe apenas tienen 1 articulo cada uno mencionandola por nombre. Hoy, CDN, "
        "Acento, N Digital y Noticias SIN registran cero articulos con su nombre. Esto contrasta "
        "dramaticamente con los 201 articulos de Hugo Beras y los 114 de Milton Morrison.", st["body"]))

    # ═══════════════ 5. RAFAEL ARIAS ═══════════════
    story.append(Spacer(1, 12))
    story.append(Paragraph("5  Rafael Arias: El Director Fantasma", st["sec"]))
    story.append(dir_header("Rafael Arias", "Ago 2020 - Ago 2022", "PRM (Abinader)",
                            DGRAY, 1, "0.0%"))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Rafael Arias dirigio el INTRANT durante dos anos completos (agosto 2020 - agosto 2022). Durante "
        "su gestion se inauguraron los corredores de autobuses Churchill y Nunez de Caceres, se implemento "
        "el programa Motoben, y se regularizaron miles de motocicletas. Sin embargo, al buscar su nombre "
        "en 6 medios dominicanos, aparece en exactamente 1 articulo.", st["body"]))

    story.append(Spacer(1, 6))
    story.append(hbox(
        "1 articulo en 2 anos. De 6 medios buscados, solo Diario Libre lo menciona por nombre. "
        "Esto no significa que el INTRANT no fue cubierto — lo fue (126 articulos en ese periodo). "
        "Significa que los medios hablaron de la institucion sin nombrar a su director.",
        bg=HexColor("#1A1A1A"), fg=DGRAY))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Este hallazgo tiene multiples lecturas. Rafael Arias era ex-dirigente de Conatra (sindicato de "
        "transporte), lo que pudo generar reservas editoriales. Tambien es posible que su estrategia de "
        "comunicacion fuera deliberadamente de bajo perfil. En cualquier caso, el contraste con sus "
        "sucesores es asombroso: Hugo Beras genero 201 articulos con su nombre en un periodo mas corto.", st["body"]))

    story.append(PageBreak())

    # ═══════════════ 6. COMPARATIVA ═══════════════
    story.append(Paragraph("6  La Gran Comparativa", st["sec"]))
    story.append(Paragraph("Que nos dice la cobertura personal sobre los medios", st["sub"]))

    story.append(Paragraph(
        "Cuando se compara la cobertura por nombre de director con la cobertura institucional del INTRANT, "
        "emergen patrones reveladores sobre como operan los medios dominicanos.", st["body"]))

    findings = [
        "Diario Libre domina la cobertura personal de TODOS los directores. Es el medio que mas personaliza "
        "las noticias institucionales — pone nombre y apellido donde otros ponen solo el nombre de la institucion.",

        "El Grupo Corripio cubre mas la institucion que a las personas. El Caribe tiene 144 articulos del INTRANT "
        "pero solo 13 de Hugo Beras y 6 de Morrison. Su estilo es institucional, no personal.",

        "La cobertura negativa de Hugo Beras es 5 veces mayor que la de Milton Morrison en terminos absolutos. "
        "Pero Morrison lleva menos tiempo — la pregunta es si mantendra su perfil positivo.",

        "Claudia Franchesca plantea la pregunta de genero: fue la unica mujer directora y tambien la mas "
        "invisible mediaticamete. ¿Coincidencia o patron?",

        "Rafael Arias es la prueba de que se puede dirigir una institucion publica durante 2 anos sin que "
        "los medios te nombren. Esto cuestiona la narrativa de que todo funcionario esta expuesto mediaticamete.",
    ]
    for i, f in enumerate(findings, 1):
        story.append(Paragraph(f"<b>{i}.</b> {f}", st["find"]))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))
    story.append(hbox(
        "CONCLUSION<br/>La cobertura mediatica personal no es proporcional al cargo ni al tiempo en funcion. "
        "Es proporcional al conflicto. Hugo Beras tiene 200 veces mas cobertura que Rafael Arias — "
        "no porque haya hecho 200 veces mas cosas, sino porque genero un escandalo de corrupcion. "
        "Los medios dominicanos cubren personas cuando hay drama, no cuando hay gestion.",
        bg=NAVY))

    story.append(PageBreak())

    # ═══════════════ ANEXO ═══════════════
    story.append(Paragraph("Anexo: Titulares por Director", st["sec"]))
    story.append(Paragraph(
        "Base de datos completa de articulos que mencionan a cada director por nombre.", st["body"]))

    for d in DIRS:
        data = dd[d["key"]]
        if not data["arts"]: continue
        nm = d["name"]; t = data["total"]; neg_p = pct(data["neg"], t)

        hdr = Table([[Paragraph(f"<b>{nm}</b> — {t} articulos — {neg_p} negativo",
                       ParagraphStyle("mh", fontName="Helvetica-Bold", fontSize=8, textColor=WHITE))]],
                    colWidths=[WC])
        hdr.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),d["color"]),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),("LEFTPADDING",(0,0),(-1,-1),8)]))
        story.append(hdr)

        ax = [["Fecha", "Medio", "Titular", "S", "Tono"]]
        for a in sorted(data["arts"], key=lambda x: x.get("article_date") or ""):
            dt = (a.get("article_date") or "")[:10] or "N/D"
            medio_nm = MEDIOS.get(a["medio_key"], (a["medio_key"],))[0]
            sent = {"POSITIVO":"POS","NEGATIVO":"NEG","NEUTRO":"NEU"}.get(a.get("sentiment",""),"")
            tone = a.get("tone_detail","") or ""
            title = a.get("title","")
            if len(title) > 72: title = title[:69] + "..."
            ax.append([
                Paragraph(dt, st["ax"]), Paragraph(medio_nm, st["ax"]),
                Paragraph(title, st["ax"]), Paragraph(sent, st["ax"]),
                Paragraph(tone, st["ax"]),
            ])

        at = Table(ax, colWidths=[0.52*inch, 0.75*inch, 2.9*inch, 0.35*inch, 0.65*inch])
        at.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),WHITE),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),6),
            ("GRID",(0,0),(-1,-1),0.3,HexColor("#DDDDDD")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,HexColor("#F8F9FA")]),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,1),(-1,-1),1),("BOTTOMPADDING",(0,1),(-1,-1),1),
        ]))
        story.append(at)
        story.append(Spacer(1, 10))

    # Final footer
    story.append(Spacer(1, 15))
    ft = Table([[Paragraph(
        "Reporte generado por NeuroData, division de inteligencia mediatica de NeuroNoticia Group. "
        "Datos: Google Search (Serper.dev). Sentimiento: Claude Haiku (Anthropic). "
        "339 articulos clasificados de 8 medios dominicanos. neurodiario.com",
        ParagraphStyle("ft", fontName="Helvetica", fontSize=6.5, textColor=CYAN, alignment=TA_CENTER))
    ]], colWidths=[WC])
    ft.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),NAVY),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12)]))
    story.append(ft)

    doc.build(story)
    print(f"Reporte generado: {out}")

if __name__ == "__main__":
    build()
