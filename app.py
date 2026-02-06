import streamlit as st
from styles import inject_custom_css

st.set_page_config(
    page_title="CV-Master AI",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="collapsed"
)

inject_custom_css()

if "page" not in st.session_state:
    st.session_state.page = "home"
if "cv_text" not in st.session_state:
    st.session_state.cv_text = ""
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "section_decisions" not in st.session_state:
    st.session_state.section_decisions = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "interview_step" not in st.session_state:
    st.session_state.interview_step = 0
if "generated_cv" not in st.session_state:
    st.session_state.generated_cv = None
if "interview_complete" not in st.session_state:
    st.session_state.interview_complete = False


def go_to(page):
    st.session_state.page = page


def reset_improve():
    st.session_state.cv_text = ""
    st.session_state.analysis_result = None
    st.session_state.section_decisions = {}


def reset_build():
    st.session_state.chat_history = []
    st.session_state.interview_step = 0
    st.session_state.generated_cv = None
    st.session_state.interview_complete = False


def render_header():
    st.markdown("""
    <div class="app-header">
        <h1>📄 CV-Master <span class="logo-text">AI</span></h1>
        <p>כלי חכם ליצירה ושיפור קורות חיים מקצועיים</p>
    </div>
    """, unsafe_allow_html=True)


def render_home():
    render_header()

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col2:
        st.markdown("""
        <div class="path-card">
            <div class="path-card-icon">📤</div>
            <div class="path-card-title">שיפור קורות חיים קיימים</div>
            <div class="path-card-desc">
                העלה קובץ קורות חיים קיים וקבל הצעות שיפור מבוססות בינה מלאכותית
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("התחל שיפור  ←", key="btn_improve", use_container_width=True):
            reset_improve()
            go_to("improve_upload")
            st.rerun()

    with col1:
        st.markdown("""
        <div class="path-card">
            <div class="path-card-icon">✨</div>
            <div class="path-card-title">בנייה מאפס</div>
            <div class="path-card-desc">
                צ'אט אינטראקטיבי שילווה אותך בבניית קורות חיים מקצועיים מהתחלה
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("התחל בנייה  ←", key="btn_build", use_container_width=True):
            reset_build()
            go_to("build_chat")
            st.rerun()


def render_improve_upload():
    render_header()

    if st.button("→ חזרה לדף הבית", key="back_home_improve"):
        go_to("home")
        st.rerun()

    st.markdown("""
    <div class="step-indicator">
        <div class="step-dot active"></div>
        <div class="step-dot"></div>
        <div class="step-dot"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">📤 העלאת קובץ קורות חיים</div>', unsafe_allow_html=True)
    st.markdown("העלה את קובץ קורות החיים שלך בפורמט PDF, DOCX או TXT")

    uploaded_file = st.file_uploader(
        "בחר קובץ",
        type=["pdf", "docx", "txt"],
        help="פורמטים נתמכים: PDF, DOCX, TXT"
    )

    if uploaded_file is not None:
        if st.button("🔍 נתח את קורות החיים", use_container_width=True, type="primary"):
            with st.spinner("מעבד את הקובץ..."):
                try:
                    from file_processor import process_uploaded_file
                    cv_text = process_uploaded_file(uploaded_file)

                    if not cv_text.strip():
                        st.error("לא הצלחנו לחלץ טקסט מהקובץ. נסה קובץ אחר.")
                        return

                    st.session_state.cv_text = cv_text

                    with st.spinner("הבינה המלאכותית מנתחת את קורות החיים שלך..."):
                        from ai_engine import analyze_cv
                        result = analyze_cv(cv_text)
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
    <div class="step-indicator">
        <div class="step-dot"></div>
        <div class="step-dot active"></div>
        <div class="step-dot"></div>
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

            col_right, col_left = st.columns(2)

            with col_right:
                st.markdown('<div class="suggestion-label">מקור</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="original-text">{original}</div>', unsafe_allow_html=True)

            with col_left:
                st.markdown('<div class="suggestion-label">מוצע</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="improved-text">{improved}</div>', unsafe_allow_html=True)

            decision_key = f"decision_{i}"
            current_decision = st.session_state.section_decisions.get(decision_key, "improved")

            choice = st.radio(
                "בחר גרסה:",
                ["השתמש בגרסה המשופרת", "השאר מקור", "ערוך ידנית"],
                key=f"radio_{i}",
                index=0 if current_decision == "improved" else (1 if current_decision == "original" else 2),
                horizontal=True
            )

            if choice == "השתמש בגרסה המשופרת":
                st.session_state.section_decisions[decision_key] = "improved"
                st.session_state.section_decisions[f"text_{i}"] = improved
            elif choice == "השאר מקור":
                st.session_state.section_decisions[decision_key] = "original"
                st.session_state.section_decisions[f"text_{i}"] = original
            else:
                st.session_state.section_decisions[decision_key] = "custom"
                custom_text = st.text_area(
                    "ערוך את הטקסט:",
                    value=st.session_state.section_decisions.get(f"text_{i}", improved),
                    key=f"custom_text_{i}",
                    height=120
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
    <div class="step-indicator">
        <div class="step-dot"></div>
        <div class="step-dot"></div>
        <div class="step-dot active"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">📄 קורות החיים המשופרים שלך</div>', unsafe_allow_html=True)

    result = st.session_state.analysis_result
    sections = result.get("sections", [])

    final_sections = []
    for i, section in enumerate(sections):
        title = section.get("title", f"סעיף {i+1}")
        final_text = st.session_state.section_decisions.get(f"text_{i}", section.get("improved", ""))
        final_sections.append({
            "title": title,
            "final_text": final_text,
            "improved": section.get("improved", ""),
            "original": section.get("original", "")
        })

    st.markdown('<div class="cv-preview">', unsafe_allow_html=True)
    for sec in final_sections:
        st.markdown(f"### {sec['title']}")
        st.markdown(sec['final_text'])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-header">⬇️ הורדת קורות החיים</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col2:
        try:
            from export_utils import export_improved_cv_to_pdf
            pdf_bytes = export_improved_cv_to_pdf(final_sections)
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
            docx_bytes = export_improved_cv_to_docx(final_sections)
            st.download_button(
                label="📥 הורד כ-DOCX",
                data=docx_bytes,
                file_name="cv_improved.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"שגיאה ביצירת DOCX: {str(e)}")

    st.markdown("---")
    if st.button("🏠 חזרה לדף הבית", use_container_width=True):
        go_to("home")
        st.rerun()


def render_build_chat():
    render_header()

    if st.button("→ חזרה לדף הבית", key="back_home_build"):
        go_to("home")
        st.rerun()

    total_steps = 7
    progress = min(st.session_state.interview_step / total_steps, 1.0)
    st.progress(progress)
    st.markdown(f"""
    <div style="text-align: center; font-size: 14px; color: #6b7c93; margin-bottom: 16px;">
        שלב {min(st.session_state.interview_step + 1, total_steps)} מתוך {total_steps}
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.chat_history:
        with st.spinner("מכין את הראיון..."):
            from ai_engine import get_interview_question
            first_q = get_interview_question([], 0)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": first_q
            })
            st.rerun()

    for msg in st.session_state.chat_history:
        if msg["role"] == "assistant":
            st.markdown(f'<div class="chat-message-ai">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-message-user">{msg["content"]}</div>', unsafe_allow_html=True)

    if not st.session_state.interview_complete:
        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "הקלד את תשובתך:",
                height=80,
                key="user_chat_input",
                placeholder="הקלד כאן..."
            )
            col1, col2 = st.columns([3, 1])
            with col2:
                submit = st.form_submit_button("שלח", use_container_width=True, type="primary")
            with col1:
                finish = st.form_submit_button("סיים ובנה קורות חיים ✨", use_container_width=True)

            if submit and user_input.strip():
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input.strip()
                })
                st.session_state.interview_step += 1

                with st.spinner("חושב..."):
                    from ai_engine import get_interview_question
                    ai_response = get_interview_question(st.session_state.chat_history, st.session_state.interview_step)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": ai_response
                    })
                st.rerun()

            if finish:
                if len(st.session_state.chat_history) < 3:
                    st.warning("נא לענות על לפחות שאלה אחת לפני יצירת קורות החיים.")
                else:
                    st.session_state.interview_complete = True
                    st.rerun()

    if st.session_state.interview_complete and not st.session_state.generated_cv:
        with st.spinner("יוצר את קורות החיים שלך... ⏳"):
            from ai_engine import generate_cv_from_interview
            cv_data = generate_cv_from_interview(st.session_state.chat_history)
            st.session_state.generated_cv = cv_data
        go_to("build_preview")
        st.rerun()


