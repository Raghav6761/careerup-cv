import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from bidi.algorithm import get_display
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
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
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily("Assistant", normal="Assistant", bold="Assistant-Bold")
        return "Assistant"
    else:
        return "Helvetica"


def _clean_hebrew_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace('\u200f', '').replace('\u200e', '')
    text = text.replace('(', ' - ').replace(')', '').replace('（', ' - ').replace('）', '')
    text = text.replace('"', "'").replace('"', "'").replace('"', "'")
    text = text.replace('״', "'").replace('׳', "'")
    return text


def reshape_hebrew(text: str) -> str:
    if not text:
        return ""
    text = _clean_hebrew_text(text)
    lines = text.split('\n')
    result_lines = []
    for line in lines:
        if not line.strip():
            result_lines.append(line)
            continue
        displayed = str(get_display(line, base_dir='R'))
        result_lines.append(displayed)
    return '\n'.join(result_lines)


def reshape_hebrew_paragraph(text: str) -> str:
    if not text:
        return ""
    text = _clean_hebrew_text(text)
    text = text.replace('\n', ' ')
    words = text.split()
    result_words = []
    for word in words:
        displayed = str(get_display(word, base_dir='R'))
        result_words.append(displayed)
    return ' '.join(result_words)


def _make_section_separator(width_mm=170):
    return HRFlowable(
        width="100%",
        thickness=1,
        color=HexColor("#7fb3d8"),
        spaceAfter=2,
        spaceBefore=6
    )


def _make_job_separator(width_mm=170):
    return HRFlowable(
        width="100%",
        thickness=1,
        color=HexColor("#e2e8f0"),
        spaceAfter=2,
        spaceBefore=3
    )


def _get_pdf_styles(font_name, bold_font):
    return {
        "name": ParagraphStyle(
            "Name",
            fontName=bold_font,
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=HexColor("#2c3e50"),
            spaceAfter=2
        ),
        "contact": ParagraphStyle(
            "Contact",
            fontName=font_name,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=HexColor("#555555"),
            spaceAfter=6
        ),
        "section_header": ParagraphStyle(
            "SectionHeader",
            fontName=bold_font,
            fontSize=12,
            leading=16,
            alignment=TA_RIGHT,
            textColor=HexColor("#2c3e50"),
            spaceAfter=2,
            spaceBefore=8
        ),
        "job_title": ParagraphStyle(
            "JobTitle",
            fontName=bold_font,
            fontSize=9,
            leading=13,
            alignment=TA_RIGHT,
            textColor=HexColor("#333333"),
            spaceAfter=1,
            spaceBefore=4
        ),
        "job_period": ParagraphStyle(
            "JobPeriod",
            fontName=font_name,
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
            textColor=HexColor("#6b7c93"),
            spaceAfter=1
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=font_name,
            fontSize=9,
            leading=13,
            alignment=TA_RIGHT,
            textColor=HexColor("#333333"),
            spaceAfter=2,
            wordWrap='RTL'
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            fontName=bold_font,
            fontSize=9,
            leading=13,
            alignment=TA_RIGHT,
            textColor=HexColor("#2c3e50"),
            spaceAfter=1
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontName=font_name,
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
            textColor=HexColor("#333333"),
            spaceAfter=1,
            rightIndent=8,
            wordWrap='RTL'
        ),
    }


