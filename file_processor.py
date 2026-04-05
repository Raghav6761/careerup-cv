import io
import re
import pdfplumber
from docx import Document
from bidi.algorithm import get_display


COMMON_HEBREW_WORDS = [
    "ניסיון", "השכלה", "מיומנויות", "שפות", "תקציר", "פרטים", "אישיים",
    "ניהול", "פיתוח", "עבודה", "חברה", "תפקיד", "שנים", "אחריות",
    "הובלת", "ניהלתי", "פיתחתי", "מכירות", "שירות", "לקוחות",
    "מנהל", "מהנדס", "רכז", "אוניברסיטת", "תואר", "ראשון",
    "עברית", "אנגלית", "טלפון", "אימייל", "כתובת", "מגורים",
    "משאבי", "אנוש", "הנדסה", "מערכות", "מידע", "תוכנה",
    "חינוך", "בריאות", "כספים", "שיווק", "תקשורת", "מחקר",
    "פרויקט", "צוות", "הדרכה", "תכנון", "ביצוע", "בקרה",
    "לימודים", "הסמכה", "קורס", "התנדבות", "צבאי", "שירות",
]


def _is_text_visually_reversed(text: str) -> bool:
    hebrew_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and re.search(r'[\u0590-\u05FF]', stripped):
            hebrew_lines.append(stripped)

    if not hebrew_lines:
        return False

    sample = " ".join(hebrew_lines[:20])

    normal_matches = 0
    reversed_matches = 0

    for word in COMMON_HEBREW_WORDS:
        if word in sample:
            normal_matches += 1
        reversed_word = word[::-1]
        if reversed_word in sample:
            reversed_matches += 1

    if reversed_matches > normal_matches and reversed_matches >= 3:
        return True

    return False


def _fix_reversed_text(text: str) -> str:
    fixed_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            fixed_lines.append("")
            continue
        if re.search(r'[\u0590-\u05FF]', stripped):
            fixed_line = get_display(stripped, base_dir='R')
            fixed_line = re.sub(r'([א-ת]{2,}) ([א-ת])([.,]?\s*)$', r'\1\2\3', fixed_line)
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(stripped)
    return "\n".join(fixed_lines)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    raw_text = "\n".join(text_parts)

    if _is_text_visually_reversed(raw_text):
        raw_text = _fix_reversed_text(raw_text)

    return raw_text


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    text_parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text.strip())
    return "\n".join(text_parts)


def extract_text_from_txt(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def process_uploaded_file(uploaded_file) -> str:
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif file_name.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    elif file_name.endswith(".txt"):
        return extract_text_from_txt(file_bytes)
    else:
        raise ValueError("סוג קובץ לא נתמך. אנא העלה קובץ PDF, DOCX או TXT.")
