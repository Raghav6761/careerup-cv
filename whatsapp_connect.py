"""
One-time "Connect WhatsApp" prompt for the CV (Streamlit) tool — the Python twin of the
React tools' ConnectWhatsAppModal. Shown once per session to an authenticated, active
user who hasn't linked their WhatsApp yet.

It asks the central hub (service-authed with CV_SERVICE_SECRET) for a wa.me deep link
that pre-fills `CRP-<code>`, and renders it as a scannable QR + a button. The user just
sends the message; the bot links the number it arrives from (the handshake IS the
verification — no OTP).
"""
import io
import os
import streamlit as st
import requests
import qrcode


def _secret(key: str, default: str = "") -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


def _central_api_url() -> str:
    return _secret("CENTRAL_API_URL", "https://lgn.careerup.co.il").rstrip("/")


def _fetch_deeplink(clerk_id: str):
    """Service-authed call that mints a link code and returns the wa.me deep link."""
    try:
        resp = requests.post(
            f"{_central_api_url()}/api/cv/whatsapp/link-start",
            json={"clerkId": clerk_id},
            headers={"X-Service-Secret": _secret("CV_SERVICE_SECRET")},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("deepLink")
    except Exception:
        pass
    return None


def _qr_png(data: str) -> bytes:
    buf = io.BytesIO()
    qrcode.make(data).save(buf, format="PNG")
    return buf.getvalue()


@st.dialog("חברו את WhatsApp לייעוץ אישי")
def _connect_dialog(clerk_id: str):
    st.markdown(
        '<div style="direction:rtl;text-align:center;color:#555;font-size:0.95rem;'
        'line-height:1.6;margin-bottom:12px;">'
        'מאמן הקריירה ב-WhatsApp ייתן לכם ייעוץ אישי מבוסס AI לפי התוצאות שלכם, יזכיר '
        'לכם את הצעד הבא ויחגוג איתכם כל הישג. סרקו את הקוד עם הטלפון, או לחצו על הכפתור — '
        'שלחו את ההודעה שתיפתח, והמספר שלכם יאומת ויחובר אוטומטית.'
        '</div>',
        unsafe_allow_html=True,
    )

    deep_link = _fetch_deeplink(clerk_id)
    if not deep_link:
        st.error("חיבור ה-WhatsApp אינו זמין כרגע. אנא נסו שוב מאוחר יותר.")
        if st.button("סגירה", use_container_width=True):
            st.session_state["_wa_snoozed"] = True
            st.rerun()
        return

    with st.columns([1, 2, 1])[1]:
        st.image(_qr_png(deep_link), use_container_width=True)
    st.markdown(
        '<div style="direction:rtl;text-align:center;color:#6b7c93;font-size:0.8rem;'
        'margin-bottom:10px;">סרקו עם מצלמת הטלפון כדי לפתוח את WhatsApp</div>',
        unsafe_allow_html=True,
    )

    st.link_button("פתחו ב-WhatsApp בטלפון זה", deep_link, use_container_width=True)
    if st.button("אולי מאוחר יותר", use_container_width=True):
        st.session_state["_wa_snoozed"] = True
        st.rerun()


def maybe_render_connect_prompt(clerk_id, whatsapp_linked):
    """Open the connect dialog once per session for an active, unlinked user."""
    if not clerk_id or whatsapp_linked:
        return
    if st.session_state.get("_wa_snoozed") or st.session_state.get("_wa_prompted"):
        return
    st.session_state["_wa_prompted"] = True
    _connect_dialog(clerk_id)
