import re
import base64
import time
import threading
import difflib
import html as html_lib
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from streamlit_sortables import sort_items
from styles import inject_custom_css
from persistence import init_storage, save_to_storage, clear_storage
from streamlit_js_eval import streamlit_js_eval as _js_eval

def _get_logo_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _format_cv_html(text: str) -> str:
    """Convert plain CV text into formatted HTML. Only year/job-header lines are bold."""
    if not text:
        return ""
    lines = text.split("\n")
    html_parts = []
    # Lines containing a year range (e.g. 2020-2024, 2022–היום) are job/edu headers → bold
    year_pattern = re.compile(r"(19|20)\d{2}[\–\-–]")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_parts.append('<div style="height:5px"></div>')
            continue
        safe = html_lib.escape(stripped)
        # Bullet point — regular weight, blue bullet
        if stripped.startswith("•") or stripped.startswith("-"):
            content = html_lib.escape(stripped.lstrip("•- ").strip())
            html_parts.append(
                f'<div style="display:flex;gap:8px;align-items:flex-start;margin:2px 0;font-weight:400;">'
                f'<span style="color:#022559;flex-shrink:0;">•</span>'
                f'<span>{content}</span></div>'
            )
        # Job/education header line — contains year range → color per segment
        elif year_pattern.search(stripped):
            parts = [p.strip() for p in stripped.split("|")]
            if len(parts) >= 3:
                date_s  = html_lib.escape(parts[0])
                title_s = html_lib.escape(parts[1])
                co_s    = html_lib.escape(" | ".join(parts[2:]))
                inner   = (
                    f'<span style="color:#2b56e0;font-weight:700;">{date_s}</span>'
                    f'<span style="color:#1a1a2e;font-weight:700;"> | {title_s} | </span>'
                    f'<span style="color:#022559;font-weight:700;">{co_s}</span>'
                )
            elif len(parts) == 2:
                date_s  = html_lib.escape(parts[0])
                rest_s  = html_lib.escape(parts[1])
                inner   = (
                    f'<span style="color:#2b56e0;font-weight:700;">{date_s}</span>'
                    f'<span style="color:#1a1a2e;font-weight:700;"> | {rest_s}</span>'
                )
            else:
                inner = f'<span style="color:#1a1a2e;font-weight:700;">{safe}</span>'
            html_parts.append(f'<div style="margin:5px 0 1px 0;">{inner}</div>')
        # Everything else — regular weight
        else:
            html_parts.append(f'<div style="font-weight:400;margin:2px 0;">{safe}</div>')
    return "".join(html_parts)


def _format_improved_html(text: str) -> str:
    """Format improved CV text as a professional CV with bullet points for descriptive lines."""
    if not text:
        return ""
    lines = text.split("\n")
    html_parts = []
    year_pattern = re.compile(r"(19|20)\d{2}[\–\-–]")
    # Patterns that indicate a header line (name, contact, title, institution, dates)
    # These should NOT become bullets — they are structural/header lines
    contact_pattern = re.compile(r"[@|]|\d{9,}|linkedin|github", re.IGNORECASE)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_parts.append('<div style="height:5px"></div>')
            continue

        safe = html_lib.escape(stripped)
        # Already a bullet marker — render as bullet
        if stripped.startswith("•") or stripped.startswith("-"):
            content = html_lib.escape(stripped.lstrip("•- ").strip())
            html_parts.append(
                f'<div style="display:flex;gap:8px;align-items:flex-start;margin:2px 0;">'
                f'<span style="color:#022559;flex-shrink:0;font-weight:600;">•</span>'
                f'<span style="font-weight:400;">{content}</span></div>'
            )
        # Year-range line → color per segment (date blue, title dark, company navy)
        elif year_pattern.search(stripped):
            parts = [p.strip() for p in stripped.split("|")]
            if len(parts) >= 3:
                date_s  = html_lib.escape(parts[0])
                title_s = html_lib.escape(parts[1])
                co_s    = html_lib.escape(" | ".join(parts[2:]))
                inner   = (
                    f'<span style="color:#2b56e0;font-weight:700;">{date_s}</span>'
                    f'<span style="color:#1a1a2e;font-weight:700;"> | {title_s} | </span>'
                    f'<span style="color:#022559;font-weight:700;">{co_s}</span>'
                )
            elif len(parts) == 2:
                date_s  = html_lib.escape(parts[0])
                rest_s  = html_lib.escape(parts[1])
                inner   = (
                    f'<span style="color:#2b56e0;font-weight:700;">{date_s}</span>'
                    f'<span style="color:#1a1a2e;font-weight:700;"> | {rest_s}</span>'
                )
            else:
                inner = f'<span style="color:#1a1a2e;font-weight:700;">{safe}</span>'
            html_parts.append(f'<div style="margin:6px 0 1px 0;">{inner}</div>')
        # Contact line (has pipe, @, phone digits) → centered, regular
        elif contact_pattern.search(stripped):
            html_parts.append(f'<div style="font-weight:400;margin:2px 0;text-align:center;">{safe}</div>')
        # Short line (≤40 chars) — likely a name, title, institution → bold header
        elif len(stripped) <= 40 and "|" not in stripped:
            html_parts.append(
                f'<div style="font-weight:700;color:#1a1a2e;margin:5px 0 1px 0;">{safe}</div>'
            )
        # Long descriptive line → convert to bullet point
        else:
            html_parts.append(
                f'<div style="display:flex;gap:8px;align-items:flex-start;margin:2px 0;">'
                f'<span style="color:#022559;flex-shrink:0;font-weight:600;">•</span>'
                f'<span style="font-weight:400;">{safe}</span></div>'
            )
    return "".join(html_parts)


def _word_diff_html(original: str, improved: str, mode: str) -> str:
    """
    Track-changes diff renderer.

    mode='original': left panel — original text with inline track changes:
        • removed words → gray strikethrough
        • inserted words → logo-blue (#2b56e0) bold, shown at insertion point
        • replaced spans → strikethrough old tokens then blue new tokens inline
    mode='improved': right panel — clean improved text, zero markup.

    Uses difflib.SequenceMatcher so every change is shown at its exact
    position in the original context (like Google Docs / Word track changes).
    """
    def _tok(text: str):
        return re.findall(r"\n|[^\S\n]+|[^\s]+", text)

    if mode not in ("original", "improved"):
        raise ValueError(f"_word_diff_html: mode must be 'original' or 'improved', got {mode!r}")

    orig_tok = _tok(original)
    impr_tok = _tok(improved)

    if mode == "improved":
        _yr = re.compile(r"(19|20)\d{2}[\–\-–]")
        out = []
        for line in improved.split("\n"):
            s = line.strip()
            if not s:
                out.append("<br>")
                continue
            if _yr.search(s):
                segs = [p.strip() for p in s.split("|")]
                if len(segs) >= 3:
                    d = html_lib.escape(segs[0])
                    t = html_lib.escape(segs[1])
                    c = html_lib.escape(" | ".join(segs[2:]))
                    out.append(
                        f'<span style="color:#2b56e0;font-weight:700;">{d}</span>'
                        f'<span style="color:#1a1a2e;font-weight:700;"> | {t} | </span>'
                        f'<span style="color:#022559;font-weight:700;">{c}</span><br>'
                    )
                elif len(segs) == 2:
                    d = html_lib.escape(segs[0])
                    r = html_lib.escape(segs[1])
                    out.append(
                        f'<span style="color:#2b56e0;font-weight:700;">{d}</span>'
                        f'<span style="color:#1a1a2e;font-weight:700;"> | {r}</span><br>'
                    )
                else:
                    out.append(f'<span style="color:#1a1a2e;font-weight:700;">{html_lib.escape(s)}</span><br>')
            else:
                out.append(html_lib.escape(s) + "<br>")
        return "".join(out)

    DEL_STYLE = (
        "text-decoration:line-through;color:#1a1a1a;"
        "display:inline;direction:rtl;unicode-bidi:isolate;"
    )
    ADD_STYLE = (
        "color:#2b56e0;font-weight:700;"
        "display:inline;direction:rtl;unicode-bidi:isolate;"
    )

    sm = difflib.SequenceMatcher(None, orig_tok, impr_tok, autojunk=False)
    parts = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for t in orig_tok[i1:i2]:
                parts.append("<br>" if t == "\n" else html_lib.escape(t))
        elif tag == "delete":
            for t in orig_tok[i1:i2]:
                if t == "\n":
                    parts.append("<br>")
                elif t.strip():
                    parts.append(f'<span style="{DEL_STYLE}">{html_lib.escape(t)}</span>')
                else:
                    parts.append(html_lib.escape(t))
        elif tag == "insert":
            for t in impr_tok[j1:j2]:
                if t == "\n":
                    parts.append("<br>")
                elif t.strip():
                    parts.append(f'<span style="{ADD_STYLE}">{html_lib.escape(t)}</span>')
                else:
                    parts.append(html_lib.escape(t))
        elif tag == "replace":
            for t in orig_tok[i1:i2]:
                if t == "\n":
                    parts.append("<br>")
                elif t.strip():
                    parts.append(f'<span style="{DEL_STYLE}">{html_lib.escape(t)}</span>')
                else:
                    parts.append(html_lib.escape(t))
            for t in impr_tok[j1:j2]:
                if t == "\n":
                    parts.append("<br>")
                elif t.strip():
                    parts.append(f'<span style="{ADD_STYLE}">{html_lib.escape(t)}</span>')
                else:
                    parts.append(html_lib.escape(t))

    html = "".join(parts)

    # ── Post-process: colorize job-header lines in the track-changes output ──
    _yr2 = re.compile(r"(19|20)\d{2}")
    _dash_markers = ("–", "—", "-", "היום", "נוכחי", "הווה", "present")

    def _colorize_diff_line(ln: str) -> str:
        plain = re.sub(r"<[^>]+>", "", ln)
        if not _yr2.search(plain):
            return ln
        if not any(m in plain.lower() for m in _dash_markers):
            return ln
        if "|" not in plain:
            return ln
        segs = ln.split(" | ")
        n = len(segs)
        if n < 2:
            return ln
        colors = ["#2b56e0"] + ["#1a1a2e"] * max(0, n - 2) + ["#022559"]
        result = []
        for i, seg in enumerate(segs):
            c = colors[i] if i < len(colors) else "#1a1a2e"
            sep = " | " if i > 0 else ""
            result.append(f'{sep}<span style="color:{c};font-weight:700;">{seg}</span>')
        return "".join(result)

    return "<br>".join(_colorize_diff_line(ln) for ln in html.split("<br>"))


