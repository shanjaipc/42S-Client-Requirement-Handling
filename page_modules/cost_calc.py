import streamlit as st  # type: ignore
import streamlit.components.v1 as components  # type: ignore
import csv
import html as _html_mod
import json
import threading
import gspread  # type: ignore
from google.oauth2.credentials import Credentials  # type: ignore
from google.auth.transport.requests import Request  # type: ignore
import os
import pandas as pd  # type: ignore
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from ui_helpers import section_header, page_title
from analytics import (
    log_event,
    EVENT_DOWNLOAD_COST_PDF, EVENT_DOWNLOAD_COST_CSV,
)
from persistence import (
    save_cost_estimate, list_cost_estimates, load_cost_estimate, delete_cost_estimate,
)

LOGO_PATH = str(Path(__file__).parent.parent / "42slogo_top.png")
SCREENSHOT_RATE_DEFAULT = 0.00044   # $/page — editable per site in the UI

_GSHEET_ID       = "1oLHi7Jn9JGP9SDSR5v6Cm02ph82fxO1QI5e7eqE0XyE"
_GSHEET_TAB      = "Sheet1"
_OAUTH_TOKEN_PATH = Path(__file__).parent.parent / "oauth_token.json"
_token_lock = threading.Lock()


def _get_gspread_client():
    with _token_lock:
        with open(_OAUTH_TOKEN_PATH) as f:
            td = json.load(f)
        creds = Credentials(
            token=td.get("token"),
            refresh_token=td["refresh_token"],
            token_uri=td["token_uri"],
            client_id=td["client_id"],
            client_secret=td["client_secret"],
            scopes=td["scopes"],
        )
        if not creds.valid:
            try:
                creds.refresh(Request())
            except Exception as _refresh_err:
                raise RuntimeError(
                    f"Google OAuth token refresh failed: {_refresh_err}. "
                    "Ask an admin to re-authorise the Google Sheets connection."
                ) from _refresh_err
            td["token"] = creds.token
            _tmp = _OAUTH_TOKEN_PATH.with_suffix(".tmp")
            with open(_tmp, "w") as f:
                json.dump(td, f, indent=2)
            os.replace(_tmp, _OAUTH_TOKEN_PATH)
    return gspread.authorize(creds)


def _safe_float(val, default=0.0):
    try:
        return float(str(val).strip()) if str(val).strip() else default
    except (ValueError, TypeError):
        return default


@st.cache_data(ttl=900, show_spinner="Loading rates from Google Sheets…")
def _load_rates_from_gsheet():
    """Fetch crawl cost rates from the Google Sheet. Cached for 5 minutes.

    Sheet columns (one row per domain):
      Domain | Display Name | SKU (No Zip) | SKU (Zip) | Category (No Zip) |
      Category (Zip) | Keyword (No Zip) | Keyword (Zip) |
      Screenshot (No Zip) | Screenshot (Zip) | Updated On | Active
    """
    gc = _get_gspread_client()
    ws = gc.open_by_key(_GSHEET_ID).worksheet(_GSHEET_TAB)
    rows = ws.get_all_records()

    platform_list, platform_display, rates = [], {}, {}
    last_updated = ""
    for row in rows:
        d = str(row.get("Domain", "")).strip()
        if not d:
            continue
        # Skip inactive rows
        active = str(row.get("Active", "✅")).strip()
        if active not in ("✅", "TRUE", "true", "1", "yes", "Yes"):
            continue

        platform_list.append(d)
        platform_display[d] = str(row.get("Display Name", d)).strip()
        rates[d] = {
            "without": {
                "sku":        _safe_float(row.get("SKU (No Zip)"),        0),
                "cat":        _safe_float(row.get("Category (No Zip)"),   0),
                "kw":         _safe_float(row.get("Keyword (No Zip)"),    0),
                "screenshot": _safe_float(row.get("Screenshot (No Zip)"), SCREENSHOT_RATE_DEFAULT),
            },
            "with": {
                "sku":        _safe_float(row.get("SKU (Zip)"),        0),
                "cat":        _safe_float(row.get("Category (Zip)"),   0),
                "kw":         _safe_float(row.get("Keyword (Zip)"),    0),
                "screenshot": _safe_float(row.get("Screenshot (Zip)"), SCREENSHOT_RATE_DEFAULT),
            },
        }
        if not last_updated:
            last_updated = str(row.get("Updated On", "")).strip()

    return platform_list, platform_display, rates, last_updated


def _fmt_cost(v, symbol="$"):
    """Smart cost formatting: fewer decimals for larger values."""
    if v == 0:
        return f"{symbol}0.00"
    if v < 0.01:
        return f"{symbol}{v:.6f}"
    if v < 1:
        return f"{symbol}{v:.4f}"
    if v < 10000:
        return f"{symbol}{v:,.2f}"
    return f"{symbol}{v:,.0f}"


