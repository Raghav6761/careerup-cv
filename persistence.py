import json
import hashlib
import streamlit as st

_LS_KEY = "cv_master_data"

_PERSIST_KEYS = [
    "build_form_data",
    "build_target_position",
    "build_max_pages",
    "generated_cv",
    "improve_target_position",
    "improve_language",
    "improve_max_pages",
    "analysis_result",
    "cv_text",
    "section_decisions",
    "improve_final_sections",
    "consultation_chats",
]

_MAX_CONSULTATION_MESSAGES_PER_SECTION = 30


def _set_build_widget_keys(fd: dict):
    st.session_state["bf_name"]        = fd.get("full_name", "")
    st.session_state["bf_phone"]       = fd.get("phone", "")
    st.session_state["bf_email"]       = fd.get("email", "")
    st.session_state["bf_city"]        = fd.get("city", "")
    st.session_state["bf_linkedin"]    = fd.get("linkedin", "")
    st.session_state["bf_summary"]     = fd.get("professional_summary", "")
    st.session_state["bf_tech"]        = fd.get("technical_skills", "")
    st.session_state["bf_soft"]        = fd.get("soft_skills", "")
    st.session_state["bf_military"]    = fd.get("military", "")
    st.session_state["bf_volunteering"]= fd.get("volunteering", "")
    st.session_state["bf_projects"]    = fd.get("projects", "")
    st.session_state["bf_additional"]  = fd.get("additional", "")

    for i, exp in enumerate(fd.get("experience", [])):
        st.session_state[f"bf_exp_title_{i}"]   = exp.get("title", "")
        st.session_state[f"bf_exp_company_{i}"] = exp.get("company", "")
        st.session_state[f"bf_exp_period_{i}"]  = exp.get("period", "")
        st.session_state[f"bf_exp_ach_{i}"]     = exp.get("achievements", "")
        st.session_state[f"bf_exp_hon_{i}"]     = exp.get("honors", "")

    for i, edu in enumerate(fd.get("education", [])):
        st.session_state[f"bf_edu_deg_{i}"]  = edu.get("degree", "")
        st.session_state[f"bf_edu_inst_{i}"] = edu.get("institution", "")
        st.session_state[f"bf_edu_year_{i}"] = edu.get("year", "")
        st.session_state[f"bf_edu_hon_{i}"]  = edu.get("honors", "")

    for i, lang in enumerate(fd.get("languages", [])):
        st.session_state[f"bf_lang_{i}"]     = lang.get("language", "")
        st.session_state[f"bf_lang_lvl_{i}"] = lang.get("level", "")


def init_storage():
    """
    Call once per script run BEFORE page routing.
    Render 1: JS fires but returns None → do nothing.
    Render 2: JS returns saved JSON → populate session state → rerun.
    Render 3+: _storage_loaded = True → return immediately.
    """
    if st.session_state.get("_storage_loaded"):
        return

    try:
        from streamlit_js_eval import streamlit_js_eval
    except ImportError:
        st.session_state["_storage_loaded"] = True
        return

    saved_json = streamlit_js_eval(
        js_expressions=f"localStorage.getItem('{_LS_KEY}')",
        key="_cv_storage_reader",
    )

    if saved_json is None:
        return

    st.session_state["_storage_loaded"] = True

    if not saved_json or saved_json in ("null", "undefined"):
        return

    try:
        data = json.loads(saved_json)
    except Exception:
        return

    if not isinstance(data, dict):
        return

    def _is_empty(val) -> bool:
        if val is None:
            return True
        if isinstance(val, (str, dict, list)) and not val:
            return True
        return False

    changed = False
    for key in _PERSIST_KEYS:
        if key in data and _is_empty(st.session_state.get(key)):
            st.session_state[key] = data[key]
            changed = True

    if not changed:
        return

    fd = data.get("build_form_data")
    if fd:
        _set_build_widget_keys(fd)

    if "build_target_position" in data:
        st.session_state["build_target_input"] = data["build_target_position"]

    if "improve_target_position" in data:
        st.session_state["improve_target_input"] = data["improve_target_position"]

    lang = data.get("improve_language", "he")
    st.session_state["lang_radio"] = "English" if lang == "en" else "עברית"

    max_p_improve = data.get("improve_max_pages", 1)
    st.session_state["improve_pages_radio"] = (
        "עד שני עמודים" if max_p_improve == 2 else "נסה להכניס לעמוד אחד (מומלץ)"
    )

    max_p_build = data.get("build_max_pages", 1)
    st.session_state["build_pages_radio"] = (
        "עד שני עמודים" if max_p_build == 2 else "נסה להכניס לעמוד אחד (מומלץ)"
    )

    saved_page = data.get("page", "home")
    if saved_page and saved_page != "home":
        if saved_page in ("improve_review", "improve_export", "improve_reorder"):
            if not data.get("analysis_result"):
                saved_page = "improve_upload"
        elif saved_page == "build_preview":
            if not data.get("generated_cv"):
                saved_page = "build_form"
        st.session_state["page"] = saved_page


def save_to_storage():
    """
    Serialize relevant session state to localStorage.
    Hash-based widget key means localStorage.setItem only fires when data changes.
    """
    try:
        from streamlit_js_eval import streamlit_js_eval
    except ImportError:
        return

    data: dict = {}

    page = st.session_state.get("page", "home")
    if page and page != "home":
        data["page"] = page

    for key in _PERSIST_KEYS:
        val = st.session_state.get(key)
        if val is not None:
            if key == "consultation_chats" and isinstance(val, dict):
                trimmed = {}
                for section, msgs in val.items():
                    if isinstance(msgs, list):
                        trimmed[section] = msgs[-_MAX_CONSULTATION_MESSAGES_PER_SECTION:]
                    else:
                        trimmed[section] = msgs
                data[key] = trimmed
            else:
                data[key] = val

    if not data:
        return

    try:
        json_str = json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        return

    data_hash = hashlib.md5(json_str.encode("utf-8")).hexdigest()[:12]
    js_literal = json.dumps(json_str)

    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('{_LS_KEY}', {js_literal}); true",
        key=f"_cv_storage_writer_{data_hash}",
    )


def clear_storage():
    """
    Remove saved data from localStorage and wipe relevant session state keys.
    """
    try:
        from streamlit_js_eval import streamlit_js_eval
    except ImportError:
        pass
    else:
        count = st.session_state.get("_storage_clear_count", 0) + 1
        st.session_state["_storage_clear_count"] = count
        streamlit_js_eval(
            js_expressions=f"localStorage.removeItem('{_LS_KEY}'); true",
            key=f"_cv_storage_clearer_{count}",
        )

    clear_keys = _PERSIST_KEYS + [
        "cv_text",
        "improve_cv_title",
        "page",
    ]
    for key in clear_keys:
        st.session_state.pop(key, None)
    st.session_state["_storage_loaded"] = True