def export_cv_to_pdf(cv_data: dict) -> bytes:
    buffer = io.BytesIO()
    font_name = register_hebrew_font()
    bold_font = f"{font_name}-Bold" if font_name == "Assistant" else "Helvetica-Bold"

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    styles = _get_pdf_styles(font_name, bold_font)
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
    if contact.get("linkedin"):
        contact_parts.append(contact["linkedin"])
    if contact_parts:
        elements.append(Paragraph(" | ".join(contact_parts), styles["contact"]))

    elements.append(HRFlowable(width="100%", thickness=2, color=HexColor("#2c3e50"), spaceAfter=4, spaceBefore=2))

    summary = cv_data.get("professional_summary", "")
    if summary:
        elements.append(Paragraph(reshape_hebrew("תקציר מקצועי"), styles["section_header"]))
        elements.append(_make_section_separator())
        elements.append(Paragraph(reshape_hebrew_paragraph(summary), styles["body"]))

    experience = cv_data.get("experience", [])
    if experience:
        elements.append(Paragraph(reshape_hebrew("ניסיון תעסוקתי"), styles["section_header"]))
        elements.append(_make_section_separator())
        for idx, exp in enumerate(experience):
            title = exp.get("title", "")
            company = exp.get("company", "")
            period = exp.get("period", "")

            if idx > 0:
                elements.append(_make_job_separator())

            header_parts = []
            if period:
                header_parts.append(period)
            if title:
                header_parts.append(title)
            if company:
                header_parts.append(company)
            if header_parts:
                elements.append(Paragraph(reshape_hebrew(" | ".join(header_parts)), styles["job_title"]))

            for ach in exp.get("achievements", []):
                if ach.strip():
                    elements.append(Paragraph(reshape_hebrew(f"• {ach}"), styles["bullet"]))

            honors = exp.get("honors", "")
            if honors and honors.strip():
                elements.append(Paragraph(reshape_hebrew(f"★ {honors}"), styles["bullet"]))

    education = cv_data.get("education", [])
    if education:
        elements.append(Paragraph(reshape_hebrew("השכלה"), styles["section_header"]))
        elements.append(_make_section_separator())
        for edu in education:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            year = edu.get("year", "")
            honors = edu.get("honors", "")
            parts = []
            if year:
                parts.append(year)
            if degree:
                parts.append(degree)
            if institution:
                parts.append(institution)
            if parts:
                elements.append(Paragraph(reshape_hebrew(" | ".join(parts)), styles["body"]))
            if honors and honors.strip():
                elements.append(Paragraph(reshape_hebrew(f"★ {honors}"), styles["bullet"]))

    skills = cv_data.get("skills", {})
    technical = skills.get("technical", [])
    soft = skills.get("soft", [])
    if technical or soft:
        elements.append(Paragraph(reshape_hebrew("מיומנויות"), styles["section_header"]))
        elements.append(_make_section_separator())
        if technical:
            tech_text = reshape_hebrew(", ".join(technical))
            elements.append(Paragraph(tech_text, styles["body"]))
        if soft:
            soft_text = reshape_hebrew(", ".join(soft))
            elements.append(Paragraph(soft_text, styles["body"]))

    languages = cv_data.get("languages", [])
    if languages:
        elements.append(Paragraph(reshape_hebrew("שפות"), styles["section_header"]))
        elements.append(_make_section_separator())
        lang_parts = []
        for lang in languages:
            lang_name = lang.get("language", "")
            level = lang.get("level", "")
            if lang_name:
                part = lang_name
                if level:
                    part += f" – {level}"
                lang_parts.append(part)
        if lang_parts:
            elements.append(Paragraph(reshape_hebrew(" | ".join(lang_parts)), styles["body"]))

    volunteering = cv_data.get("volunteering", [])
    if volunteering:
        elements.append(Paragraph(reshape_hebrew("התנדבות"), styles["section_header"]))
        elements.append(_make_section_separator())
        for item in volunteering:
            if item and item.strip():
                elements.append(Paragraph(reshape_hebrew(f"• {item}"), styles["bullet"]))

    projects = cv_data.get("projects", [])
    if projects:
        elements.append(Paragraph(reshape_hebrew("פרויקטים עצמאיים"), styles["section_header"]))
        elements.append(_make_section_separator())
        for item in projects:
            if item and item.strip():
                elements.append(Paragraph(reshape_hebrew(f"• {item}"), styles["bullet"]))

    additional = cv_data.get("additional", [])
    if additional:
        elements.append(Paragraph(reshape_hebrew("מידע נוסף"), styles["section_header"]))
        elements.append(_make_section_separator())
        for item in additional:
            if item:
                elements.append(Paragraph(reshape_hebrew(f"• {item}"), styles["bullet"]))

    doc.build(elements)
    return buffer.getvalue()


