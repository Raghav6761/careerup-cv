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
    if "improve_final_sections" in st.session_state:
        del st.session_state.improve_final_sections


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

                    st.write("🤖 הבינה המלאכותית מנתחת... (זמן משוער: 15-30 שניות)")
                    st.write("🔍 קורא את קורות החיים...")
                    st.write("📊 מזהה סעיפים ומנסח הצעות שיפור...")

                    result = analyze_cv(cv_text)

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

    st.markdown('<div class="section-header">📄 תצוגה מקדימה</div>', unsafe_allow_html=True)
    st.markdown("ניתן לערוך, לשנות או למחוק כל סעיף לפני ההורדה")

    result = st.session_state.analysis_result
    sections = result.get("sections", [])

    if "improve_final_sections" not in st.session_state:
        final_sections = []
        for i, section in enumerate(sections):
            title = section.get("title", f"סעיף {i+1}")
            final_text = st.session_state.section_decisions.get(f"text_{i}", section.get("improved", ""))
            final_sections.append({"title": title, "final_text": final_text})
        st.session_state.improve_final_sections = final_sections

    sections_to_delete = []

    for i, sec in enumerate(st.session_state.improve_final_sections):
        with st.container():
            col_title, col_delete = st.columns([5, 1])
            with col_title:
                new_title = st.text_input(
                    "כותרת סעיף",
                    value=sec["title"],
                    key=f"imp_title_{i}",
                    label_visibility="collapsed",
                    placeholder="כותרת סעיף"
                )
                st.session_state.improve_final_sections[i]["title"] = new_title
            with col_delete:
                if st.button("🗑️", key=f"imp_del_{i}", help="מחק סעיף"):
                    sections_to_delete.append(i)

            new_text = st.text_area(
                "תוכן",
                value=sec["final_text"],
                key=f"imp_text_{i}",
                height=120,
                label_visibility="collapsed",
                placeholder="תוכן הסעיף"
            )
            st.session_state.improve_final_sections[i]["final_text"] = new_text
            st.markdown("---")

    if sections_to_delete:
        for idx in sorted(sections_to_delete, reverse=True):
            st.session_state.improve_final_sections.pop(idx)
        st.rerun()

    if st.button("➕ הוסף סעיף חדש", key="imp_add_section"):
        st.session_state.improve_final_sections.append({"title": "סעיף חדש", "final_text": ""})
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="section-header">⬇️ הורדת קורות החיים</div>', unsafe_allow_html=True)

    export_sections = [s for s in st.session_state.improve_final_sections if s["final_text"].strip()]

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
                if st.button("🗑️", key=f"del_exp_{i}", help="מחק ניסיון"):
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
            st.markdown("---")

    if exp_to_delete:
        for idx in sorted(exp_to_delete, reverse=True):
            experience.pop(idx)
        cv_data["experience"] = experience
        need_rerun = True

    if st.button("➕ הוסף ניסיון תעסוקתי", key="add_exp"):
        experience.append({"title": "", "company": "", "period": "", "achievements": []})
        cv_data["experience"] = experience
        need_rerun = True

    st.markdown('<div class="section-header">🎓 השכלה</div>', unsafe_allow_html=True)
    education = cv_data.get("education", [])
    edu_to_delete = []
    for i, edu in enumerate(education):
        with st.container():
            col_header, col_del = st.columns([5, 1])
            with col_del:
                if st.button("🗑️", key=f"del_edu_{i}", help="מחק השכלה"):
                    edu_to_delete.append(i)

            ec1, ec2, ec3 = st.columns(3)
            with ec3:
                edu["degree"] = st.text_input("תואר", value=edu.get("degree", ""), key=f"edu_degree_{i}")
            with ec2:
                edu["institution"] = st.text_input("מוסד", value=edu.get("institution", ""), key=f"edu_inst_{i}")
            with ec1:
                edu["year"] = st.text_input("שנה", value=edu.get("year", ""), key=f"edu_year_{i}")
            st.markdown("---")

    if edu_to_delete:
        for idx in sorted(edu_to_delete, reverse=True):
            education.pop(idx)
        cv_data["education"] = education
        need_rerun = True

    if st.button("➕ הוסף השכלה", key="add_edu"):
        education.append({"degree": "", "institution": "", "year": ""})
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
            if st.button("🗑️", key=f"del_lang_{i}", help="מחק שפה"):
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

    st.markdown('<div class="section-header">📌 מידע נוסף</div>', unsafe_allow_html=True)
    additional = cv_data.get("additional", [])
    add_text = "\n".join(additional)
    new_add = st.text_area(
        "מידע נוסף (שורה לכל פריט)",
        value=add_text,
        key="build_additional",
        height=80,
        label_visibility="collapsed",
        placeholder="התנדבות, קורסים, הסמכות..."
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
