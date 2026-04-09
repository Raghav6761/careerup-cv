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


def _find_column_split(words, page_width) -> float | None:
    if not words:
        return None
    xs = sorted(set(round(w["x0"]) for w in words))
    if len(xs) < 2:
        return None
    max_gap = 0
    split_x = None
    for i in range(1, len(xs)):
        gap = xs[i] - xs[i - 1]
        if gap > max_gap:
            max_gap = gap
            split_x = (xs[i - 1] + xs[i]) / 2
    if max_gap >= 60 and split_x is not None:
        covered_left  = sum(1 for w in words if w["x0"] < split_x)
        covered_right = sum(1 for w in words if w["x0"] >= split_x)
        if covered_left >= 3 and covered_right >= 3:
            return split_x
    return None


def _words_to_text(words) -> str:
    if not words:
        return ""
    sorted_words = sorted(words, key=lambda w: w["top"])
    line_groups = []
    current_group = [sorted_words[0]]
    for w in sorted_words[1:]:
        if abs(w["top"] - current_group[0]["top"]) <= 1:
            current_group.append(w)
        else:
            line_groups.append(current_group)
            current_group = [w]
    line_groups.append(current_group)

    line_texts = []
    for group in line_groups:
        line_words = sorted(group, key=lambda w: w["x0"])
        parts = []
        for i, w in enumerate(line_words):
            if i == 0:
                parts.append(w["text"])
            else:
                gap = w["x0"] - line_words[i - 1]["x1"]
                if gap < 1.0:
                    parts[-1] = parts[-1] + w["text"]
                else:
                    parts.append(w["text"])
        line_texts.append(" ".join(parts))
    return "\n".join(line_texts)


def _extract_page_text_position_aware(page) -> str:
    words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False)
    if not words:
        return ""

    split_x = _find_column_split(words, page.width)
    if split_x is not None:
        col_a = [w for w in words if w["x0"] < split_x]
        col_b = [w for w in words if w["x0"] >= split_x]
        text_a = _words_to_text(col_a)
        text_b = _words_to_text(col_b)
        return text_a + "\n" + text_b if text_b.strip() else text_a

    return _words_to_text(words)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts = []
    linkedin_urls = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = _extract_page_text_position_aware(page)
            if page_text:
                text_parts.append(page_text)
            try:
                for annot in (page.annots or []):
                    uri = annot.get("uri") or ""
                    if "linkedin.com" in uri.lower() and uri not in linkedin_urls:
                        linkedin_urls.append(uri)
            except Exception:
                pass
    raw_text = "\n".join(text_parts)

    if _is_text_visually_reversed(raw_text):
        raw_text = _fix_reversed_text(raw_text)

    if linkedin_urls:
        raw_text += "\nlinkedin: " + linkedin_urls[0]

    return raw_text


def extract_text_from_docx(file_bytes: bytes) -> str:
    from docx.oxml.ns import qn
    doc = Document(io.BytesIO(file_bytes))
    text_parts = []
    for para in doc.paragraphs:
        para_text = para.text.strip()
        if not para_text:
            continue
        try:
            hyperlinks = para._element.findall(".//" + qn("w:hyperlink"))
            for hl in hyperlinks:
                r_id = hl.get(qn("r:id"))
                if r_id and r_id in para.part.rels:
                    rel = para.part.rels[r_id]
                    url = rel.target_ref
                    if "linkedin.com" in url.lower() and url not in para_text:
                        para_text = para_text + " " + url
        except Exception:
            pass
        text_parts.append(para_text)
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