def render_build_preview():
    render_header()

    if st.button("→ חזרה לצ'אט", key="back_chat"):
        st.session_state.interview_complete = False
        st.session_state.generated_cv = None
        go_to("build_chat")
        st.rerun()

    cv_data = st.session_state.generated_cv
    if not cv_data:
        st.warning("לא נמצאו נתונים. חזור לצ'אט.")
        return

    st.markdown('<div class="section-header">✨ קורות החיים שלך מוכנים!</div>', unsafe_allow_html=True)

    st.markdown('<div class="cv-preview">', unsafe_allow_html=True)

    name = cv_data.get("full_name", "")
    if name:
        st.markdown(f"## {name}")

    contact = cv_data.get("contact", {})
    contact_parts = []
    if contact.get("phone"):
        contact_parts.append(f"📱 {contact['phone']}")
    if contact.get("email"):
        contact_parts.append(f"📧 {contact['email']}")
    if contact.get("city"):
        contact_parts.append(f"📍 {contact['city']}")
    if contact_parts:
        st.markdown(" | ".join(contact_parts))

    st.markdown("---")

    summary = cv_data.get("professional_summary", "")
    if summary:
        st.markdown("### תקציר מקצועי")
        st.markdown(summary)

    experience = cv_data.get("experience", [])
    if experience:
        st.markdown("### ניסיון תעסוקתי")
        for exp in experience:
            title = exp.get("title", "")
            company = exp.get("company", "")
            period = exp.get("period", "")
            header = f"**{title}**"
            if company:
                header += f" | {company}"
            if period:
                header += f" | {period}"
            st.markdown(header)
            for ach in exp.get("achievements", []):
                st.markdown(f"• {ach}")

    education = cv_data.get("education", [])
    if education:
        st.markdown("### השכלה")
        for edu in education:
            parts = []
            if edu.get("degree"):
                parts.append(edu["degree"])
            if edu.get("institution"):
                parts.append(edu["institution"])
            if edu.get("year"):
                parts.append(edu["year"])
            st.markdown(" | ".join(parts))

    skills = cv_data.get("skills", {})
    technical = skills.get("technical", [])
    soft = skills.get("soft", [])
    if technical or soft:
        st.markdown("### מיומנויות")
        if technical:
            st.markdown(f"**טכניות:** {', '.join(technical)}")
        if soft:
            st.markdown(f"**רכות:** {', '.join(soft)}")

    languages = cv_data.get("languages", [])
    if languages:
        st.markdown("### שפות")
        lang_parts = []
        for lang in languages:
            part = lang.get("language", "")
            if lang.get("level"):
                part += f" - {lang['level']}"
            lang_parts.append(part)
        st.markdown(" | ".join(lang_parts))

    additional = cv_data.get("additional", [])
    if additional:
        st.markdown("### מידע נוסף")
        for item in additional:
            if item:
                st.markdown(f"• {item}")

    st.markdown('</div>', unsafe_allow_html=True)

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

    st.markdown("---")
    if st.button("🏠 חזרה לדף הבית", use_container_width=True):
        go_to("home")
        st.rerun()


pages = {
    "home": render_home,
    "improve_upload": render_improve_upload,
    "improve_review": render_improve_review,
    "improve_export": render_improve_export,
    "build_chat": render_build_chat,
    "build_preview": render_build_preview,
}

current_page = st.session_state.get("page", "home")
render_fn = pages.get(current_page, render_home)
render_fn()
