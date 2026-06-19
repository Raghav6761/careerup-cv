"""
Persistence for the CV tool — now backed by the central auth-hub DB instead of the
browser's localStorage. The tool's whole working state is still one JSON blob; we
just store it server-side, scoped to the Clerk user, so a returning user resumes
their draft on any device.

Same public surface as before — `init_storage()` / `save_to_storage()` /
`clear_storage()` / `_set_build_widget_keys()` — so app.py is unchanged at the call
sites. The blob shape is identical to the old localStorage `cv_master_data`.

Service-authed exactly like auth_gate.py: the user is OIDC-verified (st.user.sub =
clerk_id) and we call the hub with X-Service-Secret. No new secrets — reuses
CENTRAL_API_URL + CV_SERVICE_SECRET from .streamlit/secrets.toml.
"""
import os
import json
import hashlib
import streamlit as st
import requests

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


# ─────────────────────────── central hub plumbing ────────────────────────────

def _secret(key: str, default: str = "") -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


def _central_api_url() -> str:
    return _secret("CENTRAL_API_URL", "https://lgn.careerup.co.il").rstrip("/")


def _service_headers() -> dict:
    return {
        "X-Service-Secret": _secret("CV_SERVICE_SECRET"),
        "Content-Type": "application/json",
    }


def _clerk_id():
    """The OIDC-verified clerk id (st.user.sub), or None if not signed in.
    The access gate runs first, so a rendering app.py always has one — but fail
    soft (no-op persistence) rather than error if it's somehow missing."""
    user = getattr(st, "user", None)
    if user is None or not getattr(user, "is_logged_in", False):
        return None
    try:
        cid = user.get("sub")
    except Exception:
        cid = getattr(user, "sub", None)
    return cid or None


def _set_build_widget_keys(fd: dict):
    st.session_state["bf_name"]        = fd.get("full_name", "")
    st.session_state["bf_phone"]       = fd.get("phone", "")
    st.session_state["bf_email"]       = fd.get("email", "")
    st.session_state["bf_city"]        = fd.get("city", "")
    st.session_state["bf_linkedin"]    = fd.get("linkedin", "")
    st.session_state["bf_portfolio"]   = fd.get("portfolio", "")
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


# ─────────────────────────────── load (init) ─────────────────────────────────

def _apply_loaded_data(data: dict):
    """Populate session state from a loaded blob. Identical merge rules to the old
    localStorage path: only fill keys the user hasn't already populated this run."""
    if not isinstance(data, dict):
        return

    def _is_empty(val) -> bool:
        if val is None:
            return True
        if isinstance(val, (str, dict, list)) and not val:
            return True
        return False

    def _build_form_data_is_empty(fd) -> bool:
        """Return True when the dict has no actual user-typed content."""
        if not fd or not isinstance(fd, dict):
            return True
        for key, val in fd.items():
            if isinstance(val, str) and val.strip():
                return False
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        for v in item.values():
                            if isinstance(v, str) and v.strip():
                                return False
                    elif isinstance(item, str) and item.strip():
                        return False
        return True

    changed = False
    for key in _PERSIST_KEYS:
        if key not in data:
            continue
        if key == "build_form_data":
            if _build_form_data_is_empty(st.session_state.get(key)):
                st.session_state[key] = data[key]
                changed = True
        elif _is_empty(st.session_state.get(key)):
            st.session_state[key] = data[key]
            changed = True

    if not changed:
        # Still honour a saved page even when content keys were already populated.
        _restore_page(data)
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

    _restore_page(data)


def _restore_page(data: dict):
    saved_page = data.get("page", "home")
    if saved_page and saved_page != "home":
        if saved_page in ("improve_review", "improve_export", "improve_reorder"):
            if not data.get("analysis_result"):
                saved_page = "improve_upload"
        elif saved_page == "build_preview":
            if not data.get("generated_cv"):
                saved_page = "build_form"
        st.session_state["page"] = saved_page