st.set_page_config(
    page_title="CareerUp | CV Master AI",
    page_icon=Image.open("logo_icon.png"),
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<meta name="robots" content="noindex, nofollow">
<title>Career Up | CV Master AI</title>
""", unsafe_allow_html=True)

inject_custom_css()

if "page" not in st.session_state:
    st.session_state.page = "home"
if "cv_text" not in st.session_state:
    st.session_state.cv_text = ""
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "section_decisions" not in st.session_state:
    st.session_state.section_decisions = {}
if "generated_cv" not in st.session_state:
    st.session_state.generated_cv = None


def go_to(page):
    st.session_state.page = page


def reset_improve():
    st.session_state.cv_text = ""
    st.session_state.analysis_result = None
    st.session_state.section_decisions = {}
    for _k in ["improve_final_sections", "improve_target_position", "improve_language",
                "improve_max_pages", "improve_pages_radio",
                "improve_cv_title", "cv_title_input",
                "improve_en_translated", "improve_en_translating",
                "_improve_export_cache_key", "_improve_pdf", "_improve_docx",
                "_improve_pdf_err", "_improve_docx_err",
                "_improve_en_pdf", "_improve_en_docx",
                "staged_from_build", "staged_cv_text"]:
        st.session_state.pop(_k, None)


def _cv_dict_to_text(cv_data: dict) -> str:
    """Convert a generated_cv dict to plain text suitable for the Improve flow analyzer."""
    lines = []

    name = cv_data.get("full_name", "").strip()
    contact = cv_data.get("contact", {})
    contact_parts = [p for p in [
        contact.get("phone", ""),
        contact.get("email", ""),
        contact.get("city", ""),
        contact.get("linkedin", ""),
    ] if p.strip()]

    if name:
        lines.append(name)
    if contact_parts:
        lines.append(" | ".join(contact_parts))

    summary = cv_data.get("professional_summary", "").strip()
    if summary:
        lines.append("")
        lines.append("תקציר מקצועי")
        lines.append(summary)

    experience = cv_data.get("experience", [])
    if experience:
        lines.append("")
        lines.append("ניסיון תעסוקתי")
        for exp in experience:
            title = exp.get("title", "")
            company = exp.get("company", "")
            period = exp.get("period", "")
            header_parts = [p for p in [period, title, company] if p.strip()]
            if header_parts:
                lines.append(" | ".join(header_parts))
            for ach in exp.get("achievements", []):
                if ach.strip():
                    lines.append(f"• {ach.strip()}")
            honors = exp.get("honors", "").strip()
            if honors:
                lines.append(f"• הצטיינות: {honors}")

    education = cv_data.get("education", [])
    if education:
        lines.append("")
        lines.append("השכלה")
        for edu in education:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            year = edu.get("year", "")
            edu_parts = [p for p in [year, institution, degree] if p.strip()]
            if edu_parts:
                lines.append(" | ".join(edu_parts))
            honors = edu.get("honors", "").strip()
            if honors:
                lines.append(f"הצטיינות: {honors}")

    military = cv_data.get("military", [])
    if military:
        lines.append("")
        lines.append("שירות צבאי / לאומי")
        for item in military:
            if item.strip():
                lines.append(f"• {item.strip()}")

    skills = cv_data.get("skills", {})
    tech = skills.get("technical", [])
    soft = skills.get("soft", [])
    if tech or soft:
        lines.append("")
        lines.append("מיומנויות")
        if tech:
            lines.append("טכניות: " + ", ".join(tech))
        if soft:
            lines.append("רכות: " + ", ".join(soft))

    languages = cv_data.get("languages", [])
    if languages:
        lines.append("")
        lines.append("שפות")
        for lang in languages:
            lang_name = lang.get("language", "")
            level = lang.get("level", "")
            if lang_name.strip():
                lines.append(f"• {lang_name}" + (f" — {level}" if level.strip() else ""))

    volunteering = cv_data.get("volunteering", [])
    if volunteering:
        lines.append("")
        lines.append("התנדבות")
        for item in volunteering:
            if item.strip():
                lines.append(f"• {item.strip()}")

    projects = cv_data.get("projects", [])
    if projects:
        lines.append("")
        lines.append("פרויקטים")
        for item in projects:
            if item.strip():
                lines.append(f"• {item.strip()}")

    additional = cv_data.get("additional", [])
    if additional:
        lines.append("")
        lines.append("מידע נוסף")
        for item in additional:
            if item.strip():
                lines.append(f"• {item.strip()}")

    return "\n".join(lines)


def reset_build():
    st.session_state.generated_cv = None
    for _k in ["build_form_data", "build_target_position",
               "build_max_pages", "build_pages_radio",
               "build_en_translated", "build_en_translating"]:
        st.session_state.pop(_k, None)


def render_header():
    logo_b64 = _get_logo_b64("logo_full.png")
    st.markdown(
        f'<div class="app-header">'
        f'<img src="data:image/png;base64,{logo_b64}" style="height:56px;margin-bottom:8px;display:block;margin-left:auto;margin-right:auto;" alt="CareerUp Logo">'
        f'<p>כלי חכם ליצירה ושיפור קורות חיים מקצועיים</p>'
        f'</div>',
        unsafe_allow_html=True
    )


def render_home():
    render_header()

    with st.container(key="home_cta"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div class="home-cta-card home-cta-card-primary">
                <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="position:absolute;top:12px;left:14px;">
                    <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"/>
                    <line x1="16" y1="8" x2="2" y2="22"/>
                    <line x1="17.5" y1="15" x2="9" y2="15"/>
                </svg>
                <div class="home-cta-title">בנה קו"ח חדשים</div>
                <div class="home-cta-desc">תהליך מודרך, מובנה ומקצועי לבניית קורות חיים מנצחים מאפס.</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("בחר →", key="btn_build_cta", use_container_width=True, type="primary"):
                reset_build()
                go_to("build_form")
                st.rerun()

        with col2:
            st.markdown("""
            <div class="home-cta-card home-cta-card-secondary">
                <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#2b56e0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="position:absolute;top:12px;left:14px;">
                    <circle cx="7" cy="12" r="5"/>
                    <line x1="11" y1="16" x2="14" y2="19"/>
                    <line x1="20" y1="18" x2="20" y2="6"/>
                    <polyline points="18,8 20,6 22,8"/>
                </svg>
                <div class="home-cta-title">שפר קו"ח קיימים</div>
                <div class="home-cta-desc">קבל ניתוח שוק, טיפים לשיפור, ואיתור פערים בקלות.</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("בחר →", key="btn_improve_cta", use_container_width=True):
                reset_improve()
                st.session_state["_needs_fresh_load"] = True
                go_to("improve_upload")
                st.rerun()


def render_improve_upload():
    render_header()

    if st.button("→ חזרה לדף הבית", key="back_home_improve"):
        st.session_state.pop("staged_from_build", None)
        st.session_state.pop("staged_cv_text", None)
        go_to("home")
        st.rerun()

    if st.session_state.pop("_needs_fresh_load", False):
        st.markdown("""
        <div style="position:fixed;top:0;left:0;width:100%;height:100%;background:#fff;
                    z-index:9999;display:flex;align-items:center;justify-content:center;">
            <div style="font-size:22px;color:#2b56e0;font-family:Assistant,sans-serif;">
                טוען...
            </div>
        </div>
        """, unsafe_allow_html=True)
        _js_eval(
            js_expressions=(
                "var d={};"
                "try{d=JSON.parse(localStorage.getItem('cv_master_data')||'{}');}catch(e){}"
                "d.page='improve_upload';"
                "localStorage.setItem('cv_master_data',JSON.stringify(d));"
                "window.location.reload();"
                "true"
            ),
            key="auto_reload_improve",
        )
        st.stop()

    st.markdown("""
    <div class="progress-container">
        <div class="progress-label">שלב 1 מתוך 3</div>
        <div class="progress-track"><div class="progress-fill" style="width:33%"></div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
        [class*="st-key-card_upload"], [class*="st-key-card_language"], [class*="st-key-card_target"], [class*="st-key-card_pages"] { background-color: #f2f1ef !important; }
        div:has(>[class*="st-key-card_upload"]), div:has(>[class*="st-key-card_language"]), div:has(>[class*="st-key-card_target"]), div:has(>[class*="st-key-card_pages"]) { background-color: #f2f1ef !important; border-color: #f2f1ef !important; border-width: 2px !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

    staged_from_build = st.session_state.get("staged_from_build", False)

    with st.container(border=True, key="card_upload"):
        st.markdown('<div class="section-header">📤 העלאת קובץ קורות חיים</div>', unsafe_allow_html=True)
        st.markdown("העלה את קובץ קורות החיים שלך בפורמט PDF, DOCX או TXT")

        uploaded_file = st.file_uploader(
            "בחר קובץ",
            type=["pdf", "docx", "txt"],
            key="cv_file_uploader",
            help="פורמטים נתמכים: PDF, DOCX, TXT"
        )

        if uploaded_file is not None:
            st.success(f"✅ {uploaded_file.name} הועלה בהצלחה")

    if staged_from_build and uploaded_file is None:
        banner_col, clear_col = st.columns([9, 1])
        with banner_col:
            st.success("✅ קורות החיים שיצרת מוכנים לבדיקה — בחרו תפקיד יעד, שפה ומספר עמודים והתחילו")
        with clear_col:
            if st.button("× בטל", key="clear_staged_btn", help="בטל את הטעינה מה-Build"):
                st.session_state.pop("staged_from_build", None)
                st.session_state.pop("staged_cv_text", None)
                st.rerun()

    with st.container(border=True, key="card_language"):
        st.markdown('<div class="section-header">🌐 באיזו שפה תרצו את הגרסה החדשה?</div>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:16px; color:#6b7c93;">בחר באיזו שפה תרצה לקבל את הגרסה המשופרת של קורות החיים</span>', unsafe_allow_html=True)
        lang_choice = st.radio(
            "שפת הנוסח המשופר",
            ["עברית", "English"],
            horizontal=True,
            key="lang_radio",
            label_visibility="collapsed"
        )
        st.session_state.improve_language = "en" if lang_choice == "English" else "he"

    with st.container(border=True, key="card_pages"):
        st.markdown('<div class="section-header">📄 כמה עמודים תרצו?</div>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:16px; color:#6b7c93;">ננסה להכניס לעמוד אחד. אם הניסיון עשיר - עדיף לגלוש לעמוד שני על פני קיצוץ תוכן חשוב. בחרו "עד שני עמודים" כדי לאפשר זאת מראש.</span>', unsafe_allow_html=True)
        if "improve_max_pages" not in st.session_state:
            st.session_state.improve_max_pages = 1
        pages_choice = st.radio(
            "מספר עמודים",
            ["נסה להכניס לעמוד אחד (מומלץ)", "עד שני עמודים"],
            horizontal=True,
            key="improve_pages_radio",
            label_visibility="collapsed"
        )
        st.session_state.improve_max_pages = 1 if pages_choice == "נסה להכניס לעמוד אחד (מומלץ)" else 2

    with st.container(border=True, key="card_target"):
        st.markdown('<div class="section-header">🎯 תפקיד יעד (אופציונלי)</div>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:16px; color:#6b7c93;">ציין את שם התפקיד או הדבק את תיאור המשרה המלא — ככל שתפרטו יותר, הבינה המלאכותית תוכל להתאים את קורות החיים למסנן הממוחשב של החברה (המערכת שסורקת ומדרגת קורות חיים לפני שהם מגיעים לגורם אנושי)</span>', unsafe_allow_html=True)
        if "improve_target_position" not in st.session_state:
            st.session_state.improve_target_position = ""
        st.session_state.improve_target_position = st.text_area(
            "תפקיד יעד",
            value=st.session_state.improve_target_position,
            key="improve_target_input",
            placeholder="למשל: מנהל משאבי אנוש, מפתח Full Stack...\nאו הדבק כאן את תיאור המשרה המלא מהמודעה - ככל שתספק יותר פרטים, קורות החיים יותאמו טוב יותר",
            label_visibility="collapsed",
            height=68
        )

    _run_now = st.session_state.pop("_run_analysis", False)

    if st.session_state.get("analysis_result"):
        st.success("✅ קורות חיים קודמים מנותחים — ניתן להמשיך לסקירה או לנתח קובץ חדש")
        if st.button("← המשך לסקירה", use_container_width=True, type="primary", key="continue_to_review"):
            go_to("improve_review")
            st.rerun()

    _staged_text_ready = staged_from_build and bool(st.session_state.get("staged_cv_text", "").strip())
    _can_analyze = (uploaded_file is not None) or _staged_text_ready
    if _can_analyze:
        _bottom_clicked = st.button("🔍 נתח את קורות החיים", use_container_width=True, type="primary", key="analyze_bottom")
        if _bottom_clicked or _run_now:
            prog_bar  = None
            prog_text = None
            try:
                from file_processor import process_uploaded_file
                from ai_engine import analyze_cv_streaming

                prog_bar  = st.progress(0)
                prog_text = st.empty()

                if uploaded_file is not None:
                    # Step 1: file processing (uploaded file takes precedence)
                    prog_text.markdown("📂 מעבד את הקובץ...")
                    prog_bar.progress(5)
                    cv_text = process_uploaded_file(uploaded_file)

                    if not cv_text.strip():
                        prog_bar.empty()
                        prog_text.empty()
                        st.error("לא הצלחנו לחלץ טקסט מהקובץ. נסה קובץ אחר.")
                        return
                else:
                    # Use pre-loaded text from Build flow
                    prog_text.markdown("📂 טוען קורות חיים מה-Build...")
                    prog_bar.progress(5)
                    cv_text = st.session_state.get("staged_cv_text", "")
                    if not cv_text.strip():
                        prog_bar.empty()
                        prog_text.empty()
                        st.error("לא נמצא טקסט לניתוח. נסה להעלות קובץ.")
                        return

                st.session_state.cv_text = cv_text

                # Step 2: stream AI analysis — progress updates per completed section
                prog_text.markdown("🤖 שולח לבינה המלאכותית — מזהה סעיפים...")
                prog_bar.progress(10)

                lang      = st.session_state.get("improve_language", "he")
                max_pages = st.session_state.get("improve_max_pages", 1)

                result         = None
                sections_count = None
                sections_done  = 0

                try:
                    for event in analyze_cv_streaming(
                        cv_text,
                        target_position=st.session_state.improve_target_position,
                        language=lang,
                        max_pages=max_pages,
                    ):
                        if event["type"] == "metadata":
                            sections_count = event["sections_count"]
                            prog_bar.progress(20)
                            prog_text.markdown(f"✅ זוהו **{sections_count} סעיפים** — מנסח שיפורים...")

                        elif event["type"] == "section":
                            sections_done += 1
                            title = event["title"]
                            pct = 20 + int((sections_done / sections_count) * 70) if sections_count else min(90, 20 + sections_done * 10)
                            prog_bar.progress(min(pct, 90))
                            prog_text.markdown(f"✅ סיים: **{title}** — {sections_done}/{sections_count or '?'}")

                        elif event["type"] == "done":
                            result = event["result"]

                except Exception as stream_err:
                    import logging as _logging
                    _logging.getLogger(__name__).warning(f"Streaming failed ({stream_err}), falling back to analyze_cv()")
                    from ai_engine import analyze_cv
                    prog_bar.progress(25)
                    prog_text.markdown("🤖 הבינה המלאכותית מנתחת... (עשוי לקחת כמה דקות)")
                    result = analyze_cv(cv_text, target_position=st.session_state.improve_target_position, language=lang, max_pages=max_pages)

                # Step 3: complete
                prog_bar.progress(100)
                prog_text.markdown("✅ הניתוח הושלם!")
                time.sleep(0.45)

                prog_bar.empty()
                prog_text.empty()

                st.session_state.analysis_result = result
                st.session_state.section_decisions = {}
                st.session_state.pop("staged_from_build", None)
                st.session_state.pop("staged_cv_text", None)

                go_to("improve_review")
                st.rerun()
            except Exception as e:
                if prog_bar is not None:
                    prog_bar.empty()
                if prog_text is not None:
                    prog_text.empty()
                st.error(f"שגיאה בעיבוד הקובץ: {str(e)}")


def render_improve_review():
    render_header()

    if st.button("→ חזרה להעלאת קובץ", key="back_upload"):
        go_to("improve_upload")
        st.rerun()

    st.markdown("""
    <div class="progress-container">
        <div class="progress-label">שלב 2 מתוך 3</div>
        <div class="progress-track"><div class="progress-fill" style="width:66%"></div></div>
    </div>
    """, unsafe_allow_html=True)

    result = st.session_state.analysis_result
    if not result:
        st.warning("לא נמצאו תוצאות ניתוח. חזור להעלאת קובץ.")
        return

    score = result.get("score", 0)
    st.markdown(f"""
    <div style="text-align: center; margin: 16px 0;">
        <div style="font-size: 48px; font-weight: 800; color: {'#4CAF50' if score >= 70 else '#FF9800' if score >= 50 else '#f44336'};">
            {score}/100
        </div>
        <div style="font-size: 15px; color: #6b7c93;">ציון קורות החיים שלך</div>
    </div>
    """, unsafe_allow_html=True)

    tips = result.get("general_tips", [])
    keywords = result.get("keywords_to_add", [])

    if tips:
        with st.expander("✅ מה כדאי להוסיף", expanded=True):
            for tip in tips:
                st.markdown(f"• {tip}")

    if keywords:
        with st.expander("🔑 מילות מפתח מומלצות", expanded=True):
            st.markdown('<span style="font-size:13px;color:#6b7c93;">מילות מפתח אלה שולבו אוטומטית בקורות החיים המשופרים — מומלץ לוודא שהן מופיעות בצורה טבעית בטקסט</span>', unsafe_allow_html=True)
            st.markdown(", ".join([f"**{kw}**" for kw in keywords]))

    st.markdown('<div class="section-header">📝 הצעות שיפור לפי סעיפים</div>', unsafe_allow_html=True)

    sections = result.get("sections", [])

    for i, section in enumerate(sections):
        title = section.get("title", f"סעיף {i+1}")
        original = section.get("original", "")
        improved = section.get("improved", "")
        explanation = section.get("explanation", "")

        with st.expander(f"📌 {title}", expanded=True):
            if explanation:
                st.info(f"💡 {explanation}")

            decision_key = f"decision_{i}"
            current_decision = st.session_state.section_decisions.get(decision_key, "improved")

            orig_sel = current_decision == "original"
            impr_sel = current_decision == "improved"

            _ck = (
                '<div style="position:absolute;top:-11px;left:50%;transform:translateX(-50%);'
                'background:#022559;color:#fff;'
                'border-radius:50%;width:24px;height:24px;display:flex;align-items:center;'
                'justify-content:center;font-size:13px;font-weight:700;box-shadow:0 1px 4px rgba(0,0,0,.2);">✓</div>'
            )

            orig_border = "2px solid #022559" if orig_sel else "1.5px solid #e0e4ea"
            orig_bg     = "#f0f4ff" if orig_sel else "#fafafa"
            impr_border = "2px solid #022559" if impr_sel else "1.5px solid #e0e4ea"
            impr_bg     = "#f0f4ff" if impr_sel else "#fafafa"
            orig_ck     = _ck if orig_sel else "<!-- -->"
            impr_ck     = _ck if impr_sel else "<!-- -->"

            # ── Compute word-level diff HTML for both cards ──
            orig_diff = _word_diff_html(original, improved, mode="original")
            impr_diff = _word_diff_html(original, improved, mode="improved")

            # ── Cards — desktop: table side-by-side | mobile: CSS radio tabs ──
            _legend_html = (
                '<div style="font-size:11px;color:#666;direction:rtl;text-align:right;'
                'margin-bottom:6px;display:flex;gap:16px;justify-content:flex-end;align-items:center;">'
                '<span style="color:#2b56e0;font-weight:700;">נוסף</span>'
                '<span style="text-decoration:line-through;color:#1a1a1a;">הוסר</span>'
                '</div>'
            )
            _impr_label = f'{"✓ " if impr_sel else ""}📝 נוסח משופר'
            _orig_label = f'{"✓ " if orig_sel else ""}📄 נוסח מקור'
            st.markdown(
                # ── DESKTOP: existing table (hidden on mobile via CSS) ──
                f'<div class="cv-dt">'
                f'{_legend_html}'
                f'<table style="width:100%;border-collapse:separate;border-spacing:16px 0;'
                f'table-layout:fixed;direction:ltr;margin-bottom:4px;">'
                f'<tr>'
                f'<td style="vertical-align:top;border:{impr_border};border-radius:12px;'
                f'padding:14px 14px 10px;background:{impr_bg};position:relative;width:50%;">'
                f'{impr_ck}'
                f'<div style="font-size:12px;font-weight:700;color:#1a1a2e;margin-bottom:8px;'
                f'letter-spacing:.3px;direction:rtl;text-align:right;">נוסח מחודש / מוצע</div>'
                f'<div style="font-size:13px;line-height:1.8;direction:rtl;text-align:right;">'
                f'{impr_diff}</div>'
                f'</td>'
                f'<td style="vertical-align:top;border:{orig_border};border-radius:12px;'
                f'padding:14px 14px 10px;background:{orig_bg};position:relative;width:50%;">'
                f'{orig_ck}'
                f'<div style="font-size:12px;font-weight:700;color:#1a1a2e;margin-bottom:8px;'
                f'letter-spacing:.3px;direction:rtl;text-align:right;">נוסח מקור + שינויים</div>'
                f'<div style="font-size:13px;line-height:1.8;direction:rtl;text-align:right;">'
                f'{orig_diff}</div>'
                f'</td>'
                f'</tr>'
                f'</table>'
                f'</div>'
                # ── MOBILE: CSS radio tabs (hidden on desktop via CSS) ──
                f'<div class="cv-mob">'
                f'<input type="radio" name="cv-tabs-{i}" id="cv-t-impr-{i}" class="cv-tr" checked>'
                f'<input type="radio" name="cv-tabs-{i}" id="cv-t-orig-{i}" class="cv-tr">'
                f'<div class="cv-tab-bar">'
                f'<label for="cv-t-impr-{i}" class="cv-tl">{_impr_label}</label>'
                f'<label for="cv-t-orig-{i}" class="cv-tl">{_orig_label}</label>'
                f'</div>'
                f'<div class="cv-tc cv-tc-impr" style="background:{impr_bg};">'
                f'<div class="cv-legend">'
                f'<span style="color:#2b56e0;font-weight:700;">נוסף</span>'
                f'<span style="text-decoration:line-through;color:#1a1a1a;">הוסר</span>'
                f'</div>'
                f'{impr_diff}'
                f'</div>'
                f'<div class="cv-tc cv-tc-orig" style="background:{orig_bg};">'
                f'{orig_diff}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # ── Buttons: col_impr first (LEFT visual) under improved TD, col_orig second (RIGHT visual) under original TD ──
            col_impr, col_orig = st.columns(2)
            with col_orig:
                if st.button(
                    "✓ נבחר" if orig_sel else "בחר נוסח זה",
                    key=f"sel_orig_{i}",
                    use_container_width=True,
                    type="primary" if orig_sel else "secondary",
                    disabled=orig_sel,
                ):
                    st.session_state.section_decisions[decision_key] = "original"
                    st.session_state.section_decisions[f"text_{i}"] = original
                    if current_decision == "custom":
                        st.session_state.section_decisions.pop(f"custom_text_{i}", None)
                    st.session_state.section_decisions.pop(f"edit_source_{i}", None)
                    st.rerun()
                if st.button(
                    "✏️ ערוך נוסח זה",
                    key=f"edit_orig_{i}",
                    use_container_width=True,
                ):
                    st.session_state.section_decisions[decision_key] = "custom"
                    st.session_state.section_decisions[f"text_{i}"] = original
                    st.session_state.section_decisions[f"edit_source_{i}"] = "original"
                    st.session_state[f"custom_text_{i}"] = original
                    st.rerun()
            with col_impr:
                if st.button(
                    "✓ נבחר" if impr_sel else "בחר נוסח זה",
                    key=f"sel_impr_{i}",
                    use_container_width=True,
                    type="primary" if impr_sel else "secondary",
                    disabled=impr_sel,
                ):
                    st.session_state.section_decisions[decision_key] = "improved"
                    st.session_state.section_decisions[f"text_{i}"] = improved
                    if current_decision == "custom":
                        st.session_state.section_decisions.pop(f"custom_text_{i}", None)
                    st.session_state.section_decisions.pop(f"edit_source_{i}", None)
                    st.rerun()
                if st.button(
                    "✏️ ערוך נוסח זה",
                    key=f"edit_impr_{i}",
                    use_container_width=True,
                ):
                    st.session_state.section_decisions[decision_key] = "custom"
                    st.session_state.section_decisions[f"text_{i}"] = improved
                    st.session_state.section_decisions[f"edit_source_{i}"] = "improved"
                    st.session_state[f"custom_text_{i}"] = improved
                    st.rerun()

            # ── Edit manually — text area below card pair ──
            if current_decision == "custom":
                edit_source = st.session_state.section_decisions.get(f"edit_source_{i}", "improved")
                source_label = "נוסח מקור" if edit_source == "original" else "נוסח מחודש"
                st.session_state.setdefault(
                    f"custom_text_{i}",
                    st.session_state.section_decisions.get(f"text_{i}", improved),
                )
                custom_text = st.text_area(
                    f"✏️ עורך {source_label} — הטקסט הערוך ישמש בקו״ח הסופי:",
                    key=f"custom_text_{i}",
                    height=150,
                )
                st.session_state.section_decisions[f"text_{i}"] = custom_text

    st.markdown("---")

    if st.button("📄 צור קורות חיים סופיים", use_container_width=True, type="primary"):
        go_to("improve_export")
        st.rerun()


def render_improve_export():
    render_header()

    if st.button("→ חזרה לעריכה", key="back_review"):
        go_to("improve_review")
        st.rerun()

    st.markdown("""
    <div class="progress-container">
        <div class="progress-label">שלב 3 מתוך 4</div>
        <div class="progress-track"><div class="progress-fill" style="width:75%"></div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">✏️ עריכה סופית</div>', unsafe_allow_html=True)
    st.markdown("זה הזמן לליטושים אחרונים. ניתן לערוך את תוכן כל סעיף, לשנות כותרות, להוסיף או למחוק סעיפים")

    result = st.session_state.analysis_result
    sections = result.get("sections", [])

    if "improve_final_sections" not in st.session_state:
        final_sections = []
        _DECOMPOSED_PREFIXES = ("שונות", "כישורים נוספים", "miscellaneous", "other")
        for i, section in enumerate(sections):
            title = section.get("title", f"סעיף {i+1}")
            if any(title.strip().startswith(p) or title.strip() == p for p in _DECOMPOSED_PREFIXES):
                continue
            final_text = st.session_state.section_decisions.get(f"text_{i}", section.get("improved", ""))
            final_sections.append({"title": title, "final_text": final_text})
        st.session_state.improve_final_sections = final_sections

    if "imp_pending_delete" not in st.session_state:
        st.session_state.imp_pending_delete = None

    sections_to_delete = []

    for i, sec in enumerate(st.session_state.improve_final_sections):
        with st.container(border=True, key=f"exp_sec_{i}"):
            col_num, col_title, col_del = st.columns([0.5, 9.5, 0.6])
            with col_num:
                st.markdown(
                    f'<div style="background:#022559;color:#fff;border-radius:50%;width:26px;height:26px;'
                    f'display:flex;align-items:center;justify-content:center;font-size:11px;'
                    f'font-weight:700;margin-top:4px;">{i + 1}</div>',
                    unsafe_allow_html=True
                )
            with col_title:
                new_title = st.text_input(
                    "כותרת סעיף",
                    value=sec["title"],
                    key=f"imp_title_{i}",
                    label_visibility="collapsed",
                    placeholder="כותרת סעיף"
                )
                st.session_state.improve_final_sections[i]["title"] = new_title
            with col_del:
                if st.button("🗑️", key=f"imp_del_{i}", help="מחק סעיף", type="tertiary"):
                    st.session_state.imp_pending_delete = i
                    st.rerun()

            new_text = st.text_area(
                "תוכן",
                value=sec["final_text"],
                key=f"imp_text_{i}",
                height=120,
                label_visibility="collapsed",
                placeholder="תוכן הסעיף"
            )
            st.session_state.improve_final_sections[i]["final_text"] = new_text

            if st.session_state.imp_pending_delete == i:
                st.warning("האם למחוק סעיף זה? לא ניתן לשחזר.")
                _, col_no, col_yes = st.columns([4, 1, 1])
                with col_yes:
                    if st.button("✓ מחק", key=f"confirm_del_{i}", type="primary", use_container_width=True):
                        sections_to_delete.append(i)
                        st.session_state.imp_pending_delete = None
                with col_no:
                    if st.button("ביטול", key=f"cancel_del_{i}", use_container_width=True):
                        st.session_state.imp_pending_delete = None
                        st.rerun()

    if sections_to_delete:
        for idx in sorted(sections_to_delete, reverse=True):
            st.session_state.improve_final_sections.pop(idx)
        st.rerun()

    if st.button("➕ הוסף סעיף חדש", key="imp_add_section"):
        st.session_state.improve_final_sections.append({"title": "סעיף חדש", "final_text": ""})
        st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("המשך לסידור סעיפים ←", key="go_to_reorder", type="primary", use_container_width=True):
        go_to("improve_reorder")
        st.rerun()


def render_improve_reorder():
    render_header()
    components.html(
        """<script>
        (function() {
            var sel = ['[data-testid="stMain"]', '.main', '[data-testid="stAppViewContainer"]'];
            for (var i = 0; i < sel.length; i++) {
                var el = window.parent.document.querySelector(sel[i]);
                if (el) { el.scrollTop = 0; }
            }
        })();
        </script>""",
        height=1,
    )

    if st.button("→ חזרה לעריכה", key="back_to_export"):
        go_to("improve_export")
        st.rerun()

    st.markdown("""
    <div class="progress-container">
        <div class="progress-label">שלב 4 מתוך 4</div>
        <div class="progress-track"><div class="progress-fill" style="width:100%"></div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">🔀 סידור סעיפים</div>', unsafe_allow_html=True)
    st.markdown("גרור את הסעיפים לסדר הרצוי. השינוי ישמר אוטומטית.")

    if "improve_final_sections" not in st.session_state or not st.session_state.improve_final_sections:
        st.warning("לא נמצאו סעיפים לסידור. חזור לשלב העריכה.")
        return

    # Flush any lingering edit-widget state into the canonical list so
    # arriving here from step 3 always reflects the very latest edits.
    secs = st.session_state.improve_final_sections
    for j in range(len(secs)):
        tk, xk = f"imp_title_{j}", f"imp_text_{j}"
        if tk in st.session_state:
            secs[j]["title"] = st.session_state.pop(tk)
        if xk in st.session_state:
            new_val = st.session_state.pop(xk)
            if new_val.strip() or not secs[j].get("final_text", "").strip():
                secs[j]["final_text"] = new_val

    n_secs = len(secs)

    _REORDER_STYLE = """
        .sortable-item {
            background: #022559 !important;
            color: #ffffff !important;
            border-radius: 10px !important;
            padding: 14px 20px !important;
            font-family: 'Assistant', sans-serif !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            cursor: grab !important;
            direction: rtl !important;
            text-align: right !important;
            margin-bottom: 6px !important;
            box-shadow: 0 2px 8px rgba(2,37,89,0.18) !important;
            border: 1.5px solid #03367a !important;
            transition: background 0.15s, box-shadow 0.15s !important;
            user-select: none !important;
        }
        .sortable-item:hover {
            background: #03367a !important;
            box-shadow: 0 4px 14px rgba(2,37,89,0.28) !important;
        }
        .sortable-component {
            direction: rtl !important;
            padding: 8px !important;
        }
    """

    handle = "⠿  "
    display_labels = [f"{handle}{sec['title']}" for sec in secs]

    sorted_labels = sort_items(
        display_labels,
        direction="vertical",
        custom_style=_REORDER_STYLE,
        key="imp_reorder_sort",
    )

    stripped_labels = [lbl[len(handle):] for lbl in sorted_labels]

    _seen: dict = {}
    new_order = []
    for lbl in stripped_labels:
        count = _seen.get(lbl, 0)
        candidates = [j for j, s in enumerate(secs) if s["title"] == lbl]
        new_order.append(candidates[count] if count < len(candidates) else candidates[-1])
        _seen[lbl] = count + 1

    if new_order != list(range(n_secs)):
        st.session_state.improve_final_sections = [secs[j] for j in new_order]
        st.rerun()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    from export_utils import _is_empty_content as _exp_is_empty
    export_sections = [
        s for s in st.session_state.improve_final_sections
        if s["final_text"].strip() and (
            any(k in s.get("title", "") for k in ["פרטים", "אישיים", "פרטי", "קשר", "personal", "Personal", "contact", "Contact"])
            or not _exp_is_empty(s["final_text"])
        )
    ]
    is_english_mode = st.session_state.get("improve_language", "he") == "en"

    # ── CV document title (optional) ──
    if "improve_cv_title" not in st.session_state:
        st.session_state.improve_cv_title = ""

    st.markdown('<div style="font-size:14px;font-weight:600;color:#022559;margin-bottom:4px;">כותרת קורות החיים (אופציונלי)</div>', unsafe_allow_html=True)
    _col_input, _col_btn = st.columns([6, 1], vertical_alignment="center")
    with _col_input:
        cv_title_draft = st.text_input(
            "כותרת",
            key="cv_title_input",
            placeholder="לדוגמה: קורות חיים - דיסקרטי",
            label_visibility="collapsed",
        )
    with _col_btn:
        if st.button("שמור", key="cv_title_save_btn", use_container_width=True, type="primary"):
            st.session_state.improve_cv_title = cv_title_draft.strip()
            st.rerun()

    cv_title = st.session_state.improve_cv_title
    if cv_title:
        st.markdown(
            f'<div style="font-size:12px;color:#22c55e;margin-top:-8px;margin-bottom:8px;">'
            f'✓ הכותרת נשמרה: <strong>{cv_title}</strong></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div style="font-size:12px;color:#6b7c93;margin-bottom:16px;">הכותרת תופיע בראש קורות החיים המיוצאים</div>', unsafe_allow_html=True)

    # ── Cache export bytes so cv_title-field reruns don't break download URLs ──
    # Key is based on sections content + cv_title + language mode; regenerate only on change.
    _cache_key = (is_english_mode, cv_title, st.session_state.get("improve_max_pages", 1), tuple((s["title"], s["final_text"]) for s in export_sections))
    if st.session_state.get("_improve_export_cache_key") != _cache_key:
        st.session_state._improve_export_cache_key = _cache_key
        st.session_state._improve_pdf = None
        st.session_state._improve_docx = None
        st.session_state._improve_pdf_err = None
        st.session_state._improve_docx_err = None
        _imp_max_pages = st.session_state.get("improve_max_pages", 1)
        if is_english_mode:
            en_src = "\n\n".join([f"=== {s['title']} ===\n{s['final_text']}" for s in export_sections])
            try:
                from export_utils import export_improved_cv_to_pdf_en
                st.session_state._improve_pdf = export_improved_cv_to_pdf_en(en_src, cv_title=cv_title.strip(), max_pages=_imp_max_pages)
            except Exception as e:
                st.session_state._improve_pdf_err = str(e)
            try:
                from export_utils import export_improved_cv_to_docx_en
                st.session_state._improve_docx = export_improved_cv_to_docx_en(en_src, cv_title=cv_title.strip())
            except Exception as e:
                st.session_state._improve_docx_err = str(e)
        else:
            try:
                from export_utils import export_improved_cv_to_pdf
                st.session_state._improve_pdf = export_improved_cv_to_pdf(export_sections, cv_title=cv_title.strip(), max_pages=_imp_max_pages)
            except Exception as e:
                st.session_state._improve_pdf_err = str(e)
            try:
                from export_utils import export_improved_cv_to_docx
                st.session_state._improve_docx = export_improved_cv_to_docx(export_sections, cv_title=cv_title.strip())
            except Exception as e:
                st.session_state._improve_docx_err = str(e)

    st.markdown("""
    <div style="background:linear-gradient(135deg,#022559 0%,#03367a 100%);border-radius:16px;
                padding:24px 24px 12px;margin:12px 0 12px;text-align:center;color:#fff;">
        <div style="font-size:22px;margin-bottom:6px;">🎉</div>
        <div style="font-size:18px;font-weight:700;margin-bottom:4px;">קורות החיים שלך מוכנים!</div>
        <div style="font-size:13px;opacity:.75;">בחר פורמט להורדה</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("_improve_pdf_err"):
        st.error(f"שגיאה ביצירת PDF: {st.session_state._improve_pdf_err}")
    if st.session_state.get("_improve_docx_err"):
        st.error(f"שגיאה ביצירת DOCX: {st.session_state._improve_docx_err}")

    _pdf_label  = "📥 Download PDF (English)"  if is_english_mode else "📥 הורד כ-PDF"
    _docx_label = "📥 Download DOCX (English)" if is_english_mode else "📥 הורד כ-DOCX"
    _pdf_name   = "cv_improved_en.pdf"  if is_english_mode else "cv_improved.pdf"
    _docx_name  = "cv_improved_en.docx" if is_english_mode else "cv_improved.docx"

    if False:  # PDF_HIDDEN
        if st.session_state.get("_improve_pdf"):
            st.download_button(
                label=_pdf_label,
                data=st.session_state._improve_pdf,
                file_name=_pdf_name,
                mime="application/pdf",
                use_container_width=True,
                key="dl_pdf_main",
            )
    if st.session_state.get("_improve_docx"):
        st.download_button(
            label=_docx_label,
            data=st.session_state._improve_docx,
            file_name=_docx_name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            key="dl_docx_main",
        )

    if not is_english_mode:
        st.markdown("""
        <div style="border-top:1px solid #e0e4ea;margin:20px 0 12px;padding-top:16px;
                    text-align:center;color:#6b7c93;font-size:13px;font-weight:600;">
            🌐 רוצה גרסה באנגלית? נתרגם עבורך
        </div>
        """, unsafe_allow_html=True)

        if "improve_en_translated" not in st.session_state:
            st.session_state.improve_en_translated = None
        if "improve_en_translating" not in st.session_state:
            st.session_state.improve_en_translating = False
        if "_improve_en_pdf" not in st.session_state:
            st.session_state._improve_en_pdf = None
        if "_improve_en_docx" not in st.session_state:
            st.session_state._improve_en_docx = None

        if st.session_state.improve_en_translated is None:
            if st.button("🔄 תרגם לאנגלית", use_container_width=True, key="translate_improve_btn"):
                st.session_state.improve_en_translating = True
                st.rerun()

            if st.session_state.improve_en_translating:
                with st.spinner("מתרגם לאנגלית..."):
                    try:
                        from ai_engine import translate_cv_to_english
                        full_text = "\n\n".join([
                            f"=== {s['title']} ===\n{s['final_text']}" for s in export_sections
                        ])
                        st.session_state.improve_en_translated = translate_cv_to_english(full_text)
                        st.session_state.improve_en_translating = False
                        # Pre-generate translated export bytes immediately
                        try:
                            from export_utils import export_improved_cv_to_pdf_en
                            st.session_state._improve_en_pdf = export_improved_cv_to_pdf_en(
                                st.session_state.improve_en_translated,
                                cv_title=st.session_state.get("improve_cv_title", "").strip(),
                                max_pages=st.session_state.get("improve_max_pages", 1),
                            )
                        except Exception:
                            pass
                        try:
                            from export_utils import export_improved_cv_to_docx_en
                            st.session_state._improve_en_docx = export_improved_cv_to_docx_en(
                                st.session_state.improve_en_translated,
                                cv_title=st.session_state.get("improve_cv_title", "").strip(),
                            )
                        except Exception:
                            pass
                        st.rerun()
                    except Exception as e:
                        st.error(f"שגיאה בתרגום: {str(e)}")
                        st.session_state.improve_en_translating = False
        else:
            if False:  # PDF_HIDDEN
                if st.session_state.get("_improve_en_pdf"):
                    st.download_button(
                        label="📥 Download PDF (English)",
                        data=st.session_state._improve_en_pdf,
                        file_name="cv_improved_en.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="dl_pdf_translated",
                    )
            if st.session_state.get("_improve_en_docx"):
                st.download_button(
                    label="📥 Download DOCX (English)",
                    data=st.session_state._improve_en_docx,
                    file_name="cv_improved_en.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key="dl_docx_translated",
                )

    st.markdown("---")
    if st.button("🏠 חזרה לדף הבית", use_container_width=True, key="reorder_home_btn"):
        go_to("home")
        st.rerun()


def _init_build_form_data():
    if "build_form_data" not in st.session_state:
        st.session_state.build_form_data = {
            "full_name": "",
            "phone": "",
            "email": "",
            "city": "",
            "linkedin": "",
            "professional_summary": "",
            "experience": [{"title": "", "company": "", "period": "", "achievements": "", "honors": ""}],
            "education": [{"degree": "", "institution": "", "year": "", "honors": ""}],
            "technical_skills": "",
            "soft_skills": "",
            "languages": [{"language": "עברית", "level": "שפת אם"}, {"language": "אנגלית", "level": ""}],
            "military": "",
            "volunteering": "",
            "projects": "",
            "additional": "",
        }


_CONSULT_BUBBLE_CSS = """
<style>
@keyframes _consult_bounce {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
    30%            { transform: translateY(-6px); opacity: 1; }
}
._consult_chat_wrap {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 4px 2px;
}
._consult_row {
    display: flex;
    width: 100%;
}
._consult_row.user     { justify-content: flex-end; }
._consult_row.assistant { justify-content: flex-start; }
._consult_bubble {
    max-width: 75%;
    padding: 10px 14px;
    border-radius: 18px;
    line-height: 1.6;
    word-break: break-word;
    font-size: 14px;
}
._consult_bubble.user {
    background-color: #2b56e0;
    color: #ffffff;
    border-bottom-right-radius: 4px;
}
._consult_bubble.assistant {
    background-color: #f2f2f2;
    color: #022559;
    border-bottom-left-radius: 4px;
}
._consult_typing_bubble {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #f2f2f2;
    border-radius: 18px;
    border-bottom-left-radius: 4px;
    padding: 10px 16px;
}
._consult_typing_bubble span {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background-color: #8899b4;
    animation: _consult_bounce 1.2s infinite ease-in-out;
}
._consult_typing_bubble span:nth-child(2) { animation-delay: 0.2s; }
._consult_typing_bubble span:nth-child(3) { animation-delay: 0.4s; }
</style>
"""

_CONSULT_SCROLL_JS = """
<script>
(function() {
  var allDivs = parent.document.querySelectorAll('div');
  var scrollable = null;
  for (var i = 0; i < allDivs.length; i++) {
    var d = allDivs[i];
    if (d.scrollHeight > d.clientHeight && d.clientHeight > 80 && d.clientHeight < 500) {
      scrollable = d;
    }
  }
  if (scrollable) { scrollable.scrollTop = scrollable.scrollHeight; }
})();
</script>
"""


def _consult_build_html(history, show_typing=False):
    """Build the full chat bubble HTML for the consultation panel."""
    import html as _html
    rows = []
    for msg in history:
        role = msg["role"]
        text = _html.escape(msg["content"]).replace("\n", "<br>")
        rows.append(
            f'<div class="_consult_row {role}">'
            f'<div class="_consult_bubble {role}">{text}</div>'
            f'</div>'
        )
    if show_typing:
        rows.append(
            '<div class="_consult_row assistant">'
            '<div class="_consult_typing_bubble">'
            '<span></span><span></span><span></span>'
            '</div></div>'
        )
    inner = "\n".join(rows)
    return f'<div class="_consult_chat_wrap">{inner}</div>'


def _render_consult_panel(section_key: str):
    """Render the inline consultation chat panel for `section_key`.

    Renders nothing unless this section is the currently open one. The panel
    sits inside the same section card, beneath the section's existing inputs,
    so the card grows downward when opened and collapses when closed.
    """
    if st.session_state.get("active_consultation") != section_key:
        return

    from ai_engine import (
        section_consultation_reply,
        section_consultation_greeting,
    )
    import logging as _logging

    st.markdown(_CONSULT_BUBBLE_CSS, unsafe_allow_html=True)

    st.markdown(
        '<hr style="margin:14px 0 10px 0; border:none; border-top:1px solid #d6deea;" />'
        '<div style="font-size:13px; color:#6b7c93; margin-bottom:8px;">'
        '💬 שאל את היועץ כל שאלה על מה לכתוב בסעיף הזה. הוא עוזר אבל לא כותב במקומך.'
        '</div>',
        unsafe_allow_html=True,
    )

    if "consultation_chats" not in st.session_state:
        st.session_state.consultation_chats = {}
    if section_key not in st.session_state.consultation_chats:
        st.session_state.consultation_chats[section_key] = [
            {"role": "assistant", "content": section_consultation_greeting(section_key)}
        ]

    history = st.session_state.consultation_chats[section_key]
    consulting_flag = f"_consulting_{section_key}"
    is_consulting = st.session_state.get(consulting_flag, False)

    chat_box = st.container(height=320, border=False)
    with chat_box:
        bubbles_html = _consult_build_html(history, show_typing=is_consulting)
        st.markdown(bubbles_html, unsafe_allow_html=True)
        st.markdown(_CONSULT_SCROLL_JS, unsafe_allow_html=True)

    user_msg = st.chat_input(
        "הקלד את השאלה שלך כאן...",
        key=f"consult_chat_input_{section_key}",
    )

    if st.button(
        "🗑️ איפוס השיחה",
        key=f"consult_clear_{section_key}",
        use_container_width=True,
    ):
        st.session_state.consultation_chats[section_key] = [
            {"role": "assistant", "content": section_consultation_greeting(section_key)}
        ]
        st.session_state[consulting_flag] = False
        st.rerun()

    if is_consulting:
        try:
            reply = section_consultation_reply(section_key, history)
            if not reply or not reply.strip():
                reply = "סליחה, לא הצלחתי להפיק תשובה כרגע. נסה לנסח שוב את השאלה."
            history.append({"role": "assistant", "content": reply})
        except Exception:
            _logging.getLogger(__name__).exception(
                "Consultation chat failed for section %s", section_key
            )
            history.append({
                "role": "assistant",
                "content": "אירעה שגיאה בעת פנייה ליועץ. נסה שוב בעוד רגע."
            })
        st.session_state[consulting_flag] = False
        st.rerun()

    if user_msg and user_msg.strip():
        history.append({"role": "user", "content": user_msg.strip()})
        st.session_state[consulting_flag] = True
        st.rerun()


def _render_consult_button(section_key: str):
    is_open = st.session_state.get("active_consultation") == section_key
    label = "✖ סגור התייעצות" if is_open else "💬 התייעץ עם AI"
    help_text = (
        "סגור את שיחת הייעוץ"
        if is_open
        else "פתח צ'אט עם יועץ קריירה לקבלת עצות לכתיבת הסעיף הזה"
    )
    if st.button(
        label,
        key=f"consult_btn_{section_key}",
        type="secondary",
        help=help_text,
        use_container_width=True,
    ):
        st.session_state.active_consultation = (
            None if is_open else section_key
        )
        st.rerun()


def render_build_form():
    render_header()

    if st.button("→ חזרה לדף הבית", key="back_home_build"):
        go_to("home")
        st.rerun()

    _init_build_form_data()
    fd = st.session_state.build_form_data

    st.markdown("""
    <style>
        [class*="st-key-bfc_"] { background-color: #f2f1ef !important; }
        div:has(>[class*="st-key-bfc_"]) { background-color: #f2f1ef !important; border-color: #f2f1ef !important; }
        [class*="st-key-bfc_"] [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #022559 !important; border-width: 1.5px !important;
            border-radius: 14px !important; background-color: #f2f1ef !important;
        }
        [class*="st-key-consult_btn_"] button,
        [class*="st-key-consult_btn_"] button:hover,
        [class*="st-key-consult_btn_"] button:focus,
        [class*="st-key-consult_btn_"] button:focus-visible,
        [class*="st-key-consult_btn_"] button:active {
            background-color: #1e40af !important;
            color: #ffffff !important;
            border: 1px solid #1e40af !important;
            box-shadow: none !important;
        }
        [class*="st-key-consult_btn_"] button p,
        [class*="st-key-consult_btn_"] button div {
            color: #ffffff !important;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.container(border=True, key="bfc_pages"):
        st.markdown('<div class="section-header">📄 כמה עמודים תרצו?</div>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:15px; color:#6b7c93;">ננסה להכניס לעמוד אחד. אם הניסיון עשיר - עדיף לגלוש לעמוד שני על פני קיצוץ תוכן חשוב. בחרו "עד שני עמודים" כדי לאפשר זאת מראש.</span>', unsafe_allow_html=True)
        if "build_max_pages" not in st.session_state:
            st.session_state.build_max_pages = 1
        build_pages_choice = st.radio(
            "מספר עמודים",
            ["נסה להכניס לעמוד אחד (מומלץ)", "עד שני עמודים"],
            horizontal=True,
            key="build_pages_radio",
            label_visibility="collapsed"
        )
        st.session_state.build_max_pages = 1 if build_pages_choice == "נסה להכניס לעמוד אחד (מומלץ)" else 2

    with st.container(border=True, key="bfc_target"):
        _hdr, _btn = st.columns([3, 1.3])
        with _hdr:
            st.markdown('<div class="section-header">🎯 תפקיד יעד (אופציונלי)</div>', unsafe_allow_html=True)
        with _btn:
            _render_consult_button("target")
        st.markdown('<span style="font-size:15px; color:#6b7c93;">ציין את שם התפקיד או הדבק את תיאור המשרה המלא — ככל שתפרטו יותר, הבינה המלאכותית תוכל להתאים את קורות החיים למסנן הממוחשב של החברה (המערכת שסורקת ומדרגת קורות חיים לפני שהם מגיעים לגורם אנושי)</span>', unsafe_allow_html=True)
        if "build_target_position" not in st.session_state:
            st.session_state.build_target_position = ""
        st.session_state.build_target_position = st.text_area(
            "תפקיד יעד",
            value=st.session_state.build_target_position,
            key="build_target_input",
            placeholder="למשל: מנהל משאבי אנוש, מפתח Full Stack...\nאו הדבק כאן את תיאור המשרה המלא מהמודעה - ככל שתספק יותר פרטים, קורות החיים יותאמו טוב יותר",
            label_visibility="collapsed",
            height=68
        )
        _render_consult_panel("target")

    with st.container(border=True, key="bfc_personal"):
        _hdr, _btn = st.columns([3, 1.3])
        with _hdr:
            st.markdown('<div class="section-header">👤 פרטים אישיים</div>', unsafe_allow_html=True)
        with _btn:
            _render_consult_button("personal")
        fd["full_name"] = st.text_input("שם מלא", value=fd["full_name"], key="bf_name", placeholder="ישראל ישראלי")
        c1, c2, c3 = st.columns(3)
        with c3:
            fd["phone"] = st.text_input("טלפון", value=fd["phone"], key="bf_phone", placeholder="050-1234567")
        with c2:
            fd["email"] = st.text_input("אימייל", value=fd["email"], key="bf_email", placeholder="email@example.com")
        with c1:
            fd["city"] = st.text_input("עיר", value=fd["city"], key="bf_city", placeholder="תל אביב")
        fd["linkedin"] = st.text_input("פרופיל לינקדאין (אופציונלי)", value=fd.get("linkedin", ""), key="bf_linkedin", placeholder="https://linkedin.com/in/your-profile")
        _render_consult_panel("personal")

    with st.container(border=True, key="bfc_summary"):
        _hdr, _btn = st.columns([3, 1.3])
        with _hdr:
            st.markdown('<div class="section-header">📋 תקציר מקצועי</div>', unsafe_allow_html=True)
        with _btn:
            _render_consult_button("summary")
        st.markdown('<span style="font-size:13px; color:#6b7c93;">כתוב בקצרה על הרקע המקצועי שלך, או השאר ריק והבינה המלאכותית תכתוב עבורך</span>', unsafe_allow_html=True)
        fd["professional_summary"] = st.text_area(
            "תקציר",
            value=fd["professional_summary"],
            key="bf_summary",
            height=80,
            label_visibility="collapsed",
            placeholder="למשל: מפתח תוכנה עם 5 שנות ניסיון בפיתוח אפליקציות ווב..."
        )
        _render_consult_panel("summary")

    with st.container(border=True, key="bfc_experience"):
        _hdr, _btn = st.columns([3, 1.3])
        with _hdr:
            st.markdown('<div class="section-header">💼 ניסיון תעסוקתי</div>', unsafe_allow_html=True)
        with _btn:
            _render_consult_button("experience")
        experience = fd["experience"]
        exp_to_delete = []
        for i, exp in enumerate(experience):
            if i > 0:
                st.markdown("---")
            col_header, col_del = st.columns([5, 1])
            with col_header:
                st.markdown(f'<span style="font-size:14px; font-weight:600; color:#6b7c93;">תפקיד {i+1}</span>', unsafe_allow_html=True)
            with col_del:
                if len(experience) > 1:
                    if st.button("🗑️", key=f"bf_del_exp_{i}", help="מחק", type="tertiary"):
                        exp_to_delete.append(i)

            ec1, ec2, ec3 = st.columns(3)
            with ec3:
                exp["title"] = st.text_input("תפקיד", value=exp.get("title", ""), key=f"bf_exp_title_{i}", placeholder="מנהל פרויקטים")
            with ec2:
                exp["company"] = st.text_input("חברה", value=exp.get("company", ""), key=f"bf_exp_company_{i}", placeholder="שם החברה")
            with ec1:
                exp["period"] = st.text_input("תקופה", value=exp.get("period", ""), key=f"bf_exp_period_{i}", placeholder="2020-2024")

            exp["achievements"] = st.text_area(
                "תיאור ההישגים",
                value=exp.get("achievements", ""),
                key=f"bf_exp_ach_{i}",
                height=70,
                label_visibility="collapsed",
                placeholder="הישגים ו/או כישורים שהבאת לידי ביטוי במסגרת התפקיד"
            )
            exp["honors"] = st.text_input("הצטיינות (אופציונלי)", value=exp.get("honors", ""), key=f"bf_exp_hon_{i}", placeholder="למשל: עובד מצטיין, פרס חדשנות...")

        if exp_to_delete:
            for idx in sorted(exp_to_delete, reverse=True):
                experience.pop(idx)
            st.rerun()

        _render_consult_panel("experience")

    if st.button("+ הוסף תפקיד", key="bf_add_exp", use_container_width=True, type="primary"):
        experience.append({"title": "", "company": "", "period": "", "achievements": "", "honors": ""})
        st.rerun()

    with st.container(border=True, key="bfc_education"):
        _hdr, _btn = st.columns([3, 1.3])
        with _hdr:
            st.markdown('<div class="section-header">🎓 השכלה אקדמית / מקצועית</div>', unsafe_allow_html=True)
        with _btn:
            _render_consult_button("education")
        education = fd["education"]
        edu_to_delete = []
        for i, edu in enumerate(education):
            if i > 0:
                st.markdown("---")
            col_header, col_del = st.columns([5, 1])
            with col_del:
                if len(education) > 1:
                    if st.button("🗑️", key=f"bf_del_edu_{i}", help="מחק", type="tertiary"):
                        edu_to_delete.append(i)

            ec1, ec2, ec3 = st.columns(3)
            with ec3:
                edu["degree"] = st.text_input("תואר / תעודה", value=edu.get("degree", ""), key=f"bf_edu_deg_{i}", placeholder="תואר ראשון הנדסת תוכנה")
            with ec2:
                edu["institution"] = st.text_input("מוסד לימודים", value=edu.get("institution", ""), key=f"bf_edu_inst_{i}", placeholder="אוניברסיטת תל אביב")
            with ec1:
                edu["year"] = st.text_input("תקופה (אופציונלי)", value=edu.get("year", ""), key=f"bf_edu_year_{i}", placeholder="2018-2022 או 2022-היום")
            edu["honors"] = st.text_input("הצטיינות (אופציונלי)", value=edu.get("honors", ""), key=f"bf_edu_hon_{i}", placeholder="למשל: בוגר הצטיינות, דין של הדיקן...")

        if edu_to_delete:
            for idx in sorted(edu_to_delete, reverse=True):
                education.pop(idx)
            st.rerun()

        _render_consult_panel("education")

    if st.button("+ הוסף השכלה", key="bf_add_edu", use_container_width=True, type="primary"):
        education.append({"degree": "", "institution": "", "year": "", "honors": ""})
        st.rerun()

    with st.container(border=True, key="bfc_skills"):
        _hdr, _btn = st.columns([3, 1.3])
        with _hdr:
            st.markdown('<div class="section-header">🛠️ מיומנויות</div>', unsafe_allow_html=True)
        with _btn:
            _render_consult_button("skills")
        fd["technical_skills"] = st.text_input(
            "מיומנויות טכניות",
            value=fd["technical_skills"],
            key="bf_tech",
            placeholder="Python, JavaScript, Excel, ניהול פרויקטים..."
        )
        fd["soft_skills"] = st.text_input(
            "מיומנויות רכות",
            value=fd["soft_skills"],
            key="bf_soft",
            placeholder="עבודת צוות, מנהיגות, תקשורת בינאישית..."
        )
        _render_consult_panel("skills")

    with st.container(border=True, key="bfc_languages"):
        st.markdown('<div class="section-header">🌍 שפות</div>', unsafe_allow_html=True)
        languages = fd["languages"]
        lang_to_delete = []
        for i, lang in enumerate(languages):
            lc1, lc2, lc_del = st.columns([3, 3, 1])
            with lc1:
                lang["language"] = st.text_input("שפה", value=lang.get("language", ""), key=f"bf_lang_{i}", placeholder="עברית")
            with lc2:
                lang["level"] = st.text_input("רמה", value=lang.get("level", ""), key=f"bf_lang_lvl_{i}", placeholder="שפת אם / גבוהה / בסיסית")
            with lc_del:
                if len(languages) > 1:
                    if st.button("🗑️", key=f"bf_del_lang_{i}", help="מחק", type="tertiary"):
                        lang_to_delete.append(i)

        if lang_to_delete:
            for idx in sorted(lang_to_delete, reverse=True):
                languages.pop(idx)
            st.rerun()

    if st.button("+ הוסף שפה", key="bf_add_lang", use_container_width=True, type="primary"):
        languages.append({"language": "", "level": ""})
        st.rerun()

    with st.container(border=True, key="bfc_military"):
        _hdr, _btn = st.columns([3, 1.3])
        with _hdr:
            st.markdown('<div class="section-header">🎖️ שירות צבאי / לאומי (אופציונלי)</div>', unsafe_allow_html=True)
        with _btn:
            _render_consult_button("military")
        fd["military"] = st.text_area(
            "שירות צבאי",
            value=fd.get("military", ""),
            key="bf_military",
            height=60,
            label_visibility="collapsed",
            placeholder="למשל: חיל המודיעין - קצינת מחקר, שירות מלא 2018-2020"
        )
        _render_consult_panel("military")

    with st.container(border=True, key="bfc_volunteering"):
        _hdr, _btn = st.columns([3, 1.3])
        with _hdr:
            st.markdown('<div class="section-header">🤝 התנדבות בקהילה (אופציונלי)</div>', unsafe_allow_html=True)
        with _btn:
            _render_consult_button("volunteering")
        fd["volunteering"] = st.text_area(
            "התנדבות",
            value=fd.get("volunteering", ""),
            key="bf_volunteering",
            height=60,
            label_visibility="collapsed",
            placeholder="למשל: מנטור בעמותת יוניסטרים, מתנדב בלמ״ן..."
        )
        _render_consult_panel("volunteering")

    with st.container(border=True, key="bfc_projects"):
        _hdr, _btn = st.columns([3, 1.3])
        with _hdr:
            st.markdown('<div class="section-header">🚀 פרויקטים עצמאיים (אופציונלי)</div>', unsafe_allow_html=True)
        with _btn:
            _render_consult_button("projects")
        fd["projects"] = st.text_area(
            "פרויקטים",
            value=fd.get("projects", ""),
            key="bf_projects",
            height=60,
            label_visibility="collapsed",
            placeholder="למשל: פיתוח אפליקציה לניהול משימות בReact, בניית אתר אישי..."
        )
        _render_consult_panel("projects")

    with st.container(border=True, key="bfc_additional"):
        _hdr, _btn = st.columns([3, 1.3])
        with _hdr:
            st.markdown('<div class="section-header">📌 מידע נוסף (אופציונלי)</div>', unsafe_allow_html=True)
        with _btn:
            _render_consult_button("additional")
        fd["additional"] = st.text_area(
            "מידע נוסף",
            value=fd["additional"],
            key="bf_additional",
            height=60,
            label_visibility="collapsed",
            placeholder="קורסים, הסמכות, פרסומים..."
        )
        _render_consult_panel("additional")

    st.session_state.build_form_data = fd

    st.markdown("---")
    if st.button("✨ צור קורות חיים מקצועיים", use_container_width=True, type="primary"):
        if not fd["full_name"].strip():
            st.warning("נא למלא לפחות את השם המלא")
            return

        has_content = (
            fd["professional_summary"].strip() or
            any(e.get("title", "").strip() or e.get("company", "").strip() for e in fd["experience"]) or
            any(e.get("degree", "").strip() for e in fd["education"]) or
            fd["technical_skills"].strip()
        )
        if not has_content:
            st.warning("נא למלא לפחות תפקיד אחד או פרט נוסף כלשהו")
            return

        with st.status("יוצר את קורות החיים שלך...", expanded=True) as status:
            st.write("📋 אוסף את הנתונים מהטופס...")
            from ai_engine import generate_cv_from_form
            st.write("🤖 הבינה המלאכותית מעבדת ומשפרת... (15-30 שניות)")
            cv_data = generate_cv_from_form(fd, target_position=st.session_state.build_target_position, max_pages=st.session_state.get("build_max_pages", 1))
            st.write("✅ קורות החיים מוכנים!")
            status.update(label="קורות החיים מוכנים!", state="complete")

        from export_utils import _is_empty_content, _filter_list
        for exp in cv_data.get("experience", []):
            if _is_empty_content(exp.get("honors", "")):
                exp["honors"] = ""
            exp["achievements"] = _filter_list(exp.get("achievements", []))
        for edu in cv_data.get("education", []):
            if _is_empty_content(edu.get("honors", "")):
                edu["honors"] = ""
        cv_data["military"] = _filter_list(cv_data.get("military", []))
        cv_data["volunteering"] = _filter_list(cv_data.get("volunteering", []))
        cv_data["projects"] = _filter_list(cv_data.get("projects", []))
        cv_data["additional"] = _filter_list(cv_data.get("additional", []))
        if _is_empty_content(cv_data.get("professional_summary", "")):
            cv_data["professional_summary"] = ""

        st.session_state.generated_cv = cv_data
        go_to("build_preview")
        st.rerun()


def render_build_preview():
    from export_utils import _filter_list
    render_header()

    if st.button("→ חזרה לטופס", key="back_form"):
        st.session_state.generated_cv = None
        go_to("build_form")
        st.rerun()

    cv_data = st.session_state.generated_cv
    if not cv_data:
        st.warning("לא נמצאו נתונים. חזור לטופס.")
        return

    st.markdown('<div class="section-header">✨ קורות החיים שלך מוכנים!</div>', unsafe_allow_html=True)
    st.markdown("ניתן לערוך, לשנות או למחוק כל שדה לפני ההורדה")

    need_rerun = False

    st.markdown('<div class="section-header">👤 פרטים אישיים</div>', unsafe_allow_html=True)
    cv_data["full_name"] = st.text_input("שם מלא", value=cv_data.get("full_name", ""), key="build_name")

    contact = cv_data.get("contact", {})
    c1, c2, c3 = st.columns(3)
    with c3:
        contact["phone"] = st.text_input("טלפון", value=contact.get("phone", ""), key="build_phone")
    with c2:
        contact["email"] = st.text_input("אימייל", value=contact.get("email", ""), key="build_email")
    with c1:
        contact["city"] = st.text_input("עיר", value=contact.get("city", ""), key="build_city")
    contact["linkedin"] = st.text_input("לינקדאין", value=contact.get("linkedin", ""), key="build_linkedin")
    cv_data["contact"] = contact

    st.markdown('<div class="section-header">📋 תקציר מקצועי</div>', unsafe_allow_html=True)
    cv_data["professional_summary"] = st.text_area(
        "תקציר מקצועי",
        value=cv_data.get("professional_summary", ""),
        key="build_summary",
        height=100,
        label_visibility="collapsed"
    )

    st.markdown('<div class="section-header">💼 ניסיון תעסוקתי</div>', unsafe_allow_html=True)
    experience = cv_data.get("experience", [])
    exp_to_delete = []
    for i, exp in enumerate(experience):
        with st.container():
            col_header, col_del = st.columns([5, 1])
            with col_del:
                if st.button("🗑️", key=f"del_exp_{i}", help="מחק ניסיון", type="tertiary"):
                    exp_to_delete.append(i)

            ec1, ec2, ec3 = st.columns(3)
            with ec3:
                exp["title"] = st.text_input("תפקיד", value=exp.get("title", ""), key=f"exp_title_{i}")
            with ec2:
                exp["company"] = st.text_input("חברה", value=exp.get("company", ""), key=f"exp_company_{i}")
            with ec1:
                exp["period"] = st.text_input("תקופה", value=exp.get("period", ""), key=f"exp_period_{i}")

            achievements = exp.get("achievements", [])
            ach_text = "\n".join(achievements)
            new_ach = st.text_area(
                "הישגים (שורה לכל הישג)",
                value=ach_text,
                key=f"exp_ach_{i}",
                height=80
            )
            exp["achievements"] = [a.strip() for a in new_ach.split("\n") if a.strip()]
            exp["honors"] = st.text_input("הצטיינות", value=exp.get("honors", ""), key=f"exp_hon_{i}")
            st.markdown("---")

    if exp_to_delete:
        for idx in sorted(exp_to_delete, reverse=True):
            experience.pop(idx)
        cv_data["experience"] = experience
        need_rerun = True

    if st.button("➕ הוסף ניסיון תעסוקתי", key="add_exp"):
        experience.append({"title": "", "company": "", "period": "", "achievements": [], "honors": ""})
        cv_data["experience"] = experience
        need_rerun = True

    st.markdown('<div class="section-header">🎓 השכלה אקדמית / מקצועית</div>', unsafe_allow_html=True)
    education = cv_data.get("education", [])
    edu_to_delete = []
    for i, edu in enumerate(education):
        with st.container():
            col_header, col_del = st.columns([5, 1])
            with col_del:
                if st.button("🗑️", key=f"del_edu_{i}", help="מחק השכלה", type="tertiary"):
                    edu_to_delete.append(i)

            ec1, ec2, ec3 = st.columns(3)
            with ec3:
                edu["degree"] = st.text_input("תואר / תעודה", value=edu.get("degree", ""), key=f"edu_degree_{i}")
            with ec2:
                edu["institution"] = st.text_input("מוסד לימודים", value=edu.get("institution", ""), key=f"edu_inst_{i}")
            with ec1:
                edu["year"] = st.text_input("תקופה (אופציונלי)", value=edu.get("year", ""), key=f"edu_year_{i}", placeholder="2018-2022 או 2022-היום")
            edu["honors"] = st.text_input("הצטיינות", value=edu.get("honors", ""), key=f"edu_hon_{i}")
            st.markdown("---")

    if edu_to_delete:
        for idx in sorted(edu_to_delete, reverse=True):
            education.pop(idx)
        cv_data["education"] = education
        need_rerun = True

    if st.button("➕ הוסף השכלה", key="add_edu"):
        education.append({"degree": "", "institution": "", "year": "", "honors": ""})
        cv_data["education"] = education
        need_rerun = True

    st.markdown('<div class="section-header">🛠️ מיומנויות</div>', unsafe_allow_html=True)
    skills = cv_data.get("skills", {})
    technical = skills.get("technical", [])
    soft = skills.get("soft", [])

    tech_text = st.text_input(
        "מיומנויות טכניות (מופרדות בפסיקים)",
        value=", ".join(technical),
        key="build_tech_skills"
    )
    skills["technical"] = [s.strip() for s in tech_text.split(",") if s.strip()]

    soft_text = st.text_input(
        "מיומנויות רכות (מופרדות בפסיקים)",
        value=", ".join(soft),
        key="build_soft_skills"
    )
    skills["soft"] = [s.strip() for s in soft_text.split(",") if s.strip()]
    cv_data["skills"] = skills

    st.markdown('<div class="section-header">🌍 שפות</div>', unsafe_allow_html=True)
    languages = cv_data.get("languages", [])
    lang_to_delete = []
    for i, lang in enumerate(languages):
        lc1, lc2, lc_del = st.columns([3, 3, 1])
        with lc1:
            lang["language"] = st.text_input("שפה", value=lang.get("language", ""), key=f"lang_name_{i}")
        with lc2:
            lang["level"] = st.text_input("רמה", value=lang.get("level", ""), key=f"lang_level_{i}")
        with lc_del:
            if st.button("🗑️", key=f"del_lang_{i}", help="מחק שפה", type="tertiary"):
                lang_to_delete.append(i)

    if lang_to_delete:
        for idx in sorted(lang_to_delete, reverse=True):
            languages.pop(idx)
        cv_data["languages"] = languages
        need_rerun = True

    if st.button("➕ הוסף שפה", key="add_lang"):
        languages.append({"language": "", "level": ""})
        cv_data["languages"] = languages
        need_rerun = True

    military = cv_data.get("military", [])
    if military and _filter_list(military):
        st.markdown('<div class="section-header">🎖️ שירות צבאי / לאומי</div>', unsafe_allow_html=True)
        mil_text = "\n".join(military) if isinstance(military, list) else str(military)
        new_mil = st.text_area(
            "שירות צבאי (שורה לכל פריט)",
            value=mil_text,
            key="build_military",
            height=60,
            label_visibility="collapsed",
            placeholder="חיל המודיעין - קצינת מחקר, שירות מלא"
        )
        cv_data["military"] = [m.strip() for m in new_mil.split("\n") if m.strip()]

    volunteering = cv_data.get("volunteering", [])
    if volunteering and _filter_list(volunteering):
        st.markdown('<div class="section-header">🤝 התנדבות</div>', unsafe_allow_html=True)
        vol_text = "\n".join(volunteering) if isinstance(volunteering, list) else str(volunteering)
        new_vol = st.text_area(
            "התנדבות (שורה לכל פריט)",
            value=vol_text,
            key="build_volunteering",
            height=60,
            label_visibility="collapsed",
            placeholder="מנטור בעמותה, מתנדב בארגון..."
        )
        cv_data["volunteering"] = [v.strip() for v in new_vol.split("\n") if v.strip()]

    projects = cv_data.get("projects", [])
    if projects and _filter_list(projects):
        st.markdown('<div class="section-header">🚀 פרויקטים עצמאיים</div>', unsafe_allow_html=True)
        proj_text = "\n".join(projects) if isinstance(projects, list) else str(projects)
        new_proj = st.text_area(
            "פרויקטים (שורה לכל פריט)",
            value=proj_text,
            key="build_projects",
            height=60,
            label_visibility="collapsed",
            placeholder="פיתוח אפליקציה, בניית אתר..."
        )
        cv_data["projects"] = [p.strip() for p in new_proj.split("\n") if p.strip()]

    additional = cv_data.get("additional", [])
    if additional and _filter_list(additional):
        st.markdown('<div class="section-header">📌 מידע נוסף</div>', unsafe_allow_html=True)
        add_text = "\n".join(additional)
        new_add = st.text_area(
            "מידע נוסף (שורה לכל פריט)",
            value=add_text,
            key="build_additional",
            height=80,
            label_visibility="collapsed",
            placeholder="קורסים, הסמכות, פרסומים..."
        )
        cv_data["additional"] = [a.strip() for a in new_add.split("\n") if a.strip()]

    st.session_state.generated_cv = cv_data

    if need_rerun:
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="section-header">⬇️ הורדת קורות החיים</div>', unsafe_allow_html=True)

    if False:  # PDF_HIDDEN
        try:
            from export_utils import export_cv_to_pdf
            pdf_bytes = export_cv_to_pdf(cv_data, max_pages=st.session_state.get("build_max_pages", 1))
            st.download_button(
                label="📥 הורד כ-PDF",
                data=pdf_bytes,
                file_name="cv_master.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"שגיאה ביצירת PDF: {str(e)}")

    try:
        from export_utils import export_cv_to_docx
        docx_bytes = export_cv_to_docx(cv_data)
        st.download_button(
            label="📥 הורד כ-DOCX",
            data=docx_bytes,
            file_name="cv_master.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"שגיאה ביצירת DOCX: {str(e)}")

    st.markdown("---")
    st.markdown(
        '<div style="background:#f0f7ff;border:1.5px solid #b3d0f5;border-radius:12px;padding:16px 20px;margin:8px 0 4px 0;">'
        '<div style="font-size:15px;font-weight:600;color:#022559;margin-bottom:6px;">🔍 רוצה לוודא שהניסוח מושלם?</div>'
        '<div style="font-size:14px;color:#4a5568;">נריץ את קורות החיים שיצרת דרך מערכת השיפור כדי לוודא שהניסוח אופטימלי, מילות המפתח נכונות והמסמך עובר מסנני ATS בהצלחה.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button("🔍 בדוק את הניסוח דרך כלי השיפור", use_container_width=True, key="send_to_improve_btn"):
        staged_text = _cv_dict_to_text(st.session_state.generated_cv)
        st.session_state.staged_cv_text = staged_text
        st.session_state.staged_from_build = True
        go_to("improve_upload")
        st.rerun()

    st.markdown('<div class="section-header">🌐 הורדה באנגלית (תרגום)</div>', unsafe_allow_html=True)

    if "build_en_translated" not in st.session_state:
        st.session_state.build_en_translated = None
    if "build_en_translating" not in st.session_state:
        st.session_state.build_en_translating = False

    if st.session_state.build_en_translated is None:
        if st.button("🔄 תרגם לאנגלית", use_container_width=True, key="translate_build_btn"):
            st.session_state.build_en_translating = True
            st.rerun()

        if st.session_state.build_en_translating:
            with st.spinner("מתרגם לאנגלית..."):
                try:
                    from ai_engine import translate_cv_data_to_english
                    st.session_state.build_en_translated = translate_cv_data_to_english(cv_data)
                    st.session_state.build_en_translating = False
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאה בתרגום: {str(e)}")
                    st.session_state.build_en_translating = False
    else:
        if False:  # PDF_HIDDEN
            try:
                from export_utils import export_cv_to_pdf_en
                pdf_en = export_cv_to_pdf_en(st.session_state.build_en_translated, max_pages=st.session_state.get("build_max_pages", 1))
                st.download_button(
                    label="📥 Download PDF (English)",
                    data=pdf_en,
                    file_name="cv_english.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"שגיאה ביצירת PDF: {str(e)}")
        try:
            from export_utils import export_cv_to_docx_en
            docx_en = export_cv_to_docx_en(st.session_state.build_en_translated)
            st.download_button(
                label="📥 Download DOCX (English)",
                data=docx_en,
                file_name="cv_english.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"שגיאה ביצירת DOCX: {str(e)}")

    st.markdown("---")
    if st.button("🏠 חזרה לדף הבית", use_container_width=True):
        go_to("home")
        st.rerun()


pages = {
    "home": render_home,
    "improve_upload": render_improve_upload,
    "improve_review": render_improve_review,
    "improve_export": render_improve_export,
    "improve_reorder": render_improve_reorder,
    "build_form": render_build_form,
    "build_preview": render_build_preview,
}

init_storage()

current_page = st.session_state.get("page", "home")
render_fn = pages.get(current_page, render_home)
render_fn()

save_to_storage()
