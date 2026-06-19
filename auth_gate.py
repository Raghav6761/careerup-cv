"""
Hard access gate for the CV (Streamlit) tool — the Python equivalent of the React
tools' AccessGate.

1. Authenticates via Clerk OIDC using Streamlit's native auth (`st.login` /
   `st.user`). Same Clerk instance as every other tool, so `st.user.sub` is the
   same `clerk_id`.
2. Verifies ACTIVE access against the central hub: POST /api/cv/access (service-
   authed with CV_SERVICE_SECRET), passing the OIDC-verified clerk id.

Blocks at the door — nothing in app.py runs until the user is signed in AND active.

Requires `.streamlit/secrets.toml` (see secrets.toml.example):
  [auth]              Clerk OIDC provider (client_id / client_secret /
                      server_metadata_url / redirect_uri / cookie_secret)
  CENTRAL_API_URL     e.g. https://lgn.careerup.co.il
  CV_SERVICE_SECRET   shared secret, also set on the auth-hub api-server
"""
import os
import streamlit as st
import requests

_DENIED_TEXT = {
    "inactive":  ("חשבונך אינו פעיל", "חשבונך הושהה. לפרטים נוספים פנה אלינו."),
    "expired":   ("תקופת הגישה שלך הסתיימה", "תוקף הגישה שלך לפלטפורמה פג. לחידוש הגישה פנה אלינו."),
    "not_found": ("אין לך גישה לכלי זה", "לא נמצאה גישה פעילה עם פרטיך. לפרטים פנה אלינו."),
    "error":     ("שגיאה בבדיקת הגישה", "אירעה שגיאה בעת בדיקת הרשאות הגישה שלך. נסה שוב."),
}


def _secret(key: str, default: str = "") -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


def _central_api_url() -> str:
    return _secret("CENTRAL_API_URL", "https://lgn.careerup.co.il").rstrip("/")


def _check_access(clerk_id: str) -> dict:
    """Ask the central hub whether this clerk id has active access. Fails CLOSED."""
    try:
        resp = requests.post(
            f"{_central_api_url()}/api/cv/access",
            json={"clerkId": clerk_id},
            headers={"X-Service-Secret": _secret("CV_SERVICE_SECRET")},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {"granted": bool(data.get("granted")), "reason": data.get("reason") or "inactive"}
        return {"granted": False, "reason": "error"}
    except Exception:
        return {"granted": False, "reason": "error"}


def _centered_message(title: str, body: str):
    st.markdown(
        f"""
        <div style="max-width:460px;margin:12vh auto 24px;text-align:center;direction:rtl;
                    font-family:'Assistant',sans-serif;">
          <h1 style="font-size:1.7rem;font-weight:700;color:#1a1a2e;margin-bottom:10px;">{title}</h1>
          <p style="color:#555;font-size:1rem;line-height:1.6;">{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def require_access():
    """Call once at the very top of app.py, right after st.set_page_config."""
    user = getattr(st, "user", None)

    # 1. Signed in? If not, redirect STRAIGHT to the Clerk sign-in page — no
    #    interstitial button (matches the other tools' redirect-to-hub flow). The user
    #    returns here authenticated and the app renders directly; on reload an existing
    #    session skips this block entirely and the homepage shows as-is.
    if user is None or not user.is_logged_in:
        st.login()
        st.stop()

    # 2. Identity
    try:
        clerk_id = user.get("sub")
    except Exception:
        clerk_id = getattr(user, "sub", None)
    if not clerk_id:
        _centered_message(*_DENIED_TEXT["error"])
        _logout_button()
        st.stop()

    # 3. Active access (cached per session so we don't hit the API every rerun).
    cache = st.session_state.get("_cv_access")
    if not cache or cache.get("clerk_id") != clerk_id:
        cache = {"clerk_id": clerk_id, **_check_access(clerk_id)}
        st.session_state["_cv_access"] = cache

    if not cache.get("granted"):
        title, body = _DENIED_TEXT.get(cache.get("reason"), _DENIED_TEXT["inactive"])
        _centered_message(title, body)
        _logout_button()
        st.stop()


def _logout_button():
    with st.columns([1, 1, 1])[1]:
        if st.button("התנתק / החלף משתמש", use_container_width=True):
            st.session_state.pop("_cv_access", None)
            st.logout()


def render_user_button():
    """Persistent profile button pinned top-left — the Streamlit twin of the React
    tools' global Clerk <UserButton>. Shows the avatar (or the user's initial); click
    opens a small card with name/email + sign-out. Call once per run after the gate
    passes; the fixed positioning floats it out of the page flow on every page."""
    user = getattr(st, "user", None)
    if user is None or not getattr(user, "is_logged_in", False):
        return

    def _u(key: str, default: str = "") -> str:
        try:
            return user.get(key) or default
        except Exception:
            return getattr(user, key, default) or default

    name = _u("name") or _u("email") or "החשבון שלי"
    email = _u("email")
    picture = _u("picture")
    initial = (name.strip()[:1] or "U").upper()

    css = """
    <style>
      .st-key-cu_userbtn { position: fixed; top: 18px; left: 22px; z-index: 1000; width: auto !important; }
      .st-key-cu_userbtn button {
          border-radius: 50% !important; width: 46px !important; height: 46px !important;
          min-height: 46px !important; padding: 0 !important;
          background-color: #022559 !important; color: #ffffff !important;
          font-weight: 700 !important; font-size: 17px !important;
          border: 2px solid #ffffff !important; box-shadow: 0 2px 8px rgba(2,37,89,.25) !important;
          display: flex !important; align-items: center !important; justify-content: center !important;
      }
      .st-key-cu_userbtn button:hover { background-color: #03367a !important; }
      .st-key-cu_userbtn button p { margin: 0 !important; }
    """
    if picture:
        css += (
            ".st-key-cu_userbtn button {"
            f"background-image: url('{picture}') !important;"
            "background-size: cover !important; background-position: center !important;"
            "color: transparent !important; }"
            ".st-key-cu_userbtn button p { color: transparent !important; }"
        )
    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)

    with st.container(key="cu_userbtn"):
        with st.popover(initial, use_container_width=False):
            if picture:
                st.markdown(
                    f'<div style="text-align:center;"><img src="{picture}" '
                    f'style="width:56px;height:56px;border-radius:50%;object-fit:cover;margin-bottom:8px;" '
                    f'referrerpolicy="no-referrer"></div>',
                    unsafe_allow_html=True,
                )
            st.markdown(
                f'<div style="font-weight:700;text-align:center;direction:rtl;">{name}</div>',
                unsafe_allow_html=True,
            )
            if email:
                st.markdown(
                    f'<div style="font-size:12px;color:#6b7c93;text-align:center;margin-bottom:10px;direction:ltr;">{email}</div>',
                    unsafe_allow_html=True,
                )
            # "Manage account" → Clerk's OWN hosted account portal (the same <UserProfile>
            # UI the React tools' <UserButton> opens). Account-portal URL comes from the
            # instance's environment (display_config.user_profile_url). New tab so the CV
            # session isn't disturbed.
            st.markdown(
                '<a href="https://accounts.careerup.co.il/user" target="_blank" rel="noopener"'
                ' style="display:block;text-align:center;padding:8px 10px;border-radius:8px;'
                'background:#f0f4ff;color:#022559;text-decoration:none;font-weight:600;'
                'margin-bottom:8px;direction:rtl;">⚙️ נהל חשבון</a>',
                unsafe_allow_html=True,
            )
            if st.button("התנתק / החלף משתמש", key="cu_logout", use_container_width=True):
                st.session_state.pop("_cv_access", None)
                st.logout()
