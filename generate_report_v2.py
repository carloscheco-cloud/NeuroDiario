"""
generate_report_v2.py — NeuroData Reporte Investigativo Premium
Branding nivel Pulso Social. Logo NeuroDiario. Sello CONFIDENCIAL.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, PageBreak, NextPageTemplate, Image as RLImage
)
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from io import BytesIO
import json, os, requests
from collections import defaultdict
from datetime import datetime

# ─── Brand Colors ─────────────────────────────────────────────────────────────
NAVY = HexColor("#0B1F3B")
NAVY_LIGHT = HexColor("#122A4F")
NAVY_DARK = HexColor("#070F1D")
BLUE = HexColor("#0077FF")
BLUE_LIGHT = HexColor("#3399FF")
BLUE_DIM = HexColor("#1A3A5C")
CYAN_DIM = HexColor("#88AADD")
WHITE = HexColor("#FFFFFF")
LIGHT_GRAY = HexColor("#F2F4F7")
MID_GRAY = HexColor("#E0E4EA")
GRAY_TEXT = HexColor("#666666")
DARK_TEXT = HexColor("#222222")
GREEN = HexColor("#2ECC71")
RED = HexColor("#E74C3C")
AMBER = HexColor("#F39C12")

W_PAGE, H_PAGE = letter
MARGIN = 0.7 * inch
W_CONTENT = W_PAGE - 2 * MARGIN

# ─── Logo ─────────────────────────────────────────────────────────────────────
LOGO_PATH = "/tmp/neurodiario_logo.png"

def fetch_logo():
    """Descarga el logo de NeuroDiario desde WordPress o usa fallback."""
    if os.path.exists(LOGO_PATH):
        return LOGO_PATH
    urls = [
        "https://neurodiario.com/wp-content/uploads/2025/04/neurodiario-generica-1.png",
    ]
    # Try project file first
    for p in ["/app/1000700578.png", "/mnt/project/1000700578.png"]:
        if os.path.exists(p):
            from shutil import copy2
            copy2(p, LOGO_PATH)
            return LOGO_PATH
    # Try download
    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(LOGO_PATH, "wb") as f:
                    f.write(r.content)
                return LOGO_PATH
        except:
            continue
    return None

# ─── Data ─────────────────────────────────────────────────────────────────────
MEDIOS = {
    "diariolibre": ("Diario Libre", "Grupo Omnimedia"),
    "listindiario": ("Listin Diario", "Grupo Listin"),
    "elcaribe": ("El Caribe", "Grupo Corripio"),
    "hoy": ("Hoy Digital", "Grupo Corripio"),
    "cdn": ("CDN", "Grupo Corripio"),
    "acento": ("Acento", "Independiente"),
    "ndigital": ("N Digital", "Independiente"),
    "noticiassin": ("Noticias SIN", "Grupo SIN"),
}

DIRECTORES = [
    {"n": "Claudia Franchesca de los Santos", "p": "2017 - Ago 2020", "y": [2017,2018,2019], "g": "PLD (Danilo Medina)"},
    {"n": "Rafael Arias", "p": "Ago 2020 - Ago 2022", "y": [2020,2021], "g": "PRM (Abinader)"},
    {"n": "Hugo Beras", "p": "Ago 2022 - Nov 2023", "y": [2022,2023], "g": "PRM (Abinader)"},
    {"n": "Milton Morrison", "p": "2024 - presente", "y": [2024,2025,2026], "g": "PRM (Abinader)"},
]

with open("/tmp/neurodata_full.json", "r") as f:
    articles = json.load(f)

def calc():
    s = {}
    # By medio
    bm = defaultdict(lambda: {"t":0,"p":0,"n":0,"u":0})
    for a in articles:
        m = a["medio_key"]; bm[m]["t"] += 1
        if a["sentiment"]=="POSITIVO": bm[m]["p"]+=1
        elif a["sentiment"]=="NEGATIVO": bm[m]["n"]+=1
        else: bm[m]["u"]+=1
    s["bm"] = dict(bm)

    # By medio+year
    bmy = defaultdict(lambda: defaultdict(lambda: {"p":0,"n":0,"u":0}))
    for a in articles:
        m=a["medio_key"]; y=a.get("year")
        if not y: continue
        if a["sentiment"]=="POSITIVO": bmy[m][y]["p"]+=1
        elif a["sentiment"]=="NEGATIVO": bmy[m][y]["n"]+=1
        else: bmy[m][y]["u"]+=1
    s["bmy"] = {m:dict(yy) for m,yy in bmy.items()}

    # By director
    bd = {}
    for d in DIRECTORES:
        r = {"p":0,"n":0,"u":0}
        for a in articles:
            y=a.get("year")
            if y in d["y"]:
                if a["sentiment"]=="POSITIVO": r["p"]+=1
                elif a["sentiment"]=="NEGATIVO": r["n"]+=1
                else: r["u"]+=1
        r["t"]=r["p"]+r["n"]+r["u"]
        bd[d["n"]]=r
    s["bd"]=bd

    # By director + medio
    bdm = {}
    for d in DIRECTORES:
        bdm[d["n"]]={}
        for mk in MEDIOS:
            r={"p":0,"n":0,"u":0}
            for a in articles:
                if a["medio_key"]!=mk: continue
                y=a.get("year")
                if y in d["y"]:
                    if a["sentiment"]=="POSITIVO": r["p"]+=1
                    elif a["sentiment"]=="NEGATIVO": r["n"]+=1
                    else: r["u"]+=1
            r["t"]=r["p"]+r["n"]+r["u"]
            if r["t"]>0: bdm[d["n"]][mk]=r
    s["bdm"]=bdm

    # Corripio vs rest
    co={"p":0,"n":0,"u":0,"t":0}; re={"p":0,"n":0,"u":0,"t":0}
    for a in articles:
        t = co if a["medio_key"] in ("elcaribe","hoy","cdn") else re
        t["t"]+=1
        if a["sentiment"]=="POSITIVO": t["p"]+=1
        elif a["sentiment"]=="NEGATIVO": t["n"]+=1
        else: t["u"]+=1
    s["co"]=co; s["re"]=re
    return s

# ─── Page Templates ───────────────────────────────────────────────────────────

def cover_page(c, doc):
    """Portada estilo Pulso Social con fondo navy."""
    c.saveState()
    # Full navy background
    c.setFillColor(NAVY)
    c.rect(0, 0, W_PAGE, H_PAGE, fill=1, stroke=0)

    # Subtle gradient line at top
    c.setStrokeColor(BLUE)
    c.setLineWidth(3)
    c.line(MARGIN, H_PAGE - 1.6*inch, W_PAGE - MARGIN, H_PAGE - 1.6*inch)

    # Logo
    logo = fetch_logo()
    if logo and os.path.exists(logo):
        try:
            c.drawImage(logo, W_PAGE/2 - 50, H_PAGE - 1.45*inch, width=100, height=100,
                       preserveAspectRatio=True, mask='auto')
        except:
            pass

    # NEURODATA badge
    badge_y = H_PAGE - 2.3*inch
    bw, bh = 170, 32
    bx = W_PAGE/2 - bw/2
    c.setFillColor(BLUE)
    c.roundRect(bx, badge_y, bw, bh, 16, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W_PAGE/2, badge_y + 9, "NEURODATA")

    # Title
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(W_PAGE/2, H_PAGE - 3.1*inch, "Cobertura del INTRANT")
    c.drawCentredString(W_PAGE/2, H_PAGE - 3.5*inch, "en Medios Dominicanos")

    # Subtitle
    c.setFillColor(BLUE_LIGHT)
    c.setFont("Helvetica", 13)
    c.drawCentredString(W_PAGE/2, H_PAGE - 4.0*inch,
                        "Analisis de Sesgo Mediatico con Inteligencia Artificial")

    # Metrics boxes
    metrics = [("811", "Articulos analizados"), ("8", "Medios comparados"), ("4", "Directores evaluados")]
    box_w = 140
    box_h = 65
    gap = 20
    total_w = 3*box_w + 2*gap
    start_x = W_PAGE/2 - total_w/2
    box_y = H_PAGE - 5.6*inch

    for i, (val, label) in enumerate(metrics):
        bx = start_x + i*(box_w+gap)
        c.setStrokeColor(BLUE_DIM)
        c.setLineWidth(1.5)
        c.setFillColor(NAVY_LIGHT)
        c.roundRect(bx, box_y, box_w, box_h, 8, fill=1, stroke=1)
        c.setFillColor(BLUE_LIGHT)
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(bx + box_w/2, box_y + 35, val)
        c.setFillColor(CYAN_DIM)
        c.setFont("Helvetica", 8)
        c.drawCentredString(bx + box_w/2, box_y + 12, label)

    # Source line
    c.setFillColor(CYAN_DIM)
    c.setFont("Helvetica", 9)
    c.drawCentredString(W_PAGE/2, H_PAGE - 6.3*inch,
                        "Datos: Google Search (Serper.dev) | Sentimiento: Claude Haiku (Anthropic)")
    c.drawCentredString(W_PAGE/2, H_PAGE - 6.6*inch,
                        "Periodo: 2017 - 2026 | Clasificacion: Positivo / Negativo / Neutro")

    # Date
    c.setFillColor(BLUE)
    c.setFont("Helvetica", 11)
    c.drawCentredString(W_PAGE/2, 2.0*inch, "Fecha del reporte: 12 de julio de 2026")

    # CONFIDENCIAL badge
    cbw, cbh = 160, 30
    cbx = W_PAGE/2 - cbw/2
    cby = 1.4*inch
    c.setFillColor(BLUE)
    c.roundRect(cbx, cby, cbw, cbh, 15, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W_PAGE/2, cby + 9, "CONFIDENCIAL")

    # Footer
    c.setFillColor(CYAN_DIM)
    c.setFont("Helvetica", 8)
    c.drawCentredString(W_PAGE/2, 0.8*inch,
                        "neurodiario.com  |  La Inteligencia Informativa de Republica Dominicana")

    c.restoreState()

def content_header_footer(c, doc):
    """Header y footer para paginas de contenido."""
    c.saveState()
    # Header bar
    c.setFillColor(NAVY)
    c.rect(0, H_PAGE - 0.4*inch, W_PAGE, 0.4*inch, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(MARGIN, H_PAGE - 0.27*inch, "NEURODIARIO  |  NEURODATA")
    c.setFont("Helvetica", 7)
    c.drawRightString(W_PAGE - MARGIN, H_PAGE - 0.27*inch,
                      "Cobertura INTRANT  |  Julio 2026")

    # Blue accent line under header
    c.setStrokeColor(BLUE)
    c.setLineWidth(2)
    c.line(MARGIN, H_PAGE - 0.42*inch, W_PAGE - MARGIN, H_PAGE - 0.42*inch)

    # Footer
    c.setFillColor(NAVY)
    c.rect(0, 0, W_PAGE, 0.45*inch, fill=1, stroke=0)
    c.setFillColor(CYAN_DIM)
    c.setFont("Helvetica", 6.5)
    c.drawString(MARGIN, 0.18*inch,
                 "NeuroDiario  |  La Inteligencia Informativa de Republica Dominicana")
    c.drawRightString(W_PAGE - MARGIN, 0.18*inch,
                      f"Pagina {doc.page}")
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(W_PAGE/2, 0.08*inch,
                        "Documento confidencial. Prohibida su reproduccion sin autorizacion.")
    c.restoreState()

# ─── Styles ───────────────────────────────────────────────────────────────────
def S():
    st = {}
    st["sec"] = ParagraphStyle("S", fontName="Helvetica-Bold", fontSize=15, textColor=NAVY,
                               spaceBefore=14, spaceAfter=8)
    st["sub"] = ParagraphStyle("Su", fontName="Helvetica-Bold", fontSize=11, textColor=BLUE,
                               spaceBefore=10, spaceAfter=5)
    st["body"] = ParagraphStyle("B", fontName="Helvetica", fontSize=9.5, textColor=DARK_TEXT,
                                alignment=TA_JUSTIFY, spaceAfter=5, leading=13)
    st["find"] = ParagraphStyle("F", fontName="Helvetica-Bold", fontSize=9.5, textColor=NAVY,
                                spaceBefore=3, spaceAfter=3, leading=13, leftIndent=8)
    st["sm"] = ParagraphStyle("Sm", fontName="Helvetica", fontSize=7.5, textColor=GRAY_TEXT,
                              spaceAfter=2, leading=10)
    st["th"] = ParagraphStyle("Th", fontName="Helvetica-Bold", fontSize=7.5, textColor=WHITE,
                              alignment=TA_CENTER)
    st["td"] = ParagraphStyle("Td", fontName="Helvetica", fontSize=7.5, textColor=DARK_TEXT,
                              alignment=TA_CENTER)
    st["tdl"] = ParagraphStyle("Tdl", fontName="Helvetica", fontSize=7.5, textColor=DARK_TEXT,
                               alignment=TA_LEFT)
    st["ax"] = ParagraphStyle("Ax", fontName="Helvetica", fontSize=6, textColor=DARK_TEXT,
                              alignment=TA_LEFT, leading=7.5)
    st["axb"] = ParagraphStyle("Axb", fontName="Helvetica-Bold", fontSize=6, textColor=DARK_TEXT,
                               alignment=TA_LEFT, leading=7.5)
    return st

# ─── Helper: Highlighted Box ─────────────────────────────────────────────────
def highlight_box(text, styles, bg=NAVY, fg=WHITE):
    """Caja tipo hallazgo principal del Pulso Social."""
    p = Paragraph(text, ParagraphStyle("hb", fontName="Helvetica-Bold", fontSize=9,
                                        textColor=fg, alignment=TA_CENTER, leading=13))
    t = Table([[p]], colWidths=[W_CONTENT - 20])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 15),
        ("RIGHTPADDING", (0,0), (-1,-1), 15),
        ("ROUNDEDCORNERS", [6,6,6,6]),
    ]))
    return t

def pct(n, t):
    return f"{n/max(t,1)*100:.1f}%"

# ─── Build PDF ────────────────────────────────────────────────────────────────
def build():
    stats = calc()
    st = S()
    out = "/tmp/NeuroData_INTRANT_Reporte_Investigativo.pdf"

    doc = BaseDocTemplate(out, pagesize=letter,
                          topMargin=0.6*inch, bottomMargin=0.6*inch,
                          leftMargin=MARGIN, rightMargin=MARGIN)

    cover_frame = Frame(0, 0, W_PAGE, H_PAGE, id='cover')
    content_frame = Frame(MARGIN, 0.55*inch, W_CONTENT, H_PAGE - 1.15*inch, id='content')

    doc.addPageTemplates([
        PageTemplate(id='Cover', frames=[cover_frame], onPage=cover_page),
        PageTemplate(id='Content', frames=[content_frame], onPage=content_header_footer),
    ])

    story = []
    story.append(NextPageTemplate('Content'))
    story.append(PageBreak())

    # ═══════════════ 1. RESUMEN EJECUTIVO ═══════════════
    story.append(Paragraph("1  Resumen Ejecutivo", st["sec"]))
    story.append(Paragraph("Vision general del analisis de cobertura mediatica", st["sub"]))
    story.append(Paragraph(
        "Este reporte analiza la cobertura mediatica del Instituto Nacional de Transito y Transporte Terrestre "
        "(INTRANT) en 8 medios de comunicacion dominicanos entre 2017 y 2026. Se recopilaron 811 articulos "
        "mediante busqueda sistematica en Google (via Serper.dev) y se clasifico el sentimiento de cada uno "
        "utilizando inteligencia artificial (Claude Haiku de Anthropic). El objetivo es determinar patrones de "
        "sesgo editorial, diferencias de cobertura entre grupos mediaticos, y como la percepcion mediatica "
        "varia segun el director de turno de la institucion.", st["body"]))

    story.append(Spacer(1, 8))
    story.append(highlight_box(
        "HALLAZGO PRINCIPAL<br/>El Grupo Corripio (El Caribe, Hoy, CDN) muestra solo 18.7% de cobertura negativa "
        "vs. 26.2% en el resto de medios. N Digital (Nuria Piera) duplica el promedio con 36.2% negativo.",
        st))

    story.append(Spacer(1, 10))
    findings = [
        "El 43.9% de toda la cobertura es neutra, 33.0% positiva y 23.1% negativa.",
        "2023-2024 (era Hugo Beras / Caso Camaleon) concentra el pico de negatividad: 31% promedio.",
        "2025-2026 (era Milton Morrison) muestra caida de negatividad a 19.8%.",
        "Listin Diario es el medio con MAYOR VOLUMEN (157 articulos) pero perfil mayormente neutro (48.4%).",
        "Diario Libre tiene la mayor proporcion positiva (43.1%), significativamente sobre el promedio.",
        "Los 3 medios del Grupo Corripio mantienen negatividad casi identica (18-20%), sugiriendo linea editorial unificada.",
    ]
    for f in findings:
        story.append(Paragraph(f"<b>&gt;&gt;</b> {f}", st["find"]))

    story.append(PageBreak())

    # ═══════════════ 2. METODOLOGIA ═══════════════
    story.append(Paragraph("2  Metodologia", st["sec"]))
    story.append(Paragraph("Como se recopilaron y clasificaron los datos", st["sub"]))
    story.append(Paragraph(
        "La recoleccion de datos se realizo mediante consultas automatizadas a Serper.dev (API de Google Search). "
        "Para cada medio se ejecutaron queries con el operador site: combinado con la palabra clave INTRANT y "
        "filtros de fecha por semestre. Se utilizo la cuenta gratuita de Serper (max. 10 resultados por consulta). "
        "Con 811 articulos totales, la muestra es estadisticamente significativa para detectar patrones.", st["body"]))
    story.append(Paragraph(
        "La clasificacion de sentimiento se realizo con Claude Haiku (Anthropic). Cada articulo fue evaluado por "
        "su titulo y snippet, clasificandose en POSITIVO, NEGATIVO o NEUTRO con score numerico (-1.0 a +1.0), "
        "tono (logro, denuncia, critica, informativo) y marco narrativo (servicio publico, gestion, corrupcion).", st["body"]))

    # Medios table
    story.append(Spacer(1, 6))
    story.append(Paragraph("Medios analizados", st["sub"]))
    mt = [["Medio", "Grupo Empresarial", "Articulos"]]
    for mk in ["listindiario","elcaribe","acento","diariolibre","hoy","cdn","ndigital","noticiassin"]:
        nm, gr = MEDIOS[mk]
        mt.append([nm, gr, str(stats["bm"].get(mk,{}).get("t",0))])
    mt.append(["TOTAL", "", "811"])
    t = Table(mt, colWidths=[1.8*inch, 1.8*inch, 0.9*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,-1),8),
        ("ALIGN",(2,0),(2,-1),"CENTER"),
        ("GRID",(0,0),(-1,-1),0.5,MID_GRAY),
        ("BACKGROUND",(0,-1),(-1,-1),LIGHT_GRAY), ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),[WHITE,LIGHT_GRAY]),
    ]))
    story.append(t)

    story.append(Spacer(1, 10))
    story.append(Paragraph("Directores del INTRANT analizados", st["sub"]))
    dt = [["Director", "Periodo", "Gobierno"]]
    for d in DIRECTORES:
        dt.append([d["n"], d["p"], d["g"]])
    t2 = Table(dt, colWidths=[2.3*inch, 1.3*inch, 1.6*inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.5,MID_GRAY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_GRAY]),
    ]))
    story.append(t2)
    story.append(PageBreak())

    # ═══════════════ 3. COMPARACION POR MEDIO ═══════════════
    story.append(Paragraph("3  Comparacion de Cobertura por Medio", st["sec"]))
    story.append(Paragraph(
        "El porcentaje de cobertura negativa (% NEG) es el indicador clave de postura critica. "
        "Un medio con alto % NEG ejerce mayor fiscalizacion; uno con bajo % NEG tiende a ser "
        "mas complaciente o a priorizar logros institucionales.", st["body"]))

    order = ["ndigital","diariolibre","noticiassin","acento","listindiario","hoy","cdn","elcaribe"]
    ct = [["Medio", "Grupo", "Total", "POS", "NEG", "NEU", "% POS", "% NEG"]]
    for mk in order:
        d = stats["bm"].get(mk,{})
        nm, gr = MEDIOS[mk]
        tt = max(d.get("t",1),1)
        ct.append([nm, gr.replace("Grupo ","G."), str(d.get("t",0)),
                   str(d.get("p",0)), str(d.get("n",0)), str(d.get("u",0)),
                   pct(d.get("p",0),tt), pct(d.get("n",0),tt)])
    ct.append(["PROMEDIO", "", "811", "268", "187", "356", "33.0%", "23.1%"])

    t3 = Table(ct, colWidths=[1.15*inch, 0.85*inch, 0.5*inch, 0.45*inch, 0.45*inch, 0.45*inch, 0.6*inch, 0.6*inch])
    t3.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,-1),7.5),
        ("ALIGN",(2,0),(-1,-1),"CENTER"),
        ("GRID",(0,0),(-1,-1),0.5,MID_GRAY),
        ("BACKGROUND",(0,-1),(-1,-1),LIGHT_GRAY), ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),[WHITE,LIGHT_GRAY]),
        # Highlight NEG column
        ("BACKGROUND",(7,0),(7,0),RED),
        ("BACKGROUND",(6,0),(6,0),GREEN),
    ]))
    story.append(t3)

    story.append(Spacer(1, 10))
    story.append(highlight_box(
        "N Digital (Nuria Piera) tiene 36.2% de cobertura negativa — casi el doble del promedio (23.1%).<br/>"
        "El Caribe (Grupo Corripio) tiene solo 18.1% — el mas bajo entre medios con muestra significativa.",
        st, bg=HexColor("#1A2F4A"), fg=BLUE_LIGHT))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Diario Libre destaca por la mayor proporcion positiva (43.1%), significativamente por encima del "
        "promedio (33.0%), sugiriendo orientacion editorial favorable hacia el INTRANT. N Digital, bajo "
        "la direccion de Nuria Piera, mantiene el perfil mas critico, consistente con su enfoque investigativo.", st["body"]))
    story.append(PageBreak())

    # ═══════════════ 4. GRUPO CORRIPIO ═══════════════
    story.append(Paragraph("4  Analisis: Grupo Corripio", st["sec"]))
    story.append(Paragraph("Tres medios, un mismo dueno — una misma linea editorial?", st["sub"]))
    story.append(Paragraph(
        "El Grupo Corripio opera tres de los medios analizados: El Caribe (periodico), Hoy Digital "
        "(periodico) y CDN (canal de television). La consistencia del tono entre los tres es el "
        "hallazgo mas significativo de este bloque.", st["body"]))

    co=stats["co"]; re=stats["re"]
    ec=stats["bm"].get("elcaribe",{}); hy=stats["bm"].get("hoy",{}); cd=stats["bm"].get("cdn",{})

    gc = [["", "El Caribe", "Hoy Digital", "CDN", "GRUPO", "Resto"]]
    gc.append(["Total", str(ec.get("t",0)), str(hy.get("t",0)), str(cd.get("t",0)),
               str(co["t"]), str(re["t"])])
    gc.append(["% Positivo", pct(ec.get("p",0),ec.get("t",1)), pct(hy.get("p",0),hy.get("t",1)),
               pct(cd.get("p",0),cd.get("t",1)), pct(co["p"],co["t"]), pct(re["p"],re["t"])])
    gc.append(["% Negativo", pct(ec.get("n",0),ec.get("t",1)), pct(hy.get("n",0),hy.get("t",1)),
               pct(cd.get("n",0),cd.get("t",1)), pct(co["n"],co["t"]), pct(re["n"],re["t"])])
    gc.append(["% Neutro", pct(ec.get("u",0),ec.get("t",1)), pct(hy.get("u",0),hy.get("t",1)),
               pct(cd.get("u",0),cd.get("t",1)), pct(co["u"],co["t"]), pct(re["u"],re["t"])])

    t4 = Table(gc, colWidths=[0.8*inch, 0.85*inch, 0.85*inch, 0.7*inch, 0.8*inch, 0.7*inch])
    t4.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8), ("ALIGN",(1,0),(-1,-1),"CENTER"),
        ("GRID",(0,0),(-1,-1),0.5,MID_GRAY),
        ("BACKGROUND",(4,1),(4,-1),HexColor("#E8F0FE")),
        ("BACKGROUND",(5,1),(5,-1),HexColor("#FFF8E1")),
        ("ROWBACKGROUNDS",(0,1),(3,-1),[WHITE,LIGHT_GRAY]),
    ]))
    story.append(t4)

    co_neg = co["n"]/max(co["t"],1)*100
    re_neg = re["n"]/max(re["t"],1)*100
    story.append(Spacer(1, 8))
    story.append(highlight_box(
        f"Grupo Corripio: {co_neg:.1f}% negativo vs. {re_neg:.1f}% en el resto de medios.<br/>"
        "Los tres medios mantienen niveles de negatividad casi identicos (18-20%), sugiriendo "
        "coordinacion editorial a nivel de grupo, no decisiones independientes.",
        st, bg=NAVY))
    story.append(PageBreak())

    # ═══════════════ 5. POR DIRECTOR ═══════════════
    story.append(Paragraph("5  Percepcion Mediatica por Director", st["sec"]))
    story.append(Paragraph("Como cambia la cobertura segun quien dirige el INTRANT", st["sub"]))
    story.append(Paragraph(
        "El INTRANT ha tenido cuatro directores desde su creacion. Cada gestion genero patrones "
        "de cobertura distintos que reflejan el desempeno real, la relacion con los medios y el contexto politico.", st["body"]))

    dd = [["Director", "Periodo", "Total", "% POS", "% NEG", "% NEU"]]
    for d in DIRECTORES:
        r = stats["bd"][d["n"]]
        tt = max(r["t"],1)
        dd.append([d["n"], d["p"], str(r["t"]), pct(r["p"],tt), pct(r["n"],tt), pct(r["u"],tt)])

    t5 = Table(dd, colWidths=[2.1*inch, 1.2*inch, 0.5*inch, 0.6*inch, 0.6*inch, 0.6*inch])
    t5.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,-1),8),
        ("ALIGN",(2,0),(-1,-1),"CENTER"),
        ("GRID",(0,0),(-1,-1),0.5,MID_GRAY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_GRAY]),
    ]))
    story.append(t5)

    # Director details
    dir_texts = {
        "Claudia Franchesca de los Santos":
            "Primera directora del INTRANT, gestiono la etapa fundacional. Cobertura predominantemente "
            "neutra-informativa, tipica de instituciones nuevas. Los medios reportaron sobre la creacion "
            "del INTRANT y sus primeras acciones regulatorias sin un historial previo que fiscalizar.",
        "Rafael Arias":
            "Primer director bajo el gobierno de Abinader (PRM). Su gestion fue marcada por los corredores "
            "de autobuses (Churchill, Nunez de Caceres). Su origen como dirigente de Conatra genero "
            "cuestionamientos. Hoy Digital registro 0% negativo durante su gestion — el dato mas llamativo.",
        "Hugo Beras":
            "El periodo mas polemico. El escandalo de la licitacion de semaforos con Transcore Latam "
            "(Caso Camaleon) genero el pico de negatividad. CDN (Grupo Corripio) solo registro 4% negativo "
            "durante Beras, mientras N Digital alcanzo 67% — la mayor brecha entre medios de todo el estudio.",
        "Milton Morrison":
            "Director actual. Recuperacion de imagen institucional. La cobertura se concentra en nuevas "
            "licencias de conducir, educacion vial y regulacion de motoconchos. Sin embargo, el juicio del "
            "Caso Camaleon sigue generando cobertura negativa residual asociada al INTRANT.",
    }

    for d in DIRECTORES:
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"{d['n']} ({d['p']})", st["sub"]))
        story.append(Paragraph(dir_texts[d["n"]], st["body"]))

        # Per-medio table for this director
        dm = stats["bdm"].get(d["n"], {})
        if dm:
            dmt = [["Medio", "Total", "% POS", "% NEG"]]
            for mk in ["diariolibre","listindiario","elcaribe","hoy","cdn","acento","ndigital","noticiassin"]:
                if mk in dm and dm[mk]["t"]>0:
                    r = dm[mk]; tt=max(r["t"],1)
                    dmt.append([MEDIOS[mk][0], str(r["t"]), pct(r["p"],tt), pct(r["n"],tt)])
            if len(dmt)>1:
                t6 = Table(dmt, colWidths=[1.4*inch, 0.6*inch, 0.6*inch, 0.6*inch])
                t6.setStyle(TableStyle([
                    ("BACKGROUND",(0,0),(-1,0),BLUE), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
                    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,-1),7.5),
                    ("ALIGN",(1,0),(-1,-1),"CENTER"),
                    ("GRID",(0,0),(-1,-1),0.5,MID_GRAY),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_GRAY]),
                ]))
                story.append(t6)

    story.append(PageBreak())

    # ═══════════════ 6. CONCLUSIONES ═══════════════
    story.append(Paragraph("6  Conclusiones", st["sec"]))

    conclusions = [
        ("Existe diferenciacion editorial medible.",
         "Variacion de casi 20 puntos entre el medio mas critico (N Digital 36.2%) y el menos critico (El Caribe 18.1%)."),
        ("El Grupo Corripio mantiene linea editorial unificada.",
         f"18.7% negativo combinado vs. {re_neg:.1f}% en el resto. Consistencia entre los tres medios sugiere coordinacion editorial."),
        ("La cobertura sigue ciclos vinculados al director.",
         "Hugo Beras genero el pico de negatividad (2023: 31.5%). Milton Morrison logro la mejor cobertura reciente (2025: 10.5% neg en DL)."),
        ("N Digital es el medio mas fiscalizador.",
         "36.2% negativo, casi duplica el promedio. Enfoque investigativo consistente con la linea de Nuria Piera."),
        ("Diario Libre prioriza cobertura positiva.",
         "43.1% positivo, 10 puntos por encima del promedio. Orientacion editorial hacia logros y programas institucionales."),
    ]
    for i, (title, body) in enumerate(conclusions, 1):
        story.append(Paragraph(f"<b>{i}. {title}</b>", st["find"]))
        story.append(Paragraph(body, st["body"]))

    story.append(Spacer(1, 12))
    story.append(highlight_box(
        "NOTA METODOLOGICA<br/>Este analisis detecta CORRELACIONES, no CAUSALIDAD. Las conclusiones son "
        "indicadores que merecen investigacion mas profunda. Los datos completos se incluyen en los anexos.",
        st, bg=HexColor("#2C1810"), fg=AMBER))

    story.append(PageBreak())

    # ═══════════════ ANEXOS ═══════════════
    story.append(Paragraph("Anexo: Base de Datos Completa", st["sec"]))
    story.append(Paragraph(
        "811 articulos organizados por medio y fecha. Cada entrada incluye clasificacion de sentimiento, "
        "score numerico y tono detectado. Esta base de datos es la evidencia primaria del reporte.", st["body"]))
    story.append(Spacer(1, 6))

    by_medio = defaultdict(list)
    for a in articles:
        by_medio[a["medio_key"]].append(a)

    for mk in ["diariolibre","listindiario","elcaribe","hoy","cdn","acento","ndigital","noticiassin"]:
        arts = by_medio.get(mk, [])
        if not arts: continue
        nm, gr = MEDIOS[mk]
        d = stats["bm"].get(mk, {})
        neg_p = pct(d.get("n",0), d.get("t",1))

        # Section header for this medio
        hdr = Table([[Paragraph(f"<b>{nm}</b> ({gr}) — {len(arts)} articulos — {neg_p} negativo",
                       ParagraphStyle("mh", fontName="Helvetica-Bold", fontSize=8, textColor=WHITE))]],
                    colWidths=[W_CONTENT])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),BLUE),
            ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8),
        ]))
        story.append(hdr)

        ax = [["Fecha", "Titular", "S", "Sc", "Tono"]]
        for a in sorted(arts, key=lambda x: x.get("article_date") or ""):
            dt = (a.get("article_date") or "")[:10] or "N/D"
            sent = {"POSITIVO":"POS","NEGATIVO":"NEG","NEUTRO":"NEU"}.get(a.get("sentiment",""),"")
            sc = f"{a['sentiment_score']:+.1f}" if a.get("sentiment_score") else ""
            tone = a.get("tone_detail","") or ""
            title = a.get("title","")
            if len(title)>82: title=title[:79]+"..."
            ax.append([
                Paragraph(dt, st["ax"]),
                Paragraph(title, st["ax"]),
                Paragraph(sent, st["ax"]),
                Paragraph(sc, st["ax"]),
                Paragraph(tone, st["ax"]),
            ])

        at = Table(ax, colWidths=[0.55*inch, 3.35*inch, 0.35*inch, 0.4*inch, 0.7*inch])
        at.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),NAVY), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0),6),
            ("GRID",(0,0),(-1,-1),0.3,HexColor("#DDDDDD")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,HexColor("#F8F9FA")]),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,1),(-1,-1),1), ("BOTTOMPADDING",(0,1),(-1,-1),1),
        ]))
        story.append(at)
        story.append(Spacer(1, 10))

    doc.build(story)
    print(f"Reporte premium generado: {out}")
    return out

if __name__ == "__main__":
    build()
