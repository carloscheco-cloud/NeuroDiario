"""
NeuroDiario - Newsletter Generator
Genera el contenido semanal: resumen editorial + reporte PDF
Se ejecuta cada domingo a las 8am hora RD (12:00 UTC)
"""

import logging
import os
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

def fecha_es(dt: datetime) -> str:
    return f"{dt.day} de {MESES_ES[dt.month]} de {dt.year}"


def get_top_articles_of_week(db, limit: int = 5) -> List[Dict]:
    """Obtiene los mejores artículos publicados en los últimos 7 días."""
    from neurodiario.db.models import GeneratedArticle, Article

    since = datetime.utcnow() - timedelta(days=7)

    records = db.query(GeneratedArticle).filter(
        GeneratedArticle.status == "published",
        GeneratedArticle.published_at >= since,
        GeneratedArticle.wordpress_post_id != None,  # noqa
    ).order_by(GeneratedArticle.published_at.desc()).limit(20).all()

    # Priorizar por categoría: política > economía > sociedad > internacional
    priority = {"politica": 1, "economia": 2, "sociedad": 3, "internacional": 4, "general": 5}
    records_sorted = sorted(records, key=lambda r: priority.get(r.category or "general", 5))

    result = []
    for r in records_sorted[:limit]:
        source = None
        if r.source_article_id:
            source = db.query(Article).filter(Article.id == r.source_article_id).first()

        result.append({
            "title": r.title,
            "category": r.category or "general",
            "wordpress_post_id": r.wordpress_post_id,
            "image_url": source.image_url if source else None,
            "published_at": r.published_at,
        })

    return result