def _add_docx_section_header(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(13)
    run.font.bold = True
    run.font.color.rgb = RGBColor(44, 62, 80)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)

    pPr = p._p.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    pPr.append(bidi)
    rPr = run._r.get_or_add_rPr()
    rtl = OxmlElement('w:rtl')
    rPr.append(rtl)
    bCs = OxmlElement('w:bCs')
    rPr.append(bCs)
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:cs'), 'Assistant')
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '8')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '7fb3d8')
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_docx_job_separator(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '4')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), 'e2e8f0')
    pBdr.append(bottom)
    pPr.append(pBdr)


def export_cv_to_docx(cv_data: dict) -> bytes:
    doc = Document()

    style = doc.styles["Normal"]
    font = style.font
    font.name = "Assistant"
    font.size = Pt(10)
    font.color.rgb = RGBColor(51, 51, 51)
    paragraph_format = style.paragraph_format
    paragraph_format.space_after = Pt(2)

    for section in doc.sections:
        section.right_margin = Cm(1.8)
        section.left_margin = Cm(1.8)
        section.top_margin = Cm(1.2)
        section.bottom_margin = Cm(1.2)

    name = cv_data.get("full_name", "")
    if name:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(name)
        run.font.size = Pt(20)
        run.font.bold = True
        run.font.color.rgb = RGBColor(44, 62, 80)
        p.paragraph_format.space_after = Pt(2)
        _set_docx_rtl(p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    contact = cv_data.get("contact", {})
    contact_parts = []
    if contact.get("phone"):
        contact_parts.append(contact["phone"])
    if contact.get("email"):
        contact_parts.append(contact["email"])
    if contact.get("city"):
        contact_parts.append(contact["city"])
    if contact.get("linkedin"):
        contact_parts.append(contact["linkedin"])
    if contact_parts:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(" | ".join(contact_parts))
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(85, 85, 85)
        p.paragraph_format.space_after = Pt(4)
        _set_docx_rtl(p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    summary = cv_data.get("professional_summary", "")
    if summary:
        _add_docx_section_header(doc, "תקציר מקצועי")
        p = doc.add_paragraph()
        run = p.add_run(summary)
        run.font.size = Pt(10)
        p.paragraph_format.space_after = Pt(2)
        _set_docx_rtl(p)

    experience = cv_data.get("experience", [])
    if experience:
        _add_docx_section_header(doc, "ניסיון תעסוקתי")
        for idx, exp in enumerate(experience):
            title = exp.get("title", "")
            company = exp.get("company", "")
            period = exp.get("period", "")

            if idx > 0:
                _add_docx_job_separator(doc)

            header_parts = []
            if period:
                header_parts.append(period)
            if title:
                header_parts.append(title)
            if company:
                header_parts.append(company)
            if header_parts:
                p = doc.add_paragraph()
                run = p.add_run(" | ".join(header_parts))
                run.font.bold = True
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(51, 51, 51)
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.space_before = Pt(4)
                _set_docx_rtl(p)

            for ach in exp.get("achievements", []):
                if ach.strip():
                    p = doc.add_paragraph()
                    run = p.add_run(f"• {ach}")
                    run.font.size = Pt(9)
                    p.paragraph_format.space_after = Pt(1)
                    _set_docx_rtl(p)

            honors = exp.get("honors", "")
            if honors and honors.strip():
                p = doc.add_paragraph()
                run = p.add_run(f"★ {honors}")
                run.font.size = Pt(9)
                p.paragraph_format.space_after = Pt(1)
                _set_docx_rtl(p)

    education = cv_data.get("education", [])
    if education:
        _add_docx_section_header(doc, "השכלה")
        for edu in education:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            year = edu.get("year", "")
            honors = edu.get("honors", "")
            parts = []
            if year:
                parts.append(year)
            if degree:
                parts.append(degree)
            if institution:
                parts.append(institution)
            if parts:
                p = doc.add_paragraph()
                run = p.add_run(" | ".join(parts))
                run.font.size = Pt(10)
                _set_docx_rtl(p)
            if honors and honors.strip():
                p = doc.add_paragraph()
                run = p.add_run(f"★ {honors}")
                run.font.size = Pt(9)
                p.paragraph_format.space_after = Pt(1)
                _set_docx_rtl(p)

    skills = cv_data.get("skills", {})
    technical = skills.get("technical", [])
    soft = skills.get("soft", [])
    if technical or soft:
        _add_docx_section_header(doc, "מיומנויות")
        if technical:
            p = doc.add_paragraph()
            run = p.add_run(", ".join(technical))
            run.font.size = Pt(10)
            _set_docx_rtl(p)
        if soft:
            p = doc.add_paragraph()
            run = p.add_run(", ".join(soft))
            run.font.size = Pt(10)
            _set_docx_rtl(p)

    languages = cv_data.get("languages", [])
    if languages:
        _add_docx_section_header(doc, "שפות")
        lang_parts = []
        for lang in languages:
            lang_name = lang.get("language", "")
            level = lang.get("level", "")
            if lang_name:
                part = lang_name
                if level:
                    part += f" – {level}"
                lang_parts.append(part)
        if lang_parts:
            p = doc.add_paragraph()
            run = p.add_run(" | ".join(lang_parts))
            run.font.size = Pt(10)
            _set_docx_rtl(p)

    volunteering = cv_data.get("volunteering", [])
    if volunteering:
        _add_docx_section_header(doc, "התנדבות")
        for item in volunteering:
            if item and item.strip():
                p = doc.add_paragraph()
                run = p.add_run(f"• {item}")
                run.font.size = Pt(10)
                _set_docx_rtl(p)

    projects = cv_data.get("projects", [])
    if projects:
        _add_docx_section_header(doc, "פרויקטים עצמאיים")
        for item in projects:
            if item and item.strip():
                p = doc.add_paragraph()
                run = p.add_run(f"• {item}")
                run.font.size = Pt(10)
                _set_docx_rtl(p)

    additional = cv_data.get("additional", [])
    if additional:
        _add_docx_section_header(doc, "מידע נוסף")
        for item in additional:
            if item:
                p = doc.add_paragraph()
                run = p.add_run(f"• {item}")
                run.font.size = Pt(10)
                _set_docx_rtl(p)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _is_job_header_line(line: str) -> bool:
    import re
    line = line.strip()
    if line.startswith("-") or line.startswith("•") or line.startswith("–"):
        return False
    military_keywords_he = ['שירות מלא', 'שירות סדיר', 'חיל ', 'צה"ל', 'צבא', 'שירות לאומי', 'שירות צבאי']
    for keyword in military_keywords_he:
        if keyword in line:
            return False
    lower = line.lower()
    military_keywords_en = [
        'military service', 'army', 'air force', 'navy', 'idf',
        'israeli defense', 'israeli air force', 'israeli navy',
        'national service', 'full service', 'combat', 'compulsory service'
    ]
    for keyword in military_keywords_en:
        if keyword in lower:
            return False
    if re.search(r'\d{4}', line) and ('–' in line or '-' in line or '|' in line or 'הווה' in line or 'נוכחי' in line or 'היום' in line or 'present' in lower):
        return True
    return False


def _set_docx_rtl(paragraph, font_name="Assistant"):
    pPr = paragraph._p.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    pPr.append(bidi)
    jc_elem = pPr.find(qn('w:jc'))
    if jc_elem is not None:
        pPr.remove(jc_elem)
    for run in paragraph.runs:
        rPr = run._r.get_or_add_rPr()
        rtl = OxmlElement('w:rtl')
        rPr.append(rtl)
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = OxmlElement('w:rFonts')
            rPr.insert(0, rFonts)
        rFonts.set(qn('w:cs'), font_name)
        if run.font.bold:
            bCs = OxmlElement('w:bCs')
            rPr.append(bCs)


def export_improved_cv_to_pdf(sections: list, cv_text: str = "") -> bytes:
    buffer = io.BytesIO()
    font_name = register_hebrew_font()
    bold_font = f"{font_name}-Bold" if font_name == "Assistant" else "Helvetica-Bold"

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    styles = _get_pdf_styles(font_name, bold_font)
    elements = []

    for section in sections:
        title = section.get("title", "")
        content = section.get("final_text", section.get("improved", ""))
        if title:
            elements.append(Paragraph(reshape_hebrew(title), styles["section_header"]))
            elements.append(_make_section_separator())
        if content:
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                if _is_job_header_line(stripped):
                    elements.append(Paragraph(reshape_hebrew(stripped), styles["job_title"]))
                elif stripped.startswith("-") or stripped.startswith("•"):
                    elements.append(Paragraph(reshape_hebrew(stripped), styles["bullet"]))
                else:
                    elements.append(Paragraph(reshape_hebrew_paragraph(stripped), styles["body"]))

    doc.build(elements)
    return buffer.getvalue()


def export_improved_cv_to_docx(sections: list, cv_text: str = "") -> bytes:
    doc = Document()

    style = doc.styles["Normal"]
    font = style.font
    font.name = "Assistant"
    font.size = Pt(10)
    font.color.rgb = RGBColor(51, 51, 51)
    paragraph_format = style.paragraph_format
    paragraph_format.space_after = Pt(2)

    for s in doc.sections:
        s.right_margin = Cm(1.8)
        s.left_margin = Cm(1.8)
        s.top_margin = Cm(1.2)
        s.bottom_margin = Cm(1.2)

    for section in sections:
        title = section.get("title", "")
        content = section.get("final_text", section.get("improved", ""))

        if title:
            _add_docx_section_header(doc, title)

        if content:
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                if _is_job_header_line(stripped):
                    p = doc.add_paragraph()
                    run = p.add_run(stripped)
                    run.font.bold = True
                    run.font.size = Pt(10)
                    run.font.color.rgb = RGBColor(51, 51, 51)
                    p.paragraph_format.space_after = Pt(1)
                    p.paragraph_format.space_before = Pt(4)
                    _set_docx_rtl(p)
                elif stripped.startswith("-") or stripped.startswith("•"):
                    p = doc.add_paragraph()
                    run = p.add_run(stripped)
                    run.font.size = Pt(10)
                    p.paragraph_format.space_after = Pt(1)
                    _set_docx_rtl(p)
                else:
                    p = doc.add_paragraph()
                    run = p.add_run(stripped)
                    run.font.size = Pt(10)
                    _set_docx_rtl(p)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _get_pdf_styles_en(font_name, bold_font):
    from reportlab.lib.enums import TA_LEFT
    return {
        "name": ParagraphStyle(
            "NameEN",
            fontName=bold_font,
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=HexColor("#2c3e50"),
            spaceAfter=2
        ),
        "contact": ParagraphStyle(
            "ContactEN",
            fontName=font_name,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=HexColor("#555555"),
            spaceAfter=6
        ),
        "section_header": ParagraphStyle(
            "SectionHeaderEN",
            fontName=bold_font,
            fontSize=12,
            leading=16,
            alignment=TA_LEFT,
            textColor=HexColor("#2c3e50"),
            spaceAfter=2,
            spaceBefore=8
        ),
        "job_title": ParagraphStyle(
            "JobTitleEN",
            fontName=bold_font,
            fontSize=9,
            leading=13,
            alignment=TA_LEFT,
            textColor=HexColor("#333333"),
            spaceAfter=1,
            spaceBefore=4
        ),
        "body": ParagraphStyle(
            "BodyEN",
            fontName=font_name,
            fontSize=9,
            leading=13,
            alignment=TA_LEFT,
            textColor=HexColor("#333333"),
            spaceAfter=2
        ),
        "body_bold": ParagraphStyle(
            "BodyBoldEN",
            fontName=bold_font,
            fontSize=9,
            leading=13,
            alignment=TA_LEFT,
            textColor=HexColor("#2c3e50"),
            spaceAfter=1
        ),
        "bullet": ParagraphStyle(
            "BulletEN",
            fontName=font_name,
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
            textColor=HexColor("#333333"),
            spaceAfter=1,
            leftIndent=8
        ),
    }


def export_cv_to_pdf_en(cv_data: dict) -> bytes:
    buffer = io.BytesIO()
    font_name = register_hebrew_font()
    bold_font = f"{font_name}-Bold" if font_name == "Assistant" else "Helvetica-Bold"

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    styles = _get_pdf_styles_en(font_name, bold_font)
    elements = []

    name = cv_data.get("full_name", "")
    if name:
        elements.append(Paragraph(name, styles["name"]))

    contact = cv_data.get("contact", {})
    contact_parts = []
    if contact.get("phone"):
        contact_parts.append(contact["phone"])
    if contact.get("email"):
        contact_parts.append(contact["email"])
    if contact.get("city"):
        contact_parts.append(contact["city"])
    if contact.get("linkedin"):
        contact_parts.append(contact["linkedin"])
    if contact_parts:
        elements.append(Paragraph(" | ".join(contact_parts), styles["contact"]))

    elements.append(HRFlowable(width="100%", thickness=2, color=HexColor("#2c3e50"), spaceAfter=4, spaceBefore=2))

    summary = cv_data.get("professional_summary", "")
    if summary:
        elements.append(Paragraph("Professional Summary", styles["section_header"]))
        elements.append(_make_section_separator())
        elements.append(Paragraph(summary, styles["body"]))

    experience = cv_data.get("experience", [])
    if experience:
        elements.append(Paragraph("Professional Experience", styles["section_header"]))
        elements.append(_make_section_separator())
        for idx, exp in enumerate(experience):
            title = exp.get("title", "")
            company = exp.get("company", "")
            period = exp.get("period", "")
            if idx > 0:
                elements.append(_make_job_separator())
            header_parts = []
            if period:
                header_parts.append(period)
            if title:
                header_parts.append(title)
            if company:
                header_parts.append(company)
            if header_parts:
                elements.append(Paragraph(" | ".join(header_parts), styles["job_title"]))
            for ach in exp.get("achievements", []):
                if ach.strip():
                    elements.append(Paragraph(f"• {ach}", styles["bullet"]))
            honors = exp.get("honors", "")
            if honors and honors.strip():
                elements.append(Paragraph(f"★ {honors}", styles["bullet"]))

    education = cv_data.get("education", [])
    if education:
        elements.append(Paragraph("Education", styles["section_header"]))
        elements.append(_make_section_separator())
        for edu in education:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            year = edu.get("year", "")
            honors = edu.get("honors", "")
            parts = []
            if year:
                parts.append(year)
            if degree:
                parts.append(degree)
            if institution:
                parts.append(institution)
            if parts:
                elements.append(Paragraph(" | ".join(parts), styles["body"]))
            if honors and honors.strip():
                elements.append(Paragraph(f"★ {honors}", styles["bullet"]))

    skills = cv_data.get("skills", {})
    technical = skills.get("technical", [])
    soft = skills.get("soft", [])
    if technical or soft:
        elements.append(Paragraph("Skills", styles["section_header"]))
        elements.append(_make_section_separator())
        if technical:
            elements.append(Paragraph(", ".join(technical), styles["body"]))
        if soft:
            elements.append(Paragraph(", ".join(soft), styles["body"]))

    languages = cv_data.get("languages", [])
    if languages:
        elements.append(Paragraph("Languages", styles["section_header"]))
        elements.append(_make_section_separator())
        lang_parts = []
        for lang in languages:
            lang_name = lang.get("language", "")
            level = lang.get("level", "")
            if lang_name:
                part = lang_name
                if level:
                    part += f" – {level}"
                lang_parts.append(part)
        if lang_parts:
            elements.append(Paragraph(" | ".join(lang_parts), styles["body"]))

    volunteering = cv_data.get("volunteering", [])
    if volunteering:
        elements.append(Paragraph("Volunteering", styles["section_header"]))
        elements.append(_make_section_separator())
        for item in volunteering:
            if item and item.strip():
                elements.append(Paragraph(f"• {item}", styles["bullet"]))

    projects = cv_data.get("projects", [])
    if projects:
        elements.append(Paragraph("Personal Projects", styles["section_header"]))
        elements.append(_make_section_separator())
        for item in projects:
            if item and item.strip():
                elements.append(Paragraph(f"• {item}", styles["bullet"]))

    additional = cv_data.get("additional", [])
    if additional:
        elements.append(Paragraph("Additional Information", styles["section_header"]))
        elements.append(_make_section_separator())
        for item in additional:
            if item:
                elements.append(Paragraph(f"• {item}", styles["bullet"]))

    doc.build(elements)
    return buffer.getvalue()


def export_cv_to_docx_en(cv_data: dict) -> bytes:
    doc = Document()

    style = doc.styles["Normal"]
    font = style.font
    font.name = "Assistant"
    font.size = Pt(10)
    font.color.rgb = RGBColor(51, 51, 51)
    paragraph_format = style.paragraph_format
    paragraph_format.space_after = Pt(2)

    for section in doc.sections:
        section.right_margin = Cm(1.8)
        section.left_margin = Cm(1.8)
        section.top_margin = Cm(1.2)
        section.bottom_margin = Cm(1.2)

    name = cv_data.get("full_name", "")
    if name:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(name)
        run.font.size = Pt(20)
        run.font.bold = True
        run.font.color.rgb = RGBColor(44, 62, 80)
        p.paragraph_format.space_after = Pt(2)

    contact = cv_data.get("contact", {})
    contact_parts = []
    if contact.get("phone"):
        contact_parts.append(contact["phone"])
    if contact.get("email"):
        contact_parts.append(contact["email"])
    if contact.get("city"):
        contact_parts.append(contact["city"])
    if contact.get("linkedin"):
        contact_parts.append(contact["linkedin"])
    if contact_parts:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(" | ".join(contact_parts))
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(85, 85, 85)
        p.paragraph_format.space_after = Pt(4)

    summary = cv_data.get("professional_summary", "")
    if summary:
        _add_docx_section_header_en(doc, "Professional Summary")
        p = doc.add_paragraph()
        run = p.add_run(summary)
        run.font.size = Pt(10)
        p.paragraph_format.space_after = Pt(2)

    experience = cv_data.get("experience", [])
    if experience:
        _add_docx_section_header_en(doc, "Professional Experience")
        for idx, exp in enumerate(experience):
            title = exp.get("title", "")
            company = exp.get("company", "")
            period = exp.get("period", "")
            if idx > 0:
                _add_docx_job_separator(doc)
            header_parts = []
            if period:
                header_parts.append(period)
            if title:
                header_parts.append(title)
            if company:
                header_parts.append(company)
            if header_parts:
                p = doc.add_paragraph()
                run = p.add_run(" | ".join(header_parts))
                run.font.bold = True
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(51, 51, 51)
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.space_before = Pt(4)
            for ach in exp.get("achievements", []):
                if ach.strip():
                    p = doc.add_paragraph()
                    run = p.add_run(f"• {ach}")
                    run.font.size = Pt(9)
                    p.paragraph_format.space_after = Pt(1)
            honors = exp.get("honors", "")
            if honors and honors.strip():
                p = doc.add_paragraph()
                run = p.add_run(f"★ {honors}")
                run.font.size = Pt(9)
                p.paragraph_format.space_after = Pt(1)

    education = cv_data.get("education", [])
    if education:
        _add_docx_section_header_en(doc, "Education")
        for edu in education:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            year = edu.get("year", "")
            honors = edu.get("honors", "")
            parts = []
            if year:
                parts.append(year)
            if degree:
                parts.append(degree)
            if institution:
                parts.append(institution)
            if parts:
                p = doc.add_paragraph()
                run = p.add_run(" | ".join(parts))
                run.font.size = Pt(10)
            if honors and honors.strip():
                p = doc.add_paragraph()
                run = p.add_run(f"★ {honors}")
                run.font.size = Pt(9)
                p.paragraph_format.space_after = Pt(1)

    skills = cv_data.get("skills", {})
    technical = skills.get("technical", [])
    soft = skills.get("soft", [])
    if technical or soft:
        _add_docx_section_header_en(doc, "Skills")
        if technical:
            p = doc.add_paragraph()
            run = p.add_run(", ".join(technical))
            run.font.size = Pt(10)
        if soft:
            p = doc.add_paragraph()
            run = p.add_run(", ".join(soft))
            run.font.size = Pt(10)

    languages = cv_data.get("languages", [])
    if languages:
        _add_docx_section_header_en(doc, "Languages")
        lang_parts = []
        for lang in languages:
            lang_name = lang.get("language", "")
            level = lang.get("level", "")
            if lang_name:
                part = lang_name
                if level:
                    part += f" – {level}"
                lang_parts.append(part)
        if lang_parts:
            p = doc.add_paragraph()
            run = p.add_run(" | ".join(lang_parts))
            run.font.size = Pt(10)

    volunteering = cv_data.get("volunteering", [])
    if volunteering:
        _add_docx_section_header_en(doc, "Volunteering")
        for item in volunteering:
            if item and item.strip():
                p = doc.add_paragraph()
                run = p.add_run(f"• {item}")
                run.font.size = Pt(10)

    projects = cv_data.get("projects", [])
    if projects:
        _add_docx_section_header_en(doc, "Personal Projects")
        for item in projects:
            if item and item.strip():
                p = doc.add_paragraph()
                run = p.add_run(f"• {item}")
                run.font.size = Pt(10)

    additional = cv_data.get("additional", [])
    if additional:
        _add_docx_section_header_en(doc, "Additional Information")
        for item in additional:
            if item:
                p = doc.add_paragraph()
                run = p.add_run(f"• {item}")
                run.font.size = Pt(10)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _add_docx_section_header_en(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(13)
    run.font.bold = True
    run.font.color.rgb = RGBColor(44, 62, 80)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)

    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '8')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '7fb3d8')
    pBdr.append(bottom)
    pPr.append(pBdr)


