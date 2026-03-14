import streamlit as st
import streamlit.components.v1 as components
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image  # type: ignore
from reportlab.lib import colors  # type: ignore
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
from reportlab.lib import pagesizes  # type: ignore
from reportlab.lib.units import inch  # type: ignore
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY  # type: ignore
from reportlab.lib.colors import HexColor  # type: ignore
from docx import Document
from io import BytesIO
from datetime import date, datetime, timedelta, timezone
import os
import base64
import html as _html_mod
import re
import time
import json
import uuid
from pathlib import Path
from credentials import verify_password, get_user, MAX_ATTEMPTS, LOCKOUT_SECONDS

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

try:
    from PIL import Image as _PIL_Image
    _page_icon = _PIL_Image.open("42slogo_top.png") if os.path.exists("42slogo_top.png") else "🔍"
except Exception:
    _page_icon = "🔍"

st.set_page_config(
    page_title="42Signals | Requirement Handling",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

LOGO_PATH = "42slogo.png"

# D3.js bundled locally so mind maps work on servers without internet access.
# Falls back to CDN if the file is missing (dev convenience only).
_D3_PATH = Path("d3.v7.min.js")
_D3_INLINE = (
    f"<script>{_D3_PATH.read_text()}</script>"
    if _D3_PATH.exists()
    else '{_D3_INLINE}'
)

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


def _save_session(username: str, display_name: str) -> None:
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


def _load_session():
    """Return (username, display_name) if a valid non-expired session exists, else (None, None)."""
    try:
        if not _SESSION_FILE.exists():
            return None, None
        data = json.loads(_SESSION_FILE.read_text())
        if datetime.now(timezone.utc) > datetime.fromisoformat(data["expires"]):
            _SESSION_FILE.unlink(missing_ok=True)
            return None, None
        return data["username"], data["display_name"]
    except (OSError, KeyError, ValueError):
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
header     { visibility: hidden; }

/* ── App background & global font ── */
.stApp {
    background-color: #f0f2f6;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* ── Main block container spacing ── */
.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 2.5rem !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e5e7eb;
    box-shadow: 2px 0 12px rgba(0,0,0,0.05);
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .element-container p,
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] .stCaption {
    color: #6b7280 !important;
}
section[data-testid="stSidebar"] hr {
    border-color: #f3f4f6 !important;
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
section[data-testid="stSidebar"] .stButton > button:focus:not(:active) {
    box-shadow: none !important;
    outline: none !important;
}

/* ── Sidebar expander ── */
section[data-testid="stSidebar"] details summary p {
    color: #374151 !important;
    font-weight: 600 !important;
}

/* ── Text inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > textarea,
.stNumberInput > div > div > input {
    border-radius: 8px !important;
    border: 1.5px solid #e5e7eb !important;
    background: #ffffff !important;
    font-size: 0.875rem !important;
    color: #1f2937 !important;
    transition: border-color 0.2s, box-shadow 0.2s;
    padding: 8px 12px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > textarea:focus,
.stNumberInput > div > div > input:focus {
    border-color: #374151 !important;
    box-shadow: 0 0 0 3px rgba(55,65,81,0.12) !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder,
.stTextArea > div > textarea::placeholder {
    color: #b0b7c3 !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    border-radius: 8px !important;
    border: 1.5px solid #e5e7eb !important;
    background: white !important;
    font-size: 0.875rem !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.stSelectbox > div > div:focus-within {
    border-color: #374151 !important;
    box-shadow: 0 0 0 3px rgba(55,65,81,0.12) !important;
}

/* ── Multiselect ── */
.stMultiSelect > div > div {
    border-radius: 8px !important;
    border: 1.5px solid #e5e7eb !important;
    background: white !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.stMultiSelect > div > div:focus-within {
    border-color: #374151 !important;
    box-shadow: 0 0 0 3px rgba(55,65,81,0.12) !important;
}

/* ── Primary button ── */
div[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1f2937 0%, #374151 100%) !important;
    color: white !important;
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
    box-shadow: 0 8px 24px rgba(0,0,0,0.2) !important;
    transform: translateY(-1px) !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #1f2937 0%, #374151 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 12px 0 !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(31,41,55,0.22) !important;
}
.stDownloadButton > button:hover {
    background: linear-gradient(135deg, #111827 0%, #1f2937 100%) !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2) !important;
    transform: translateY(-1px) !important;
}

/* ── Expander (main area) ── */
details > summary > div > p {
    font-weight: 600 !important;
    color: #1f2937 !important;
    font-size: 0.875rem !important;
}
details {
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
    background: white !important;
    margin-bottom: 10px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    transition: box-shadow 0.2s !important;
}
details[open] {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
}

/* ── Radio ── */
.stRadio > div { gap: 8px !important; }
.stRadio > div > label { font-size: 0.875rem !important; }

/* ── Date input ── */
.stDateInput > div > div > input {
    border-radius: 8px !important;
    border: 1.5px solid #e5e7eb !important;
    font-size: 0.875rem !important;
    padding: 8px 12px !important;
}

/* ── Labels ── */
.stTextInput label, .stTextArea label, .stSelectbox label,
.stMultiSelect label, .stNumberInput label, .stDateInput label {
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    color: #374151 !important;
    letter-spacing: 0.01em !important;
}

/* ── Dividers ── */
hr {
    border: none !important;
    border-top: 1px solid #e5e7eb !important;
    margin: 18px 0 !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #374151 !important; }

/* ── Success/warning/error alerts ── */
.stAlert {
    border-radius: 10px !important;
    font-size: 0.875rem !important;
}

/* ── Markdown bold ── */
.stMarkdown strong { color: #111827; font-weight: 600; }

/* ── Tag chips in multiselect ── */
.stMultiSelect span[data-baseweb="tag"] {
    background-color: #f1f5f9 !important;
    border-radius: 6px !important;
    color: #1f2937 !important;
    font-size: 0.78rem !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

if "page"             not in st.session_state: st.session_state["page"]             = "main"
if "authenticated"    not in st.session_state: st.session_state["authenticated"]    = False
if "current_user"     not in st.session_state: st.session_state["current_user"]     = None
if "display_name"     not in st.session_state: st.session_state["display_name"]     = None
if "failed_attempts"  not in st.session_state: st.session_state["failed_attempts"]  = 0
if "lockout_until"    not in st.session_state: st.session_state["lockout_until"]    = 0.0

# Auto-restore session from disk on first load (persistent login)
if not st.session_state["authenticated"]:
    _sess_user, _sess_display = _load_session()
    if _sess_user:
        st.session_state["authenticated"] = True
        st.session_state["current_user"]  = _sess_user
        st.session_state["display_name"]  = _sess_display

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
            <div style="font-weight:700;color:#15803d;font-size:0.95rem;letter-spacing:0.01em;">{message}</div>
            {"" if not sub else f'<div style="color:#166534;font-size:0.8rem;margin-top:4px;opacity:0.85;">{sub}</div>'}
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
        <div style="font-size: 1.65rem; font-weight: 700; color: #0f172a; line-height: 1.2; letter-spacing: -0.025em; font-family: 'Inter', sans-serif;">{title}</div>
        {"" if not subtitle else f'<div style="font-size:0.875rem;color:#6b7280;margin-top:7px;font-weight:400;line-height:1.5;">{subtitle}</div>'}
        <div style="height:3px;background:linear-gradient(90deg,#1f2937 0%,#6b7280 55%,transparent 100%);border-radius:2px;margin-top:16px;"></div>
    </div>
    """, unsafe_allow_html=True)


def info_row(label, value):
    # _h() escapes user-supplied value to prevent XSS via unsafe_allow_html
    st.markdown(f"""
    <div style="padding: 8px 10px 7px 10px; border-bottom: 1px solid #f3f4f6;">
        <div style="color:#94a3b8; font-size:0.66rem; text-transform:uppercase; letter-spacing:0.08em; font-weight:700; margin-bottom:3px; font-family:'Inter',sans-serif;">{_h(label)}</div>
        <div style="color:#111827; font-size:0.875rem; font-weight:500; font-family:'Inter',sans-serif;">{_h(value)}</div>
    </div>
    """, unsafe_allow_html=True)


def frequency_selector(label, key_prefix):
    col1, col2 = st.columns([1, 1])
    with col1:
        freq = st.selectbox(f"{label} — Frequency", ["Daily", "Hourly"], key=f"{key_prefix}_freq")
    hourly_count = None
    if freq == "Hourly":
        with col2:
            hourly_count = st.number_input("Times / day", min_value=1, key=f"{key_prefix}_hourly")
    return freq, hourly_count


def calculate_risk(freq_string, volume_string):
    if not freq_string or not volume_string:
        return None
    freq_score = 1
    if "Hourly" in freq_string:
        try:
            times = int(freq_string.split("(")[1].split()[0])
            freq_score = 3 if times > 6 else 2
        except:
            freq_score = 2
    vol_score = 1
    try:
        volume = int(str(volume_string).replace(",", ""))
        vol_score = 1 if volume <= 10_000 else (2 if volume <= 50_000 else 3)
    except:
        pass
    total = freq_score + vol_score
    return "LOW" if total <= 2 else ("MODERATE" if total <= 4 else "CRITICAL")


PREDEFINED_DOMAINS = ["swiggy.com", "blinkit.com", "zepto.com", "amazon.in", "flipkart.in"]

def domain_selector(label, key_prefix):
    st.markdown(f"**{label}**")
    col1, col2 = st.columns([3, 1])
    with col1:
        selected = st.multiselect(label, PREDEFINED_DOMAINS, key=f"{key_prefix}_domains", label_visibility="collapsed")
    with col2:
        custom = st.text_input("Custom", placeholder="+ Add domain", key=f"{key_prefix}_custom_domain", label_visibility="collapsed")
    domains = selected + ([custom.strip()] if custom.strip() else [])
    return ", ".join(domains) if domains else ""


def validate_required(client_name):
    if not client_name:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #fffbeb 0%, #fef9ec 100%);
            border: 1px solid #fcd34d;
            border-left: 4px solid #f59e0b;
            border-radius: 10px;
            padding: 13px 18px;
            color: #78350f;
            font-size: 0.875rem;
            margin: 6px 0 22px 0;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 1px 4px rgba(245,158,11,0.12);
            font-family: 'Inter', sans-serif;
        ">
            <span style="font-size:1.1rem;">⚠️</span>
            <span>Please enter a <strong>Client Name</strong> above to unlock the full form.</span>
        </div>
        """, unsafe_allow_html=True)
        st.stop()


def render_summary(data):
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 18px;
        box-shadow: 0 4px 12px rgba(31,41,55,0.2);
    ">
        <div style="font-size: 0.9rem; font-weight: 700; color: #ffffff; letter-spacing: 0.02em; font-family:'Inter',sans-serif;">📋 Live Summary</div>
        <div style="font-size: 0.73rem; color: #9ca3af; margin-top: 3px; font-family:'Inter',sans-serif;">Auto-updates as you fill the form</div>
    </div>
    """, unsafe_allow_html=True)

    has_content = any(
        any(v not in ["", None, [], {}] for v in c.values())
        for c in data.values()
    )

    if not has_content:
        st.markdown("""
        <div style="
            text-align:center; padding:44px 20px;
            background:white; border-radius:12px; border:2px dashed #e5e7eb;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        ">
            <div style="font-size:2.4rem; margin-bottom:12px; opacity:0.55;">📝</div>
            <div style="font-size:0.875rem; font-weight:600; color:#64748b; margin-bottom:5px; font-family:'Inter',sans-serif;">Nothing here yet</div>
            <div style="font-size:0.78rem; color:#94a3b8; line-height:1.6; font-family:'Inter',sans-serif;">
                Start filling the form<br>to preview a summary here
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    for section, content in data.items():
        filled = {k: v for k, v in content.items() if v not in ["", None, [], {}]}
        if not filled:
            continue
        with st.expander(f"**{section}**", expanded=True):
            for k, v in filled.items():
                info_row(k, v)

    if "Products + Trends" in data:
        pt = data["Products + Trends"]
        risk = calculate_risk(pt.get("Overall Frequency"), pt.get("Expected Volume"))
        if risk:
            st.markdown("---")
            st.markdown("**⚡ Crawl Load Risk**")
            if risk == "LOW":
                st.success("**LOW** — Infrastructure load is safe.")
            elif risk == "MODERATE":
                st.warning("**MODERATE** — Monitor scaling & proxy usage.")
            else:
                st.error("**CRITICAL** — High infra saturation risk.")


def generate_pdf(data, client_name):
    """Build a formatted PDF from form_data. All user values are XML-escaped
    before being passed to ReportLab Paragraph to prevent markup injection."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=pagesizes.A4,
        topMargin=0.5*inch, bottomMargin=0.6*inch,
        leftMargin=0.6*inch, rightMargin=0.6*inch,
    )
    styles = getSampleStyleSheet()
    el = []

    title_s = ParagraphStyle("T", parent=styles["Heading1"], fontSize=20, textColor=HexColor("#1f2937"),
                              alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=3)
    sub_s   = ParagraphStyle("S", parent=styles["Normal"], fontSize=9, textColor=HexColor("#6b7280"),
                              alignment=TA_CENTER, spaceAfter=16)
    sec_s   = ParagraphStyle("H", parent=styles["Heading2"], fontSize=10.5, textColor=HexColor("#1f2937"),
                              backColor=HexColor("#f3f4f6"), leftIndent=8, fontName="Helvetica-Bold",
                              spaceBefore=6, spaceAfter=4)
    key_s   = ParagraphStyle("K", parent=styles["Normal"], fontSize=8, textColor=HexColor("#6b7280"),
                              fontName="Helvetica-Bold")
    val_s   = ParagraphStyle("V", parent=styles["Normal"], fontSize=9, textColor=HexColor("#111827"),
                              wordWrap="CJK", alignment=TA_JUSTIFY)

    try:
        if os.path.exists(LOGO_PATH):
            logo = Image(LOGO_PATH, width=0.9*inch, height=0.72*inch)
            hdr = Table([[logo, Paragraph("<b>Requirement Handling Form</b>", title_s)]],
                        colWidths=[1.1*inch, 5.9*inch])
            hdr.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]))
            el.append(hdr)
        else:
            el.append(Paragraph("<b>Requirement Handling Form</b>", title_s))
    except Exception:
        el.append(Paragraph("<b>Requirement Handling Form</b>", title_s))

    # Escape client_name before embedding in ReportLab XML
    safe_client = _html_mod.escape(str(client_name), quote=True)
    el.append(Paragraph(
        f"Client: {safe_client} &nbsp;|&nbsp; Generated: {date.today().strftime('%d %b %Y')}",
        sub_s
    ))
    el.append(Spacer(1, 0.1*inch))

    row_colors = [HexColor("#f9fafb"), HexColor("#ffffff")]
    ci = 0
    for section, content in data.items():
        el.append(Paragraph(f"  {_html_mod.escape(str(section))}", sec_s))
        el.append(Spacer(1, 0.04*inch))
        rows = [
            # Escape both key and value — ReportLab Paragraph parses XML-like tags
            [Paragraph(_html_mod.escape(str(k)), key_s),
             Paragraph(_html_mod.escape(str(v)) if v else "—", val_s)]
            for k, v in content.items()
        ]
        if rows:
            t = Table(rows, colWidths=[1.9*inch, 4.1*inch])
            t.setStyle(TableStyle([
                ("GRID",         (0, 0), (-1, -1), 0.4, HexColor("#e5e7eb")),
                ("VALIGN",       (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND",   (0, 0), (-1, -1), row_colors[ci % 2]),
                ("BACKGROUND",   (0, 0), (0, -1),  HexColor("#f3f4f6")),
                ("TOPPADDING",   (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
                ("LEFTPADDING",  (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]))
            el.append(t)
            el.append(Spacer(1, 0.14*inch))
            ci += 1

    doc.build(el)
    buffer.seek(0)
    return buffer


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

    /* ── Login inputs ── */
    .stTextInput > div > div > input {
        background: #f8fafc !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 10px !important;
        font-size: 0.9rem !important;
        color: #0f172a !important;
        padding: 10px 14px !important;
        transition: all .2s !important;
    }
    .stTextInput > div > div > input:focus {
        background: #ffffff !important;
        border-color: #374151 !important;
        box-shadow: 0 0 0 3px rgba(31,41,55,.1) !important;
    }
    .stTextInput > div > div > input::placeholder { color: #94a3b8 !important; }
    .stTextInput label {
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        color: #374151 !important;
        letter-spacing: .04em !important;
        text-transform: uppercase !important;
    }

    /* ── Sign-in button ── */
    [data-testid="stMainBlockContainer"] .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1f2937 0%, #374151 100%) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 11px !important;
        padding: 14px 0 !important;
        font-size: .95rem !important;
        font-weight: 700 !important;
        letter-spacing: .035em !important;
        box-shadow: 0 4px 18px rgba(31,41,55,.38) !important;
        transition: all .22s ease !important;
    }
    [data-testid="stMainBlockContainer"] .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%) !important;
        box-shadow: 0 10px 30px rgba(0,0,0,.35) !important;
        transform: translateY(-2px) !important;
    }
    [data-testid="stMainBlockContainer"] .stButton > button[kind="primary"]:active {
        transform: translateY(0) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,.25) !important;
    }

    /* ── Streamlit warning tweak ── */
    .stAlert { border-radius: 10px !important; font-size: .85rem !important; }
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

    st.markdown(f"""<div style="text-align:center;padding:36px 32px 24px 32px;margin:0 -32px;background:linear-gradient(180deg,#f8fafc 0%,#ffffff 100%);border-bottom:1px solid #f1f5f9;">
{logo_html}
<div style="font-size:1.55rem;font-weight:800;color:#0f172a;letter-spacing:-.035em;line-height:1.15;font-family:'Inter',sans-serif;">Welcome back</div>
<div style="font-size:0.875rem;color:#64748b;margin-top:9px;font-family:'Inter',sans-serif;line-height:1.55;font-weight:400;">Sign in to access the 42Signals<br>Requirement Handling portal</div>
<div style="display:flex;justify-content:center;gap:8px;margin-top:18px;flex-wrap:wrap;">
<span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:20px;padding:4px 12px;font-size:0.7rem;color:#475569;font-weight:600;font-family:'Inter',sans-serif;">&#128203; Forms</span>
<span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:20px;padding:4px 12px;font-size:0.7rem;color:#475569;font-weight:600;font-family:'Inter',sans-serif;">&#128202; Feasibility</span>
<span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:20px;padding:4px 12px;font-size:0.7rem;color:#475569;font-weight:600;font-family:'Inter',sans-serif;">&#128256; Workflows</span>
</div>
</div>""", unsafe_allow_html=True)

    # ── Lockout check ────────────────────────────────────────────────────
    now = time.time()
    locked    = st.session_state["lockout_until"] > now
    remaining = int(st.session_state["lockout_until"] - now)

    if locked:
        st.markdown(f"""<div style="background:linear-gradient(135deg,#fef2f2,#fee2e2);border:1px solid #fca5a5;border-left:4px solid #dc2626;border-radius:12px;padding:15px 18px;margin-bottom:4px;color:#7f1d1d;font-family:'Inter',sans-serif;font-size:.875rem;display:flex;align-items:center;gap:12px;">
<span style="font-size:1.5rem;flex-shrink:0;">&#128274;</span>
<div><div style="font-weight:700;margin-bottom:3px;">Account temporarily locked</div>
<div style="opacity:.8;">Too many failed attempts.<br>Try again in <strong>{remaining // 60}m {remaining % 60}s</strong>.</div>
</div></div>""", unsafe_allow_html=True)
        st.markdown("""<div style="text-align:center;padding:20px 0 6px 0;font-size:.72rem;color:#94a3b8;font-family:'Inter',sans-serif;">Access restricted to authorised users only &middot; 42Signals &copy; 2026</div>""", unsafe_allow_html=True)
        return

    # ── Form fields ──────────────────────────────────────────────────────
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

    # Failed-attempt inline alert
    if st.session_state["failed_attempts"] > 0:
        left = MAX_ATTEMPTS - st.session_state["failed_attempts"]
        st.markdown(f"""<div style="background:linear-gradient(135deg,#fffbeb,#fef9ec);border:1px solid #fcd34d;border-left:4px solid #f59e0b;border-radius:10px;padding:11px 15px;color:#78350f;font-size:.82rem;margin-top:4px;font-family:'Inter',sans-serif;display:flex;align-items:center;gap:9px;">
<span style="font-size:1rem;flex-shrink:0;">&#9888;&#65039;</span>
<span>Incorrect credentials &mdash; <strong>{left} attempt{'s' if left != 1 else ''}</strong> left before lockout.</span>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    if st.button("Sign In  →", type="primary", use_container_width=True, key="login_submit"):
        if not username or not password:
            st.warning("Please enter both username and password.")
        elif verify_password(username, password):
            user = get_user(username)
            clean_user = username.strip().lower()
            st.session_state["authenticated"]   = True
            st.session_state["current_user"]    = clean_user
            st.session_state["display_name"]    = user["display_name"]
            st.session_state["failed_attempts"] = 0
            st.session_state["lockout_until"]   = 0.0
            _save_session(clean_user, user["display_name"])
            st.rerun()
        else:
            st.session_state["failed_attempts"] += 1
            if st.session_state["failed_attempts"] >= MAX_ATTEMPTS:
                st.session_state["lockout_until"] = time.time() + LOCKOUT_SECONDS
                st.session_state["failed_attempts"] = 0
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

    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:0 0 14px 0;">', unsafe_allow_html=True)

    # Section label
    st.markdown('<div style="color:#b0b7c3;font-size:0.67rem;text-transform:uppercase;letter-spacing:0.14em;padding:0 6px 10px 6px;font-weight:600;font-family:\'Inter\',sans-serif;">Navigation</div>', unsafe_allow_html=True)

    # Nav items — SVG icons, consistent active/inactive styling
    _NAV = {
        "main": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/></svg>',
            "New Requirement Form",
        ),
        "feasibility": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 20h18M7 20V12M12 20V5M17 20v-8"/></svg>',
            "Feasibility Assessment",
        ),
        "req_flow": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="12" r="2.5"/><circle cx="19" cy="12" r="2.5"/><path d="M7.5 12h9"/><path d="M14.5 9l3 3-3 3"/></svg>',
            "New Requirement Flow",
        ),
        "ops_map": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
            "Day-to-Day Ops Map",
        ),
        "poc_guide": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
            "Task POC Guide",
        ),
    }

    for key, (svg, label) in _NAV.items():
        active = st.session_state["page"] == key
        if active:
            st.markdown(
                f"""<div style="background:linear-gradient(135deg,#f1f5f9 0%,#e8ecf0 100%);border:1px solid #dde3ea;border-left:3px solid #1f2937;border-radius:8px;padding:9px 12px;color:#111827;font-size:0.83rem;font-weight:600;margin-bottom:3px;display:flex;align-items:center;gap:9px;font-family:'Inter',sans-serif;white-space:nowrap;box-shadow:0 1px 3px rgba(0,0,0,0.05);">{svg}&nbsp;{label}</div>""",
                unsafe_allow_html=True,
            )
        else:
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state["page"] = key
                st.rerun()

    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:14px 0 10px 0;">', unsafe_allow_html=True)

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
            font-size:0.8rem; font-weight:700; color:#fff; flex-shrink:0;
        ">{_h(display_name[:1].upper()) if display_name else "?"}</div>
        <div>
            <div style="font-size:0.82rem;font-weight:600;color:#111827;">{_h(display_name)}</div>
            <div style="font-size:0.7rem;color:#9ca3af;margin-top:1px;">Signed in</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Sign Out", key="logout_btn", use_container_width=True):
        _clear_session()
        st.session_state["authenticated"]   = False
        st.session_state["current_user"]    = None
        st.session_state["display_name"]    = None
        st.session_state["failed_attempts"] = 0
        st.session_state["lockout_until"]   = 0.0
        st.session_state["page"]            = "main"
        st.rerun()

    st.markdown("""
    <div style="text-align:center; padding:6px 0 12px 0;">
        <div style="color:#c9d0d9; font-size:0.68rem; font-family:'Inter',sans-serif; letter-spacing:0.04em;">v1.0 &nbsp;·&nbsp; 42Signals &nbsp;·&nbsp; 2026</div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: New Requirement Form
# ─────────────────────────────────────────────────────────────────────────────

def render_main_form():
    page_title(
        "New Requirement Form",
        "Capture complete client crawl requirements for project planning and scoping."
    )

    left, right = st.columns([2, 1], gap="large")
    form_data = {}

    with left:

        # ── 1. Client Information ──────────────────────────────────────────
        section_header("👤", "1. Client Information")

        c1, c2 = st.columns([2, 1])
        with c1:
            client_name = st.text_input("Client Name *", placeholder="e.g., Unilever India", key="form_client_name")
        with c2:
            priority = st.selectbox("Priority Level", ["High", "Medium", "Low"], key="form_priority")

        c3, c4 = st.columns(2)
        with c3:
            completion_date = st.date_input("Expected Completion Date", key="form_completion_date")
        with c4:
            expected_market = st.text_input("Target Market / Geography", placeholder="e.g., India, Southeast Asia", key="form_target_market")

        form_data["Client Information"] = {
            "Client Name":            client_name,
            "Priority Level":         priority,
            "Expected Completion":    str(completion_date),
            "Target Market":          expected_market,
        }

        validate_required(client_name)

        # ── 2. Modules to Crawl ───────────────────────────────────────────
        section_header("🧩", "2. Modules to Crawl")

        modules = st.multiselect(
            "Select the modules required for this client",
            ["Products + Trends", "SOS (Search on Site)", "Reviews",
             "Price Violation", "Store ID Crawls", "Festive Sale Crawls"],
            key="form_modules",
        )
        form_data["Modules Selected"] = {
            "Selected Modules": ", ".join(modules) if modules else "None"
        }

        # ── 3. Products + Trends ──────────────────────────────────────────
        if "Products + Trends" in modules:
            section_header("📦", "3. Products + Trends Module")
            pt = {}

            st.markdown("**Crawl Type**")
            crawl_type = st.radio(
                "crawl_type", ["Category-based (Category_ES)", "Input-based (URL/Input driven)"],
                label_visibility="collapsed", horizontal=True, key="pt_crawl_type"
            )
            pt["Crawl Type"] = crawl_type

            st.markdown("**Domains**")
            pt["Domains"] = domain_selector("Select Domains", "pt")

            st.markdown("**Overall Crawl Frequency**")
            freq, hourly = frequency_selector("Overall", "pt_overall")
            pt["Overall Frequency"] = f"{freq} ({hourly} times/day)" if hourly else freq

            if crawl_type == "Category-based (Category_ES)":
                st.markdown("---")
                st.markdown("##### A) Category_ES Configuration")

                st.markdown("**Index Frequency**")
                c1, c2 = st.columns(2)
                with c1:
                    pf, ph = frequency_selector("Products Index", "pt_prod")
                    pt["Products Index Frequency"] = f"{pf} ({ph} times/day)" if ph else pf
                with c2:
                    tf, th = frequency_selector("Trends Index", "pt_trend")
                    pt["Trends Index Frequency"] = f"{tf} ({th} times/day)" if th else tf

                if ph or th:
                    pt["Hourly Crawl Timings"] = st.text_input(
                        "Specify crawl hours", placeholder="e.g., 9 AM, 12 PM, 3 PM, 6 PM",
                        key="pt_hourly_timings"
                    )

                st.markdown("**Trends Configuration**")
                c1, c2 = st.columns(2)
                with c1:
                    pt["No of RSS Crawls"] = st.number_input("Number of RSS crawls into Trends", min_value=0, key="pt_rss_crawls")
                with c2:
                    pt["Expected Data Push Volume"] = st.text_input("Products volume to push into Trends", key="pt_data_push_volume")

                st.markdown("**Category Details**")
                pt["Sample Category List"] = st.text_area(
                    "Sample Category List", placeholder="e.g., Electronics, Fashion, Home & Kitchen",
                    key="pt_sample_category_list"
                )
                cat_status = st.radio("Is final category list available?", ["Yes", "No"], key="pt_category_status", horizontal=True)
                if cat_status == "Yes":
                    pt["Client Category Sheet Link"] = st.text_input("Category Sheet Link", key="pt_category_sheet_link")
                else:
                    pt["Client Category Expected Date"] = str(st.date_input("Expected date for category list", key="pt_category_expected_date"))

            else:
                st.markdown("---")
                st.markdown("##### B) Input-Based Configuration")

                st.markdown("**Products Crawl**")
                need_product = st.radio("Products crawl required?", ["Yes", "No"], key="pt_input_products_needed", horizontal=True)
                pt["Products Crawl Needed"] = need_product
                if need_product == "Yes":
                    pf, ph = frequency_selector("Products Crawl", "pt_input_prod")
                    pt["Products Crawl Frequency"] = f"{pf} ({ph} times/day)" if ph else pf

                st.markdown("**Trends Crawl**")
                tf, th = frequency_selector("Trends Crawl", "pt_input_trend")
                pt["Trends Crawl Frequency"] = f"{tf} ({th} times/day)" if th else tf
                if th:
                    pt["Trends Hourly Timings"] = st.text_input(
                        "Specify timing if hourly", placeholder="e.g., 10 AM, 2 PM, 6 PM, 10 PM",
                        key="pt_trends_hourly_timings"
                    )

                st.markdown("**Inputs**")
                pt["Sample Input URLs"] = st.text_area("Sample Input URLs", placeholder="If client inputs not available, provide testing URLs", key="pt_sample_input_urls")
                inp_status = st.radio("Client Inputs Status", ["Not Yet Provided", "Available — See Link Below"], key="pt_inputs_status", horizontal=True)
                if inp_status == "Not Yet Provided":
                    pt["Client Inputs Expected Date"] = str(st.date_input("Expected delivery date for inputs", key="pt_inputs_expected_date"))
                else:
                    pt["Client Inputs Sheet Link"] = st.text_input("Sheet Link with client inputs", key="pt_inputs_sheet_link")

                st.markdown("**Location Dependency**")
                is_pincode = st.radio("Pincode / Zipcode based?", ["Yes", "No"], key="pt_pincode_based", horizontal=True)
                pt["Pincode Based"] = is_pincode
                if is_pincode == "Yes":
                    c1, c2 = st.columns(2)
                    with c1:
                        pt["Sample Pincode"] = st.text_input("Sample Pincode", placeholder="e.g., 110001, 560001", key="pt_sample_pincode")
                    with c2:
                        pt["Client Pincode List Link"] = st.text_input("Pincode list link (if available)", key="pt_pincode_list_link")

                st.markdown("**Volume & Output**")
                c1, c2 = st.columns(2)
                with c1:
                    pt["Expected Volume"] = st.text_input("Expected Volume / day", placeholder="e.g., 50,000 products", key="pt_expected_volume")
                with c2:
                    pt["Screenshot Required"] = st.radio("Screenshot Required?", ["Yes", "No"], key="pt_screenshot", horizontal=True)

            st.markdown("**Specific Fields to Capture**")
            pt["Specific Fields"] = st.text_area(
                "Any additional fields to extract",
                placeholder="e.g., seller name, discount %, stock status, rating breakdown, delivery time",
                key="pt_specific_fields",
            )
            form_data["Products + Trends"] = pt

        # ── 4. SOS Module ─────────────────────────────────────────────────
        if "SOS (Search on Site)" in modules:
            section_header("🔍", "4. SOS (Search On Site) Module")
            sos = {}

            st.markdown("**Keywords**")
            c1, c2 = st.columns(2)
            with c1:
                sos["No. of Keywords"] = st.number_input("Number of Keywords", min_value=0, key="sos_keyword_count")
            with c2:
                keywords_source = st.radio("Keywords source", ["Client Provided", "Provide Sample for Testing"], key="sos_keywords_source")
            if keywords_source == "Client Provided":
                sos["SOS Keywords Sheet Link"] = st.text_input("Link to client keywords sheet", key="sos_keywords_sheet_link")
            else:
                sos["Sample Keywords"] = st.text_area("Sample keywords for testing", placeholder="e.g., laptop, shoes, home appliances", key="sos_sample_keywords")

            st.markdown("**Domains**")
            sos["Domains"] = domain_selector("Select Domains", "sos")

            c1, c2 = st.columns(2)
            with c1:
                sos["Zipcode Required"] = st.radio("Zipcode required?", ["Yes", "No"], horizontal=True, key="sos_zipcode_required")
            if sos["Zipcode Required"] == "Yes":
                sos["Pincode List"] = st.text_area("Pincode list (comma-separated or sheet link)", placeholder="e.g., 110001, 560001, 400001", key="sos_pincode_list")

            st.markdown("**Crawl Depth**")
            c1, c2 = st.columns(2)
            with c1:
                sos["No. of Pages per Keyword"] = st.number_input("Pages per keyword", min_value=1, value=1, key="sos_pages")
            with c2:
                sos["No. of Products per Keyword"] = st.number_input("Products per keyword", min_value=1, value=10, key="sos_products")

            st.markdown("**Crawl Frequency**")
            freq, hourly = frequency_selector("SOS Crawl", "sos")
            sos["Frequency"] = f"{freq} ({hourly} times/day)" if hourly else freq
            form_data["SOS (Search on Site)"] = sos

        # ── 5. Reviews Module ─────────────────────────────────────────────
        if "Reviews" in modules:
            section_header("⭐", "5. Reviews Module")
            rev = {}

            st.markdown("**Domains**")
            rev["Domains"] = domain_selector("Select Domains", "reviews")

            st.markdown("**Review Source Type**")
            rev["Input Sources"] = st.multiselect(
                "Where to pull review inputs from",
                ["From Products Index", "From Trends Index", "From Review Input URLs", "Category-based Reviews Crawl"],
                key="rev_source",
            )
            if "From Review Input URLs" in rev["Input Sources"]:
                rev["Sample Review URLs"] = st.text_area("Sample review page URLs", placeholder="Provide product review page URLs", key="rev_sample_urls")

            st.markdown("**Frequency**")
            c1, c2 = st.columns(2)
            with c1:
                freq, hourly = frequency_selector("Reviews Crawl", "rev")
                rev["Frequency"] = f"{freq} ({hourly} times/day)" if hourly else freq
            if hourly:
                with c2:
                    rev["Hourly Timings"] = st.text_input("Timing if hourly", placeholder="e.g., 8 AM, 12 PM, 6 PM, 10 PM", key="rev_hourly_timings")
            form_data["Reviews"] = rev

        # ── 6. Price Violation Module ─────────────────────────────────────
        if "Price Violation" in modules:
            section_header("💰", "6. Price Violation Module")
            pv = {}

            st.markdown("**Domains**")
            pv["Domains"] = domain_selector("Select Domains", "pv")

            st.markdown("**Frequency**")
            freq, hourly = frequency_selector("Price Violation Crawl", "pv")
            pv["Frequency"] = f"{freq} ({hourly} times/day)" if hourly else freq

            st.markdown("**Inputs**")
            pv["Product URL List"] = st.text_area("Product URL list to monitor", placeholder="Sample product URLs", key="pv_product_url_list")

            c1, c2 = st.columns(2)
            with c1:
                pv["Zipcode Required"] = st.radio("Zipcode required?", ["Yes", "No"], horizontal=True, key="pv_zipcode_required")
            if pv["Zipcode Required"] == "Yes":
                pv["Zipcode List"] = st.text_area("Zipcode list", placeholder="e.g., 110001, 560001, 400001", key="pv_zipcode_list")

            pv["Price Violation Condition"] = st.text_area(
                "Violation condition / rule",
                placeholder="e.g., MRP > X, Discount < Y%, price diff > 15%",
                key="pv_violation_condition"
            )
            c1, c2 = st.columns(2)
            with c1:
                pv["Sample Inputs Sheet Link"] = st.text_input("Sample inputs sheet link", placeholder="Link to sample data", key="pv_sample_inputs_link")
            with c2:
                pv["Screenshot Required"] = st.radio("Screenshot Required?", ["Yes", "No"], key="pv_screenshot", horizontal=True)
            form_data["Price Violation"] = pv

        # ── 7. Store ID Crawls ────────────────────────────────────────────
        if "Store ID Crawls" in modules:
            section_header("🏪", "7. Store ID Crawl")
            storeid = {}

            st.markdown("**Domains**")
            storeid["Domains"] = domain_selector("Select Domains", "storeid")

            c1, c2 = st.columns(2)
            with c1:
                storeid["Specific Location Required"] = st.radio(
                    "Specific store locations needed?", ["No", "Yes"], horizontal=True, key="storeid_location"
                )
            if storeid["Specific Location Required"] == "Yes":
                storeid["Location Details"] = st.text_area("Location details", placeholder="e.g., Bangalore, Mumbai, Delhi", key="storeid_location_details")

            storeid_status = st.radio("Specific Pincode list available?", ["Yes", "No"], horizontal=True, key="storeid_list_status")
            if storeid_status == "Yes":
                storeid["Specific Pincode List Link"] = st.text_input("Pincode list link", key="storeid_pincode_list_link")
            form_data["Store ID Crawls"] = storeid

        # ── 8. Festive Sale Crawls ────────────────────────────────────────
        if "Festive Sale Crawls" in modules:
            section_header("🎉", "8. Festive Sale Crawls")
            festive = {}

            st.markdown("**Crawl Type**")
            festive["Crawl Type"] = st.radio(
                "festive_type",
                ["Products + Trends Based", "SOS Type", "Category URL Based"],
                key="festive_type", horizontal=True, label_visibility="collapsed",
            )
            if festive["Crawl Type"] == "Products + Trends Based":
                festive["Domains"] = domain_selector("Select Domains", "festive")
            elif festive["Crawl Type"] == "Category URL Based":
                festive["Category URL List"] = st.text_area("Category URLs", placeholder="Provide category URLs for festive crawl", key="festive_category_urls")

            st.markdown("**Schedule**")
            c1, c2, c3 = st.columns(3)
            with c1:
                festive["Frequency Per Day"] = st.number_input("Frequency / day", min_value=1, value=1, key="festive_freq")
            with c2:
                festive["Start Date"] = str(st.date_input("Start Date", key="festive_start"))
            with c3:
                festive["End Date"] = str(st.date_input("End Date", key="festive_end"))
            form_data["Festive Sale Crawls"] = festive

        # ── 9. Final Alignment ────────────────────────────────────────────
        section_header("🎯", "9. Final Alignment")
        form_data["Final Alignment"] = {
            "Client Core Objective": st.text_area(
                "What is the client's core objective?",
                placeholder="e.g., Market gap analysis, brand monitoring, competitive pricing intelligence, demand trends…",
                key="final_objective",
            ),
            "Expectations From Us": st.text_area(
                "What are you expecting from us?",
                placeholder="e.g., Real-time dashboards, daily reports, anomaly alerts, competitive benchmarking…",
                key="final_expectation",
            ),
        }

        # ── 10. Comments ──────────────────────────────────────────────────
        section_header("💬", "10. Comments & Notes")
        form_data["Comments & Notes"] = {
            "Additional Comments": st.text_area(
                "Any additional notes or special instructions",
                placeholder="Anything else important for the team to know…",
                key="final_comments",
            )
        }

        st.markdown("<br>", unsafe_allow_html=True)

        # PDF Generation
        if st.button("⬇️  Generate & Download PDF", type="primary", use_container_width=True):
            with st.spinner("Building PDF…"):
                pdf_bytes = generate_pdf(form_data, client_name).read()
            st.session_state["pdf_bytes"] = pdf_bytes
            # _safe_filename strips path-traversal chars from user-supplied client name
            st.session_state["pdf_name"] = _safe_filename(client_name, "_Requirement_Form.pdf")
            celebrate(
                message="PDF generated successfully!",
                sub=f"{_h(client_name)} Requirement Form is ready to download."
            )
            st.toast("PDF ready! Click below to download.", icon="🎉")

        if st.session_state.get("pdf_bytes"):
            st.download_button(
                label="📄  Download Requirement PDF",
                data=st.session_state["pdf_bytes"],
                file_name=st.session_state.get("pdf_name", "requirement.pdf"),
                mime="application/pdf",
                use_container_width=True,
            )

    with right:
        render_summary(form_data)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: FEASIBILITY ASSESSMENT
# ─────────────────────────────────────────────────────────────────────────────

def render_feasibility():
    page_title(
        "Feasibility Assessment",
        "Evaluate crawl feasibility before project kickoff — exports a Word document for the team."
    )

    # Stats strip
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div style="background:white;border-radius:12px;padding:18px 20px;border-left:4px solid #1f2937;box-shadow:0 2px 8px rgba(0,0,0,0.07);transition:box-shadow 0.2s;">
            <div style="font-size:0.67rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.09em;font-weight:700;font-family:'Inter',sans-serif;">Purpose</div>
            <div style="font-size:0.9rem;font-weight:600;color:#111827;margin-top:5px;font-family:'Inter',sans-serif;">Pre-project scoping</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div style="background:white;border-radius:12px;padding:18px 20px;border-left:4px solid #1f2937;box-shadow:0 2px 8px rgba(0,0,0,0.07);transition:box-shadow 0.2s;">
            <div style="font-size:0.67rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.09em;font-weight:700;font-family:'Inter',sans-serif;">Output</div>
            <div style="font-size:0.9rem;font-weight:600;color:#111827;margin-top:5px;font-family:'Inter',sans-serif;">Word Document (.docx)</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div style="background:white;border-radius:12px;padding:18px 20px;border-left:4px solid #1f2937;box-shadow:0 2px 8px rgba(0,0,0,0.07);transition:box-shadow 0.2s;">
            <div style="font-size:0.67rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.09em;font-weight:700;font-family:'Inter',sans-serif;">Use Case</div>
            <div style="font-size:0.9rem;font-weight:600;color:#111827;margin-top:5px;font-family:'Inter',sans-serif;">Share with tech / ops team</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col, _ = st.columns([3, 1])
    with col:

        # Requirement Information
        section_header("📌", "Requirement Information")
        c1, c2 = st.columns(2)
        with c1:
            client_name = st.text_input("Client Name", placeholder="e.g., Unilever India", key="feas_client")
        with c2:
            requestor_name = st.text_input("Requestor Name", placeholder="Your name", key="feas_requestor")

        # Domains
        section_header("🌐", "Domain List")
        num_domains = st.number_input("Number of Domains", min_value=1, step=1, value=1, key="feas_num_domains")
        domains = []
        if num_domains <= 6:
            cols = st.columns(min(int(num_domains), 3))
            for i in range(int(num_domains)):
                with cols[i % 3]:
                    d = st.text_input(f"Domain {i+1}", placeholder="example.com", key=f"feas_domain_{i}")
                    if d:
                        domains.append(d)
        else:
            for i in range(int(num_domains)):
                d = st.text_input(f"Domain {i+1}", placeholder="example.com", key=f"feas_domain_{i}")
                if d:
                    domains.append(d)

        # Crawl Configuration
        section_header("⚙️", "Crawl Configuration")
        crawl_options = st.multiselect(
            "Select crawl type and special requirements",
            ["Category Based", "Product URL Input Based", "SOS", "Reviews",
             "Festive Sales Day Crawl", "Banner Crawl", "Others"],
            key="feas_crawl_options",
        )
        crawl_type = None
        if "Category Based" in crawl_options:
            crawl_type = "Category Based"
        elif "Product URL Input Based" in crawl_options:
            crawl_type = "Product URL Input Based"

        crawl_features = [o for o in crawl_options if o not in ["Category Based", "Product URL Input Based"]]
        others_desc = ""
        if "Others" in crawl_features:
            others_desc = st.text_input("If Others, please specify", key="feas_others")

        # Zipcode
        section_header("📍", "Zipcode Requirement")
        zipcode_type = st.radio(
            "Zipcode handling", ["With Zipcode", "Without Zipcode", "Both"],
            horizontal=True, key="feas_zipcode"
        )
        target_city = target_state = target_country = ""
        if zipcode_type in ["With Zipcode", "Both"]:
            st.markdown("**Target Location**")
            c1, c2, c3 = st.columns(3)
            with c1:
                target_city = st.text_input("City", key="feas_city")
            with c2:
                target_state = st.text_input("State", key="feas_state")
            with c3:
                target_country = st.text_input("Country", key="feas_country")

        # Additional
        section_header("📝", "Additional Information")
        additional_notes = st.text_area("Additional details / notes", key="feas_notes", height=120)

        st.markdown("<br>", unsafe_allow_html=True)

        # Generate document
        if st.button("📄  Generate Feasibility Document", type="primary", use_container_width=True):
            if not client_name:
                st.warning("Please enter a Client Name before generating.")
            else:
                with st.spinner("Building document…"):
                    doc = Document()
                    doc.add_heading(f"{client_name} — Feasibility Requirement", level=1)

                    doc.add_heading("Requirement Information", level=2)
                    doc.add_paragraph(f"Client Name: {client_name}")
                    doc.add_paragraph(f"Requestor Name: {requestor_name}")

                    doc.add_heading("Domains", level=2)
                    for d in domains:
                        doc.add_paragraph(d, style="List Bullet")

                    doc.add_heading("Crawl Configuration", level=2)
                    doc.add_paragraph(f"Crawl Type: {crawl_type or 'Not specified'}")
                    doc.add_paragraph(f"Special Requirements: {', '.join(crawl_features) or 'None'}")
                    if others_desc:
                        doc.add_paragraph(f"Others: {others_desc}")

                    doc.add_heading("Zipcode Requirement", level=2)
                    doc.add_paragraph(f"Zipcode Handling: {zipcode_type}")
                    if zipcode_type in ["With Zipcode", "Both"]:
                        doc.add_heading("Target Location", level=2)
                        doc.add_paragraph(f"City: {target_city}")
                        doc.add_paragraph(f"State: {target_state}")
                        doc.add_paragraph(f"Country: {target_country}")

                    doc.add_heading("Additional Notes", level=2)
                    doc.add_paragraph(additional_notes or "None")

                    buf = BytesIO()
                    doc.save(buf)
                    buf.seek(0)

                st.session_state["feas_doc"]  = buf.getvalue()
                # _safe_filename strips path-traversal chars from user-supplied client name
                st.session_state["feas_name"] = _safe_filename(client_name, "_Feasibility_Requirement.docx")
                celebrate(
                    message="Feasibility Document generated!",
                    sub=f"{_h(client_name)} feasibility doc is ready to download."
                )
                st.toast("Document ready! Click below to download.", icon="🎉")

        if st.session_state.get("feas_doc"):
            st.download_button(
                label="⬇️  Download Feasibility Document",
                data=st.session_state["feas_doc"],
                file_name=st.session_state.get("feas_name", "feasibility.docx"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: DECISION MIND MAP
# ─────────────────────────────────────────────────────────────────────────────

def render_req_flow():
    page_title("New Requirement Decision Tree", "Step-by-step guide from client intake to delivery. Click nodes to expand.")
    st.markdown("""<div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:10px 20px;margin-bottom:14px;display:flex;gap:24px;flex-wrap:wrap;align-items:center;font-size:0.82rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);font-family:'Inter',sans-serif;"><span style="color:#3b82f6;font-weight:600;">&#9646; Step</span><span style="color:#d97706;font-weight:600;">&#9646; Decision</span><span style="color:#22c55e;font-weight:600;">&#9646; Outcome</span><span style="color:#94a3b8;font-weight:600;">&#9646; Action</span><span style="color:#94a3b8;margin-left:auto;font-size:0.78rem;">8 sequential steps &mdash; intake to delivery</span></div>""", unsafe_allow_html=True)
    _html = """<!DOCTYPE html><meta charset="utf-8">
<style>
html,body{margin:0;padding:0;width:100vw;height:100vh;overflow:hidden;
  background:#f0f2f6;font-family:'Inter','Segoe UI',-apple-system,sans-serif;}
#tree{width:100vw;height:100vh;}
.node rect{stroke-width:1.8px;transition:all .18s;cursor:pointer;}
.node rect:hover{opacity:.82;}
.node text{pointer-events:none;font-weight:500;}
.link{fill:none;stroke-width:1.6px;opacity:.4;}
#legend{position:absolute;top:12px;right:14px;background:rgba(255,255,255,.93);
  border:1px solid #e5e7eb;border-radius:9px;padding:10px 14px;
  font-size:12px;color:#374151;line-height:2.1;
  box-shadow:0 2px 8px rgba(0,0,0,.07);}
#hint{position:absolute;bottom:10px;right:14px;font-size:10px;color:#9ca3af;}
</style>
<div id="tree"></div>
<div id="legend"><b>Node Types</b><br><span style='color:#3b82f6'>&#9646;</span> Step &nbsp;<span style='color:#d97706'>&#9646;</span> Decision &nbsp;<span style='color:#22c55e'>&#9646;</span> Outcome &nbsp;<span style='color:#94a3b8'>&#9646;</span> Action</div>
<div id="hint">Scroll = zoom &nbsp;·&nbsp; Drag = pan &nbsp;·&nbsp; Click = expand/collapse</div>
{_D3_INLINE}
<script>
var data={name:"New Requirement Intake",k:"start",children:[
{name:"1. Finalise Domains",k:"step",children:[
  {name:"QCommerce",k:"act",children:[{name:"Swiggy Instamart"},{name:"ZeptoNow"},{name:"Blinkit"},{name:"BigBasket"}]},
  {name:"ECom",k:"act",children:[{name:"Amazon"},{name:"Flipkart"},{name:"Nykaa"},{name:"Purplle"}]},
  {name:"Fashion Retail",k:"act",children:[{name:"AJIO"},{name:"Myntra"}]}
]},
{name:"2. Classify Seed URLs",k:"step",children:[
  {name:"Category URL?",k:"dec",children:[
    {name:"PDP crawl",k:"out",children:[{name:"Products Index"},{name:"Trends Index"}]},
    {name:"Listing page",k:"out",children:[{name:"SOS Index"}]},
    {name:"Banner present",k:"out",children:[{name:"Misc Index"}]}
  ]},
  {name:"Direct Product URL?",k:"dec",children:[
    {name:"Trends Index only",k:"out"}
  ]},
  {name:"SOS Keyword input?",k:"dec",children:[
    {name:"SOS Index",k:"out",children:[{name:"No PDP fetch"},{name:"Listing page only"}]}
  ]},
  {name:"Reviews needed?",k:"dec",children:[
    {name:"Reviews Index",k:"out",children:[{name:"ES input from Products"}]}
  ]},
  {name:"Banner tracking?",k:"dec",children:[
    {name:"API available",k:"out",children:[{name:"Misc API crawl"}]},
    {name:"No API",k:"out",children:[{name:"Screenshot method"}]}
  ]}
]},
{name:"3. Index Decision",k:"step",children:[
  {name:"Zipcode based?",k:"dec",children:[
    {name:"YES: add _zipcode",k:"out"},
    {name:"NO: standard name",k:"out"}
  ]},
  {name:"Historical tracking?",k:"dec",children:[
    {name:"YES: Trends/SOS/Misc",k:"out"},
    {name:"NO: Products/Reviews",k:"out"}
  ]},
  {name:"Variants needed?",k:"dec",children:[
    {name:"YES: uniq_id/variant",k:"out"},
    {name:"NO: uniq_id/product",k:"out"}
  ]},
  {name:"Assign Domain #",k:"act",children:[
    {name:"Products: no number"},
    {name:"Sheet Hourly: #1"},
    {name:"ES Daily: #2"},
    {name:"ES Hourly: #3"},
    {name:"SOS / PV: #4"},
    {name:"Others: #5+"}
  ]}
]},
{name:"4. Feasibility Check",k:"step",children:[
  {name:"Check schema sheet",k:"act",children:[
    {name:"Must-have fields"},{name:"General feasibility"}
  ]},
  {name:"Special fields?",k:"dec",children:[
    {name:"YES: define + Platform",k:"out"},
    {name:"NO: proceed",k:"out"}
  ]},
  {name:"Blocking challenge?",k:"dec",children:[
    {name:"YES: raise flag early",k:"out"},
    {name:"NO: proceed",k:"out"}
  ]}
]},
{name:"5. Site Setup",k:"step",children:[
  {name:"Domain exists?",k:"dec",children:[
    {name:"YES: reuse (even active)",k:"out"},
    {name:"NO: ask TPM to create",k:"out"}
  ]},
  {name:"Define site name",k:"act",children:[
    {name:"domain_tld{#}{_zip}"},
    {name:"_{index}_forty_two_signals"}
  ]},
  {name:"Update mapping JSON",k:"act",children:[
    {name:"domain_numbered_sites"},
    {name:"_mapping.json"}
  ]}
]},
{name:"6. Dev Implementation",k:"step",children:[
  {name:"Products: RSS→DSK→EXT",k:"act",children:[
    {name:"uniq_id unique always"},
    {name:"internal_client_name"},
    {name:"joining_key required"},
    {name:"ISO date format only"}
  ]},
  {name:"Trends: inherit DSK+EXT",k:"act",children:[
    {name:"RSS changes only"},
    {name:"uniq_id unchanged"}
  ]},
  {name:"SOS: listing only",k:"act",children:[
    {name:"No PDP fetch"},
    {name:"Scroll / page limit"}
  ]}
]},
{name:"7. Post-Setup Checks",k:"step",children:[
  {name:"Dev QA all fields",k:"act"},
  {name:"Count match?",k:"dec",children:[
    {name:"Crawlboard = Kibana",k:"out"},
    {name:"Mismatch: check logs",k:"out"}
  ]},
  {name:"All records indexed?",k:"dec",children:[
    {name:"YES: QA phase",k:"out"},
    {name:"NO: debug logstash",k:"out"}
  ]}
]},
{name:"8. QA & Delivery",k:"step",children:[
  {name:"Products dashboard QA",k:"act"},
  {name:"Trends QA (after prod)",k:"act"},
  {name:"Kibana = Crawlboard?",k:"dec",children:[
    {name:"OK: share Kibana link",k:"out"},
    {name:"Fail: debug logstash",k:"out"}
  ]},
  {name:"QA passed?",k:"dec",children:[
    {name:"YES: deliver to client",k:"out"},
    {name:"NO: fix and re-QA",k:"out"}
  ]}
]}
]};
var NW=196,NH=48,NR=9;
var M={top:60,right:240,bottom:60,left:210};
var W=window.innerWidth-M.left-M.right;
var H=window.innerHeight-M.top-M.bottom;
var svg=d3.select("#tree").append("svg")
  .attr("width",W+M.left+M.right).attr("height",H+M.top+M.bottom)
  .call(d3.zoom().scaleExtent([.18,3]).on("zoom",e=>g.attr("transform",e.transform)))
  .on("dblclick.zoom",null);
var g=svg.append("g").attr("transform","translate("+M.left+","+(M.top+H/2)+")");
var i=0,dur=400;
var root=d3.hierarchy(data);
root.x0=0;root.y0=0;

var KF={start:"#1f2937",step:"#dbeafe",dec:"#fef3c7",out:"#dcfce7",act:"#f1f5f9"};
var KB={start:"#111827",step:"#3b82f6",dec:"#d97706",out:"#22c55e",act:"#94a3b8"};
var KT={start:"#fff",step:"#1e40af",dec:"#92400e",out:"#14532d",act:"#374151"};
function nFill(d){if(d.depth===0)return KF.start;return KF[d.data.k]||"#f3f4f6";}
function nBorder(d){if(d.depth===0)return KB.start;return KB[d.data.k]||"#d1d5db";}
function nText(d){if(d.depth===0)return KT.start;return KT[d.data.k]||"#374151";}
root.children.forEach(collapse);
update(root);
function collapse(d){if(d.children){d._children=d.children;d._children.forEach(collapse);d.children=null;}}
function wrap(t,n){if(t.length<=n)return[t];var m=t.lastIndexOf(" ",n);if(m<1)m=n;return[t.slice(0,m),t.slice(m+1)];}
function update(src){
  var tree=d3.tree().nodeSize([NH+28,1]);
  var td=tree(root);
  var nodes=td.descendants(),links=td.descendants().slice(1);
  var colW=Math.max(NW+36,W/5.4);nodes.forEach(d=>d.y=d.depth*colW);
  var node=g.selectAll("g.node").data(nodes,d=>d.id||(d.id=++i));
  var ne=node.enter().append("g").attr("class","node")
    .attr("transform",()=>"translate("+src.y0+","+src.x0+")")
    .on("click",click);
  ne.append("rect")
    .attr("width",NW).attr("height",NH).attr("x",-NW/2).attr("y",-NH/2)
    .attr("rx",NR).attr("ry",NR)
    .style("fill",d=>nFill(d)).style("stroke",d=>nBorder(d))
    .style("filter","drop-shadow(0 2px 5px rgba(0,0,0,.07))");
  ne.each(function(d){
    var el=d3.select(this),ln=wrap(d.data.name,23);
    var dy1=ln.length===1?"0.35em":"-0.5em", dy2="0.82em";
    el.append("text").attr("dy",dy1).attr("text-anchor","middle")
      .style("font-size","13px").style("fill",nText(d)).text(ln[0]);
    if(ln.length>1)
      el.append("text").attr("dy",dy2).attr("text-anchor","middle")
        .style("font-size","12px").style("fill",nText(d)).text(ln[1]);
  });
  ne.append("text").attr("class","ind")
    .attr("dy","0.35em").attr("x",NW/2-9).attr("text-anchor","middle")
    .style("font-size","9px");
  var nu=ne.merge(node);
  nu.transition().duration(dur).attr("transform",d=>"translate("+d.y+","+d.x+")");
  nu.select("rect").style("fill",d=>nFill(d)).style("stroke",d=>nBorder(d));
  nu.select(".ind")
    .text(d=>(d._children||d.children)?"●":"")
    .style("fill",d=>nBorder(d))
    .style("opacity",d=>(d._children||d.children)?1:0);
  node.exit().transition().duration(dur)
    .attr("transform",()=>"translate("+src.y+","+src.x+")").remove();
  var link=g.selectAll("path.link").data(links,d=>d.id);
  var le=link.enter().insert("path","g").attr("class","link")
    .attr("d",()=>{var o={x:src.x0,y:src.y0};return diag(o,o);})
    .style("stroke",d=>nBorder(d));
  le.merge(link).transition().duration(dur).attr("d",d=>diag(d,d.parent));
  link.exit().transition().duration(dur)
    .attr("d",()=>{var o={x:src.x,y:src.y};return diag(o,o);}).remove();
  nodes.forEach(d=>{d.x0=d.x;d.y0=d.y;});
}
function diag(s,d){
  return"M"+s.y+" "+s.x+" C"+(s.y+d.y)/2+" "+s.x+","+(s.y+d.y)/2+" "+d.x+","+d.y+" "+d.x;
}
function click(e,d){
  if(d.children){d._children=d.children;d.children=null;}
  else{d.children=d._children;d._children=null;}
  update(d);
}
</script>"""
    components.html(_html.replace("{_D3_INLINE}", _D3_INLINE), height=1000, scrolling=False)

def render_ops_map():
    page_title("Day-to-Day Operations Mind Map", "All 7 operational areas — expand any branch to explore tasks & tools.")
    st.markdown("""<div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:10px 20px;margin-bottom:14px;font-size:0.82rem;color:#6b7280;box-shadow:0 1px 4px rgba(0,0,0,0.04);font-family:'Inter',sans-serif;">7 operational areas &mdash; expand any branch &nbsp;&middot;&nbsp; scroll to zoom &nbsp;&middot;&nbsp; drag to pan</div>""", unsafe_allow_html=True)
    _html = """<!DOCTYPE html><meta charset="utf-8">
<style>
html,body{margin:0;padding:0;width:100vw;height:100vh;overflow:hidden;
  background:#f0f2f6;font-family:'Inter','Segoe UI',-apple-system,sans-serif;}
#tree{width:100vw;height:100vh;}
.node rect{stroke-width:1.8px;transition:all .18s;cursor:pointer;}
.node rect:hover{opacity:.82;}
.node text{pointer-events:none;font-weight:500;}
.link{fill:none;stroke-width:1.6px;opacity:.4;}
#legend{position:absolute;top:12px;right:14px;background:rgba(255,255,255,.93);
  border:1px solid #e5e7eb;border-radius:9px;padding:10px 14px;
  font-size:12px;color:#374151;line-height:2.1;
  box-shadow:0 2px 8px rgba(0,0,0,.07);}
#hint{position:absolute;bottom:10px;right:14px;font-size:10px;color:#9ca3af;}
</style>
<div id="tree"></div>
<div id="legend"><b>Operational Areas</b><br><span style='color:#2563eb'>&#9646;</span> Kibana Monitoring<br><span style='color:#059669'>&#9646;</span> Input Sheets<br><span style='color:#d97706'>&#9646;</span> Cost Analysis<br><span style='color:#7c3aed'>&#9646;</span> Crawl Health<br><span style='color:#dc2626'>&#9646;</span> Mapping & Tracking<br><span style='color:#0891b2'>&#9646;</span> Maintenance<br><span style='color:#be185d'>&#9646;</span> Automation<br></div>
<div id="hint">Scroll = zoom &nbsp;·&nbsp; Drag = pan &nbsp;·&nbsp; Click = expand/collapse</div>
{_D3_INLINE}
<script>
var data={name:"Daily Operations Hub",children:[
{name:"Kibana Monitoring",children:[
  {name:"Client vs Site",children:[
    {name:"Active clients list"},
    {name:"Crawl frequency"},
    {name:"Records by site"},
    {name:"Client % share/site"}
  ]},
  {name:"Proxy Status",children:[
    {name:"Success/fail rate"},
    {name:"Oxylabs premium"},
    {name:"Weekly check"}
  ]},
  {name:"Disk Time Opt.",children:[
    {name:"Slow sites identify"},
    {name:"Infinity loop detect"},
    {name:"Weekly + on-demand"}
  ]},
  {name:"Extraction Duration",children:[
    {name:"Slow parsers"},
    {name:"XPath bottlenecks"},
    {name:"Weekly check"}
  ]},
  {name:"Cost Analytics",children:[
    {name:"Client vs Site dash"},
    {name:"Monthly infra cost"},
    {name:"% data per client"}
  ]}
]},
{name:"Input Sheet Mgmt",children:[
  {name:"Data Request Format",children:[
    {name:"Client URLs + pincodes"},
    {name:"Crawl scheduling"},
    {name:"pincode_uniq_id logic"},
    {name:"Closed clients view"},
    {name:"Kibana link viewer"}
  ]},
  {name:"Add / Update URLs",children:[
    {name:"Sheet-based input"},
    {name:"ES-based input"},
    {name:"Pincode CSV input"}
  ]},
  {name:"AppScript Automation",children:[
    {name:"Auto crawl tracking"},
    {name:"Threshold alerts"},
    {name:"Status updates"}
  ]}
]},
{name:"Cost Analysis",children:[
  {name:"Clientwise (Monthly)",children:[
    {name:"Current vs prev cycle"},
    {name:"n-month trend"},
    {name:"42s Clientwise sheet"}
  ]},
  {name:"Sitewise (Monthly)",children:[
    {name:"Cost per site"},
    {name:"% data per client"},
    {name:"42s Sitewise sheet"}
  ]},
  {name:"InfraCost Input",children:[
    {name:"Platform + DevOps"},
    {name:"Manual ES indexing"},
    {name:"42s input data sheet"}
  ]}
]},
{name:"Crawl Health",children:[
  {name:"Count Mismatch",children:[
    {name:"Kibana vs Crawlboard"},
    {name:"Threshold sheet"},
    {name:"42S avg threshold"}
  ]},
  {name:"Failure Logs",children:[
    {name:"lbhdf12_logstash.log"},
    {name:"lbhdf13_logstash.log"},
    {name:"Copied hourly to ex51"}
  ]},
  {name:"Misc + Dep Sites",children:[
    {name:"Misc processing tracker"},
    {name:"Dep data upload tracker"},
    {name:"Banner sites progress"}
  ]}
]},
{name:"Mapping & Tracking",children:[
  {name:"Client-Site Mapping",children:[
    {name:"Client to site view"},
    {name:"Site to client view"},
    {name:"Active sites list"}
  ]},
  {name:"Domain Mapping JSON",children:[
    {name:"Products to Trends link"},
    {name:"domain_numbered_sites"},
    {name:"Update on new site"}
  ]},
  {name:"42S Schema Sheet",children:[
    {name:"Field definitions"},
    {name:"Must-have fields"},
    {name:"Index-specific fields"}
  ]}
]},
{name:"Maintenance",children:[
  {name:"Weekly Tasks",children:[
    {name:"Disk time review"},
    {name:"Extraction duration"},
    {name:"Proxy health check"},
    {name:"Image count check"}
  ]},
  {name:"Monthly Tasks",children:[
    {name:"Retrospection doc"},
    {name:"Aggregated report"},
    {name:"Clientwise cost"},
    {name:"Sitewise cost"}
  ]},
  {name:"On-Demand Tasks",children:[
    {name:"New site addition"},
    {name:"Client pause/resume"},
    {name:"Threshold updates"},
    {name:"InfraCost update"}
  ]}
]},
{name:"Automation",children:[
  {name:"Google App Scripts",children:[
    {name:"Data Request Format"},
    {name:"Clientwise cost"},
    {name:"Sitewise cost"},
    {name:"Threshold alerts"}
  ]},
  {name:"Ruby Scripts",children:[
    {name:"Volume adjustment"},
    {name:"Missing upload check"},
    {name:"Weekly crawl tracker"}
  ]}
]}
]};
var NW=196,NH=48,NR=9;
var M={top:60,right:240,bottom:60,left:210};
var W=window.innerWidth-M.left-M.right;
var H=window.innerHeight-M.top-M.bottom;
var svg=d3.select("#tree").append("svg")
  .attr("width",W+M.left+M.right).attr("height",H+M.top+M.bottom)
  .call(d3.zoom().scaleExtent([.18,3]).on("zoom",e=>g.attr("transform",e.transform)))
  .on("dblclick.zoom",null);
var g=svg.append("g").attr("transform","translate("+M.left+","+(M.top+H/2)+")");
var i=0,dur=400;
var root=d3.hierarchy(data);
root.x0=0;root.y0=0;
var BC=["#2563eb", "#059669", "#d97706", "#7c3aed", "#dc2626", "#0891b2", "#be185d"];
function getBC(d){
  var a=d;while(a.depth>1&&a.parent)a=a.parent;
  if(a.depth===0)return"#1f2937";
  return BC[(a.parent?a.parent.children.indexOf(a):0)%BC.length];
}
function nFill(d){
  if(d.depth===0)return"#1f2937";
  if(d.depth===1){var c=getBC(d);return c+"18";}
  return"#f3f4f6";
}
function nBorder(d){return getBC(d);}
function nText(d){
  if(d.depth===0)return"#fff";
  if(d.depth===1)return getBC(d);
  return"#374151";
}
root.children.forEach(collapse);
update(root);
function collapse(d){if(d.children){d._children=d.children;d._children.forEach(collapse);d.children=null;}}
function wrap(t,n){if(t.length<=n)return[t];var m=t.lastIndexOf(" ",n);if(m<1)m=n;return[t.slice(0,m),t.slice(m+1)];}
function update(src){
  var tree=d3.tree().nodeSize([NH+28,1]);
  var td=tree(root);
  var nodes=td.descendants(),links=td.descendants().slice(1);
  var colW=Math.max(NW+36,W/5.4);nodes.forEach(d=>d.y=d.depth*colW);
  var node=g.selectAll("g.node").data(nodes,d=>d.id||(d.id=++i));
  var ne=node.enter().append("g").attr("class","node")
    .attr("transform",()=>"translate("+src.y0+","+src.x0+")")
    .on("click",click);
  ne.append("rect")
    .attr("width",NW).attr("height",NH).attr("x",-NW/2).attr("y",-NH/2)
    .attr("rx",NR).attr("ry",NR)
    .style("fill",d=>nFill(d)).style("stroke",d=>nBorder(d))
    .style("filter","drop-shadow(0 2px 5px rgba(0,0,0,.07))");
  ne.each(function(d){
    var el=d3.select(this),ln=wrap(d.data.name,23);
    var dy1=ln.length===1?"0.35em":"-0.5em", dy2="0.82em";
    el.append("text").attr("dy",dy1).attr("text-anchor","middle")
      .style("font-size","13px").style("fill",nText(d)).text(ln[0]);
    if(ln.length>1)
      el.append("text").attr("dy",dy2).attr("text-anchor","middle")
        .style("font-size","12px").style("fill",nText(d)).text(ln[1]);
  });
  ne.append("text").attr("class","ind")
    .attr("dy","0.35em").attr("x",NW/2-9).attr("text-anchor","middle")
    .style("font-size","9px");
  var nu=ne.merge(node);
  nu.transition().duration(dur).attr("transform",d=>"translate("+d.y+","+d.x+")");
  nu.select("rect").style("fill",d=>nFill(d)).style("stroke",d=>nBorder(d));
  nu.select(".ind")
    .text(d=>(d._children||d.children)?"●":"")
    .style("fill",d=>nBorder(d))
    .style("opacity",d=>(d._children||d.children)?1:0);
  node.exit().transition().duration(dur)
    .attr("transform",()=>"translate("+src.y+","+src.x+")").remove();
  var link=g.selectAll("path.link").data(links,d=>d.id);
  var le=link.enter().insert("path","g").attr("class","link")
    .attr("d",()=>{var o={x:src.x0,y:src.y0};return diag(o,o);})
    .style("stroke",d=>nBorder(d));
  le.merge(link).transition().duration(dur).attr("d",d=>diag(d,d.parent));
  link.exit().transition().duration(dur)
    .attr("d",()=>{var o={x:src.x,y:src.y};return diag(o,o);}).remove();
  nodes.forEach(d=>{d.x0=d.x;d.y0=d.y;});
}
function diag(s,d){
  return"M"+s.y+" "+s.x+" C"+(s.y+d.y)/2+" "+s.x+","+(s.y+d.y)/2+" "+d.x+","+d.y+" "+d.x;
}
function click(e,d){
  if(d.children){d._children=d.children;d.children=null;}
  else{d.children=d._children;d._children=null;}
  update(d);
}
</script>"""
    components.html(_html.replace("{_D3_INLINE}", _D3_INLINE), height=1000, scrolling=False)

def render_poc_guide():
    page_title("Task POC Guide", "Who to contact for every task type. Colour-coded by responsible team.")
    st.markdown("""<div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:10px 20px;margin-bottom:14px;display:flex;gap:22px;flex-wrap:wrap;align-items:center;font-size:0.82rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);font-family:'Inter',sans-serif;"><span style="color:#3b82f6;font-weight:600;">&#9646; Shanjai / Srinivas</span><span style="color:#7c3aed;font-weight:600;">&#9646; Dev Team</span><span style="color:#d97706;font-weight:600;">&#9646; Platform</span><span style="color:#dc2626;font-weight:600;">&#9646; TPM</span><span style="color:#16a34a;font-weight:600;">&#9646; DS / QA / Product</span></div>""", unsafe_allow_html=True)
    _html = """<!DOCTYPE html><meta charset="utf-8">
<style>
html,body{margin:0;padding:0;width:100vw;height:100vh;overflow:hidden;
  background:#f0f2f6;font-family:'Inter','Segoe UI',-apple-system,sans-serif;}
#tree{width:100vw;height:100vh;}
.node rect{stroke-width:1.8px;transition:all .18s;cursor:pointer;}
.node rect:hover{opacity:.82;}
.node text{pointer-events:none;font-weight:500;}
.link{fill:none;stroke-width:1.6px;opacity:.4;}
#legend{position:absolute;top:12px;right:14px;background:rgba(255,255,255,.93);
  border:1px solid #e5e7eb;border-radius:9px;padding:10px 14px;
  font-size:12px;color:#374151;line-height:2.1;
  box-shadow:0 2px 8px rgba(0,0,0,.07);}
#hint{position:absolute;bottom:10px;right:14px;font-size:10px;color:#9ca3af;}
</style>
<div id="tree"></div>
<div id="legend"><b>Point of Contact</b><br><span style='color:#3b82f6'>&#9646;</span> Shanjai / Srinivas<br><span style='color:#7c3aed'>&#9646;</span> Dev Team<br><span style='color:#d97706'>&#9646;</span> Platform Team<br><span style='color:#dc2626'>&#9646;</span> TPM<br><span style='color:#16a34a'>&#9646;</span> DS / QA / Product</div>
<div id="hint">Scroll = zoom &nbsp;·&nbsp; Drag = pan &nbsp;·&nbsp; Click = expand/collapse</div>
{_D3_INLINE}
<script>
var data={name:"Task POC Guide",k:"root",children:[
{name:"Site Setup",k:"dev",children:[
  {name:"New site needed",k:"tpm",children:[
    {name:"Contact: TPM",k:"tpm"},
    {name:"Provide: name + index"},
    {name:"PSS created by TPM"},
    {name:"Dev does setup after"}
  ]},
  {name:"Reuse existing site",k:"dev",children:[
    {name:"Contact: Dev team",k:"dev"},
    {name:"Add seed URLs only"},
    {name:"OK even if site active"}
  ]},
  {name:"Naming convention",k:"sh",children:[
    {name:"Contact: Shanjai",k:"sh"},
    {name:"Ref: 42S Documentation"},
    {name:"domain_tld{#}_{idx}_42s"}
  ]},
  {name:"Domain mapping JSON",k:"dev",children:[
    {name:"Contact: Dev team",k:"dev"},
    {name:"domain_numbered_sites"},
    {name:"_mapping.json"}
  ]}
]},
{name:"Schema & Fields",k:"plat",children:[
  {name:"New field addition",k:"plat",children:[
    {name:"Contact: Platform team",k:"plat"},
    {name:"Finalise name + type"},
    {name:"Platform updates DRL"},
    {name:"Then Dev implements"},
    {name:"Eg: weekly_units_sold"}
  ]},
  {name:"DRL / EXT changes",k:"dev",children:[
    {name:"Contact: Dev team",k:"dev"},
    {name:"After Platform mapping"}
  ]},
  {name:"Schema review",k:"sh",children:[
    {name:"Contact: Shanjai/Dev",k:"sh"},
    {name:"Check 42S schema sheet"}
  ]}
]},
{name:"Crawl Issues",k:"dev",children:[
  {name:"Crawl not running",k:"dev",children:[
    {name:"Contact: Dev → TPM",k:"dev"},
    {name:"Check crawl-board logs"},
    {name:"Check proxy status"}
  ]},
  {name:"Count mismatch",k:"sh",children:[
    {name:"Contact: Shanjai/Srinivas",k:"sh"},
    {name:"Kibana vs Crawlboard"},
    {name:"Check logstash logs"},
    {name:"Threshold sheet review"}
  ]},
  {name:"Proxy failures",k:"sh",children:[
    {name:"Contact: Srinivas/Shanjai",k:"sh"},
    {name:"proxy_overview dash"},
    {name:"Oxylabs premium check"}
  ]},
  {name:"Extraction errors",k:"dev",children:[
    {name:"Contact: Dev team",k:"dev"},
    {name:"XPath / JS page issues"},
    {name:"lbhdf12/13 logstash"}
  ]}
]},
{name:"Client Requirements",k:"sh",children:[
  {name:"New client intake",k:"sh",children:[
    {name:"Contact: Shanjai",k:"sh"},
    {name:"Classify seed URLs"},
    {name:"Feasibility check"},
    {name:"Coordinate with product"}
  ]},
  {name:"New Balance",k:"sh",children:[
    {name:"Image download: Shanjai",k:"sh"},
    {name:"Server upload: Platform",k:"plat"},
    {name:"Product matching: DS",k:"ds"},
    {name:"QA annotation: QA team",k:"ds"},
    {name:"New fields: Platform",k:"plat"}
  ]},
  {name:"RamyBrook",k:"dev",children:[
    {name:"JSON mapping: Dev",k:"dev"},
    {name:"Saks cart flow: Dev",k:"dev"},
    {name:"Python-Ruby: Dev",k:"dev"},
    {name:"Validation: DS+QA",k:"ds"}
  ]},
  {name:"Client escalation",k:"tpm",children:[
    {name:"Contact: TPM",k:"tpm"},
    {name:"TPM → Mgmt if needed"}
  ]}
]},
{name:"Cost & Infra",k:"plat",children:[
  {name:"Monthly cost report",k:"plat",children:[
    {name:"Contact: Platform+DevOps",k:"plat"},
    {name:"Generates infra spend"},
    {name:"Manually indexed to ES"}
  ]},
  {name:"Clientwise analysis",k:"sh",children:[
    {name:"Contact: Shanjai",k:"sh"},
    {name:"42s Clientwise sheet"},
    {name:"Current vs prev cycle"}
  ]},
  {name:"Sitewise analysis",k:"sh",children:[
    {name:"Contact: Shanjai",k:"sh"},
    {name:"42s Sitewise sheet"}
  ]},
  {name:"InfraCost input",k:"sh",children:[
    {name:"Contact: Shanjai/Srinivas",k:"sh"},
    {name:"42s input data sheet"}
  ]}
]},
{name:"Maintenance Tasks",k:"sh",children:[
  {name:"Weekly checks",k:"sh",children:[
    {name:"Contact: Shanjai/Srinivas",k:"sh"},
    {name:"Disk, Proxy, Extraction"},
    {name:"Image counts"}
  ]},
  {name:"Monthly reports",k:"sh",children:[
    {name:"Contact: Shanjai/Srinivas",k:"sh"},
    {name:"Retrospection doc"},
    {name:"Cost analysis sheets"}
  ]},
  {name:"On-demand updates",k:"sh",children:[
    {name:"Contact: Shanjai",k:"sh"},
    {name:"New site threshold"},
    {name:"Mapping sheet update"}
  ]}
]},
{name:"Escalation Path",k:"tpm",children:[
  {name:"Platform change",k:"plat",children:[
    {name:"Contact: Platform team",k:"plat"},
    {name:"Schema / DRL / infra"}
  ]},
  {name:"New site creation",k:"tpm",children:[
    {name:"Contact: TPM",k:"tpm"},
    {name:"PSS → Dev setup"}
  ]},
  {name:"Client SLA issue",k:"tpm",children:[
    {name:"Contact: TPM",k:"tpm"},
    {name:"TPM → Management"}
  ]}
]}
]};
var NW=196,NH=48,NR=9;
var M={top:60,right:240,bottom:60,left:210};
var W=window.innerWidth-M.left-M.right;
var H=window.innerHeight-M.top-M.bottom;
var svg=d3.select("#tree").append("svg")
  .attr("width",W+M.left+M.right).attr("height",H+M.top+M.bottom)
  .call(d3.zoom().scaleExtent([.18,3]).on("zoom",e=>g.attr("transform",e.transform)))
  .on("dblclick.zoom",null);
var g=svg.append("g").attr("transform","translate("+M.left+","+(M.top+H/2)+")");
var i=0,dur=400;
var root=d3.hierarchy(data);
root.x0=0;root.y0=0;

var KF={root:"#1f2937",sh:"#dbeafe",dev:"#ede9fe",plat:"#fef3c7",tpm:"#fee2e2",ds:"#dcfce7"};
var KB={root:"#111827",sh:"#3b82f6",dev:"#7c3aed",plat:"#d97706",tpm:"#dc2626",ds:"#16a34a"};
var KT={root:"#fff",sh:"#1e40af",dev:"#5b21b6",plat:"#92400e",tpm:"#991b1b",ds:"#14532d"};
function nFill(d){if(d.depth===0)return KF.root;return KF[d.data.k]||"#f3f4f6";}
function nBorder(d){if(d.depth===0)return KB.root;return KB[d.data.k]||"#d1d5db";}
function nText(d){if(d.depth===0)return KT.root;return KT[d.data.k]||"#374151";}
root.children.forEach(collapse);
update(root);
function collapse(d){if(d.children){d._children=d.children;d._children.forEach(collapse);d.children=null;}}
function wrap(t,n){if(t.length<=n)return[t];var m=t.lastIndexOf(" ",n);if(m<1)m=n;return[t.slice(0,m),t.slice(m+1)];}
function update(src){
  var tree=d3.tree().nodeSize([NH+28,1]);
  var td=tree(root);
  var nodes=td.descendants(),links=td.descendants().slice(1);
  var colW=Math.max(NW+36,W/5.4);nodes.forEach(d=>d.y=d.depth*colW);
  var node=g.selectAll("g.node").data(nodes,d=>d.id||(d.id=++i));
  var ne=node.enter().append("g").attr("class","node")
    .attr("transform",()=>"translate("+src.y0+","+src.x0+")")
    .on("click",click);
  ne.append("rect")
    .attr("width",NW).attr("height",NH).attr("x",-NW/2).attr("y",-NH/2)
    .attr("rx",NR).attr("ry",NR)
    .style("fill",d=>nFill(d)).style("stroke",d=>nBorder(d))
    .style("filter","drop-shadow(0 2px 5px rgba(0,0,0,.07))");
  ne.each(function(d){
    var el=d3.select(this),ln=wrap(d.data.name,23);
    var dy1=ln.length===1?"0.35em":"-0.5em", dy2="0.82em";
    el.append("text").attr("dy",dy1).attr("text-anchor","middle")
      .style("font-size","13px").style("fill",nText(d)).text(ln[0]);
    if(ln.length>1)
      el.append("text").attr("dy",dy2).attr("text-anchor","middle")
        .style("font-size","12px").style("fill",nText(d)).text(ln[1]);
  });
  ne.append("text").attr("class","ind")
    .attr("dy","0.35em").attr("x",NW/2-9).attr("text-anchor","middle")
    .style("font-size","9px");
  var nu=ne.merge(node);
  nu.transition().duration(dur).attr("transform",d=>"translate("+d.y+","+d.x+")");
  nu.select("rect").style("fill",d=>nFill(d)).style("stroke",d=>nBorder(d));
  nu.select(".ind")
    .text(d=>(d._children||d.children)?"●":"")
    .style("fill",d=>nBorder(d))
    .style("opacity",d=>(d._children||d.children)?1:0);
  node.exit().transition().duration(dur)
    .attr("transform",()=>"translate("+src.y+","+src.x+")").remove();
  var link=g.selectAll("path.link").data(links,d=>d.id);
  var le=link.enter().insert("path","g").attr("class","link")
    .attr("d",()=>{var o={x:src.x0,y:src.y0};return diag(o,o);})
    .style("stroke",d=>nBorder(d));
  le.merge(link).transition().duration(dur).attr("d",d=>diag(d,d.parent));
  link.exit().transition().duration(dur)
    .attr("d",()=>{var o={x:src.x,y:src.y};return diag(o,o);}).remove();
  nodes.forEach(d=>{d.x0=d.x;d.y0=d.y;});
}
function diag(s,d){
  return"M"+s.y+" "+s.x+" C"+(s.y+d.y)/2+" "+s.x+","+(s.y+d.y)/2+" "+d.x+","+d.y+" "+d.x;
}
function click(e,d){
  if(d.children){d._children=d.children;d.children=null;}
  else{d.children=d._children;d._children=null;}
  update(d);
}
</script>"""
    components.html(_html.replace("{_D3_INLINE}", _D3_INLINE), height=1000, scrolling=False)





# ─────────────────────────────────────────────────────────────────────────────
# ROUTER  (auth-gated)
# ─────────────────────────────────────────────────────────────────────────────

if not st.session_state["authenticated"]:
    render_login()
else:
    page = st.session_state["page"]
    if page == "main":
        render_main_form()
    elif page == "feasibility":
        render_feasibility()
    elif page == "req_flow":
        render_req_flow()
    elif page == "ops_map":
        render_ops_map()
    elif page == "poc_guide":
        render_poc_guide()