def generate_editorial_summary(articles: List[Dict], youtube_url: str = "") -> str:
    """Usa OpenAI para generar el resumen editorial de la semana."""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    articles_text = "\n".join([
        f"- [{a['category'].upper()}] {a['title']}"
        for a in articles
    ])

    youtube_section = f"\n\nVIDEO DE LA SEMANA: {youtube_url}" if youtube_url else ""

    prompt = f"""Eres el editor jefe de NeuroDiario. Redacta el email semanal para los suscriptores.

NOTICIAS DE LA SEMANA:
{articles_text}
{youtube_section}

INSTRUCCIONES:
- Saludo cálido y breve (1-2 oraciones)
- Intro de contexto de la semana en RD (2-3 oraciones)
- Para cada noticia: título en negrita + 2 oraciones de contexto/análisis
- Cierre motivacional sobre el periodismo dominicano (1-2 oraciones)
- Tono: profesional, dominicano, cercano
- NO uses markdown, usa HTML simple: <p>, <strong>, <br>
- Máximo 500 palabras en total"""

    response = client.chat.completions.create(
        model=model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def generate_weekly_pdf(articles: List[Dict], week_label: str) -> Optional[str]:
    """Genera el reporte PDF semanal con análisis de indicadores."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, white, black
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, PageBreak
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        NAVY = HexColor("#0B1F3B")
        BLUE = HexColor("#0077FF")
        LIGHT_GRAY = HexColor("#F5F5F5")
        DARK_GRAY = HexColor("#333333")

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", prefix="nd_report_", delete=False)
        tmp.close()

        doc = SimpleDocTemplate(
            tmp.name,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
        )

        styles = getSampleStyleSheet()

        style_title = ParagraphStyle(
            "NDTitle",
            fontSize=24,
            fontName="Helvetica-Bold",
            textColor=white,
            alignment=TA_CENTER,
            spaceAfter=4,
        )
        style_subtitle = ParagraphStyle(
            "NDSubtitle",
            fontSize=12,
            fontName="Helvetica",
            textColor=HexColor("#CCDDFF"),
            alignment=TA_CENTER,
            spaceAfter=2,
        )
        style_section = ParagraphStyle(
            "NDSection",
            fontSize=14,
            fontName="Helvetica-Bold",
            textColor=NAVY,
            spaceBefore=16,
            spaceAfter=8,
            borderPadding=(0, 0, 4, 0),
        )
        style_body = ParagraphStyle(
            "NDBody",
            fontSize=10,
            fontName="Helvetica",
            textColor=DARK_GRAY,
            spaceAfter=6,
            leading=14,
        )
        style_article_title = ParagraphStyle(
            "NDArticleTitle",
            fontSize=11,
            fontName="Helvetica-Bold",
            textColor=NAVY,
            spaceAfter=3,
        )
        style_category = ParagraphStyle(
            "NDCategory",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=BLUE,
            spaceAfter=2,
        )
        style_footer = ParagraphStyle(
            "NDFooter",
            fontSize=8,
            fontName="Helvetica",
            textColor=HexColor("#888888"),
            alignment=TA_CENTER,
        )

        story = []

        # ── HEADER BANNER ──
        header_data = [[
            Paragraph("NeuroDiario", style_title),
        ]]
        header_table = Table(header_data, colWidths=[7*inch])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), NAVY),
            ("ROUNDEDCORNERS", [8]),
            ("TOPPADDING", (0,0), (-1,-1), 20),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (-1,-1), 20),
            ("RIGHTPADDING", (0,0), (-1,-1), 20),
        ]))
        story.append(header_table)

        subtitle_data = [[
            Paragraph(f"Reporte Semanal — {week_label}", style_subtitle),
        ]]
        subtitle_table = Table(subtitle_data, colWidths=[7*inch])
        subtitle_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), BLUE),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (-1,-1), 20),
            ("RIGHTPADDING", (0,0), (-1,-1), 20),
        ]))
        story.append(subtitle_table)
        story.append(Spacer(1, 20))

        # ── RESUMEN EJECUTIVO ──
        story.append(Paragraph("Resumen Ejecutivo", style_section))
        story.append(HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=10))

        intro = (
            f"Este reporte presenta las {len(articles)} noticias más relevantes de la semana "
            f"en República Dominicana, clasificadas por categoría e impacto. "
            f"NeuroDiario utiliza inteligencia artificial para seleccionar y analizar "
            f"la información más importante para nuestros lectores."
        )
        story.append(Paragraph(intro, style_body))
        story.append(Spacer(1, 10))

        # ── TABLA DE NOTICIAS ──
        story.append(Paragraph("Noticias Destacadas de la Semana", style_section))
        story.append(HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=10))

        for i, article in enumerate(articles, 1):
            cat = article["category"].upper()
            date_str = fecha_es(article["published_at"]) if article.get("published_at") else ""

            row_data = [[
                Paragraph(f"#{i}", ParagraphStyle("Num", fontSize=16, fontName="Helvetica-Bold",
                          textColor=BLUE, alignment=TA_CENTER)),
                [
                    Paragraph(cat, style_category),
                    Paragraph(article["title"], style_article_title),
                    Paragraph(f"Publicado: {date_str}", style_footer),
                ]
            ]]
            row_table = Table(row_data, colWidths=[0.5*inch, 6.5*inch])
            row_table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), LIGHT_GRAY if i % 2 == 0 else white),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("TOPPADDING", (0,0), (-1,-1), 10),
                ("BOTTOMPADDING", (0,0), (-1,-1), 10),
                ("LEFTPADDING", (0,0), (-1,-1), 8),
                ("RIGHTPADDING", (0,0), (-1,-1), 8),
                ("ROUNDEDCORNERS", [4]),
            ]))
            story.append(row_table)
            story.append(Spacer(1, 6))

        story.append(Spacer(1, 20))

        # ── DISTRIBUCIÓN POR CATEGORÍA ──
        story.append(Paragraph("Distribución por Categoría", style_section))
        story.append(HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=10))

        cat_count = {}
        for a in articles:
            cat = a["category"].title()
            cat_count[cat] = cat_count.get(cat, 0) + 1

        cat_data = [["Categoría", "Artículos", "Porcentaje"]]
        for cat, count in sorted(cat_count.items(), key=lambda x: -x[1]):
            pct = f"{round(count / len(articles) * 100)}%"
            cat_data.append([cat, str(count), pct])

        cat_table = Table(cat_data, colWidths=[3*inch, 2*inch, 2*inch])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY),
            ("TEXTCOLOR", (0,0), (-1,0), white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 10),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
            ("FONTSIZE", (0,1), (-1,-1), 10),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, LIGHT_GRAY]),
            ("GRID", (0,0), (-1,-1), 0.5, HexColor("#DDDDDD")),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 30))

        # ── FOOTER ──
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#DDDDDD"), spaceAfter=10))
        story.append(Paragraph(
            f"© {datetime.now().year} NeuroDiario — El Primer Periódico IA de República Dominicana | neurodiario.com",
            style_footer
        ))
        story.append(Paragraph(
            "Este reporte fue generado automáticamente por inteligencia artificial.",
            style_footer
        ))

        doc.build(story)
        logger.info(f"  📄 PDF generado: {tmp.name}")
        return tmp.name

    except Exception as e:
        logger.error(f"  📄 Error generando PDF: {e}", exc_info=True)
        return None
