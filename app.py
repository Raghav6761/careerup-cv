import re
import base64
import difflib
import html as html_lib
import streamlit as st
from PIL import Image
from styles import inject_custom_css

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
        # Job/education header line — contains year range → bold only
        elif year_pattern.search(stripped):
            html_parts.append(
                f'<div style="font-weight:700;color:#1a1a2e;margin:5px 0 1px 0;">{safe}</div>'
            )
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
        # Year-range line → bold job/edu header
        elif year_pattern.search(stripped):
            html_parts.append(
                f'<div style="font-weight:700;color:#1a1a2e;margin:6px 0 1px 0;">{safe}</div>'
            )
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
    Return HTML of text with word-level diff highlights.
    mode='original': removed words (in orig, not in improved) → orange #fde68a
    mode='improved': added words (in improved, not in orig)   → green  #bbf7d0
    Preserves newlines as <br> tags.
    """
    # Tokenize into words, whitespace runs, and newlines (kept as separate tokens)
    def _tok(text: str):
        return re.findall(r"\n|[^\S\n]+|[^\s]+", text)

    if mode not in ("original", "improved"):
        raise ValueError(f"_word_diff_html: mode must be 'original' or 'improved', got {mode!r}")

    orig_tok = _tok(original)
    impr_tok = _tok(improved)

    sm = difflib.SequenceMatcher(None, orig_tok, impr_tok, autojunk=False)
    parts = []

    DEL_STYLE = "background:#fde68a;border-radius:3px;padding:0 2px;display:inline;direction:rtl;unicode-bidi:isolate;"
    ADD_STYLE = "background:#bbf7d0;border-radius:3px;padding:0 2px;display:inline;direction:rtl;unicode-bidi:isolate;"

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for t in orig_tok[i1:i2]:
                parts.append("<br>" if t == "\n" else html_lib.escape(t))

        elif tag == "delete":
            if mode == "original":
                for t in orig_tok[i1:i2]:
                    if t == "\n":
                        parts.append("<br>")
                    elif t.strip():
                        parts.append(f'<span style="{DEL_STYLE}">{html_lib.escape(t)}</span>')
                    else:
                        parts.append(html_lib.escape(t))
            # mode='improved' — deleted tokens don't appear in the improved text, skip

        elif tag == "insert":
            if mode == "improved":
                for t in impr_tok[j1:j2]:
                    if t == "\n":
                        parts.append("<br>")
                    elif t.strip():
                        parts.append(f'<span style="{ADD_STYLE}">{html_lib.escape(t)}</span>')
                    else:
                        parts.append(html_lib.escape(t))
            # mode='original' — inserted tokens don't appear in the original text, skip

        elif tag == "replace":
            if mode == "original":
                for t in orig_tok[i1:i2]:
                    if t == "\n":
                        parts.append("<br>")
                    elif t.strip():
                        parts.append(f'<span style="{DEL_STYLE}">{html_lib.escape(t)}</span>')
                    else:
                        parts.append(html_lib.escape(t))
            else:  # mode='improved'
                for t in impr_tok[j1:j2]:
                    if t == "\n":
                        parts.append("<br>")
                    elif t.strip():
                        parts.append(f'<span style="{ADD_STYLE}">{html_lib.escape(t)}</span>')
                    else:
                        parts.append(html_lib.escape(t))

    return "".join(parts)


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
    if "improve_final_sections" in st.session_state:
        del st.session_state.improve_final_sections
    if "improve_target_position" in st.session_state:
        del st.session_state.improve_target_position
    if "improve_language" in st.session_state:
        del st.session_state.improve_language


def reset_build():
    st.session_state.generated_cv = None
    if "build_form_data" in st.session_state:
        del st.session_state.build_form_data
    if "build_target_position" in st.session_state:
        del st.session_state.build_target_position


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
                go_to("improve_upload")
                st.rerun()


def render_improve_upload():
    render_header()

    if st.button("→ חזרה לדף הבית", key="back_home_improve"):
        go_to("home")
        st.rerun()

    st.markdown("""
    <div class="progress-container">
        <div class="progress-label">שלב 1 מתוך 3</div>
        <div class="progress-track"><div class="progress-fill" style="width:33%"></div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
        [class*="st-key-card_upload"], [class*="st-key-card_language"], [class*="st-key-card_target"] { background-color: #f2f1ef !important; }
        div:has(>[class*="st-key-card_upload"]), div:has(>[class*="st-key-card_language"]), div:has(>[class*="st-key-card_target"]) { background-color: #f2f1ef !important; border-color: #f2f1ef !important; border-width: 2px !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

    with st.container(border=True, key="card_upload"):
        st.markdown('<div class="section-header">📤 העלאת קובץ קורות חיים</div>', unsafe_allow_html=True)
        st.markdown("העלה את קובץ קורות החיים שלך בפורמט PDF, DOCX או TXT")

        uploaded_file = st.file_uploader(
            "בחר קובץ",
            type=["pdf", "docx", "txt"],
            help="פורמטים נתמכים: PDF, DOCX, TXT"
        )

    with st.container(border=True, key="card_language"):
        st.markdown('<div class="section-header">🌐 באיזו שפה תרצו את הגרסה החדשה?</div>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:16px; color:#6b7c93;">בחר באיזו שפה תרצה לקבל את הגרסה המשופרת של קורות החיים</span>', unsafe_allow_html=True)
        lang_choice = st.radio(
            "שפת הנוסח המשופר",
            ["🇮🇱 עברית", "🇺🇸 English"],
            horizontal=True,
            key="lang_radio",
            label_visibility="collapsed"
        )
        st.session_state.improve_language = "en" if "English" in lang_choice else "he"

    with st.container(border=True, key="card_target"):
        st.markdown('<div class="section-header">🎯 תפקיד יעד (אופציונלי)</div>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:16px; color:#6b7c93;">ציין את שם התפקיד או הדבק את תיאור המשרה המלא - ככל שתפרטו יותר, נוכל להתאים את מילות המפתח למערכות הסינון ATS בצורה מדויקת יותר</span>', unsafe_allow_html=True)
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

    if uploaded_file is not None:
        if st.button("🔍 נתח את קורות החיים", use_container_width=True, type="primary"):
            try:
                from file_processor import process_uploaded_file
                from ai_engine import analyze_cv

                with st.status("מנתח את קורות החיים שלך...", expanded=True) as status:
                    st.write("📂 מעבד את הקובץ...")
                    cv_text = process_uploaded_file(uploaded_file)

                    if not cv_text.strip():
                        st.error("לא הצלחנו לחלץ טקסט מהקובץ. נסה קובץ אחר.")
                        return

                    st.session_state.cv_text = cv_text

                    st.write("🤖 הבינה המלאכותית מנתחת... (עשוי לקחת כמה דקות)")
                    st.write("🔍 קורא את קורות החיים...")
                    st.write("📊 מזהה סעיפים ומנסח הצעות שיפור...")

                    lang = st.session_state.get("improve_language", "he")
                    result = analyze_cv(cv_text, target_position=st.session_state.improve_target_position, language=lang)

                    st.write("✅ הניתוח הושלם!")
                    status.update(label="הניתוח הושלם!", state="complete")

                st.session_state.analysis_result = result
                st.session_state.section_decisions = {}

                go_to("improve_review")
                st.rerun()
            except Exception as e:
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
        with st.expander("💡 טיפים כלליים", expanded=False):
            for tip in tips:
                st.markdown(f"• {tip}")

    if keywords:
        with st.expander("🔑 מילות מפתח מומלצות", expanded=False):
            st.markdown(", ".join([f"**{kw}**" for kw in keywords]))

    st.markdown('<div class="section-header">📝 הצעות שיפור לפי סעיפים</div>', unsafe_allow_html=True)

    sections = result.get("sections", [])

    for i, section in enumerate(sections):
        title = section.get("title", f"סעיף {i+1}")
        original = section.get("original", "")
        improved = section.get("improved", "")
        explanation = section.get("explanation", "")

        with st.expander(f"📌 {title}", expanded=(i == 0)):
            if explanation:
                st.info(f"💡 {explanation}")

            decision_key = f"decision_{i}"
            current_decision = st.session_state.section_decisions.get(decision_key, "improved")

            orig_sel = current_decision == "original"
            impr_sel = current_decision == "improved"

            _ck = (
                '<div style="position:absolute;top:-11px;right:-11px;background:#022559;color:#fff;'
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

            # ── Cards as HTML table — cells in same row are always equal height ──
            legend = (
                '<div style="font-size:11px;color:#666;direction:rtl;text-align:right;'
                'margin-bottom:6px;display:flex;gap:12px;justify-content:flex-end;">'
                '<span><span style="background:#bbf7d0;border-radius:3px;padding:0 4px;">מילים שנוספו</span></span>'
                '<span><span style="background:#fde68a;border-radius:3px;padding:0 4px;">מילים שהוסרו</span></span>'
                '</div>'
            )
            st.markdown(legend, unsafe_allow_html=True)
            st.markdown(
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
                f'letter-spacing:.3px;direction:rtl;text-align:right;">נוסח מקור</div>'
                f'<div style="font-size:13px;line-height:1.8;direction:rtl;text-align:right;">'
                f'{orig_diff}</div>'
                f'</td>'
                f'</tr>'
                f'</table>',
                unsafe_allow_html=True,
            )

            # ── Buttons — col_orig is first (rightmost in RTL) matching original cell ──
            col_orig, col_impr = st.columns(2)
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
                custom_text = st.text_area(
                    f"✏️ עורך {source_label} — הטקסט הערוך ישמש בקו״ח הסופי:",
                    value=st.session_state.section_decisions.get(f"text_{i}", improved),
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
        <div class="progress-label">שלב 3 מתוך 3</div>
        <div class="progress-track"><div class="progress-fill" style="width:100%"></div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">✏️ עריכה סופית</div>', unsafe_allow_html=True)
    st.markdown("זה הזמן לליטושים אחרונים. ניתן לערוך כל חלק או לשנות את סדר הסעיפים")

    st.markdown("""
    <style>
        [class*="st-key-imp_up_"] button,
        [class*="st-key-imp_down_"] button {
            background: #022559 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            font-size: 20px !important;
            font-weight: 700 !important;
            width: 100% !important;
            min-height: 38px !important;
            padding: 0 !important;
            box-shadow: none !important;
            line-height: 1 !important;
        }
        [class*="st-key-imp_up_"] button:hover,
        [class*="st-key-imp_down_"] button:hover {
            background: #03367a !important;
        }
    </style>
    """, unsafe_allow_html=True)

    result = st.session_state.analysis_result
    sections = result.get("sections", [])

    if "improve_final_sections" not in st.session_state:
        final_sections = []
        for i, section in enumerate(sections):
            title = section.get("title", f"סעיף {i+1}")
            final_text = st.session_state.section_decisions.get(f"text_{i}", section.get("improved", ""))
            final_sections.append({"title": title, "final_text": final_text})
        st.session_state.improve_final_sections = final_sections

    if "imp_pending_delete" not in st.session_state:
        st.session_state.imp_pending_delete = None

    def _swap_imp_sections(a, b):
        secs = st.session_state.improve_final_sections
        for idx in [a, b]:
            tk, xk = f"imp_title_{idx}", f"imp_text_{idx}"
            if tk in st.session_state:
                secs[idx]["title"] = st.session_state[tk]
                del st.session_state[tk]
            if xk in st.session_state:
                secs[idx]["final_text"] = st.session_state[xk]
                del st.session_state[xk]
        secs[a], secs[b] = secs[b], secs[a]

    sections_to_delete = []
    n_secs = len(st.session_state.improve_final_sections)

    for i, sec in enumerate(st.session_state.improve_final_sections):
        col_arrows, col_card = st.columns([0.7, 11.3])
        with col_arrows:
            if i > 0:
                if st.button("↑", key=f"imp_up_{i}", help="הזז למעלה"):
                    _swap_imp_sections(i, i - 1)
                    st.rerun()
            if i < n_secs - 1:
                if st.button("↓", key=f"imp_down_{i}", help="הזז למטה"):
                    _swap_imp_sections(i, i + 1)
                    st.rerun()
        with col_card:
            with st.container(border=True, key=f"exp_sec_{i}"):
                col_num, col_title, col_del = st.columns([0.5, 9, 0.8])
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
                    col_yes, col_no, _ = st.columns([1, 1, 4])
                    with col_yes:
                        if st.button("✓ מחק", key=f"confirm_del_{i}", type="primary"):
                            sections_to_delete.append(i)
                            st.session_state.imp_pending_delete = None
                    with col_no:
                        if st.button("ביטול", key=f"cancel_del_{i}"):
                            st.session_state.imp_pending_delete = None
                            st.rerun()

    if sections_to_delete:
        for idx in sorted(sections_to_delete, reverse=True):
            st.session_state.improve_final_sections.pop(idx)
        st.rerun()

    if st.button("➕ הוסף סעיף חדש", key="imp_add_section"):
        st.session_state.improve_final_sections.append({"title": "סעיף חדש", "final_text": ""})
        st.rerun()

    export_sections = [s for s in st.session_state.improve_final_sections if s["final_text"].strip()]
    is_english_mode = st.session_state.get("improve_language", "he") == "en"

    st.markdown("""
    <div style="background:linear-gradient(135deg,#022559 0%,#03367a 100%);border-radius:16px;
                padding:24px 24px 12px;margin:28px 0 12px;text-align:center;color:#fff;">
        <div style="font-size:22px;margin-bottom:6px;">🎉</div>
        <div style="font-size:18px;font-weight:700;margin-bottom:4px;">קורות החיים שלך מוכנים!</div>
        <div style="font-size:13px;opacity:.75;">בחר פורמט להורדה</div>
    </div>
    """, unsafe_allow_html=True)

    if is_english_mode:
        en_text = "\n\n".join([
            f"=== {s['title']} ===\n{s['final_text']}" for s in export_sections
        ])
        col1, col2 = st.columns(2)
        with col2:
            try:
                from export_utils import export_improved_cv_to_pdf_en
                pdf_en = export_improved_cv_to_pdf_en(en_text)
                st.download_button(
                    label="📥 Download PDF (English)",
                    data=pdf_en,
                    file_name="cv_improved_en.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"שגיאה ביצירת PDF: {str(e)}")
        with col1:
            try:
                from export_utils import export_improved_cv_to_docx_en
                docx_en = export_improved_cv_to_docx_en(en_text)
                st.download_button(
                    label="📥 Download DOCX (English)",
                    data=docx_en,
                    file_name="cv_improved_en.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"שגיאה ביצירת DOCX: {str(e)}")
    else:
        col1, col2 = st.columns(2)
        with col2:
            try:
                from export_utils import export_improved_cv_to_pdf
                pdf_bytes = export_improved_cv_to_pdf(export_sections)
                st.download_button(
                    label="📥 הורד כ-PDF",
                    data=pdf_bytes,
                    file_name="cv_improved.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"שגיאה ביצירת PDF: {str(e)}")
        with col1:
            try:
                from export_utils import export_improved_cv_to_docx
                docx_bytes = export_improved_cv_to_docx(export_sections)
                st.download_button(
                    label="📥 הורד כ-DOCX",
                    data=docx_bytes,
                    file_name="cv_improved.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"שגיאה ביצירת DOCX: {str(e)}")

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
                        st.rerun()
                    except Exception as e:
                        st.error(f"שגיאה בתרגום: {str(e)}")
                        st.session_state.improve_en_translating = False
        else:
            col3, col4 = st.columns(2)
            with col4:
                try:
                    from export_utils import export_improved_cv_to_pdf_en
                    pdf_en = export_improved_cv_to_pdf_en(st.session_state.improve_en_translated)
                    st.download_button(
                        label="📥 Download PDF (English)",
                        data=pdf_en,
                        file_name="cv_english.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"שגיאה ביצירת PDF: {str(e)}")
            with col3:
                try:
                    from export_utils import export_improved_cv_to_docx_en
                    docx_en = export_improved_cv_to_docx_en(st.session_state.improve_en_translated)
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
        [class*="st-key-bf_add_exp"] button,
        [class*="st-key-bf_add_edu"] button,
        [class*="st-key-bf_add_lang"] button {
            background: #80d6c5 !important; color: #022559 !important;
            font-size: 22px !important; font-weight: 700 !important;
            height: 44px !important; border: none !important;
            border-radius: 10px !important; box-shadow: none !important;
        }
        [class*="st-key-bf_add_exp"] button:hover,
        [class*="st-key-bf_add_edu"] button:hover,
        [class*="st-key-bf_add_lang"] button:hover { background: #5ec4b0 !important; }
    </style>
    """, unsafe_allow_html=True)

    with st.container(border=True, key="bfc_target"):
        st.markdown('<div class="section-header">🎯 תפקיד יעד (אופציונלי)</div>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:15px; color:#6b7c93;">ציין את שם התפקיד או הדבק את תיאור המשרה המלא - ככל שתפרטו יותר, נוכל להתאים את מילות המפתח למערכות הסינון ATS בצורה מדויקת יותר</span>', unsafe_allow_html=True)
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

    with st.container(border=True, key="bfc_personal"):
        st.markdown('<div class="section-header">👤 פרטים אישיים</div>', unsafe_allow_html=True)
        fd["full_name"] = st.text_input("שם מלא", value=fd["full_name"], key="bf_name", placeholder="ישראל ישראלי")
        c1, c2, c3 = st.columns(3)
        with c3:
            fd["phone"] = st.text_input("טלפון", value=fd["phone"], key="bf_phone", placeholder="050-1234567")
        with c2:
            fd["email"] = st.text_input("אימייל", value=fd["email"], key="bf_email", placeholder="email@example.com")
        with c1:
            fd["city"] = st.text_input("עיר", value=fd["city"], key="bf_city", placeholder="תל אביב")
        fd["linkedin"] = st.text_input("פרופיל לינקדאין (אופציונלי)", value=fd.get("linkedin", ""), key="bf_linkedin", placeholder="https://linkedin.com/in/your-profile")

    with st.container(border=True, key="bfc_summary"):
        st.markdown('<div class="section-header">📋 תקציר מקצועי</div>', unsafe_allow_html=True)
        st.markdown('<span style="font-size:13px; color:#6b7c93;">כתוב בקצרה על הרקע המקצועי שלך, או השאר ריק והבינה המלאכותית תכתוב עבורך</span>', unsafe_allow_html=True)
        fd["professional_summary"] = st.text_area(
            "תקציר",
            value=fd["professional_summary"],
            key="bf_summary",
            height=80,
            label_visibility="collapsed",
            placeholder="למשל: מפתח תוכנה עם 5 שנות ניסיון בפיתוח אפליקציות ווב..."
        )

    with st.container(border=True, key="bfc_experience"):
        st.markdown('<div class="section-header">💼 ניסיון תעסוקתי</div>', unsafe_allow_html=True)
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

        if st.button("+", key="bf_add_exp", use_container_width=True):
            experience.append({"title": "", "company": "", "period": "", "achievements": "", "honors": ""})
            st.rerun()

    with st.container(border=True, key="bfc_education"):
        st.markdown('<div class="section-header">🎓 השכלה אקדמית / מקצועית</div>', unsafe_allow_html=True)
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
                edu["year"] = st.text_input("תקופה", value=edu.get("year", ""), key=f"bf_edu_year_{i}", placeholder="2018-2022 או 2022-היום")
            edu["honors"] = st.text_input("הצטיינות (אופציונלי)", value=edu.get("honors", ""), key=f"bf_edu_hon_{i}", placeholder="למשל: בוגר הצטיינות, דין של הדיקן...")

        if edu_to_delete:
            for idx in sorted(edu_to_delete, reverse=True):
                education.pop(idx)
            st.rerun()

        if st.button("+", key="bf_add_edu", use_container_width=True):
            education.append({"degree": "", "institution": "", "year": "", "honors": ""})
            st.rerun()

    with st.container(border=True, key="bfc_skills"):
        st.markdown('<div class="section-header">🛠️ מיומנויות</div>', unsafe_allow_html=True)
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

        if st.button("+", key="bf_add_lang", use_container_width=True):
            languages.append({"language": "", "level": ""})
            st.rerun()

    with st.container(border=True, key="bfc_military"):
        st.markdown('<div class="section-header">🎖️ שירות צבאי / לאומי (אופציונלי)</div>', unsafe_allow_html=True)
        fd["military"] = st.text_area(
            "שירות צבאי",
            value=fd.get("military", ""),
            key="bf_military",
            height=60,
            label_visibility="collapsed",
            placeholder="למשל: חיל המודיעין - קצינת מחקר, שירות מלא 2018-2020"
        )

    with st.container(border=True, key="bfc_volunteering"):
        st.markdown('<div class="section-header">🤝 התנדבות בקהילה (אופציונלי)</div>', unsafe_allow_html=True)
        fd["volunteering"] = st.text_area(
            "התנדבות",
            value=fd.get("volunteering", ""),
            key="bf_volunteering",
            height=60,
            label_visibility="collapsed",
            placeholder="למשל: מנטור בעמותת יוניסטרים, מתנדב בלמ״ן..."
        )

    with st.container(border=True, key="bfc_projects"):
        st.markdown('<div class="section-header">🚀 פרויקטים עצמאיים (אופציונלי)</div>', unsafe_allow_html=True)
        fd["projects"] = st.text_area(
            "פרויקטים",
            value=fd.get("projects", ""),
            key="bf_projects",
            height=60,
            label_visibility="collapsed",
            placeholder="למשל: פיתוח אפליקציה לניהול משימות בReact, בניית אתר אישי..."
        )

    with st.container(border=True, key="bfc_additional"):
        st.markdown('<div class="section-header">📌 מידע נוסף (אופציונלי)</div>', unsafe_allow_html=True)
        fd["additional"] = st.text_area(
            "מידע נוסף",
            value=fd["additional"],
            key="bf_additional",
            height=60,
            label_visibility="collapsed",
            placeholder="קורסים, הסמכות, פרסומים..."
        )

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
            cv_data = generate_cv_from_form(fd, target_position=st.session_state.build_target_position)
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
                edu["year"] = st.text_input("תקופה", value=edu.get("year", ""), key=f"edu_year_{i}", placeholder="2018-2022 או 2022-היום")
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

    col1, col2 = st.columns(2)

    with col2:
        try:
            from export_utils import export_cv_to_pdf
            pdf_bytes = export_cv_to_pdf(cv_data)
            st.download_button(
                label="📥 הורד כ-PDF",
                data=pdf_bytes,
                file_name="cv_master.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"שגיאה ביצירת PDF: {str(e)}")

    with col1:
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
        col3, col4 = st.columns(2)
        with col4:
            try:
                from export_utils import export_cv_to_pdf_en
                pdf_en = export_cv_to_pdf_en(st.session_state.build_en_translated)
                st.download_button(
                    label="📥 Download PDF (English)",
                    data=pdf_en,
                    file_name="cv_english.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"שגיאה ביצירת PDF: {str(e)}")
        with col3:
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
    "build_form": render_build_form,
    "build_preview": render_build_preview,
}

current_page = st.session_state.get("page", "home")
render_fn = pages.get(current_page, render_home)
render_fn()