def init_storage():
    """
    Call once per script run BEFORE page routing. One synchronous fetch of the
    user's blob from the hub; populate session state; mark loaded so subsequent
    reruns skip the network. (No more localStorage multi-render dance.)
    """
    if st.session_state.get("_storage_loaded"):
        return

    clerk_id = _clerk_id()
    if not clerk_id:
        st.session_state["_storage_loaded"] = True
        return

    data = None
    try:
        resp = requests.post(
            f"{_central_api_url()}/api/cv/state/load",
            json={"clerkId": clerk_id},
            headers=_service_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json().get("data")
    except Exception:
        data = None

    st.session_state["_storage_loaded"] = True

    if isinstance(data, dict) and data:
        _apply_loaded_data(data)

    # Seed the saved-hash from whatever we just loaded so the end-of-run
    # save_to_storage() doesn't immediately re-POST identical data.
    st.session_state["_cv_saved_hash"] = _current_data_hash()


# ─────────────────────────────── save ────────────────────────────────────────

def _build_data_dict() -> dict:
    """Serialize the relevant session state into the blob (same keys as before)."""
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

    return data


def _serialize(data: dict):
    try:
        return json.dumps(data, ensure_ascii=False, default=str, sort_keys=True)
    except Exception:
        return None


def _current_data_hash():
    s = _serialize(_build_data_dict())
    return hashlib.md5(s.encode("utf-8")).hexdigest() if s is not None else None


def save_to_storage():
    """
    Push the blob to the hub — but only when it actually changed since the last
    save (hash guard), so a plain Streamlit rerun never hits the network.
    """
    clerk_id = _clerk_id()
    if not clerk_id:
        return

    data = _build_data_dict()
    if not data:
        return

    json_str = _serialize(data)
    if json_str is None:
        return

    data_hash = hashlib.md5(json_str.encode("utf-8")).hexdigest()
    if st.session_state.get("_cv_saved_hash") == data_hash:
        return  # unchanged — skip the round-trip

    try:
        resp = requests.post(
            f"{_central_api_url()}/api/cv/state/save",
            json={"clerkId": clerk_id, "data": data},
            headers=_service_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            st.session_state["_cv_saved_hash"] = data_hash
    except Exception:
        pass


def persist_partial(updates: dict):
    """
    Merge a few keys into the stored blob server-side WITHOUT clobbering the rest —
    load the current blob, apply `updates`, save it back. Used by the improve-entry
    hard reload to set `page` while keeping any prior analysis (mirrors the old JS
    that read localStorage, set page, and wrote it back before reloading).
    """
    clerk_id = _clerk_id()
    if not clerk_id:
        return

    blob = {}
    try:
        resp = requests.post(
            f"{_central_api_url()}/api/cv/state/load",
            json={"clerkId": clerk_id},
            headers=_service_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            loaded = resp.json().get("data")
            if isinstance(loaded, dict):
                blob = loaded
    except Exception:
        blob = {}

    blob.update(updates)
    try:
        requests.post(
            f"{_central_api_url()}/api/cv/state/save",
            json={"clerkId": clerk_id, "data": blob},
            headers=_service_headers(),
            timeout=10,
        )
    except Exception:
        pass
    # Force the next run's save_to_storage() to re-evaluate against the new blob.
    st.session_state.pop("_cv_saved_hash", None)


# ─────────────────────────────── clear ───────────────────────────────────────

def clear_storage():
    """
    Drop the saved blob on the hub and wipe the relevant session state keys.
    """
    clerk_id = _clerk_id()
    if clerk_id:
        try:
            requests.post(
                f"{_central_api_url()}/api/cv/state/clear",
                json={"clerkId": clerk_id},
                headers=_service_headers(),
                timeout=10,
            )
        except Exception:
            pass

    clear_keys = _PERSIST_KEYS + [
        "cv_text",
        "improve_cv_title",
        "page",
    ]
    for key in clear_keys:
        st.session_state.pop(key, None)
    st.session_state["_storage_loaded"] = True
    st.session_state["_cv_saved_hash"] = None