def _is_section_header_en(line: str) -> bool:
    import re
    stripped = line.strip()
    section_keywords = [
        "personal details", "professional summary", "professional experience",
        "work experience", "education", "skills", "languages", "additional",
        "contact", "certifications", "training", "volunteering", "military",
        "profile", "objective", "qualifications", "additional information",
        "summary", "experience", "personal information", "contact details",
        "contact information"
    ]
    if re.match(r'^===\s*(.+?)\s*===$', stripped):
        return True
    lower = stripped.lower().rstrip(":")
    if lower in section_keywords:
        return True
    if len(stripped) < 40 and not stripped.startswith("•") and not stripped.startswith("-") and stripped.endswith(":"):
        return True
    return False


def _clean_section_title(line: str) -> str:
    import re
    stripped = line.strip()
    m = re.match(r'^===\s*(.+?)\s*===$', stripped)
    if m:
        return m.group(1).rstrip(":")
    return stripped.rstrip(":")


def export_improved_cv_to_pdf_en(translated_text: str) -> bytes:
    buffer = io.BytesIO()
    font_name = register_hebrew_font()
    bold_font = f"{font_name}-Bold" if font_name == "Assistant" else "Helvetica-Bold"

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    styles = _get_pdf_styles_en(font_name, bold_font)
    elements = []

    for line in translated_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if _is_section_header_en(stripped):
            elements.append(Paragraph(_clean_section_title(stripped), styles["section_header"]))
            elements.append(_make_section_separator())
        elif _is_job_header_line(stripped):
            elements.append(Paragraph(stripped, styles["job_title"]))
        elif stripped.startswith("-") or stripped.startswith("•"):
            elements.append(Paragraph(stripped, styles["bullet"]))
        else:
            elements.append(Paragraph(stripped, styles["body"]))

    doc.build(elements)
    return buffer.getvalue()


def export_improved_cv_to_docx_en(translated_text: str) -> bytes:
    doc = Document()

    style = doc.styles["Normal"]
    font = style.font
    font.name = "Assistant"
    font.size = Pt(10)
    font.color.rgb = RGBColor(51, 51, 51)
    paragraph_format = style.paragraph_format
    paragraph_format.space_after = Pt(2)

    for s in doc.sections:
        s.right_margin = Cm(1.8)
        s.left_margin = Cm(1.8)
        s.top_margin = Cm(1.2)
        s.bottom_margin = Cm(1.2)

    for line in translated_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if _is_section_header_en(stripped):
            _add_docx_section_header_en(doc, _clean_section_title(stripped))
        elif _is_job_header_line(stripped):
            p = doc.add_paragraph()
            run = p.add_run(stripped)
            run.font.bold = True
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(51, 51, 51)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(4)
        elif stripped.startswith("-") or stripped.startswith("•"):
            p = doc.add_paragraph()
            run = p.add_run(stripped)
            run.font.size = Pt(10)
            p.paragraph_format.space_after = Pt(1)
        else:
            p = doc.add_paragraph()
            run = p.add_run(stripped)
            run.font.size = Pt(10)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
