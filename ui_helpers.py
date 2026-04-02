import streamlit as st  # type: ignore
import streamlit.components.v1 as components  # type: ignore
import base64
import html as _html_mod
import re
from pathlib import Path


def _h(value) -> str:
    """HTML-escape any user-supplied value before injecting into unsafe_allow_html contexts."""
    return _html_mod.escape(str(value), quote=True)


def _safe_filename(name: str, suffix: str = "") -> str:
    """Sanitize a user-supplied string for use as a download filename."""
    safe = re.sub(r'[^\w\s\-]', '', str(name), flags=re.UNICODE).strip()
    safe = re.sub(r'\s+', '_', safe)
    safe = safe[:80]
    return (safe or "document") + suffix


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
