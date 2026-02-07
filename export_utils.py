import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from bidi.algorithm import get_display
import arabic_reshaper
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os


FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")


def register_hebrew_font():
    font_path = os.path.join(FONT_DIR, "Assistant-Regular.ttf")
    font_bold_path = os.path.join(FONT_DIR, "Assistant-Bold.ttf")

    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("Assistant", font_path))
        if os.path.exists(font_bold_path):
            pdfmetrics.registerFont(TTFont("Assistant-Bold", font_bold_path))
        else:
            pdfmetrics.registerFont(TTFont("Assistant-Bold", font_path))
        return "Assistant"
    else:
        return "Helvetica"


def reshape_hebrew(text: str) -> str:
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def export_cv_to_pdf(cv_data: dict) -> bytes:
    buffer = io.BytesIO()
    font_name = register_hebrew_font()
    bold_font = f"{font_name}-Bold" if font_name == "Assistant" else "Helvetica-Bold"

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = {
        "name": ParagraphStyle(
            "Name",
            fontName=bold_font,
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            textColor=HexColor("#2c3e50"),
            spaceAfter=4
        ),
        "contact": ParagraphStyle(
            "Contact",
            fontName=font_name,
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=HexColor("#6b7c93"),
            spaceAfter=12
        ),
        "section_header": ParagraphStyle(
            "SectionHeader",
            fontName=bold_font,
            fontSize=13,
            leading=18,
            alignment=TA_RIGHT,
            textColor=HexColor("#7fb3d8"),
            spaceAfter=6,
            spaceBefore=14
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=font_name,
            fontSize=10,
            leading=15,
            alignment=TA_RIGHT,
            textColor=HexColor("#2c3e50"),
            spaceAfter=4
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            fontName=bold_font,
            fontSize=10,
            leading=15,
            alignment=TA_RIGHT,
            textColor=HexColor("#2c3e50"),
            spaceAfter=2
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontName=font_name,
            fontSize=10,
            leading=14,
            alignment=TA_RIGHT,
            textColor=HexColor("#444444"),
            spaceAfter=3,
            rightIndent=10
        ),
    }

    elements = []

    name = cv_data.get("full_name", "")
    if name:
        elements.append(Paragraph(reshape_hebrew(name), styles["name"]))

    contact = cv_data.get("contact", {})
    contact_parts = []
    if contact.get("phone"):
        contact_parts.append(contact["phone"])
    if contact.get("email"):
        contact_parts.append(contact["email"])
    if contact.get("city"):
        contact_parts.append(reshape_hebrew(contact["city"]))
    if contact_parts:
        elements.append(Paragraph(" | ".join(contact_parts), styles["contact"]))

    line_data = [[""]]
    line_table = Table(line_data, colWidths=[170 * mm])
    line_table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 1, HexColor("#e2e8f0")),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 6))

    summary = cv_data.get("professional_summary", "")
    if summary:
        elements.append(Paragraph(reshape_hebrew("תקציר מקצועי"), styles["section_header"]))
        elements.append(Paragraph(reshape_hebrew(summary), styles["body"]))

    experience = cv_data.get("experience", [])
    if experience:
        elements.append(Paragraph(reshape_hebrew("ניסיון תעסוקתי"), styles["section_header"]))
        for exp in experience:
            title = exp.get("title", "")
            company = exp.get("company", "")
            period = exp.get("period", "")
            header_text = f"{title}"
            if company:
                header_text += f" | {company}"
            if period:
                header_text += f" | {period}"
            elements.append(Paragraph(reshape_hebrew(header_text), styles["body_bold"]))
            for ach in exp.get("achievements", []):
                elements.append(Paragraph(reshape_hebrew(f"• {ach}"), styles["bullet"]))
            elements.append(Spacer(1, 4))

    education = cv_data.get("education", [])
    if education:
        elements.append(Paragraph(reshape_hebrew("השכלה"), styles["section_header"]))
        for edu in education:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            year = edu.get("year", "")
            edu_text = degree
            if institution:
                edu_text += f" | {institution}"
            if year:
                edu_text += f" | {year}"
            elements.append(Paragraph(reshape_hebrew(edu_text), styles["body"]))

    skills = cv_data.get("skills", {})
    technical = skills.get("technical", [])
    soft = skills.get("soft", [])
    if technical or soft:
        elements.append(Paragraph(reshape_hebrew("מיומנויות"), styles["section_header"]))
        if technical:
            tech_text = reshape_hebrew("טכניות: " + " ,".join(technical))
            elements.append(Paragraph(tech_text, styles["body"]))
        if soft:
            soft_text = reshape_hebrew("רכות: " + " ,".join(soft))
            elements.append(Paragraph(soft_text, styles["body"]))

    languages = cv_data.get("languages", [])
    if languages:
        elements.append(Paragraph(reshape_hebrew("שפות"), styles["section_header"]))
        lang_parts = []
        for lang in languages:
            lang_name = lang.get("language", "")
            level = lang.get("level", "")
            if lang_name:
                part = lang_name
                if level:
                    part += f" - {level}"
                lang_parts.append(part)
        if lang_parts:
            elements.append(Paragraph(reshape_hebrew(" | ".join(lang_parts)), styles["body"]))

    additional = cv_data.get("additional", [])
    if additional:
        elements.append(Paragraph(reshape_hebrew("מידע נוסף"), styles["section_header"]))
        for item in additional:
            if item:
                elements.append(Paragraph(reshape_hebrew(f"• {item}"), styles["bullet"]))

    doc.build(elements)
    return buffer.getvalue()