def _generate_cost_pdf(results, grand_total, selected_domains, platform_display, rates_last_updated="",
                       fx=1.0, symbol="$", period="As configured", period_factor_fn=None, pdf_note="",
                       client_name=""):
    """Spreadsheet-style black & white PDF cost estimate."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
    from reportlab.lib import pagesizes  # type: ignore
    from reportlab.lib.units import inch  # type: ignore
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT  # type: ignore
    from reportlab.lib.colors import white, black, HexColor  # type: ignore

    # ── Page setup ────────────────────────────────────────────────────────────
    LM = RM = 0.60 * inch
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=pagesizes.A4,
                            topMargin=0.45*inch, bottomMargin=0.50*inch,
                            leftMargin=LM, rightMargin=RM)
    PW = pagesizes.A4[0] - LM - RM          # usable width ≈ 6.9"

    # ── Palette ───────────────────────────────────────────────────────────────
    C_BLACK  = black
    C_WHITE  = white
    C_DARK   = HexColor("#111111")           # near-black text
    C_GRAY   = HexColor("#555555")           # secondary text
    C_LGRAY  = HexColor("#f0f0f0")           # light row tint / subtotal bg
    C_MGRAY  = HexColor("#dddddd")           # border color
    C_THDR   = black                         # table header bg
    C_SHDR   = HexColor("#333333")           # platform section header bg

    # ── Styles ────────────────────────────────────────────────────────────────
    S = getSampleStyleSheet()
    def _ps(name, **kw):
        return ParagraphStyle(name, parent=S["Normal"], **kw)

    title_s   = _ps("TI", fontSize=18, fontName="Helvetica-Bold", textColor=C_DARK,   leading=22)
    sub_s     = _ps("SU", fontSize=8,  fontName="Helvetica",      textColor=C_GRAY,   leading=11)
    meta_lbl  = _ps("ML", fontSize=7,  fontName="Helvetica-Bold", textColor=C_GRAY,   leading=10)
    meta_val  = _ps("MV", fontSize=8,  fontName="Helvetica-Bold", textColor=C_DARK,   leading=11)
    th_l      = _ps("HL", fontSize=8,  fontName="Helvetica-Bold", textColor=C_WHITE,  leading=10)
    th_c      = _ps("HC", fontSize=8,  fontName="Helvetica-Bold", textColor=C_WHITE,  leading=10, alignment=TA_CENTER)
    th_r      = _ps("HR", fontSize=8,  fontName="Helvetica-Bold", textColor=C_WHITE,  leading=10, alignment=TA_RIGHT)
    td_l      = _ps("DL", fontSize=8.5, textColor=C_DARK,  leading=11)
    td_c      = _ps("DC", fontSize=8.5, textColor=C_DARK,  leading=11, alignment=TA_CENTER)
    td_r      = _ps("DR", fontSize=8.5, textColor=C_DARK,  leading=11, alignment=TA_RIGHT)
    td_rb     = _ps("DB", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_DARK, leading=11, alignment=TA_RIGHT)
    td_muted  = _ps("DM", fontSize=8,  textColor=C_GRAY,  leading=11, alignment=TA_RIGHT)
    sub_lbl   = _ps("SL", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_DARK,  leading=11)
    sub_val   = _ps("SV", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_DARK,  leading=11, alignment=TA_RIGHT)
    plat_hdr  = _ps("PH", fontSize=9.5, fontName="Helvetica-Bold", textColor=C_WHITE, leading=12)
    plat_tot  = _ps("PT", fontSize=9.5, fontName="Helvetica-Bold", textColor=C_WHITE, leading=12, alignment=TA_RIGHT)
    sum_hdr_l = _ps("SHL", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_WHITE, leading=11)
    sum_hdr_r = _ps("SHR", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_WHITE, leading=11, alignment=TA_RIGHT)
    sum_td_l  = _ps("SDL", fontSize=9,   textColor=C_DARK,  leading=12)
    sum_td_r  = _ps("SDR", fontSize=9,   fontName="Helvetica-Bold", textColor=C_DARK, leading=12, alignment=TA_RIGHT)
    gt_lbl    = _ps("GTL", fontSize=10,  fontName="Helvetica-Bold", textColor=C_WHITE, leading=13)
    gt_val    = _ps("GTV", fontSize=12,  fontName="Helvetica-Bold", textColor=C_WHITE, leading=15, alignment=TA_RIGHT)
    foot_s    = _ps("FT",  fontSize=7,   textColor=C_GRAY, leading=10, alignment=TA_CENTER)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _pf(usd, days=None):
        pf = period_factor_fn(days) if (period_factor_fn and days is not None) else 1.0
        v  = usd * fx * pf
        if v == 0:     return f"{symbol}0.00"
        if v < 0.0001: return f"{symbol}{v:.6f}"
        if v < 1:      return f"{symbol}{v:.4f}"
        if v < 10000:  return f"{symbol}{v:,.2f}"
        return         f"{symbol}{v:,.0f}"

    def _cpm(cost_per_crawl, volume):
        if not volume: return "—"
        v = (cost_per_crawl / volume) * 1000 * fx
        if v == 0:    return f"{symbol}0.00"
        if v < 0.001: return f"{symbol}{v:.6f}"
        if v < 1:     return f"{symbol}{v:.4f}"
        return        f"{symbol}{v:,.4f}"

    _period_lbl = {"As configured": "Total", "Monthly": "Monthly", "Annual": "Annual"}.get(period, "Total")
    _gt_avg_days = (sum(r["total_cost"] * r["days"] for r in results) / grand_total) if grand_total else 30

    def _bordered(style_extra=None):
        base = [
            ("BOX",         (0,0),(-1,-1), 0.6, C_DARK),
            ("INNERGRID",   (0,0),(-1,-1), 0.4, C_MGRAY),
            ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",  (0,0),(-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LEFTPADDING", (0,0),(-1,-1), 7),
            ("RIGHTPADDING",(0,0),(-1,-1), 7),
        ]
        if style_extra:
            base += style_extra
        return TableStyle(base)

    el = []

    # ── Header block ─────────────────────────────────────────────────────────
    # Logo cell
    logo_el = []
    if os.path.exists(LOGO_PATH):
        try:
            logo_el.append(Image(LOGO_PATH, width=0.55*inch, height=0.45*inch))
        except Exception:
            pass
    logo_cell = logo_el or [Paragraph("", sub_s)]

    # Title cell
    title_cell = [
        Paragraph("Cost Estimate", title_s),
        Spacer(1, 3),
        Paragraph("42Signals · Analytics Platform", sub_s),
    ]

    # Meta cell (right side)
    _meta = [("DATE", date.today().strftime("%d %b %Y"))]
    if client_name:
        _meta.append(("CLIENT", client_name))
    if rates_last_updated:
        _meta.append(("RATES", rates_last_updated))
    _meta += [("CURRENCY", symbol), ("PERIOD", _period_lbl)]
    meta_rows = [[Paragraph(l, meta_lbl), Paragraph(v, meta_val)] for l, v in _meta]
    meta_t = Table(meta_rows, colWidths=[0.75*inch, 1.10*inch])
    meta_t.setStyle(_bordered())

    hdr_t = Table([[logo_cell, title_cell, meta_t]],
                  colWidths=[0.75*inch, PW - 0.75*inch - 1.90*inch, 1.90*inch])
    hdr_t.setStyle(TableStyle([
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("RIGHTPADDING",(0,0),(-1,-1), 0),
        ("TOPPADDING",  (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ("LINEBELOW",   (0,0),(-1,-1), 1.0, C_DARK),
    ]))
    el.append(hdr_t)
    el.append(Spacer(1, 0.18*inch))

    # ── Column widths: Crawl Type | Vol | Freq×Days | Zip | CPM | Cost/Crawl | Total ──
    CW = [2.00*inch, 0.82*inch, 0.95*inch, 0.65*inch, 0.75*inch, 0.88*inch, 0.85*inch]

    # ── Per-platform tables ───────────────────────────────────────────────────
    for domain in selected_domains:
        dr = [r for r in results if r["domain"] == domain]
        if not dr: continue
        disp          = platform_display.get(domain, domain)
        crawl_usd     = sum(r["total_cost"] for r in dr)
        ss_usd        = sum(r.get("screenshot_total", 0) for r in dr)
        dom_total_usd = crawl_usd + ss_usd
        avg_days      = (sum(r["total_cost"] * r["days"] for r in dr) / crawl_usd) if crawl_usd else 30
        dom_total_str = _pf(dom_total_usd, avg_days)

        # Platform header row (dark, spans all cols)
        plat_row = Table(
            [[Paragraph(f"{disp}  ({domain})", plat_hdr),
              Paragraph(f"Platform Total:  {dom_total_str}", plat_tot)]],
            colWidths=[sum(CW)*0.60, sum(CW)*0.40]
        )
        plat_row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), C_SHDR),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("RIGHTPADDING",  (0,0),(-1,-1), 8),
            ("BOX",           (0,0),(-1,-1), 0.6, C_DARK),
        ]))

        # Column header row
        col_hdr = [
            Paragraph("Crawl Type",          th_l),
            Paragraph("Vol/Crawl",           th_c),
            Paragraph("Freq × Days",    th_c),
            Paragraph("Zip",                 th_c),
            Paragraph(f"CPM ({symbol})",     th_r),
            Paragraph("Cost/Crawl",          th_r),
            Paragraph(f"{_period_lbl} Cost", th_r),
        ]
        rows = [col_hdr]
        for r in dr:
            rows.append([
                Paragraph(_html_mod.escape(r["crawl_type"]), td_l),
                Paragraph(f"{r['volume_per_crawl']:,}", td_c),
                Paragraph(f"{r['freq']}×/day × {r['days']}d", td_c),
                Paragraph(r["zip_mode"].replace(" Zipcode",""), td_c),
                Paragraph(_cpm(r["cost_per_crawl"], r["volume_per_crawl"]), td_muted),
                Paragraph(_pf(r["cost_per_crawl"]), td_r),
                Paragraph(_pf(r["total_cost"], r["days"]), td_rb),
            ])
        if ss_usd > 0:
            _ss_rate = dr[0].get("screenshot_rate", SCREENSHOT_RATE_DEFAULT)
            rows.append([
                Paragraph("⤷  Screenshots", _ps("SS", fontSize=8, fontName="Helvetica-Oblique", textColor=C_GRAY, leading=11)),
                Paragraph("", td_c), Paragraph("", td_c), Paragraph("", td_c),
                Paragraph(f"{symbol}{_ss_rate*1000:.4f}", td_muted),
                Paragraph("", td_c),
                Paragraph(_pf(ss_usd, avg_days), td_rb),
            ])
        rows.append([
            Paragraph("Platform Total", sub_lbl),
            Paragraph("", td_c), Paragraph("", td_c), Paragraph("", td_c),
            Paragraph("", td_c), Paragraph("", td_c),
            Paragraph(dom_total_str, sub_val),
        ])

        data_t = Table(rows, colWidths=CW, repeatRows=1)
        n = len(rows)
        data_t.setStyle(_bordered([
            ("BACKGROUND",    (0,0), (-1,0),   C_THDR),
            ("BACKGROUND",    (0,-1),(-1,-1),  C_LGRAY),
            ("LINEABOVE",     (0,-1),(-1,-1),  0.6, C_DARK),
            ("LINEBELOW",     (0,-1),(-1,-1),  0.6, C_DARK),
        ]))
        el.append(KeepTogether([plat_row, data_t]))
        el.append(Spacer(1, 0.18*inch))

    # ── Platform summary ──────────────────────────────────────────────────────
    sum_rows = [[
        Paragraph("Platform Summary", sum_hdr_l),
        Paragraph(f"{_period_lbl} Cost ({symbol})", sum_hdr_r),
    ]]
    for domain in selected_domains:
        _dr  = [r for r in results if r["domain"] == domain]
        _du  = sum(r["total_cost"] + r.get("screenshot_total", 0) for r in _dr)
        if _du == 0: continue
        _cu  = sum(r["total_cost"] for r in _dr)
        _ad  = (sum(r["total_cost"] * r["days"] for r in _dr) / _cu) if _cu else 30
        sum_rows.append([
            Paragraph(_html_mod.escape(platform_display.get(domain, domain)), sum_td_l),
            Paragraph(_pf(_du, _ad), sum_td_r),
        ])
    # Grand total row
    sum_rows.append([
        Paragraph(f"Grand Total  ·  {_period_lbl}", gt_lbl),
        Paragraph(_pf(grand_total, _gt_avg_days), gt_val),
    ])

    sum_t = Table(sum_rows, colWidths=[PW * 0.70, PW * 0.30])
    n = len(sum_rows)
    sum_t.setStyle(_bordered([
        ("BACKGROUND",    (0,0), (-1,0),   C_THDR),
        ("BACKGROUND",    (0,-1),(-1,-1),  C_BLACK),
        ("LINEABOVE",     (0,-1),(-1,-1),  0.8, C_BLACK),
    ]))
    el.append(sum_t)
    el.append(Spacer(1, 0.20*inch))

    # ── Footer ────────────────────────────────────────────────────────────────
    el.append(Paragraph(
        "Rates are benchmarks derived from internal crawl cost data. "
        "Actual costs may vary based on site complexity, proxy usage and infrastructure load. "
        "This estimate is for internal planning purposes only. "
        "CPM = cost per 1,000 records.",
        foot_s,
    ))

    doc.build(el)
    buffer.seek(0)
    return buffer.read()


def render_cost_calculator():
    _hdr_col, _new_col = st.columns([5, 1])
    with _hdr_col:
        page_title(
            "Cost Calculator",
            "Select platforms, configure crawl types per domain, and get a detailed cost estimate with PDF/CSV download."
        )
    with _new_col:
        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        if st.button("✚ New Estimate", key="_cc_new_btn", width="stretch"):
            _cc_keep = {"cc_gen_top", "cc_currency", "cc_period", "cc_fx_rate"}
            for _k in list(st.session_state.keys()):
                if isinstance(_k, str) and _k.startswith("cc_") and _k not in _cc_keep:
                    del st.session_state[_k]
            st.session_state["cc_show_results"] = False
            st.session_state.pop("_editing_cost_file", None)
            st.rerun()

    # ── Editing banner ────────────────────────────────────────────────────────
    if st.session_state.get("_editing_cost_file"):
        _ec = st.session_state["_editing_cost_file"]
        st.markdown(
            f'<div style="background:#eff6ff;border:1px solid #93c5fd;border-left:4px solid #3b82f6;'
            f'border-radius:8px;padding:10px 14px;font-family:Inter,sans-serif;font-size:0.83rem;'
            f'color:#1e40af;margin-bottom:12px;">'
            f'✏️ Editing saved estimate: <b>{_html_mod.escape(_ec)}</b>. Use <b>✚ New Estimate</b> to start fresh.</div>',
            unsafe_allow_html=True,
        )

    # ── Saved estimates panel ─────────────────────────────────────────────────
    _saved_ests = list_cost_estimates()
    if _saved_ests:
        with st.expander(f"📂  Saved Estimates ({len(_saved_ests)})", expanded=False):
            for _est in _saved_ests:
                _ec1, _ec2, _ec3, _ec4 = st.columns([3, 2, 1, 1])
                with _ec1:
                    st.markdown(
                        f'<div style="font-size:0.88rem;font-weight:600;color:#0f172a;'
                        f'font-family:Inter,sans-serif;">{_html_mod.escape(_est["client_name"])}</div>'
                        f'<div style="font-size:0.75rem;color:#94a3b8;">'
                        f'by {_html_mod.escape(_est["saved_by"])} · {_est["saved_at"][:16].replace("T"," ")}</div>',
                        unsafe_allow_html=True,
                    )
                with _ec2:
                    st.markdown(
                        f'<div style="font-size:0.9rem;font-weight:700;color:#dc2626;'
                        f'font-family:Inter,sans-serif;margin-top:6px;">'
                        f'{_fmt_cost(_est["grand_total"])}</div>',
                        unsafe_allow_html=True,
                    )
                with _ec3:
                    if st.button("✏️ Edit", key=f"_cc_edit_{_est['filename']}"):
                        load_cost_estimate(_est["filename"])
                with _ec4:
                    if st.button("🗑️", key=f"_cc_del_{_est['filename']}"):
                        delete_cost_estimate(_est["filename"])
                        st.rerun()
                st.markdown("<hr style='margin:4px 0;border-color:#f1f5f9;'>", unsafe_allow_html=True)

    # ── Load domain/rate config from Google Sheets ────────────────────────────
    try:
        PLATFORM_LIST, PLATFORM_DISPLAY, RATES, _rates_last_updated = _load_rates_from_gsheet()
    except Exception as e:
        st.error(f"Failed to load rates from Google Sheets: {e}")
        return

    if not PLATFORM_LIST:
        st.warning(
            "No domains found in the Google Sheet. "
            f"Add rows to the **'{_GSHEET_TAB}'** tab in the rates sheet."
        )
        return

    # Remove stale selections
    _saved_sel = st.session_state.get("cc_selected_domains", [])
    _stale = [d for d in _saved_sel if d not in PLATFORM_LIST]
    if _stale:
        st.warning(
            f"The following platform(s) are no longer in the rate config and have been removed from your selection: "
            + ", ".join(_stale)
        )
        st.session_state["cc_selected_domains"] = [d for d in _saved_sel if d in PLATFORM_LIST]

    CRAWL_TYPES = [
        "Category Based", "SKU / Product URL Based", "SOS (Share of Search)",
        "Reviews", "Keyword Level", "Festive Sales Day Crawl", "Banner Crawl",
    ]
    CRAWL_ICONS = {
        "Category Based": "🗂️", "SKU / Product URL Based": "📦",
        "SOS (Share of Search)": "🔍", "Reviews": "⭐",
        "Keyword Level": "🔑", "Festive Sales Day Crawl": "🎉", "Banner Crawl": "🖼️",
    }
    CRAWL_DESC = {
        "Category Based":          "Browse category pages with pagination",
        "SKU / Product URL Based": "Direct product URL / API fetch",
        "SOS (Share of Search)":   "Search result pages crawled by keyword",
        "Reviews":                 "Product review page crawling",
        "Keyword Level":           "Keyword-based search result crawling",
        "Festive Sales Day Crawl": "High-freq category crawl for sale events (1.2× rate)",
        "Banner Crawl":            "Promotional / banner URL monitoring ($0.001/URL/crawl)",
    }

    def get_rate(domain, crawl_type, with_zip):
        if domain not in RATES:
            return 0.0
        key = "with" if with_zip else "without"
        r = RATES[domain].get(key, RATES[domain].get("without", {}))
        if crawl_type == "Category Based":           return r.get("cat", 0.0)
        if crawl_type == "Festive Sales Day Crawl":  return r.get("cat", 0.0) * 1.2
        if crawl_type == "SKU / Product URL Based":  return r.get("sku", 0.0)
        if crawl_type == "Reviews":                  return r.get("sku", 0.0) * 0.7
        if crawl_type in ("SOS (Share of Search)", "Keyword Level"): return r.get("kw", 0.0)
        if crawl_type == "Banner Crawl":             return 0.001
        return 0.0

    def compute_volume(crawl_type, a, b):
        if crawl_type in ("Category Based", "Festive Sales Day Crawl"): return a * b
        if crawl_type == "SKU / Product URL Based":  return a
        if crawl_type == "Reviews":                  return a
        if crawl_type in ("SOS (Share of Search)", "Keyword Level"): return a * b
        if crawl_type == "Banner Crawl":             return a
        return 0

    # ── Step 1: Platform Selection ────────────────────────────────────────────
    section_header("🌐", "Step 1 — Select Platforms")
    selected_domains = st.multiselect(
        "Choose platforms to include in this estimate",
        options=PLATFORM_LIST,
        format_func=lambda x: PLATFORM_DISPLAY.get(x, x),
        key="cc_selected_domains",
        placeholder="Select one or more platforms...",
    )

    if not selected_domains:
        st.markdown("""
        <div style="text-align:center;padding:56px 20px;color:#94a3b8;font-family:'Inter',sans-serif;
        background:white;border-radius:14px;border:2px dashed #e5e7eb;margin-top:20px;">
            <div style="font-size:2.8rem;margin-bottom:14px;">📊</div>
            <div style="font-size:1rem;font-weight:600;color:#374151;">Select platforms above to begin</div>
            <div style="font-size:0.82rem;margin-top:6px;">
                Choose one or more platforms, configure crawl types for each,<br>then click Generate.
            </div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Step 2: Per-Domain Configuration ─────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _step2_hdr, _step2_btn = st.columns([3, 1])
    with _step2_hdr:
        section_header("⚙️", "Step 2 — Configure Crawl Types")
    with _step2_btn:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("📊 Generate ↓", key="cc_gen_top", width="stretch", type="primary"):
            st.session_state.pop("_cc_pdf_cache", None)
            st.session_state.pop("_cc_csv_cache", None)
            st.session_state["cc_show_results"] = True

    for domain in selected_domains:
        display_name = PLATFORM_DISPLAY.get(domain, domain)

        with st.expander(f"**{display_name}**  ·  {domain}", expanded=True):
            col_ct, col_zip, col_ss = st.columns([3, 1, 1])
            with col_ct:
                selected_cts = st.multiselect(
                    "Crawl types",
                    options=CRAWL_TYPES,
                    format_func=lambda x: f"{CRAWL_ICONS.get(x, '')}  {x}",
                    key=f"cc_ct_{domain}",
                    placeholder="Select crawl type(s)...",
                )
            with col_zip:
                st.radio("Zipcode", ["Without Zipcode", "With Zipcode", "Both"],
                         key=f"cc_zip_{domain}")
            with col_ss:
                st.radio("Screenshot", ["Without Screenshot", "With Screenshot"],
                         key=f"cc_ss_mode_{domain}")

            _zip_mode_now = st.session_state.get(f"cc_zip_{domain}", "Without Zipcode")
            _ss_mode_now  = st.session_state.get(f"cc_ss_mode_{domain}", "Without Screenshot")
            _extra_cols = []
            if _zip_mode_now in ("With Zipcode", "Both"):
                _extra_cols.append("zip")
            if _ss_mode_now == "With Screenshot":
                _extra_cols.append("ss")

            if _extra_cols:
                _ecol_widths = [1] * len(_extra_cols) + [4 - len(_extra_cols)]
                _ecols = st.columns(_ecol_widths)
                _ci = 0
                if "zip" in _extra_cols:
                    with _ecols[_ci]:
                        st.number_input("Number of Zipcodes", min_value=1, value=1, step=1,
                                        key=f"cc_zipcount_{domain}")
                    _ci += 1
                if "ss" in _extra_cols:
                    with _ecols[_ci]:
                        st.number_input("Screenshot Pages/Crawl", min_value=1, value=500, step=50,
                                        key=f"cc_ss_vol_{domain}")
                    _ci += 1
                    with _ecols[_ci]:
                        _default_ss_rate = RATES.get(domain, {}).get("without", {}).get("screenshot", SCREENSHOT_RATE_DEFAULT)
                        st.number_input("📸 Rate ($/page)", min_value=0.0, max_value=0.01,
                                        value=float(st.session_state.get(f"cc_{domain}_ss_rate", _default_ss_rate)),
                                        step=0.00001, format="%.5f",
                                        key=f"cc_{domain}_ss_rate")

            if not selected_cts:
                st.caption("No crawl types selected for this platform.")
                continue

            for ct in selected_cts:
                st.markdown(
                    f'<div style="font-size:0.82rem;font-weight:600;color:#374151;'
                    f'margin:14px 0 6px 0;font-family:\'Inter\',sans-serif;">'
                    f'{CRAWL_ICONS.get(ct, "")} {ct}'
                    f'<span style="font-size:0.72rem;color:#9ca3af;font-weight:400;'
                    f'margin-left:8px;">— {CRAWL_DESC.get(ct, "")}</span></div>',
                    unsafe_allow_html=True,
                )
                if ct in ("Category Based", "Festive Sales Day Crawl"):
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.number_input("Category URLs",   min_value=1, value=100, step=10, key=f"cc_{domain}_{ct}_a")
                    with c2: st.number_input("SKUs/Category",   min_value=1, value=50,  step=5,  key=f"cc_{domain}_{ct}_b")
                    with c3: st.number_input("Crawls/day",      min_value=1, value=1,   step=1,  key=f"cc_{domain}_{ct}_c")
                    with c4: st.number_input("Duration (days)", min_value=1, value=30,  step=1,  key=f"cc_{domain}_{ct}_d")
                elif ct == "SKU / Product URL Based":
                    c1, c2, c3 = st.columns(3)
                    with c1: st.number_input("Number of SKUs",  min_value=1, value=1000, step=100, key=f"cc_{domain}_{ct}_a")
                    with c2: st.number_input("Crawls/day",      min_value=1, value=1,    step=1,   key=f"cc_{domain}_{ct}_c")
                    with c3: st.number_input("Duration (days)", min_value=1, value=30,   step=1,   key=f"cc_{domain}_{ct}_d")
                elif ct == "Reviews":
                    c1, c2, c3 = st.columns(3)
                    with c1: st.number_input("Number of Products", min_value=1, value=500, step=50, key=f"cc_{domain}_{ct}_a")
                    with c2: st.number_input("Crawls/day",         min_value=1, value=1,   step=1,  key=f"cc_{domain}_{ct}_c")
                    with c3: st.number_input("Duration (days)",    min_value=1, value=30,  step=1,  key=f"cc_{domain}_{ct}_d")
                elif ct in ("SOS (Share of Search)", "Keyword Level"):
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.number_input("Keywords",          min_value=1, value=200, step=10, key=f"cc_{domain}_{ct}_a")
                    with c2: st.number_input("SKUs/Keyword",      min_value=1, value=60,  step=5,  key=f"cc_{domain}_{ct}_b")
                    with c3: st.number_input("Crawls/day",        min_value=1, value=1,   step=1,  key=f"cc_{domain}_{ct}_c")
                    with c4: st.number_input("Duration (days)",   min_value=1, value=30,  step=1,  key=f"cc_{domain}_{ct}_d")
                elif ct == "Banner Crawl":
                    c1, c2, c3 = st.columns(3)
                    with c1: st.number_input("Banner URLs",       min_value=1, value=20,  step=5,  key=f"cc_{domain}_{ct}_a")
                    with c2: st.number_input("Crawls/day",        min_value=1, value=1,   step=1,  key=f"cc_{domain}_{ct}_c")
                    with c3: st.number_input("Duration (days)",   min_value=1, value=30,  step=1,  key=f"cc_{domain}_{ct}_d")
                st.markdown('<div style="height:1px;background:#f1f5f9;margin:6px 0 2px 0;"></div>',
                            unsafe_allow_html=True)


    # ── Generate button ───────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    g1, g2 = st.columns([3, 1])
    with g1:
        st.text_input(
            "Client Name",
            placeholder="e.g. Hindustan Unilever",
            key="cc_client_name",
        )
    with g2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("📊  Generate Estimate", width="stretch", type="primary"):
            st.session_state["cc_show_results"] = True
            st.session_state.pop("_cc_pdf_cache", None)
            st.session_state.pop("_cc_csv_cache", None)
            components.html(
                "<script>window.parent.document.querySelector('[data-testid=\"stAppViewContainer\"] > section')?.scrollTo({top:999999,behavior:'smooth'});</script>",
                height=0,
            )

    if not st.session_state.get("cc_show_results"):
        return

    # ── Compute results ───────────────────────────────────────────────────────
    results = []
    for domain in selected_domains:
        display_name = PLATFORM_DISPLAY.get(domain, domain)
        selected_cts = st.session_state.get(f"cc_ct_{domain}", [])
        zip_mode = st.session_state.get(f"cc_zip_{domain}", "Without Zipcode")
        zip_variants = (
            [("Without Zipcode", False), ("With Zipcode", True)]
            if zip_mode == "Both"
            else [(zip_mode, zip_mode == "With Zipcode")]
        )

        zip_count = st.session_state.get(f"cc_zipcount_{domain}", 1)
        ss_mode   = st.session_state.get(f"cc_ss_mode_{domain}", "Without Screenshot")
        ss_vol    = st.session_state.get(f"cc_ss_vol_{domain}", 0)
        _sheet_ss_rate = RATES.get(domain, {}).get("without", {}).get("screenshot", SCREENSHOT_RATE_DEFAULT)
        ss_rate   = st.session_state.get(f"cc_{domain}_ss_rate", _sheet_ss_rate)
        for ct in selected_cts:
            a  = st.session_state.get(f"cc_{domain}_{ct}_a", 0)
            b  = st.session_state.get(f"cc_{domain}_{ct}_b", 0)
            c_ = st.session_state.get(f"cc_{domain}_{ct}_c", 1)
            d  = st.session_state.get(f"cc_{domain}_{ct}_d", 30)
            volume = compute_volume(ct, a, b)
            if volume == 0 and ct != "Banner Crawl":
                st.warning(f"**{display_name} — {ct}**: volume is 0. Check your inputs (e.g. number of SKUs / categories / keywords).")
            for zm, wz in zip_variants:
                effective_volume = volume * zip_count if wz else volume
                rate  = get_rate(domain, ct, wz)
                cpc   = effective_volume * rate
                total = cpc * c_ * d
                results.append({
                    "domain": domain, "display": display_name, "crawl_type": ct,
                    "volume_per_crawl": effective_volume, "freq": c_, "days": d,
                    "zip_mode": zm, "rate": rate,
                    "cost_per_crawl": cpc, "total_cost": total,
                    "screenshot_rate": ss_rate,
                    "screenshot_total": (ss_vol * ss_rate * c_ * d) if ss_mode == "With Screenshot" else 0,
                })

    if not results:
        st.session_state["cc_show_results"] = False
        st.warning("No crawl types configured. Select crawl types for at least one platform.")
        return

    st.session_state["_cc_last_results"] = results

    # ── Results header ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📊", "Cost Estimate Results")

    grand_total_usd = sum(r["total_cost"] + r.get("screenshot_total", 0) for r in results)

    # ── View controls: Currency + Period ──────────────────────────────────────
    _vc1, _vc2, _vc3, _vc4 = st.columns([1.2, 1, 1.2, 2.6])
    with _vc1:
        _currency = st.radio("Currency", ["USD ($)", "INR (₹)"],
                             key="cc_currency", horizontal=True)
    with _vc2:
        _use_inr = _currency == "INR (₹)"
        if _use_inr:
            _fx = st.number_input("₹ per $1", min_value=1.0, value=st.session_state.get("cc_fx_rate", 84.0),
                                  step=0.5, key="cc_fx_rate", label_visibility="collapsed")
        else:
            _fx = 1.0
    with _vc3:
        _period = st.radio("View as", ["As configured", "Monthly", "Annual"],
                           key="cc_period", horizontal=False)

    _sym = "₹" if _use_inr else "$"

    def _period_factor(days):
        """Scale factor from configured duration to selected period."""
        if _period == "Monthly":
            return 30 / max(days, 1)
        if _period == "Annual":
            return 365 / max(days, 1)
        return 1.0

    def _fmt_c(usd_val, days=None):
        """Format a USD cost in the selected currency and period."""
        v = usd_val * _fx * (_period_factor(days) if days is not None else 1.0)
        if v == 0:           return f"{_sym}0.00"
        if v < 0.01:         return f"{_sym}{v:.6f}"
        if v < 1:            return f"{_sym}{v:.4f}"
        if v < 10000:        return f"{_sym}{v:,.2f}"
        return f"{_sym}{v:,.0f}"

    def _cost_cell_v(usd_val, days=None):
        v = usd_val * _fx * (_period_factor(days) if days is not None else 1.0)
        if v == 0:     return f'<span style="color:#16a34a;font-weight:700;">{_sym}0.00</span>'
        if v < 1:      return f'<span style="color:#ca8a04;font-weight:700;">{_fmt_c(usd_val, days)}</span>'
        if v < 100:    return f'<span style="color:#ea580c;font-weight:700;">{_fmt_c(usd_val, days)}</span>'
        return         f'<span style="color:#dc2626;font-weight:700;">{_fmt_c(usd_val, days)}</span>'

    def _cpm(usd_per_crawl, volume):
        """Cost per 1000 records (CPM) in selected currency."""
        if not volume:
            return "—"
        v = (usd_per_crawl / volume) * 1000 * _fx
        if v == 0:    return f"{_sym}0.00"
        if v < 0.001: return f"{_sym}{v:.6f}"
        if v < 1:     return f"{_sym}{v:.4f}"
        return        f"{_sym}{v:,.4f}"

    _period_label = {"As configured": "Total", "Monthly": "Monthly", "Annual": "Annual"}[_period]
    if grand_total_usd == 0:
        st.info("All configured crawl types have a $0 rate. Check that the platforms and crawl types are correct, or update the rates in the Google Sheet.")

    # Correct period-adjusted grand total: sum each row's period-scaled cost
    _gt_period_val = sum(
        (r["total_cost"] + r.get("screenshot_total", 0)) * _fx * _period_factor(r["days"])
        for r in results
    )
    _gt_display = _fmt_cost(_gt_period_val, _sym)

    s1, s2, s3, s4, s5 = st.columns(5)
    for col, lbl, val, accent in [
        (s1, f"Grand Total ({_currency.split()[0]}) — {_period_label}", _gt_display, "#ef4444"),
        (s2, "Platforms",          str(len(set(r["domain"] for r in results))), "#1f2937"),
        (s3, "Crawl Configs",      str(len(results)),                           "#1f2937"),
        (s4, "Calculated On",      datetime.now().strftime("%d %b %Y"),         "#1f2937"),
        (s5, "Rates Last Updated", _html_mod.escape(_rates_last_updated),        "#0369a1"),
    ]:
        with col:
            st.markdown(f"""
            <div style="background:white;border-radius:12px;padding:16px 18px;
            border-left:4px solid {accent};box-shadow:0 2px 8px rgba(0,0,0,0.07);
            font-family:'Inter',sans-serif;">
                <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
                letter-spacing:0.09em;font-weight:700;">{lbl}</div>
                <div style="font-size:1.15rem;font-weight:700;color:#0f172a;margin-top:5px;">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Per-platform result tables ────────────────────────────────────────────
    for domain in selected_domains:
        domain_results = [r for r in results if r["domain"] == domain]
        if not domain_results:
            continue
        display_name = PLATFORM_DISPLAY.get(domain, domain)
        _dom_crawl_usd   = sum(r["total_cost"] for r in domain_results)
        _dom_ss_usd      = sum(r.get("screenshot_total", 0) for r in domain_results)
        domain_total_usd = _dom_crawl_usd + _dom_ss_usd
        _dom_avg_days    = sum(r["total_cost"] * r["days"] for r in domain_results) / _dom_crawl_usd if _dom_crawl_usd else 30
        domain_total_disp = _fmt_c(domain_total_usd, _dom_avg_days)

        _period_note = "" if _period == "As configured" else f" <span style='font-size:0.72rem;color:#fbbf24;'>({_period})</span>"
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1f2937 0%,#374151 100%);
        border-radius:12px 12px 0 0;padding:12px 18px;display:flex;
        justify-content:space-between;align-items:center;font-family:'Inter',sans-serif;">
            <div style="font-size:0.95rem;font-weight:700;color:white;">
                {_html_mod.escape(display_name)}
                <span style="font-size:0.75rem;font-weight:400;color:#9ca3af;margin-left:6px;">({_html_mod.escape(domain)})</span>
            </div>
            <div style="font-size:0.9rem;font-weight:700;color:#fde68a;">
                Platform Total: {domain_total_disp}{_period_note}
            </div>
        </div>""", unsafe_allow_html=True)

        rows_html = ""
        for i, r in enumerate(domain_results):
            bg   = "#ffffff" if i % 2 == 0 else "#f9fafb"
            icon = CRAWL_ICONS.get(r["crawl_type"], "")
            _cpm_val = _cpm(r["cost_per_crawl"], r["volume_per_crawl"])
            _total_disp = _cost_cell_v(r["total_cost"], r["days"])
            _cpc_disp   = _cost_cell_v(r["cost_per_crawl"])
            rows_html += (
                f'<tr style="background:{bg};border-bottom:1px solid #f1f5f9;">'
                f'<td style="padding:10px 16px;font-size:0.875rem;color:#0f172a;font-weight:500;">{icon} {r["crawl_type"]}</td>'
                f'<td style="padding:10px 16px;text-align:center;font-size:0.8rem;color:#374151;">{r["volume_per_crawl"]:,}</td>'
                f'<td style="padding:10px 16px;text-align:center;font-size:0.8rem;color:#374151;">{r["freq"]}×/day</td>'
                f'<td style="padding:10px 16px;text-align:center;font-size:0.8rem;color:#374151;">{r["days"]} days</td>'
                f'<td style="padding:10px 16px;text-align:center;font-size:0.75rem;color:#6b7280;">{r["zip_mode"].replace(" Zipcode","")}</td>'
                f'<td style="padding:10px 16px;text-align:center;font-size:0.78rem;color:#6366f1;font-weight:600;">{_cpm_val}</td>'
                f'<td style="padding:10px 16px;text-align:right;">{_cpc_disp}</td>'
                f'<td style="padding:10px 16px;text-align:right;">{_total_disp}</td>'
                f'</tr>'
            )

        # Screenshot row (if any rate is set for this domain)
        if _dom_ss_usd > 0:
            _ss_r        = domain_results[0].get("screenshot_rate", SCREENSHOT_RATE_DEFAULT)
            _ss_period   = sum(r.get("screenshot_total", 0) * _fx * _period_factor(r["days"]) for r in domain_results)
            _ss_disp     = _fmt_c(_ss_period)
            _ss_pages    = sum(r.get("screenshot_total", 0) / _ss_r for r in domain_results) if _ss_r > 0 else 0
            rows_html += (
                f'<tr style="background:#eff6ff;border-bottom:1px solid #dbeafe;">'
                f'<td style="padding:9px 16px;font-size:0.85rem;color:#1d4ed8;font-weight:500;font-style:italic;">📸 Screenshots</td>'
                f'<td style="padding:9px 16px;text-align:center;font-size:0.8rem;color:#1d4ed8;">{int(_ss_pages):,} pages</td>'
                f'<td style="padding:9px 16px;text-align:center;font-size:0.8rem;color:#6b7280;">—</td>'
                f'<td style="padding:9px 16px;text-align:center;font-size:0.8rem;color:#6b7280;">—</td>'
                f'<td style="padding:9px 16px;text-align:center;font-size:0.75rem;color:#6b7280;">—</td>'
                f'<td style="padding:9px 16px;text-align:center;font-size:0.78rem;color:#1d4ed8;font-weight:600;">{_sym}{_ss_r*1000:.4f} CPM</td>'
                f'<td style="padding:9px 16px;text-align:right;font-size:0.8rem;color:#1d4ed8;">—</td>'
                f'<td style="padding:9px 16px;text-align:right;font-size:0.85rem;font-weight:700;color:#1d4ed8;">{_ss_disp}</td>'
                f'</tr>'
            )

        th = ("padding:9px 16px;font-size:0.7rem;text-transform:uppercase;"
              "letter-spacing:0.1em;color:#64748b;font-weight:700;background:#f8fafc;")
        st.markdown(f"""
        <div style="border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;
        overflow:hidden;margin-bottom:24px;box-shadow:0 4px 12px rgba(0,0,0,0.06);">
        <table style="width:100%;border-collapse:collapse;font-family:'Inter',sans-serif;">
        <thead><tr style="border-bottom:2px solid #e2e8f0;">
            <th style="{th}text-align:left;">Crawl Type</th>
            <th style="{th}text-align:center;">Volume/Crawl</th>
            <th style="{th}text-align:center;">Frequency</th>
            <th style="{th}text-align:center;">Duration</th>
            <th style="{th}text-align:center;">Zipcode</th>
            <th style="{th}text-align:center;">CPM ({_sym})</th>
            <th style="{th}text-align:right;">Cost/Crawl</th>
            <th style="{th}text-align:right;">{_period_label} Cost</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
        </table>
        <div style="padding:6px 16px 8px 16px;font-size:0.72rem;color:#94a3b8;
        font-family:'Inter',sans-serif;border-top:1px solid #f1f5f9;">
            CPM = cost per 1,000 records · Rates last updated: {_html_mod.escape(_rates_last_updated)}
            {f" · 1 USD = {_sym}{_fx:,.2f}" if _use_inr else ""}
            {f" · Showing {_period.lower()} run-rate" if _period != "As configured" else ""}
        </div>
        </div>""", unsafe_allow_html=True)

    # ── Scenario Comparison ───────────────────────────────────────────────────
    _saved_scenarios = st.session_state.get("cc_saved_scenarios", {})
    if len(_saved_scenarios) >= 2:
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("🗂️", "Scenario Comparison")

        _all_keys = sorted({(r["display"], r["crawl_type"], r["zip_mode"])
                            for sc in _saved_scenarios.values()
                            for r in sc.get("results", [])})
        _comp_rows = []
        for _disp, _ct, _zm in _all_keys:
            _row = {"Platform": _disp, "Crawl Type": _ct, "Zipcode": _zm}
            for _sc_name, _sc_data in _saved_scenarios.items():
                _match = next(
                    (r for r in _sc_data.get("results", [])
                     if r["display"] == _disp and r["crawl_type"] == _ct and r["zip_mode"] == _zm),
                    None,
                )
                _row[_sc_name] = _fmt_cost(_match['total_cost'] * _fx, _sym) if _match else "—"
            _comp_rows.append(_row)

        if _comp_rows:
            st.dataframe(pd.DataFrame(_comp_rows), width="stretch", hide_index=True)

            _gt_row = {"Platform": "**Grand Total**", "Crawl Type": "", "Zipcode": ""}
            for _sc_name, _sc_data in _saved_scenarios.items():
                _gt = sum(r["total_cost"] for r in _sc_data.get("results", []))
                _gt_row[_sc_name] = _fmt_cost(_gt * _fx, _sym)
            st.dataframe(pd.DataFrame([_gt_row]), width="stretch", hide_index=True)

        if st.button("🗑️  Clear All Scenarios", key="cc_clear_scenarios"):
            st.session_state["cc_saved_scenarios"] = {}
            st.rerun()

    elif len(_saved_scenarios) == 1:
        st.caption("Save one more scenario to enable side-by-side comparison.")

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📥", "Download Estimate")
    dl1, dl2, _ = st.columns([1, 1, 2])

    _cur_label   = _currency.split()[0]
    _pdf_note    = f"Currency: {_cur_label}" + (f" (1 USD = {_sym}{_fx:,.2f})" if _use_inr else "") + f"  ·  Period: {_period}"
    _client_name = st.session_state.get("cc_client_name", "").strip()
    if "_cc_pdf_cache" not in st.session_state:
        with st.spinner("Building PDF…"):
            st.session_state["_cc_pdf_cache"] = _generate_cost_pdf(
                results, grand_total_usd, selected_domains, PLATFORM_DISPLAY, _rates_last_updated,
                fx=_fx, symbol=_sym, period=_period, period_factor_fn=_period_factor, pdf_note=_pdf_note,
                client_name=_client_name,
            )
    pdf_bytes = st.session_state["_cc_pdf_cache"]
    with dl1:
        if st.download_button(
            "⬇️  Download PDF",
            data=pdf_bytes,
            file_name=f"cost_estimate_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            width="stretch",
        ):
            log_event(EVENT_DOWNLOAD_COST_PDF, st.session_state.get("current_user", ""), st.session_state.get("analytics_sid", ""), "cost_calc")

    if "_cc_csv_cache" not in st.session_state:
        _csv_cur  = _cur_label
        _csv_hdr  = f"Platform,Domain,Crawl Type,Volume/Crawl,Crawls/day,Days,Zipcode,CPM ({_csv_cur}),Cost/Crawl ({_csv_cur}),{_period_label} Cost ({_csv_cur})"
        _csv_lines = [_csv_hdr]
        for r in results:
            _pf_r   = _period_factor(r["days"])
            _cpc_r  = r["cost_per_crawl"] * _fx
            _tot_r  = r["total_cost"] * _fx * _pf_r
            _cpm_r  = (r["cost_per_crawl"] / r["volume_per_crawl"] * 1000 * _fx) if r["volume_per_crawl"] else 0
            _csv_lines.append(
                f'{r["display"]},{r["domain"]},{r["crawl_type"]},'
                f'{r["volume_per_crawl"]},{r["freq"]},{r["days"]},{r["zip_mode"]},'
                f'{_cpm_r:.6f},{_cpc_r:.6f},{_tot_r:.6f}'
            )
        _gt_csv = sum((r["total_cost"] + r.get("screenshot_total", 0)) * _fx * _period_factor(r["days"]) for r in results)
        _csv_lines += ["", f'Grand Total,,,,,,,,,{_gt_csv:.6f}']
        st.session_state["_cc_csv_cache"] = "\n".join(_csv_lines).encode()
    with dl2:
        if st.download_button(
            "⬇️  Download CSV",
            data=st.session_state["_cc_csv_cache"],
            file_name=f"cost_estimate_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            width="stretch",
        ):
            log_event(EVENT_DOWNLOAD_COST_CSV, st.session_state.get("current_user", ""), st.session_state.get("analytics_sid", ""), "cost_calc")
