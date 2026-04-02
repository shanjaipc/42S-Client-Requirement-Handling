import sys
from pathlib import Path as _Path
_project_root = str(_Path(__file__).parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st # type: ignore
import streamlit.components.v1 as components # type: ignore
from datetime import date, datetime, timedelta, timezone
import os
import base64
import html as _html_mod
import re
import time
import json
import uuid
from pathlib import Path
from typing import Optional
from credentials import (
    verify_password, get_user, MAX_ATTEMPTS, LOCKOUT_SECONDS,
    add_user, set_password, set_role, set_active, list_users, save_users,
)
from analytics import (
    log_event,
    EVENT_LOGIN, EVENT_LOGOUT, EVENT_PAGE_VIEW,
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

try:
    from PIL import Image as _PIL_Image  # type: ignore
    _page_icon = _PIL_Image.open("42slogo_top.png") if os.path.exists("42slogo_top.png") else "🔍"
except Exception:
    _page_icon = "🔍"

st.set_page_config(
    page_title="42Signals | Requirement Handling",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

LOGO_PATH = str(Path(__file__).parent / "42slogo.png")

# Bidirectional component for secure localStorage-based session persistence.
_session_mgr = components.declare_component(
    "session_manager",
    path=str(Path(__file__).parent / "session_component"),
)

# D3.js bundled locally so mind maps work on servers without internet access.
# Falls back to CDN if the file is missing (dev convenience only).
@st.cache_resource
def _load_d3_inline():
    _path = Path("d3.v7.min.js")
    if _path.exists():
        return f"<script>{_path.read_text()}</script>"
    return '<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>'

_D3_INLINE = _load_d3_inline()

# ─────────────────────────────────────────────────────────────────────────────
# SECURITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _h(value) -> str:
    """HTML-escape any user-supplied value before injecting into unsafe_allow_html contexts.
    Prevents XSS when user text is embedded in st.markdown HTML strings."""
    return _html_mod.escape(str(value), quote=True)


def _safe_filename(name: str, suffix: str = "") -> str:
    """Sanitize a user-supplied string for use as a download filename.
    Strips path-traversal characters, null bytes, and limits length."""
    safe = re.sub(r'[^\w\s\-]', '', str(name), flags=re.UNICODE).strip()
    safe = re.sub(r'\s+', '_', safe)
    safe = safe[:80]  # cap at 80 chars to avoid filesystem limits
    return (safe or "document") + suffix


# ─────────────────────────────────────────────────────────────────────────────
# PERSISTENT SESSION  (file-based, stdlib only, 7-day expiry)
# ─────────────────────────────────────────────────────────────────────────────

_SESSION_FILE = Path(".42s_session.json")
_SESSION_TTL_DAYS = 7

# ── Server-side lockout (per username, survives new tabs / refreshes) ─────────
_LOCKOUT_FILE = Path(".42s_lockout.json")


def _get_lockout(username: str) -> tuple:
    """Return (attempts, lockout_until_timestamp) for a username."""
    try:
        if not _LOCKOUT_FILE.exists():
            return 0, 0.0
        data = json.loads(_LOCKOUT_FILE.read_text())
        rec = data.get(username.strip().lower(), {})
        return int(rec.get("attempts", 0)), float(rec.get("lockout_until", 0.0))
    except (OSError, KeyError, ValueError):
        return 0, 0.0


def _set_lockout(username: str, attempts: int, lockout_until: float) -> None:
    try:
        data = {}
        if _LOCKOUT_FILE.exists():
            try:
                data = json.loads(_LOCKOUT_FILE.read_text())
            except (ValueError, OSError):
                data = {}
        data[username.strip().lower()] = {"attempts": attempts, "lockout_until": lockout_until}
        # Prune entries whose lockout has expired and attempt count is reset
        now = time.time()
        data = {u: v for u, v in data.items() if v.get("lockout_until", 0) > now or v.get("attempts", 0) > 0}
        _LOCKOUT_FILE.write_text(json.dumps(data))
    except OSError:
        pass


def _clear_lockout(username: str) -> None:
    try:
        if not _LOCKOUT_FILE.exists():
            return
        data = json.loads(_LOCKOUT_FILE.read_text())
        data.pop(username.strip().lower(), None)
        _LOCKOUT_FILE.write_text(json.dumps(data))
    except (OSError, ValueError):
        pass


def _save_session(username: str, display_name: str) -> str:
    token = str(uuid.uuid4())
    data = {
        "token": token,
        "username": username,
        "display_name": display_name,
        "expires": (datetime.now(timezone.utc) + timedelta(days=_SESSION_TTL_DAYS)).isoformat(),
    }
    try:
        _SESSION_FILE.write_text(json.dumps(data))
    except OSError:
        pass
    return token


def _load_session(token: str):
    """Return (username, display_name) if token matches a valid non-expired session, else (None, None)."""
    if not token:
        return None, None
    try:
        if not _SESSION_FILE.exists():
            return None, None
        data = json.loads(_SESSION_FILE.read_text())
        if data.get("token") != token:
            return None, None
        if datetime.now(timezone.utc) > datetime.fromisoformat(data["expires"]):
            _SESSION_FILE.unlink(missing_ok=True)
            return None, None
        return data["username"], data["display_name"]
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return None, None




def _clear_session() -> None:
    try:
        _SESSION_FILE.unlink(missing_ok=True)
    except OSError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────────────

# Load Inter font via <link> (faster than @import inside <style>)
st.markdown(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

st.markdown("""
<style>

/* ── Streamlit chrome ── */
#MainMenu { visibility: hidden; }
footer     { visibility: hidden; }
[data-testid="stToolbar"]    { visibility: hidden; }
[data-testid="stDecoration"] { visibility: hidden; }
[data-testid="stStatusWidget"] { visibility: hidden; }
header     { visibility: hidden; }
header button,
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}

/* ── App background & global font ── */
.stApp {
    background-color: #f0f2f6;
    color: #1f2937 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* ── Global text colour (markdown, labels, captions) ── */
.stMarkdown p,
.stMarkdown li,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
.stMarkdown h4, .stMarkdown h5,
.element-container p,
[data-testid="stMainBlockContainer"] > div p,
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span,
.stCaption, .stText {
    color: #1f2937 !important;
}

/* ── Main block container spacing ── */
.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 2.5rem !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #d1d5db;
    box-shadow: 2px 0 12px rgba(0,0,0,0.05);
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .element-container p,
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] .stCaption {
    color: #6b7280 !important;
}
section[data-testid="stSidebar"] hr {
    border-color: #e5e7eb !important;
    margin: 12px 0 !important;
}

/* ── Sidebar nav buttons ── */
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    padding: 9px 12px !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    color: #4b5563 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    box-shadow: none !important;
    letter-spacing: 0 !important;
    transition: background .15s ease, color .15s ease !important;
    margin-bottom: 1px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #f1f5f9 !important;
    color: #1f2937 !important;
    border-color: transparent !important;
    box-shadow: none !important;
    transform: none !important;
}
section[data-testid="stSidebar"] .stButton > button:active {
    background: #e8ecf0 !important;
    box-shadow: none !important;
    transform: none !important;
}
/* Sidebar button inner <p>/<span> — let them inherit the button's colour
   instead of being forced to #1f2937 by the global .element-container p rule */
section[data-testid="stSidebar"] .stButton > button p,
section[data-testid="stSidebar"] .stButton > button span {
    color: inherit !important;
}
/* Use focus-visible so keyboard users see a clear outline; mouse clicks don't trigger it */
section[data-testid="stSidebar"] .stButton > button:focus-visible {
    outline: 2px solid #374151 !important;
    outline-offset: 2px !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton > button:focus:not(:focus-visible) {
    outline: none !important;
    box-shadow: none !important;
}

/* ── Sidebar expander ── */
section[data-testid="stSidebar"] details summary p {
    color: #374151 !important;
    font-weight: 600 !important;
}

/* ── Text inputs & textareas ── */
/* Use broad selectors to cover Streamlit's nested data-baseweb wrappers */
.stTextInput input,
.stTextArea textarea {
    border-radius: 8px !important;
    border: 1.5px solid #c9cfd8 !important;
    background: #ffffff !important;
    font-size: 0.875rem !important;
    color: #1f2937 !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    padding: 8px 12px !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: #374151 !important;
    box-shadow: 0 0 0 3px rgba(55,65,81,0.12) !important;
    outline: none !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #b0b7c3 !important;
}
/* Ensure the baseweb container itself doesn't show a competing background */
.stTextArea [data-baseweb="textarea"],
.stTextArea > div > div {
    background: transparent !important;
    border: none !important;
}

/* ── Selectbox ── */
.stSelectbox [data-baseweb="select"] > div:first-child {
    border-radius: 8px !important;
    border: 1.5px solid #c9cfd8 !important;
    background: #ffffff !important;
    font-size: 0.875rem !important;
    color: #1f2937 !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stSelectbox [data-baseweb="select"] > div:first-child:focus-within {
    border-color: #374151 !important;
    box-shadow: 0 0 0 3px rgba(55,65,81,0.12) !important;
}
/* Text & icon colours inside the closed select box only (not the portal) */
.stSelectbox [data-baseweb="select"] > div:first-child span,
.stSelectbox [data-baseweb="select"] > div:first-child > div { color: #1f2937 !important; }

/* ── Multiselect ── */
.stMultiSelect [data-baseweb="select"] > div:first-child {
    border-radius: 8px !important;
    border: 1.5px solid #c9cfd8 !important;
    background: #ffffff !important;
    font-size: 0.875rem !important;
    color: #1f2937 !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stMultiSelect [data-baseweb="select"] > div:first-child:focus-within {
    border-color: #374151 !important;
    box-shadow: 0 0 0 3px rgba(55,65,81,0.12) !important;
}
.stMultiSelect input { color: #1f2937 !important; }
.stMultiSelect [data-baseweb="select"] span { color: #1f2937 !important; }

/* ── Dropdown portal (renders at body root, outside stApp) ── */
/* Option list container */
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="select__dropdown"] {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 8px !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12) !important;
}
/* Individual options */
[data-baseweb="menu"] [role="option"],
[data-baseweb="popover"] li {
    font-size: 0.875rem !important;
    color: #1f2937 !important;
    background: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
}
/* Hovered option */
[data-baseweb="menu"] [role="option"]:hover,
[data-baseweb="popover"] li:hover {
    background: #f1f5f9 !important;
    color: #0f172a !important;
}
/* Selected/active option */
[data-baseweb="menu"] [aria-selected="true"],
[data-baseweb="menu"] [role="option"][data-highlighted] {
    background: #1f2937 !important;
    color: #ffffff !important;
}

/* ── Primary button ── */
div[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1f2937 0%, #374151 100%) !important;
    color: #ffffff !important;
    border: none !important;
    padding: 12px 32px !important;
    border-radius: 9px !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(31,41,55,0.22) !important;
}
div[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #111827 0%, #1f2937 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2) !important;
    transform: translateY(-1px) !important;
}
div[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"]:focus-visible {
    outline: 2px solid #374151 !important;
    outline-offset: 3px !important;
    box-shadow: 0 0 0 4px rgba(55,65,81,0.2) !important;
}
/* White text for primary buttons only — scoped to [kind="primary"] so
   secondary buttons (light bg) are NOT affected. */
div[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"] p,
div[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"] span {
    color: #ffffff !important;
}

/* ── Secondary button (default st.button with no type=) ── */
div[data-testid="stMainBlockContainer"] .stButton > button[kind="secondary"] {
    background: #ffffff !important;
    color: #1f2937 !important;
    border: 1.5px solid #c9cfd8 !important;
    border-radius: 9px !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    padding: 8px 18px !important;
    transition: all 0.2s ease !important;
    box-shadow: none !important;
}
div[data-testid="stMainBlockContainer"] .stButton > button[kind="secondary"]:hover {
    background: #f1f5f9 !important;
    border-color: #9ca3af !important;
    color: #0f172a !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
}
div[data-testid="stMainBlockContainer"] .stButton > button[kind="secondary"]:active {
    background: #e8ecf0 !important;
    border-color: #9ca3af !important;
    color: #0f172a !important;
    box-shadow: none !important;
    transform: translateY(1px) !important;
}
div[data-testid="stMainBlockContainer"] .stButton > button[kind="secondary"]:focus-visible {
    outline: 2px solid #374151 !important;
    outline-offset: 3px !important;
}
div[data-testid="stMainBlockContainer"] .stButton > button[kind="secondary"] p,
div[data-testid="stMainBlockContainer"] .stButton > button[kind="secondary"] span {
    color: #1f2937 !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #1f2937 0%, #374151 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 12px 20px !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(31,41,55,0.22) !important;
}
.stDownloadButton > button:hover {
    background: linear-gradient(135deg, #111827 0%, #1f2937 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2) !important;
    transform: translateY(-1px) !important;
}
.stDownloadButton > button:focus-visible {
    outline: 2px solid #374151 !important;
    outline-offset: 3px !important;
    box-shadow: 0 0 0 4px rgba(55,65,81,0.2) !important;
}
/* Same fix for download button inner text */
.stDownloadButton > button p,
.stDownloadButton > button span {
    color: #ffffff !important;
}

/* ── Expander (main area) ── */
details > summary > div > p {
    font-weight: 600 !important;
    color: #1f2937 !important;
    font-size: 0.875rem !important;
}
/* Chevron icon beside the summary label */
details > summary svg {
    color: #4b5563 !important;
    fill: #4b5563 !important;
}
details {
    border: 1px solid #d1d5db !important;
    border-radius: 10px !important;
    background: white !important;
    margin-bottom: 10px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    transition: box-shadow 0.2s !important;
}
details[open] {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
}

/* ── Radio — rectangular pill buttons ── */
.stRadio > label {
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    color: #374151 !important;
    letter-spacing: 0.01em !important;
}
.stRadio > div,
.stRadio [role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
}
.stRadio > div > label,
.stRadio [role="radiogroup"] label {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 6px 14px !important;
    height: 32px !important;
    border-radius: 6px !important;
    border: 1.5px solid #c9cfd8 !important;
    background: #ffffff !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: #374151 !important;
    cursor: pointer !important;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
    margin: 0 !important;
    line-height: 1 !important;
    box-sizing: border-box !important;
}
.stRadio > div > label:hover,
.stRadio [role="radiogroup"] label:hover {
    background: #f1f5f9 !important;
    border-color: #9ca3af !important;
}
.stRadio > div > label:has(input:checked),
.stRadio [role="radiogroup"] label:has(input:checked) {
    background: #1f2937 !important;
    border-color: #1f2937 !important;
    color: #ffffff !important;
}
/* Ensure text and nested elements inherit white color on selected state */
.stRadio > div > label:has(input:checked) p,
.stRadio > div > label:has(input:checked) span,
.stRadio > div > label:has(input:checked) div,
.stRadio [role="radiogroup"] label:has(input:checked) p,
.stRadio [role="radiogroup"] label:has(input:checked) span,
.stRadio [role="radiogroup"] label:has(input:checked) div {
    color: #ffffff !important;
}
.stRadio label p {
    margin: 0 !important;
    line-height: 1 !important;
    color: inherit !important;
}
/* Radio keyboard focus */
.stRadio > div > label:has(input:focus-visible),
.stRadio [role="radiogroup"] label:has(input:focus-visible) {
    outline: 2px solid #374151 !important;
    outline-offset: 2px !important;
}

/* ── Date input ── */
.stDateInput input {
    border-radius: 8px !important;
    border: 1.5px solid #c9cfd8 !important;
    background: #ffffff !important;
    font-size: 0.875rem !important;
    color: #1f2937 !important;
    padding: 8px 12px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stDateInput input:focus {
    border-color: #374151 !important;
    box-shadow: 0 0 0 3px rgba(55,65,81,0.12) !important;
    outline: none !important;
}
.stDateInput input::placeholder { color: #b0b7c3 !important; }
.stDateInput [data-baseweb="input"],
.stDateInput > div > div {
    background: transparent !important;
    border: none !important;
}

/* ── Labels ── */
.stTextInput label, .stTextArea label, .stSelectbox label,
.stMultiSelect label, .stNumberInput label, .stDateInput label,
.stRadio > label {
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    color: #374151 !important;
    letter-spacing: 0.01em !important;
}

/* ── Dividers ── */
hr {
    border: none !important;
    border-top: 1px solid #d1d5db !important;
    margin: 18px 0 !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #374151 !important; }

/* ── Alerts (info / success / warning / error) ── */
.stAlert {
    border-radius: 10px !important;
    font-size: 0.875rem !important;
    font-family: 'Inter', sans-serif !important;
}
/* Let each alert type keep its own colour — the global "> div p" rule would
   otherwise force all alert text to #1f2937, killing green/red/yellow coding. */
.stAlert p, .stAlert span, .stAlert a {
    color: inherit !important;
    font-size: 0.875rem !important;
}
[data-testid="stNotification"] {
    border-radius: 10px !important;
}

/* ── Markdown bold ── */
.stMarkdown strong { color: #111827 !important; font-weight: 600 !important; }

/* ── Tag chips in multiselect ── */
.stMultiSelect span[data-baseweb="tag"] {
    background-color: #f1f5f9 !important;
    border-radius: 6px !important;
    color: #1f2937 !important;
    font-size: 0.78rem !important;
}
.stMultiSelect span[data-baseweb="tag"] button { color: #6b7280 !important; }
.stMultiSelect input::placeholder { color: #b0b7c3 !important; }

/* ── Number input — full styling including stepper buttons ── */
.stNumberInput input {
    background: #ffffff !important;
    border: 1.5px solid #c9cfd8 !important;
    border-radius: 8px !important;
    color: #1f2937 !important;
    font-size: 0.875rem !important;
    padding: 8px 12px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stNumberInput input:focus {
    border-color: #374151 !important;
    box-shadow: 0 0 0 3px rgba(55,65,81,0.12) !important;
    outline: none !important;
}
.stNumberInput input::placeholder { color: #b0b7c3 !important; }
/* Stepper +/- buttons */
.stNumberInput [data-baseweb="input"] button {
    background: #f8fafc !important;
    border-left: 1px solid #c9cfd8 !important;
    color: #374151 !important;
}
.stNumberInput [data-baseweb="input"] button:hover {
    background: #f1f5f9 !important;
    color: #1f2937 !important;
}
/* Remove competing wrapper border */
.stNumberInput [data-baseweb="input"] {
    border: none !important;
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

if "page"             not in st.session_state: st.session_state["page"]             = "dashboard"
if "authenticated"    not in st.session_state: st.session_state["authenticated"]    = False
if "current_user"     not in st.session_state: st.session_state["current_user"]     = None
if "display_name"     not in st.session_state: st.session_state["display_name"]     = None
if "failed_attempts"        not in st.session_state: st.session_state["failed_attempts"]        = 0
if "lockout_until"          not in st.session_state: st.session_state["lockout_until"]          = 0.0
if "login_username_preview" not in st.session_state: st.session_state["login_username_preview"] = ""
if "cc_show_results"        not in st.session_state: st.session_state["cc_show_results"]        = False
if "cc_saved_scenarios"     not in st.session_state: st.session_state["cc_saved_scenarios"]     = {}
if "_cc_last_results"       not in st.session_state: st.session_state["_cc_last_results"]       = []
if "analytics_sid"          not in st.session_state: st.session_state["analytics_sid"]          = str(uuid.uuid4())
if "analytics_last_page"    not in st.session_state: st.session_state["analytics_last_page"]    = ""
if "ls_write_token"         not in st.session_state: st.session_state["ls_write_token"]         = ""
if "ls_clear"               not in st.session_state: st.session_state["ls_clear"]               = False
if "_editing_submission_file" not in st.session_state: st.session_state["_editing_submission_file"] = None
if "_draft_dismissed"           not in st.session_state: st.session_state["_draft_dismissed"]           = False
if "hist_status_filter_init"  not in st.session_state: st.session_state["hist_status_filter_init"]  = "All"
if "_form_touched"            not in st.session_state: st.session_state["_form_touched"]            = False

# Session restoration from localStorage is handled by _session_mgr component below.


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data
def get_base64_image(path):
    """Read and base64-encode an image file. Result is cached across rerenders."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def celebrate(message="Done!", sub=""):
    """Balloons + confetti burst + animated success banner."""
    st.balloons()
    components.html("""
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.3/dist/confetti.browser.min.js"></script>
    <script>
    (function(){
        var end = Date.now() + 2200;
        var colors = ['#1f2937','#374151','#6b7280','#9ca3af','#d1d5db'];
        (function frame(){
            confetti({ particleCount:6, angle:60,  spread:55, origin:{x:0}, colors:colors });
            confetti({ particleCount:6, angle:120, spread:55, origin:{x:1}, colors:colors });
            if (Date.now() < end) requestAnimationFrame(frame);
        }());
    })();
    </script>
    """, height=0)
    st.markdown(f"""
    <style>
    @keyframes slideDown {{
        from {{ opacity: 0; transform: translateY(-16px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    </style>
    <div style="
        animation: slideDown 0.4s cubic-bezier(0.34,1.56,0.64,1) forwards;
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 1px solid #86efac;
        border-left: 5px solid #16a34a;
        border-radius: 12px;
        padding: 15px 20px;
        margin: 14px 0 10px 0;
        display: flex; align-items: center; gap: 14px;
        box-shadow: 0 4px 16px rgba(22,163,74,0.12);
        font-family: 'Inter', sans-serif;
    ">
        <div style="font-size:1.7rem; flex-shrink:0;">✅</div>
        <div>
            <div style="font-weight:700;color:#15803d;font-size:0.95rem;letter-spacing:0.01em;">{_h(message)}</div>
            {"" if not sub else f'<div style="color:#166534;font-size:0.8rem;margin-top:4px;opacity:0.85;">{_h(sub)}</div>'}
        </div>
    </div>
    """, unsafe_allow_html=True)


def section_header(icon, title):
    """Styled section header bar used inside form pages."""
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-left: 4px solid #1f2937;
        border-radius: 0 10px 10px 0;
        color: #0f172a;
        padding: 11px 18px;
        font-weight: 700;
        font-size: 0.875rem;
        margin: 30px 0 16px 0;
        letter-spacing: 0.02em;
        display: flex;
        align-items: center;
        gap: 9px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        font-family: 'Inter', sans-serif;
    ">{icon}&ensp;{title}</div>
    """, unsafe_allow_html=True)


def page_title(title, subtitle=""):
    st.markdown(f"""
    <div style="padding: 4px 0 22px 0; margin-bottom: 4px;">
        <div style="font-size: 1.65rem; font-weight: 700; color: #0f172a; line-height: 1.2; letter-spacing: -0.025em; font-family: 'Inter', sans-serif;">{_h(title)}</div>
        {"" if not subtitle else f'<div style="font-size:0.875rem;color:#6b7280;margin-top:7px;font-weight:400;line-height:1.5;">{_h(subtitle)}</div>'}
        <div style="height:3px;background:linear-gradient(90deg,#1f2937 0%,#6b7280 55%,transparent 100%);border-radius:2px;margin-top:16px;"></div>
    </div>
    """, unsafe_allow_html=True)


def info_row(label, value):
    # _h() escapes user-supplied value to prevent XSS via unsafe_allow_html
    st.markdown(f"""
    <div style="padding: 8px 10px 7px 10px; border-bottom: 1px solid #e5e7eb;">
        <div style="color:#6b7280; font-size:0.66rem; text-transform:uppercase; letter-spacing:0.08em; font-weight:700; margin-bottom:3px; font-family:'Inter',sans-serif;">{_h(label)}</div>
        <div style="color:#111827; font-size:0.875rem; font-weight:500; font-family:'Inter',sans-serif;">{_h(value)}</div>
    </div>
    """, unsafe_allow_html=True)


def frequency_selector(label, key_prefix):
    col1, col2 = st.columns([1, 1])
    with col1:
        freq = st.selectbox(f"{label} — Frequency", ["Daily", "Weekly", "Monthly", "Hourly"], key=f"{key_prefix}_freq")
    hourly_count = None
    daily_count = None
    if freq == "Hourly":
        with col2:
            hourly_count = st.number_input("Times / day", min_value=1, key=f"{key_prefix}_hourly")
    elif freq == "Daily":
        with col2:
            daily_count = st.radio("Times / day", [1, 2], key=f"{key_prefix}_daily", horizontal=True)
    return freq, hourly_count, daily_count


def calculate_risk(freq_string, volume_string):
    if not freq_string or not volume_string:
        return None
    freq_score = 1
    if "Hourly" in freq_string:
        try:
            times = int(freq_string.split("(")[1].split()[0])
            freq_score = 3 if times > 6 else 2
        except (IndexError, ValueError):
            freq_score = 2
    vol_score = 1
    try:
        volume = int(str(volume_string).replace(",", ""))
        vol_score = 1 if volume <= 10_000 else (2 if volume <= 50_000 else 3)
    except ValueError:
        pass
    total = freq_score + vol_score
    return "LOW" if total <= 2 else ("MODERATE" if total <= 4 else "CRITICAL")


PREDEFINED_DOMAINS = ["swiggy.com", "blinkit.com", "zeptonow.com", "amazon.in", "flipkart.com"]


def _section_label(text: str) -> None:
    """Render a bold section label as HTML.

    Use this instead of st.markdown(f"**{text}**") whenever `text` is a
    variable or contains an asterisk — trailing/embedded asterisks break
    Markdown bold syntax (e.g. "**Domains ***" is invalid).
    """
    if text.endswith(" *"):
        base = text[:-2]
        html = (
            f'<span style="font-weight:600;color:#374151;font-size:0.875rem;">'
            f'{base} <span style="color:#dc2626;font-weight:700;">*</span></span>'
        )
    else:
        html = f'<span style="font-weight:600;color:#374151;font-size:0.875rem;">{text}</span>'
    st.markdown(html, unsafe_allow_html=True)


def domain_selector(label, key_prefix):
    _section_label(label)
    col1, col2 = st.columns([3, 1])
    with col1:
        selected = st.multiselect(label, PREDEFINED_DOMAINS, key=f"{key_prefix}_domains", label_visibility="collapsed")
    with col2:
        custom = st.text_input("Custom", placeholder="+ Add domain", key=f"{key_prefix}_custom_domain", label_visibility="collapsed")
    domains = selected + ([custom.strip()] if custom.strip() else [])
    return ", ".join(domains) if domains else "", domains


def _safe_key(s):
    """Return a Streamlit-safe widget key fragment from an arbitrary string."""
    return re.sub(r'[^a-zA-Z0-9]', '_', s)



# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────

def render_login():
    """Full-page sign-in screen — dark gradient background with white card."""

    # ── Page-level CSS (dark theme, animated orbs, card shell) ───────────
    st.markdown("""
    <style>
    @keyframes orbFloat {
        0%   { opacity:.5;  transform:scale(1)    translate(0,    0);    }
        100% { opacity:.85; transform:scale(1.08) translate(1.5%, 1.5%); }
    }
    @keyframes cardIn {
        from { opacity:0; transform:translateY(28px) scale(.97); }
        to   { opacity:1; transform:translateY(0)    scale(1);   }
    }
    @keyframes shimmer {
        0%   { background-position: -400px 0; }
        100% { background-position:  400px 0; }
    }

    /* ── Full-page dark background ── */
    .stApp {
        background: linear-gradient(145deg, #0a0f1e 0%, #0f172a 40%, #111827 100%) !important;
        min-height: 100vh;
        position: relative;
        overflow: hidden;
    }

    /* ── Animated gradient orbs ── */
    .stApp::before {
        content: '';
        position: fixed;
        inset: 0;
        background:
            radial-gradient(ellipse at 12% 22%,  rgba(99,102,241,.22) 0%, transparent 42%),
            radial-gradient(ellipse at 88% 78%,  rgba(16,185,129,.15) 0%, transparent 42%),
            radial-gradient(ellipse at 60% 5%,   rgba(59,130,246,.12) 0%, transparent 38%),
            radial-gradient(ellipse at 30% 90%,  rgba(139,92,246,.1)  0%, transparent 38%);
        animation: orbFloat 11s ease-in-out infinite alternate;
        pointer-events: none;
        z-index: 0;
    }

    /* ── Hide all chrome ── */
    section[data-testid="stSidebar"] { display:none !important; }
    header   { display:none !important; }
    footer   { display:none !important; }
    #MainMenu { display:none !important; }

    /* ── Card shell ── */
    .block-container {
        max-width: 450px !important;
        margin-top: 6vh !important;
        padding: 0 !important;
        background: #ffffff !important;
        border-radius: 24px !important;
        box-shadow:
            0 32px 80px rgba(0,0,0,.55),
            0  0   0  1px rgba(255,255,255,.07),
            inset 0 1px 0 rgba(255,255,255,.9) !important;
        position: relative !important;
        z-index: 1 !important;
        animation: cardIn .6s cubic-bezier(.34,1.56,.64,1) both !important;
    }

    /* ── Inner padding for Streamlit widgets (inputs, button, alerts) ── */
    [data-testid="stVerticalBlock"] {
        padding: 0 32px 24px 32px !important;
    }

    /* ── Login inputs (broad selectors to cover Streamlit's nested wrappers) ── */
    .stTextInput input,
    .stTextInput > div > div > input {
        background: #f8fafc !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 10px !important;
        font-size: 0.9rem !important;
        color: #0f172a !important;
        padding: 10px 14px !important;
        transition: all .2s !important;
    }
    .stTextInput input:focus,
    .stTextInput > div > div > input:focus {
        background: #ffffff !important;
        border-color: #374151 !important;
        box-shadow: 0 0 0 3px rgba(31,41,55,.1) !important;
        outline: none !important;
    }
    .stTextInput input::placeholder { color: #94a3b8 !important; }
    .stTextInput label {
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        color: #374151 !important;
        letter-spacing: .04em !important;
        text-transform: uppercase !important;
    }

    /* ── Sign-in button (form_submit_button renders inside .stFormSubmitButton) ── */
    [data-testid="stMainBlockContainer"] .stButton > button[kind="primary"],
    [data-testid="stMainBlockContainer"] .stFormSubmitButton > button,
    [data-testid="stMainBlockContainer"] .stFormSubmitButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1f2937 0%, #374151 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 11px !important;
        padding: 14px 0 !important;
        font-size: .95rem !important;
        font-weight: 700 !important;
        letter-spacing: .035em !important;
        box-shadow: 0 4px 18px rgba(31,41,55,.38) !important;
        transition: all .22s ease !important;
    }
    [data-testid="stMainBlockContainer"] .stButton > button[kind="primary"]:hover,
    [data-testid="stMainBlockContainer"] .stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 10px 30px rgba(0,0,0,.35) !important;
        transform: translateY(-2px) !important;
    }
    [data-testid="stMainBlockContainer"] .stButton > button[kind="primary"]:active,
    [data-testid="stMainBlockContainer"] .stFormSubmitButton > button:active {
        transform: translateY(0) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,.25) !important;
    }
    /* Ensure text inside the button is always white */
    [data-testid="stMainBlockContainer"] .stFormSubmitButton > button p,
    [data-testid="stMainBlockContainer"] .stFormSubmitButton > button span {
        color: #ffffff !important;
    }

    /* ── Alerts on login page ── */
    .stAlert {
        border-radius: 10px !important;
        font-size: .85rem !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stAlert p, .stAlert span { font-size: .85rem !important; color: inherit !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── Accent bar (top of card) ──────────────────────────────────────────
    st.markdown("""<div style="height:5px;margin:0 -32px;background:linear-gradient(90deg,#1f2937 0%,#6366f1 35%,#8b5cf6 55%,#6366f1 75%,#1f2937 100%);background-size:200% 100%;animation:shimmer 3s linear infinite;"></div>""", unsafe_allow_html=True)

    # ── Hero section ─────────────────────────────────────────────────────
    if os.path.exists(LOGO_PATH):
        img_b64 = get_base64_image(LOGO_PATH)
        logo_html = f'<img src="data:image/png;base64,{img_b64}" style="height:54px;width:auto;margin-bottom:16px;filter:drop-shadow(0 4px 12px rgba(0,0,0,.12));">'
    else:
        logo_html = '<div style="font-size:1.6rem;font-weight:800;color:#0f172a;letter-spacing:-.03em;margin-bottom:16px;">42Signals</div>'

    st.markdown(f"""<div style="text-align:center;padding:36px 32px 24px 32px;margin:0 -32px;background:linear-gradient(180deg,#f8fafc 0%,#ffffff 100%);border-bottom:1px solid #e2e8f0;">
{logo_html}
<div style="font-size:1.55rem;font-weight:800;color:#0f172a;letter-spacing:-.035em;line-height:1.15;font-family:'Inter',sans-serif;">Welcome back</div>
<div style="font-size:0.875rem;color:#475569;margin-top:9px;font-family:'Inter',sans-serif;line-height:1.55;font-weight:400;">Sign in to access the 42Signals<br>Requirement Handling portal</div>
<div style="display:flex;justify-content:center;gap:8px;margin-top:18px;flex-wrap:wrap;">
<span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:20px;padding:4px 12px;font-size:0.7rem;color:#475569;font-weight:600;font-family:'Inter',sans-serif;">&#128203; Forms</span>
<span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:20px;padding:4px 12px;font-size:0.7rem;color:#475569;font-weight:600;font-family:'Inter',sans-serif;">&#128202; Feasibility</span>
<span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:20px;padding:4px 12px;font-size:0.7rem;color:#475569;font-weight:600;font-family:'Inter',sans-serif;">&#128256; Workflows</span>
</div>
</div>""", unsafe_allow_html=True)

    # ── Lockout check (server-side — persists across tabs) ───────────────
    # We need a username to check server-side lockout, so show the field first
    # for the lockout lookup. We re-read it after form submission too.
    _preview_user = st.session_state.get("login_username_preview", "")

    now = time.time()
    _srv_attempts, _srv_lockout_until = _get_lockout(_preview_user) if _preview_user else (0, 0.0)
    # Also check session-state lockout (covers anonymous pre-username-entry state)
    _ss_lockout = st.session_state["lockout_until"]
    locked    = (_srv_lockout_until > now) or (_ss_lockout > now)
    remaining = int(max(_srv_lockout_until, _ss_lockout) - now)

    if locked:
        st.markdown(f"""<div role="alert" style="background:linear-gradient(135deg,#fef2f2,#fee2e2);border:1px solid #fca5a5;border-left:4px solid #dc2626;border-radius:12px;padding:15px 18px;margin-bottom:4px;color:#7f1d1d;font-family:'Inter',sans-serif;font-size:.875rem;display:flex;align-items:center;gap:12px;">
<span style="font-size:1.5rem;flex-shrink:0;">&#128274;</span>
<div><div style="font-weight:700;margin-bottom:3px;">Account temporarily locked</div>
<div style="opacity:.8;">Too many failed attempts.<br>Try again in <strong>{remaining // 60}m {remaining % 60}s</strong>.</div>
</div></div>""", unsafe_allow_html=True)
        st.markdown("""<div style="text-align:center;padding:20px 0 6px 0;font-size:.72rem;color:#94a3b8;font-family:'Inter',sans-serif;">Access restricted to authorised users only &middot; 42Signals &copy; 2026</div>""", unsafe_allow_html=True)
        # Auto-refresh every second so the countdown ticks live
        time.sleep(1)
        st.rerun()

    # ── Session-expiry notice ─────────────────────────────────────────────
    if st.session_state.get("_session_expired"):
        st.markdown("""<div role="alert" style="background:linear-gradient(135deg,#fff7ed,#ffedd5);border:1px solid #fed7aa;border-left:4px solid #f97316;border-radius:12px;padding:14px 18px;margin-bottom:4px;color:#7c2d12;font-family:'Inter',sans-serif;font-size:.875rem;display:flex;align-items:center;gap:12px;">
<span style="font-size:1.4rem;flex-shrink:0;">&#9201;</span>
<div><div style="font-weight:700;margin-bottom:3px;">Session expired</div>
<div style="opacity:.85;">Your session has expired. Please sign in again.</div>
</div></div>""", unsafe_allow_html=True)
        st.session_state["_session_expired"] = False

    # ── Form (st.form enables Enter-to-submit) ────────────────────────────
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input(
            "Username",
            placeholder="e.g. shanjai",
            key="login_username",
            autocomplete="username",
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="••••••••••",
            key="login_password",
            autocomplete="current-password",
        )

        # Failed-attempt inline alert (inside form so it's visible before submit)
        attempts = st.session_state.get("failed_attempts", 0)
        if attempts > 0:
            left = MAX_ATTEMPTS - attempts
            st.markdown(f"""<div role="alert" style="background:linear-gradient(135deg,#fffbeb,#fef9ec);border:1px solid #fcd34d;border-left:4px solid #f59e0b;border-radius:10px;padding:11px 15px;color:#78350f;font-size:.82rem;margin-top:4px;font-family:'Inter',sans-serif;display:flex;align-items:center;gap:9px;">
<span style="font-size:1rem;flex-shrink:0;">&#9888;&#65039;</span>
<span>Incorrect credentials &mdash; <strong>{left} attempt{'s' if left != 1 else ''}</strong> left before lockout.</span>
</div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Sign In  →", type="primary", width="stretch")

    if submitted:
        clean_user = username.strip().lower()
        # Store username preview for server-side lockout lookup on next render
        st.session_state["login_username_preview"] = clean_user
        # Re-check server-side lockout for this specific username
        _srv_attempts, _srv_lockout_until = _get_lockout(clean_user)
        if _srv_lockout_until > time.time():
            st.rerun()
        elif not username or not password:
            st.warning("Please enter both username and password.")
        elif verify_password(username, password):
            user = get_user(username)
            display_name = user["display_name"] if user else clean_user
            st.session_state["authenticated"]   = True
            st.session_state["current_user"]    = clean_user
            st.session_state["display_name"]    = display_name
            st.session_state["failed_attempts"] = 0
            st.session_state["lockout_until"]   = 0.0
            _clear_lockout(clean_user)
            _new_analytics_sid = str(uuid.uuid4())
            st.session_state["analytics_sid"] = _new_analytics_sid
            log_event(EVENT_LOGIN, clean_user, _new_analytics_sid)
            _sid = _save_session(clean_user, display_name)
            st.session_state["ls_write_token"] = _sid
            st.rerun()
        else:
            new_attempts = _srv_attempts + 1
            if new_attempts >= MAX_ATTEMPTS:
                _set_lockout(clean_user, 0, time.time() + LOCKOUT_SECONDS)
                st.session_state["lockout_until"]   = time.time() + LOCKOUT_SECONDS
                st.session_state["failed_attempts"] = 0
            else:
                _set_lockout(clean_user, new_attempts, 0.0)
                st.session_state["failed_attempts"] = new_attempts
            st.rerun()

    # ── Card footer ──────────────────────────────────────────────────────
    st.markdown("""<div style="text-align:center;padding:20px 32px 6px 32px;margin:8px -32px 0 -32px;border-top:1px solid #f1f5f9;">
<div style="font-size:.72rem;color:#94a3b8;font-family:'Inter',sans-serif;display:flex;align-items:center;justify-content:center;gap:10px;">
<span style="display:inline-block;width:24px;height:1px;background:#e2e8f0;"></span>
Access restricted to authorised users only
<span style="display:inline-block;width:24px;height:1px;background:#e2e8f0;"></span>
</div></div>""", unsafe_allow_html=True)

    # ── Below-card caption ────────────────────────────────────────────────
    st.markdown("""<div style="text-align:center;margin-top:22px;font-size:.7rem;color:rgba(255,255,255,.2);font-family:'Inter',sans-serif;letter-spacing:.05em;">42Signals &nbsp;&copy;&nbsp; 2026</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR  (CSS-hidden on login page via render_login(); Python still runs safely)
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:

    # Brand header
    if os.path.exists(LOGO_PATH):
        img_b64 = get_base64_image(LOGO_PATH)
        st.markdown(f"""
        <div style="text-align:center; padding:28px 16px 20px 16px;">
            <img src="data:image/png;base64,{img_b64}"
                 style="height:52px; width:auto; margin-bottom:12px; display:block; margin-left:auto; margin-right:auto;">
            <div style="font-size:0.7rem; font-weight:600; color:#9ca3af; letter-spacing:0.12em; text-transform:uppercase; font-family:'Inter',sans-serif;">Requirement Handling</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center; padding:28px 16px 20px 16px;">
            <div style="font-size:1.1rem; font-weight:700; color:#1f2937;">42Signals</div>
            <div style="font-size:0.7rem; font-weight:600; color:#9ca3af; letter-spacing:0.12em; text-transform:uppercase; margin-top:4px;">Requirement Handling</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 14px 0;">', unsafe_allow_html=True)

    def _nav_group(group_label, items):
        st.markdown(
            f'<div style="color:#9ca3af;font-size:0.62rem;text-transform:uppercase;'
            f'letter-spacing:0.14em;padding:10px 6px 5px 6px;font-weight:700;'
            f'font-family:\'Inter\',sans-serif;">{group_label}</div>',
            unsafe_allow_html=True,
        )
        for key, (svg, label) in items.items():
            active = st.session_state["page"] == key
            if active:
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#f1f5f9 0%,#e8ecf0 100%);'
                    f'border:1px solid #dde3ea;border-left:3px solid #1f2937;border-radius:8px;'
                    f'padding:9px 12px;color:#111827;font-size:0.83rem;font-weight:600;'
                    f'margin-bottom:3px;display:flex;align-items:center;gap:9px;'
                    f'font-family:\'Inter\',sans-serif;white-space:nowrap;'
                    f'box-shadow:0 1px 3px rgba(0,0,0,0.05);">{svg}&nbsp;{label}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(label, key=f"nav_{key}", width="stretch"):
                    st.session_state["page"] = key
                    st.rerun()

    _current_role = (get_user(st.session_state.get("current_user", "") or "") or {}).get("role", "")

    _NAV_TOOLS = {
        "dashboard": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
            "Dashboard",
        ),
        "main": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/></svg>',
            "New Requirement Form",
        ),
        "sub_history": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
            "Submission History",
        ),
        "feasibility": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 20h18M7 20V12M12 20V5M17 20v-8"/></svg>',
            "Feasibility Assessment",
        ),
        "cost_calc": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 8h2m4 0h3M7 12h2m4 0h3M7 16h2m4 0h3"/></svg>',
            "Cost Calculator",
        ),
    }
    _NAV_REF = {
        "req_flow": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="12" r="2.5"/><circle cx="19" cy="12" r="2.5"/><path d="M7.5 12h9"/><path d="M14.5 9l3 3-3 3"/></svg>',
            "Requirement Flow",
        ),
        "ops_map": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
            "Ops Map",
        ),
        "poc_guide": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
            "Task POC Guide",
        ),
        "ext_tools": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
            "External Tools",
        ),
    }

    _nav_group("Tools", _NAV_TOOLS)
    _nav_group("Reference", _NAV_REF)

    if _current_role == "admin":
        _NAV_ADMIN = {
            "analytics": (
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 20h18M7 20V12M12 20V5M17 20v-8"/></svg>',
                "Analytics Dashboard",
            ),
            "rate_mgr": (
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
                "Rate Manager",
            ),
            "user_mgmt": (
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="7" r="4"/><path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/><path d="M21 21v-2a4 4 0 0 0-3-3.85"/></svg>',
                "User Management",
            ),
        }
        _nav_group("Admin", _NAV_ADMIN)

    st.markdown('<hr style="border:none;border-top:1px solid #e5e7eb;margin:14px 0 10px 0;">', unsafe_allow_html=True)

    # ── Logged-in user info + logout ──────────────────────────────────────────
    display_name = st.session_state.get("display_name") or ""
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg,#f8fafc 0%,#f1f5f9 100%);
        border:1px solid #e5e7eb; border-radius:10px;
        padding:11px 14px; margin-bottom:10px;
        font-family:'Inter',sans-serif;
        display:flex; align-items:center; gap:10px;
    ">
        <div style="
            width:32px; height:32px; border-radius:50%;
            background:linear-gradient(135deg,#1f2937 0%,#374151 100%);
            display:flex; align-items:center; justify-content:center;
            font-size:0.875rem; font-weight:700; color:#fff; flex-shrink:0;
        ">{_h(display_name[:1].upper()) if display_name else "?"}</div>
        <div>
            <div style="font-size:0.82rem;font-weight:600;color:#111827;">{_h(display_name)}</div>
            <div style="font-size:0.7rem;color:#6b7280;margin-top:1px;">Signed in</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Sign Out", key="logout_btn", width="stretch"):
        log_event(EVENT_LOGOUT, st.session_state.get("current_user", ""), st.session_state.get("analytics_sid", ""))
        _clear_session()
        st.query_params.clear()
        st.session_state["ls_clear"]        = True
        st.session_state["authenticated"]   = False
        st.session_state["current_user"]    = None
        st.session_state["display_name"]    = None
        st.session_state["failed_attempts"] = 0
        st.session_state["lockout_until"]   = 0.0
        st.session_state["page"]                = "main"
        st.session_state["cc_show_results"]     = False
        st.session_state["analytics_sid"]       = str(uuid.uuid4())
        st.session_state["analytics_last_page"] = ""
        st.rerun()

    st.markdown("""
    <div style="text-align:center; padding:6px 0 12px 0;">
        <div style="color:#9ca3af; font-size:0.68rem; font-family:'Inter',sans-serif; letter-spacing:0.04em;">v1.0 &nbsp;·&nbsp; 42Signals &nbsp;·&nbsp; 2026</div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SUBMISSION PERSISTENCE
# ─────────────────────────────────────────────────────────────────────────────

_SUBMISSIONS_DIR = Path("submissions")
_FORM_KEY_PREFIXES = (
    "form_", "pt_", "sos_", "rev_", "pv_", "storeid_", "festive_", "final_",
)


def _json_default(obj):
    """JSON serialiser for types not handled natively (date, set, etc.)."""
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, set):
        return list(obj)
    return str(obj)


def save_submission(form_data: dict, client_name: str, username: str) -> None:
    """Persist the current form widget state and form_data to submissions/.
    If a submission was loaded for editing, overwrite that file instead of creating a new one."""
    _SUBMISSIONS_DIR.mkdir(exist_ok=True)
    editing_file = st.session_state.get("_editing_submission_file")
    if editing_file and (_SUBMISSIONS_DIR / editing_file).exists():
        filename = editing_file
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", client_name or "unknown")
        filename = f"{safe_name}_{timestamp}.json"
    # Capture all widget keys that belong to the requirement form
    snapshot = {
        k: v for k, v in st.session_state.items()
        if isinstance(k, str) and k.startswith(_FORM_KEY_PREFIXES)
    }
    payload = {
        "client_name": client_name,
        "saved_at": datetime.now().isoformat(),
        "saved_by": username,
        "status": st.session_state.get(f"_sub_status_{filename}", "Submitted"),
        "form_data": form_data,
        "session_state": snapshot,
    }
    with open(_SUBMISSIONS_DIR / filename, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=_json_default)
    st.session_state["_editing_submission_file"] = filename
    list_submissions.clear()  # invalidate cache so the new file appears immediately


@st.cache_data(ttl=60)
def list_submissions() -> list[dict]:
    """Return list of submission metadata dicts, newest first.
    Cached for 60 s so repeated reruns don't re-read the filesystem."""
    if not _SUBMISSIONS_DIR.exists():
        return []
    result = []
    for p in sorted(_SUBMISSIONS_DIR.glob("*.json"), reverse=True):
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            _mods = data.get("form_data", {}).get("Modules Selected", {}).get("Selected Modules", [])
            _mods_str = ", ".join(_mods) if isinstance(_mods, list) else str(_mods) if _mods else "—"
            result.append({
                "filename":    p.name,
                "client_name": data.get("client_name", p.stem),
                "saved_at":    data.get("saved_at", ""),
                "saved_by":    data.get("saved_by", ""),
                "modules":     _mods_str,
                "status":      data.get("status", "Submitted"),
            })
        except Exception:
            pass
    return result


def load_submission(filename: str) -> None:
    """Restore form widget state from a saved submission JSON and trigger rerun."""
    path = _SUBMISSIONS_DIR / filename
    if not path.exists():
        st.error("Submission file not found.")
        return
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    _ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for k, v in data.get("session_state", {}).items():
        # Re-hydrate any ISO date string back to datetime.date.
        # Per-domain date keys get a suffix (e.g. pt_inputs_expected_date_swiggy_com)
        # so key-name matching is unreliable — match on value shape instead.
        if isinstance(v, str) and _ISO_DATE_RE.match(v):
            try:
                v = date.fromisoformat(v)
            except ValueError:
                pass
        st.session_state[k] = v
    st.session_state["_editing_submission_file"] = filename
    st.rerun()


def _update_submission_status(filename: str, status: str) -> None:
    """Write a new status field into an existing submission JSON file."""
    path = _SUBMISSIONS_DIR / filename
    if not path.exists():
        return
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        data["status"] = status
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=_json_default)
        list_submissions.clear()
    except (OSError, json.JSONDecodeError):
        pass


# ── Auto-draft helpers ────────────────────────────────────────────────────────

def _draft_path(username: str) -> Path:
    safe = re.sub(r"[^a-z0-9_]", "", username.lower())
    return Path(f".42s_draft_{safe}.json")


def _save_draft(username: str, form_data: dict) -> None:
    try:
        snapshot = {k: v for k, v in st.session_state.items()
                    if isinstance(k, str) and k.startswith(_FORM_KEY_PREFIXES)}
        payload = {
            "form_data": form_data,
            "session_state": snapshot,
            "saved_at": datetime.now().isoformat(),
        }
        _draft_path(username).write_text(json.dumps(payload, default=_json_default))
    except OSError:
        pass


def _load_draft(username: str) -> Optional[dict]:
    p = _draft_path(username)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _clear_draft(username: str) -> None:
    try:
        _draft_path(username).unlink(missing_ok=True)
    except OSError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: New Requirement Form
# ─────────────────────────────────────────────────────────────────────────────

def _field_filled(section, field):
    """True if field is non-empty directly, or via any per-domain key ('domain — field')."""
    val = section.get(field)
    if isinstance(val, list):
        return bool(val)
    if val:
        return True
    return any(v for k, v in section.items() if k.endswith(f"\u2014 {field}") and v)


def _validate_form(form_data, modules):
    """Return list of error strings for all missing required fields."""
    errors = []

    if not form_data.get("Client Information", {}).get("Target Market"):
        errors.append("**Client Information** \u2014 Target Market / Geography is required.")

    if not modules:
        errors.append("**Modules** \u2014 Select at least one module.")

    if "Products + Trends" in modules:
        if not form_data.get("Products + Trends", {}).get("Domains"):
            errors.append("**Products + Trends** \u2014 At least one domain is required.")

    if "SOS (Search on Site)" in modules:
        sos = form_data.get("SOS (Search on Site)", {})
        if not sos.get("Domains"):
            errors.append("**SOS** \u2014 At least one domain is required.")
        if not int(sos.get("No. of Keywords", 0)):
            errors.append("**SOS** \u2014 Number of Keywords must be greater than 0.")

    if "Reviews" in modules:
        rev = form_data.get("Reviews", {})
        if not rev.get("Domains"):
            errors.append("**Reviews** \u2014 At least one domain is required.")
        if not _field_filled(rev, "Input Sources"):
            errors.append("**Reviews** \u2014 At least one input source must be selected.")

    if "Price Violation" in modules:
        pv = form_data.get("Price Violation", {})
        if not pv.get("Domains"):
            errors.append("**Price Violation** \u2014 At least one domain is required.")
        if not _field_filled(pv, "Product URL List"):
            errors.append("**Price Violation** \u2014 Product URL list is required.")

    if "Store ID Crawls" in modules:
        if not form_data.get("Store ID Crawls", {}).get("Domains"):
            errors.append("**Store ID Crawls** \u2014 At least one domain is required.")

    if "Festive Sale Crawls" in modules:
        festive = form_data.get("Festive Sale Crawls", {})
        if festive.get("Crawl Type") == "Products + Trends Based" and not festive.get("Domains"):
            errors.append("**Festive Sale Crawls** \u2014 Domains required for Products + Trends Based type.")

    if not form_data.get("Final Alignment", {}).get("Client Core Objective"):
        errors.append("**Final Alignment** \u2014 Client Core Objective is required.")

    return errors


# ─────────────────────────────────────────────────────────────────────────────
# FORM TEMPLATES  (stored in form_templates.json next to app.py)
# ─────────────────────────────────────────────────────────────────────────────

_TEMPLATES_FILE = Path("form_templates.json")


def _load_form_templates() -> dict:
    if not _TEMPLATES_FILE.exists():
        return {}
    try:
        return json.loads(_TEMPLATES_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_form_template(name: str, snapshot: dict) -> None:
    tpls = _load_form_templates()
    tpls[name] = {"snapshot": snapshot, "saved_at": datetime.now().isoformat()}
    try:
        _TEMPLATES_FILE.write_text(json.dumps(tpls, indent=2, default=_json_default))
    except OSError:
        pass


def _delete_form_template(name: str) -> None:
    tpls = _load_form_templates()
    tpls.pop(name, None)
    try:
        _TEMPLATES_FILE.write_text(json.dumps(tpls, indent=2, default=_json_default))
    except OSError:
        pass


def _extract_domains_from_submission(form_data: dict) -> list[str]:
    """Collect all unique domain values from every module section of a form_data dict."""
    domains: list[str] = []
    for _section in form_data.values():
        if isinstance(_section, dict):
            _d = _section.get("Domains")
            if isinstance(_d, list):
                domains.extend(_d)
    return list(dict.fromkeys(d for d in domains if d))  # dedup, preserve order



# ─────────────────────────────────────────────────────────────────────────────
# LOCALSTORAGE SESSION SYNC  (bidirectional component — no URL exposure)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state["ls_write_token"]:
    _tok = st.session_state["ls_write_token"]
    st.session_state["ls_write_token"] = ""
    _session_mgr(action="write", token=_tok, key="ls_write")

elif st.session_state["ls_clear"]:
    st.session_state["ls_clear"] = False
    _session_mgr(action="clear", token="", key="ls_clear")

elif not st.session_state["authenticated"]:
    # Read the stored token from localStorage.  Returns None on the first render
    # (before the component JS has responded), then the token string on the next.
    _stored_token = _session_mgr(action="read", token="", key="ls_read")
    if _stored_token:
        _sess_user, _sess_display = _load_session(_stored_token)
        if _sess_user:
            st.session_state["authenticated"] = True
            st.session_state["current_user"]  = _sess_user
            st.session_state["display_name"]  = _sess_display
            st.rerun()
        else:
            # Token is invalid/expired — wipe it from localStorage
            st.session_state["ls_clear"]        = True
            st.session_state["_session_expired"] = True
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER  (auth-gated)
# ─────────────────────────────────────────────────────────────────────────────

if not st.session_state["authenticated"]:
    render_login()
else:
    page = st.session_state["page"]
    # Log page_view once per actual navigation (not on every Streamlit rerun)
    if page != st.session_state.get("analytics_last_page", ""):
        log_event(
            EVENT_PAGE_VIEW,
            st.session_state.get("current_user", ""),
            st.session_state.get("analytics_sid", ""),
            page,
        )
        st.session_state["analytics_last_page"] = page
    if page == "dashboard":
        from page_modules.dashboard import render_dashboard
        render_dashboard()
    elif page == "main":
        from page_modules.main_form import render_main_form
        render_main_form()
    elif page == "feasibility":
        from page_modules.feasibility import render_feasibility
        render_feasibility()
    elif page == "req_flow":
        from page_modules.req_flow import render_req_flow
        render_req_flow()
    elif page == "ops_map":
        from page_modules.ops_map import render_ops_map
        render_ops_map()
    elif page == "poc_guide":
        from page_modules.poc_guide import render_poc_guide
        render_poc_guide()
    elif page == "cost_calc":
        from page_modules.cost_calc import render_cost_calculator
        render_cost_calculator()
    elif page == "sub_history":
        from page_modules.sub_history import render_submission_history
        render_submission_history()
    elif page == "user_mgmt":
        _role = (get_user(st.session_state.get("current_user", "") or "") or {}).get("role", "")
        if _role == "admin":
            from page_modules.user_mgmt import render_user_management
            render_user_management()
        else:
            st.error("Access denied. This page is restricted to administrators.")
            st.session_state["page"] = "main"
            st.rerun()
    elif page == "rate_mgr":
        _role = (get_user(st.session_state.get("current_user", "") or "") or {}).get("role", "")
        if _role == "admin":
            from page_modules.rate_mgr import render_rate_manager
            render_rate_manager()
        else:
            st.error("Access denied. This page is restricted to administrators.")
            st.session_state["page"] = "main"
            st.rerun()
    elif page == "analytics":
        _role = (get_user(st.session_state.get("current_user", "") or "") or {}).get("role", "")
        if _role == "admin":
            from page_modules.analytics_page import render_analytics
            render_analytics()
        else:
            st.error("Access denied. This page is restricted to administrators.")
            st.session_state["page"] = "main"
            st.rerun()
    elif page == "ext_tools":
        st.markdown("""
        <div style="font-family:'Inter',sans-serif;padding-bottom:8px;">
            <div style="font-size:1.2rem;font-weight:700;color:#1f2937;margin-bottom:4px;">External Tools &amp; Dashboards</div>
            <div style="font-size:0.82rem;color:#9ca3af;">Quick access to external platforms used by the team.</div>
        </div>
        <hr style="border:none;border-top:1px solid #e5e7eb;margin:12px 0 24px 0;">
        """, unsafe_allow_html=True)

        _EXT_TOOLS = [
            {
                "icon": "📓",
                "name": "NotebookLM",
                "desc": "AI-powered notebook for research, summarisation, and Q&A on uploaded documents.",
                "url": "https://notebooklm.google.com/notebook/1657537a-75b5-4f77-9228-24613e4d78ea?authuser=0&pli=1",
                "label": "Open NotebookLM",
            },
            {
                "icon": "📊",
                "name": "Kibana Dashboard",
                "desc": "Client vs Site — 42Signals Crawl Insights. Live crawl monitoring and analytics.",
                "url": "https://kibana42s-internal.promptcloud.com/app/dashboards#/view/e31a5fb0-41c3-11f0-ae05-5901704110bc?_g=(filters:!(),refreshInterval:(pause:!t,value:0),time:(from:'2025-08-19T18:30:00.000Z',to:now))",
                "label": "Open Kibana",
            },
            {
                "icon": "📋",
                "name": "Client Requirement Sheet",
                "desc": "Master Google Sheet tracking all client requirements and project details.",
                "url": "https://docs.google.com/spreadsheets/d/16vondEsN55P-HibdIGgrtxFTg02cc_VmiKU0pNJVR-8/edit?gid=1545244868#gid=1545244868",
                "label": "Open Sheet",
            },
            {
                "icon": "📉",
                "name": "42S Daily Threshold Sheet",
                "desc": "Daily threshold tracking sheet for 42Signals crawl volume and data pipeline.",
                "url": "https://docs.google.com/spreadsheets/d/1pDjioZXBY0TtFBb-sSQvzMXbWdBl_6xwTlCHrWbrQAY/edit?gid=0#gid=0",
                "label": "Open Sheet",
            },
            {
                "icon": "🎯",
                "name": "Redmine Agile Board",
                "desc": "Team ticket tracker — active sprints, assignments, and burndown chart for the 42S project.",
                "url": "https://redmine.promptcloud.com/agile/board?set_filter=1&f%5B%5D=project_id&op%5Bproject_id%5D=%3D&v%5Bproject_id%5D%5B%5D=40733&f%5B%5D=assigned_to_id&op%5Bassigned_to_id%5D=%21&v%5Bassigned_to_id%5D%5B%5D=57565&v%5Bassigned_to_id%5D%5B%5D=97098&v%5Bassigned_to_id%5D%5B%5D=77277&v%5Bassigned_to_id%5D%5B%5D=5972&v%5Bassigned_to_id%5D%5B%5D=60148&v%5Bassigned_to_id%5D%5B%5D=96645&v%5Bassigned_to_id%5D%5B%5D=97240&v%5Bassigned_to_id%5D%5B%5D=96993&v%5Bassigned_to_id%5D%5B%5D=53918&v%5Bassigned_to_id%5D%5B%5D=97369&v%5Bassigned_to_id%5D%5B%5D=95248&v%5Bassigned_to_id%5D%5B%5D=85453&v%5Bassigned_to_id%5D%5B%5D=96640&v%5Bassigned_to_id%5D%5B%5D=84753&v%5Bassigned_to_id%5D%5B%5D=86398&f%5B%5D=status_id&op%5Bstatus_id%5D=%3D&f_status%5B%5D=1&f_status%5B%5D=8&f_status%5B%5D=7&f_status%5B%5D=21&f_status%5B%5D=20&f_status%5B%5D=2&f_status%5B%5D=25&f_status%5B%5D=74&f_status%5B%5D=4&c%5B%5D=day_in_state&c%5B%5D=parent&default_chart=burndown_chart&chart_unit=issues&group_by=assigned_to&color_base=priority",
                "label": "Open Redmine",
            },
            {
                "icon": "✍️",
                "name": "Redmine Ticket Creation",
                "desc": "To create any new tickets",
                "url": "https://redmine.promptcloud.com/issues/new",
                "label": "Open Redmine",
            },
        ]

        cols = st.columns(2, gap="large")
        for i, tool in enumerate(_EXT_TOOLS):
            with cols[i % 2]:
                st.markdown(f"""
                <div style="
                    background:#fff;
                    border:1px solid #e5e7eb;
                    border-radius:12px;
                    padding:20px 22px;
                    margin-bottom:16px;
                    box-shadow:0 1px 4px rgba(0,0,0,0.05);
                    font-family:'Inter',sans-serif;
                ">
                    <div style="font-size:1.6rem;margin-bottom:10px;">{tool["icon"]}</div>
                    <div style="font-size:0.95rem;font-weight:700;color:#1f2937;margin-bottom:6px;">{tool["name"]}</div>
                    <div style="font-size:0.8rem;color:#6b7280;line-height:1.55;margin-bottom:16px;">{tool["desc"]}</div>
                    <a href="{tool["url"]}" target="_blank" style="
                        display:inline-block;
                        background:linear-gradient(135deg,#1f2937 0%,#374151 100%);
                        color:#fff;
                        text-decoration:none;
                        font-size:0.78rem;
                        font-weight:600;
                        padding:8px 18px;
                        border-radius:6px;
                        letter-spacing:0.02em;
                        box-shadow:0 1px 4px rgba(0,0,0,0.12);
                    ">{tool["label"]} ↗</a>
                </div>
                """, unsafe_allow_html=True)