def export_cv_to_docx(cv_data: dict) -> bytes:
    doc = Document()

    style = doc.styles["Normal"]
    font = style.font
    font.name = "Assistant"
    font.size = Pt(11)
    font.color.rgb = RGBColor(44, 62, 80)
    paragraph_format = style.paragraph_format
    paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    for section in doc.sections:
        section.right_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)

    name = cv_data.get("full_name", "")
    if name:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(name)
        run.font.size = Pt(24)
        run.font.bold = True
        run.font.color.rgb = RGBColor(44, 62, 80)

    contact = cv_data.get("contact", {})
    contact_parts = []
    if contact.get("phone"):
        contact_parts.append(contact["phone"])
    if contact.get("email"):
        contact_parts.append(contact["email"])
    if contact.get("city"):
        contact_parts.append(contact["city"])
    if contact_parts:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(" | ".join(contact_parts))
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(107, 124, 147)

    def add_section_header(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = p.add_run(text)
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(127, 179, 216)
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)

    summary = cv_data.get("professional_summary", "")
    if summary:
        add_section_header("תקציר מקצועי")
        p = doc.add_paragraph(summary)
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    experience = cv_data.get("experience", [])
    if experience:
        add_section_header("ניסיון תעסוקתי")
        for exp in experience:
            title = exp.get("title", "")
            company = exp.get("company", "")
            period = exp.get("period", "")

            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            header_text = title
            if company:
                header_text += f" | {company}"
            if period:
                header_text += f" | {period}"
            run = p.add_run(header_text)
            run.font.bold = True
            run.font.size = Pt(11)

            for ach in exp.get("achievements", []):
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                run = p.add_run(f"• {ach}")
                run.font.size = Pt(10)

    education = cv_data.get("education", [])
    if education:
        add_section_header("השכלה")
        for edu in education:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            year = edu.get("year", "")
            edu_text = degree
            if institution:
                edu_text += f" | {institution}"
            if year:
                edu_text += f" | {year}"
            p = doc.add_paragraph(edu_text)
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    skills = cv_data.get("skills", {})
    technical = skills.get("technical", [])
    soft = skills.get("soft", [])
    if technical or soft:
        add_section_header("מיומנויות")
        if technical:
            p = doc.add_paragraph("טכניות: " + ", ".join(technical))
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if soft:
            p = doc.add_paragraph("רכות: " + ", ".join(soft))
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    languages = cv_data.get("languages", [])
    if languages:
        add_section_header("שפות")
        lang_parts = []
        for lang in languages:
            lang_name = lang.get("language", "")
            level = lang.get("level", "")
            if lang_name:
                part = lang_name
                if level:
                    part += f" - {level}"
                lang_parts.append(part)
        if lang_parts:
            p = doc.add_paragraph(" | ".join(lang_parts))
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    additional = cv_data.get("additional", [])
    if additional:
        add_section_header("מידע נוסף")
        for item in additional:
            if item:
                p = doc.add_paragraph(f"• {item}")
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def export_improved_cv_to_pdf(sections: list, cv_text: str = "") -> bytes:
    buffer = io.BytesIO()
    font_name = register_hebrew_font()
    bold_font = f"{font_name}-Bold" if font_name == "Assistant" else "Helvetica-Bold"

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = {
        "section_header": ParagraphStyle(
            "SectionHeader",
            fontName=bold_font,
            fontSize=14,
            leading=18,
            alignment=TA_RIGHT,
            textColor=HexColor("#7fb3d8"),
            spaceAfter=6,
            spaceBefore=14
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=font_name,
            fontSize=10,
            leading=15,
            alignment=TA_RIGHT,
            textColor=HexColor("#2c3e50"),
            spaceAfter=6
        ),
        "title": ParagraphStyle(
            "Title",
            fontName=bold_font,
            fontSize=18,
            leading=24,
            alignment=TA_CENTER,
            textColor=HexColor("#2c3e50"),
            spaceAfter=12
        ),
    }

    elements = []

    for section in sections:
        title = section.get("title", "")
        content = section.get("final_text", section.get("improved", ""))
        if title:
            elements.append(Paragraph(reshape_hebrew(title), styles["section_header"]))
        if content:
            for line in content.split("\n"):
                if line.strip():
                    elements.append(Paragraph(reshape_hebrew(line.strip()), styles["body"]))

    doc.build(elements)
    return buffer.getvalue()


def export_improved_cv_to_docx(sections: list, cv_text: str = "") -> bytes:
    doc = Document()

    style = doc.styles["Normal"]
    font = style.font
    font.name = "Assistant"
    font.size = Pt(11)
    font.color.rgb = RGBColor(44, 62, 80)

    for s in doc.sections:
        s.right_margin = Inches(0.8)
        s.left_margin = Inches(0.8)
        s.top_margin = Inches(0.6)
        s.bottom_margin = Inches(0.6)

    for section in sections:
        title = section.get("title", "")
        content = section.get("final_text", section.get("improved", ""))

        if title:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            run = p.add_run(title)
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.color.rgb = RGBColor(127, 179, 216)
            p.paragraph_format.space_before = Pt(14)

        if content:
            for line in content.split("\n"):
                if line.strip():
                    p = doc.add_paragraph(line.strip())
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
