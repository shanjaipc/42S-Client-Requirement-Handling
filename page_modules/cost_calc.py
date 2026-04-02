import streamlit as st  # type: ignore
import streamlit.components.v1 as components  # type: ignore
import csv
import html as _html_mod
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

LOGO_PATH = str(Path(__file__).parent.parent / "42slogo.png")


def _generate_cost_pdf(results, grand_total, selected_domains, platform_display, rates_last_updated=""):
    """Build a professional PDF cost estimate using ReportLab."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
    from reportlab.lib import pagesizes  # type: ignore
    from reportlab.lib.units import inch  # type: ignore
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT  # type: ignore
    from reportlab.lib.colors import HexColor, white  # type: ignore

    # ── Page setup ────────────────────────────────────────────────────────────
    L_MARGIN = R_MARGIN = 0.55 * inch
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=pagesizes.A4,
        topMargin=0.45 * inch, bottomMargin=0.55 * inch,
        leftMargin=L_MARGIN, rightMargin=R_MARGIN,
    )
    PAGE_W = pagesizes.A4[0] - L_MARGIN - R_MARGIN

    # ── Colour palette ────────────────────────────────────────────────────────
    C_DARK    = HexColor("#1e293b")
    C_MID     = HexColor("#475569")
    C_BORDER  = HexColor("#e2e8f0")
    C_ACCENT  = HexColor("#0f172a")
    C_RED     = HexColor("#dc2626")
    C_SUBHDR  = HexColor("#334155")
    C_ROWALT  = HexColor("#f1f5f9")
    C_SUBTOT  = HexColor("#e2e8f0")
    C_META    = HexColor("#94a3b8")

    # ── Styles ────────────────────────────────────────────────────────────────
    S = getSampleStyleSheet()

    def _ps(name, **kw):
        return ParagraphStyle(name, parent=S["Normal"], **kw)

    title_s  = _ps("pdf_title",  fontSize=20, fontName="Helvetica-Bold",
                   textColor=C_DARK, alignment=TA_LEFT, spaceAfter=2, leading=24)
    meta_s   = _ps("pdf_meta",   fontSize=8,  textColor=C_META,  alignment=TA_LEFT, leading=12)
    sec_s    = _ps("pdf_sec",    fontSize=9.5, fontName="Helvetica-Bold",
                   textColor=white, leading=13)
    th_s     = _ps("pdf_th",     fontSize=7.5, fontName="Helvetica-Bold",
                   textColor=white, leading=10)
    td_s     = _ps("pdf_td",     fontSize=8,  textColor=C_DARK,  leading=11)
    tdc_s    = _ps("pdf_tdc",    fontSize=8,  textColor=C_MID,   alignment=TA_CENTER, leading=11)
    cost_s   = _ps("pdf_cost",   fontSize=8,  fontName="Helvetica-Bold",
                   textColor=C_RED, alignment=TA_RIGHT, leading=11)
    sub_s    = _ps("pdf_sub",    fontSize=8,  fontName="Helvetica-Bold",
                   textColor=C_SUBHDR, leading=11)
    subcost_s= _ps("pdf_subcost",fontSize=8,  fontName="Helvetica-Bold",
                   textColor=C_RED, alignment=TA_RIGHT, leading=11)
    note_s   = _ps("pdf_note",   fontSize=7,  textColor=C_META,
                   alignment=TA_RIGHT, leading=10, spaceAfter=4)
    foot_s   = _ps("pdf_foot",   fontSize=7,  textColor=C_META,
                   alignment=TA_CENTER, leading=10)
    gt_s     = _ps("pdf_gt",     fontSize=10, fontName="Helvetica-Bold",
                   textColor=white, alignment=TA_RIGHT, leading=14)

    # ── Column widths (total = PAGE_W) ────────────────────────────────────────
    CW = [2.3*inch, 1.0*inch, 0.7*inch, 0.57*inch, 0.7*inch, 0.95*inch, 0.95*inch]

    el = []

    # ── Header band ───────────────────────────────────────────────────────────
    try:
        logo_cell = Image(LOGO_PATH, width=0.85*inch, height=0.68*inch) if os.path.exists(LOGO_PATH) else Paragraph("42S", title_s)
    except Exception:
        logo_cell = Paragraph("42S", title_s)

    meta_lines = (
        f"Generated: {date.today().strftime('%d %b %Y')}"
        + (f"   |   Rates last updated: {rates_last_updated}" if rates_last_updated else "")
        + f"   |   Platforms: {len(selected_domains)}"
        + f"   |   Grand Total: <b>${grand_total:,.4f}</b>"
    )

    hdr = Table(
        [[logo_cell,
          [Paragraph("Crawl Cost Estimate", title_s),
           Paragraph(meta_lines, meta_s)]]],
        colWidths=[1.0*inch, PAGE_W - 1.0*inch],
    )
    hdr.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",(0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
        ("TOPPADDING",  (0, 0), (-1, -1), 0),
    ]))
    el.append(hdr)
    el.append(HRFlowable(width="100%", thickness=1.5, color=C_DARK, spaceAfter=10))

    # ── Per-domain tables ─────────────────────────────────────────────────────
    for domain in selected_domains:
        domain_results = [r for r in results if r["domain"] == domain]
        if not domain_results:
            continue
        display_name = platform_display.get(domain, domain)
        domain_total = sum(r["total_cost"] for r in domain_results)

        sec_hdr = Table(
            [[Paragraph(f"{display_name}  <font size='8' color='#94a3b8'>({domain})</font>", sec_s),
              Paragraph(f"Platform Total:  ${domain_total:,.4f}", gt_s)]],
            colWidths=[PAGE_W * 0.55, PAGE_W * 0.45],
        )
        sec_hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_ACCENT),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (0,  0),  10),
            ("RIGHTPADDING",  (-1, 0),(-1, 0),  10),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        el.append(sec_hdr)

        header_row = [
            Paragraph("Crawl Type",   th_s), Paragraph("Vol / Crawl", th_s),
            Paragraph("Frequency",    th_s), Paragraph("Days",        th_s),
            Paragraph("Zipcode",      th_s), Paragraph("Cost / Crawl",th_s),
            Paragraph("Total Cost",   th_s),
        ]
        table_rows = [header_row]
        for r in domain_results:
            table_rows.append([
                Paragraph(_html_mod.escape(r["crawl_type"]), td_s),
                Paragraph(f"{r['volume_per_crawl']:,}", tdc_s),
                Paragraph(f"{r['freq']}×/day", tdc_s),
                Paragraph(str(r["days"]), tdc_s),
                Paragraph(r["zip_mode"].replace(" Zipcode", ""), tdc_s),
                Paragraph(f"${r['cost_per_crawl']:,.4f}", cost_s),
                Paragraph(f"${r['total_cost']:,.4f}", cost_s),
            ])
        table_rows.append([
            Paragraph("Subtotal", sub_s),
            Paragraph("", tdc_s), Paragraph("", tdc_s), Paragraph("", tdc_s),
            Paragraph("", tdc_s), Paragraph("", tdc_s),
            Paragraph(f"${domain_total:,.4f}", subcost_s),
        ])

        t = Table(table_rows, colWidths=CW, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),   C_SUBHDR),
            ("LINEBELOW",     (0, 0), (-1, 0),   1, C_DARK),
            ("ROWBACKGROUNDS",(0, 1), (-1, -2),  [white, C_ROWALT]),
            ("BACKGROUND",    (0, -1), (-1, -1), C_SUBTOT),
            ("LINEABOVE",     (0, -1), (-1, -1), 0.75, C_MID),
            ("GRID",          (0, 0), (-1, -1),  0.3, C_BORDER),
            ("LINEBEFORE",    (0, 0), (0, -1),   0,   C_BORDER),
            ("VALIGN",        (0, 0), (-1, -1),  "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1),  5),
            ("BOTTOMPADDING", (0, 0), (-1, -1),  5),
            ("LEFTPADDING",   (0, 0), (-1, -1),  8),
            ("RIGHTPADDING",  (0, 0), (-1, -1),  8),
            ("ALIGN",         (5, 1), (6, -1),   "RIGHT"),
        ]))
        el.append(t)

        if rates_last_updated:
            el.append(Paragraph(f"Rates last updated: {rates_last_updated}", note_s))
        el.append(Spacer(1, 0.18 * inch))

    # ── Grand total footer ────────────────────────────────────────────────────
    gt_row = Table(
        [[Paragraph("Grand Total", gt_s), Paragraph(f"USD  ${grand_total:,.4f}", gt_s)]],
        colWidths=[PAGE_W * 0.7, PAGE_W * 0.3],
    )
    gt_row.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (0,  0),  12),
        ("RIGHTPADDING",  (-1,0), (-1, 0),  12),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    el.append(gt_row)
    el.append(Spacer(1, 0.15 * inch))
    el.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    el.append(Spacer(1, 0.06 * inch))
    el.append(Paragraph(
        "Rates are benchmarks derived from internal crawl cost data. Actual costs may vary. "
        "This estimate is for internal planning purposes only.",
        foot_s,
    ))

    doc.build(el)
    buffer.seek(0)
    return buffer.read()


def render_cost_calculator():
    page_title(
        "Cost Calculator",
        "Select platforms, configure crawl types per domain, and get a detailed cost estimate with PDF/CSV download."
    )

    # ── Load domain/rate config from CSV ──────────────────────────────────────
    _RATES_CSV = Path("crawl_cost_rates.csv")

    if not _RATES_CSV.exists():
        st.error("crawl_cost_rates.csv not found. Please add it next to app.py.")
        return

    PLATFORM_LIST, PLATFORM_DISPLAY, RATES = [], {}, {}
    _rates_last_updated = ""
    try:
        with open(_RATES_CSV, newline="") as _fh:
            for _row in csv.DictReader(_fh):
                _d   = _row["domain"].strip()
                _zip = _row["zipcode"].strip().lower() == "true"
                _key = "with" if _zip else "without"
                if _d not in RATES:
                    PLATFORM_LIST.append(_d)
                    PLATFORM_DISPLAY[_d] = _row["display_name"].strip()
                    RATES[_d] = {}
                _sku = float(_row["sku_rate"])
                _cat = float(_row["cat_rate"])
                _kw  = float(_row["kw_rate"])
                if _sku < 0 or _cat < 0 or _kw < 0:
                    st.error(f"crawl_cost_rates.csv: negative rate for '{_d}' (zipcode={_row['zipcode']}). Rates must be ≥ 0.")
                    return
                RATES[_d][_key] = {"sku": _sku, "cat": _cat, "kw": _kw}
                if not _rates_last_updated:
                    _rates_last_updated = _row.get("last_updated", "").strip()
    except KeyError as e:
        st.error(f"crawl_cost_rates.csv is missing column: {e}. Expected columns: domain, display_name, zipcode, sku_rate, cat_rate, kw_rate, last_updated")
        return
    except ValueError as e:
        st.error(f"crawl_cost_rates.csv contains an invalid number: {e}")
        return
    except Exception as e:
        st.error(f"Failed to load crawl_cost_rates.csv: {e}")
        return

    if not PLATFORM_LIST:
        st.error("crawl_cost_rates.csv loaded successfully but contains no domains. Add at least one domain row.")
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

    def _cost_cell(val):
        if val == 0:      return '<span style="color:#16a34a;font-weight:700;">$0.00</span>'
        if val < 1:       return f'<span style="color:#ca8a04;font-weight:700;">${val:.4f}</span>'
        if val < 100:     return f'<span style="color:#ea580c;font-weight:700;">${val:,.4f}</span>'
        return f'<span style="color:#dc2626;font-weight:700;">${val:,.4f}</span>'

    # ── Step 1: Platform Selection ────────────────────────────────────────────
    section_header("🌐", "Step 1 — Select Platforms")
    _input_mode = st.radio(
        "Input method",
        ["Select from list", "Paste comma-separated", "Upload CSV"],
        horizontal=True,
        key="cc_domain_input_mode",
        label_visibility="collapsed",
    )

    if _input_mode == "Select from list":
        selected_domains = st.multiselect(
            "Choose platforms to include in this estimate",
            options=PLATFORM_LIST,
            format_func=lambda x: PLATFORM_DISPLAY.get(x, x),
            key="cc_selected_domains",
            placeholder="Select one or more platforms...",
        )

    elif _input_mode == "Paste comma-separated":
        _raw_paste = st.text_area(
            "Paste domain names (comma-separated)",
            placeholder="e.g. amazon.in, flipkart.com, blinkit.com",
            key="cc_bulk_paste",
            height=80,
        )
        _parsed_paste = [d.strip() for d in _raw_paste.split(",") if d.strip()]
        _unknown_paste = [d for d in _parsed_paste if d not in PLATFORM_LIST]
        if _unknown_paste:
            st.warning(f"Not in rate config (skipped): {', '.join(_unknown_paste)}")
        selected_domains = [d for d in _parsed_paste if d in PLATFORM_LIST]
        st.session_state["cc_selected_domains"] = selected_domains

    else:  # Upload CSV
        import io as _io
        _csv_file = st.file_uploader(
            "Upload CSV (one domain per row, or comma-separated in first column)",
            type=["csv"],
            key="cc_bulk_csv",
        )
        if _csv_file:
            _reader = csv.reader(_io.StringIO(_csv_file.getvalue().decode()))
            _all_csv = []
            for _row in _reader:
                for _cell in _row:
                    _all_csv.extend([c.strip() for c in _cell.split(",") if c.strip()])
            _unknown_csv = [d for d in _all_csv if d not in PLATFORM_LIST]
            if _unknown_csv:
                st.warning(f"Not in rate config (skipped): {', '.join(_unknown_csv)}")
            selected_domains = [d for d in _all_csv if d in PLATFORM_LIST]
            st.session_state["cc_selected_domains"] = selected_domains
            if selected_domains:
                st.success(f"Loaded {len(selected_domains)} domain(s): {', '.join(PLATFORM_DISPLAY.get(d,d) for d in selected_domains)}")
        else:
            selected_domains = st.session_state.get("cc_selected_domains", [])

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
            st.session_state["cc_show_results"] = True

    for domain in selected_domains:
        display_name = PLATFORM_DISPLAY.get(domain, domain)

        with st.expander(f"**{display_name}**  ·  {domain}", expanded=True):
            col_ct, col_zip = st.columns([3, 1])
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

            _zip_mode_now = st.session_state.get(f"cc_zip_{domain}", "Without Zipcode")
            if _zip_mode_now in ("With Zipcode", "Both"):
                _zc_col, _ = st.columns([1, 3])
                with _zc_col:
                    st.number_input("Number of Zipcodes", min_value=1, value=1, step=1,
                                    key=f"cc_zipcount_{domain}")

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

    # ── Generate / Scenario buttons ───────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    g1, g2, g3 = st.columns([2, 1, 2])
    with g1:
        _scenario_name = st.text_input(
            "Scenario name (optional)",
            placeholder="e.g. With Zipcode / High Freq",
            key="cc_scenario_name",
            label_visibility="collapsed",
        )
    with g2:
        if st.button("📊  Generate Estimate ↓", width="stretch", type="primary"):
            st.session_state["cc_show_results"] = True
            components.html(
                "<script>window.parent.document.querySelector('[data-testid=\"stAppViewContainer\"] > section')?.scrollTo({top:999999,behavior:'smooth'});</script>",
                height=0,
            )
    with g3:
        if st.session_state.get("cc_show_results"):
            _sname = (_scenario_name.strip() or
                      f"Scenario {len(st.session_state.get('cc_saved_scenarios', {})) + 1}")
            if st.button(f"💾  Save as '{_sname}'", width="stretch"):
                st.session_state.setdefault("cc_saved_scenarios", {})
                _snap = {
                    "domains": list(selected_domains),
                    "config": {
                        k: v for k, v in st.session_state.items()
                        if isinstance(k, str) and k.startswith("cc_") and k not in (
                            "cc_show_results", "cc_saved_scenarios",
                            "cc_domain_input_mode", "cc_bulk_paste", "cc_bulk_csv",
                            "cc_scenario_name",
                        )
                    },
                }
                _snap["results"] = list(st.session_state.get("_cc_last_results", []))
                st.session_state["cc_saved_scenarios"][_sname] = _snap
                st.success(f"Saved scenario '{_sname}'")

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
                })

    if not results:
        st.session_state["cc_show_results"] = False
        st.warning("No crawl types configured. Select crawl types for at least one platform.")
        return

    st.session_state["_cc_last_results"] = results

    # ── Results header ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📊", "Cost Estimate Results")

    grand_total = sum(r["total_cost"] for r in results)
    if grand_total == 0:
        st.info("All configured crawl types have a $0 rate. Check that the platforms and crawl types are correct, or update the rates in crawl_cost_rates.csv.")
    s1, s2, s3, s4, s5 = st.columns(5)
    for col, lbl, val, accent in [
        (s1, "Grand Total (USD)", f"${grand_total:,.4f}",             "#ef4444"),
        (s2, "Platforms",         str(len(set(r["domain"] for r in results))), "#1f2937"),
        (s3, "Crawl Configs",     str(len(results)),                           "#1f2937"),
        (s4, "Calculated On",     datetime.now().strftime("%d %b %Y"),         "#1f2937"),
        (s5, "Rates Last Updated", _rates_last_updated,                        "#0369a1"),
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
        domain_total = sum(r["total_cost"] for r in domain_results)

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1f2937 0%,#374151 100%);
        border-radius:12px 12px 0 0;padding:12px 18px;display:flex;
        justify-content:space-between;align-items:center;font-family:'Inter',sans-serif;">
            <div style="font-size:0.95rem;font-weight:700;color:white;">
                {display_name}
                <span style="font-size:0.75rem;font-weight:400;color:#9ca3af;margin-left:6px;">({domain})</span>
            </div>
            <div style="font-size:0.9rem;font-weight:700;color:#fde68a;">
                Platform Total: ${domain_total:,.4f}
            </div>
        </div>""", unsafe_allow_html=True)

        rows_html = ""
        for i, r in enumerate(domain_results):
            bg   = "#ffffff" if i % 2 == 0 else "#f9fafb"
            icon = CRAWL_ICONS.get(r["crawl_type"], "")
            rows_html += (
                f'<tr style="background:{bg};border-bottom:1px solid #f1f5f9;">'
                f'<td style="padding:10px 16px;font-size:0.875rem;color:#0f172a;font-weight:500;">{icon} {r["crawl_type"]}</td>'
                f'<td style="padding:10px 16px;text-align:center;font-size:0.8rem;color:#374151;">{r["volume_per_crawl"]:,}</td>'
                f'<td style="padding:10px 16px;text-align:center;font-size:0.8rem;color:#374151;">{r["freq"]}×/day</td>'
                f'<td style="padding:10px 16px;text-align:center;font-size:0.8rem;color:#374151;">{r["days"]} days</td>'
                f'<td style="padding:10px 16px;text-align:center;font-size:0.75rem;color:#6b7280;">{r["zip_mode"].replace(" Zipcode","")}</td>'
                f'<td style="padding:10px 16px;text-align:right;">{_cost_cell(r["cost_per_crawl"])}</td>'
                f'<td style="padding:10px 16px;text-align:right;">{_cost_cell(r["total_cost"])}</td>'
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
            <th style="{th}text-align:right;">Cost/Crawl</th>
            <th style="{th}text-align:right;">Total Cost</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
        </table>
        <div style="padding:6px 16px 8px 16px;font-size:0.72rem;color:#94a3b8;
        font-family:'Inter',sans-serif;border-top:1px solid #f1f5f9;">
            Rates last updated: {_rates_last_updated}
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
                _row[_sc_name] = f"${_match['total_cost']:,.4f}" if _match else "—"
            _comp_rows.append(_row)

        if _comp_rows:
            st.dataframe(pd.DataFrame(_comp_rows), width="stretch", hide_index=True)

            _gt_row = {"Platform": "**Grand Total**", "Crawl Type": "", "Zipcode": ""}
            for _sc_name, _sc_data in _saved_scenarios.items():
                _gt = sum(r["total_cost"] for r in _sc_data.get("results", []))
                _gt_row[_sc_name] = f"${_gt:,.4f}"
            st.dataframe(pd.DataFrame([_gt_row]), width="stretch", hide_index=True)

        if st.button("🗑️  Clear All Scenarios", key="cc_clear_scenarios"):
            st.session_state["cc_saved_scenarios"] = {}
            st.rerun()

    elif len(_saved_scenarios) == 1:
        st.caption("Save one more scenario to enable side-by-side comparison.")

    section_header("📥", "Download Estimate")
    dl1, dl2, _ = st.columns([1, 1, 2])

    pdf_bytes = _generate_cost_pdf(results, grand_total, selected_domains, PLATFORM_DISPLAY, _rates_last_updated)
    with dl1:
        if st.download_button(
            "⬇️  Download PDF",
            data=pdf_bytes,
            file_name=f"cost_estimate_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            width="stretch",
        ):
            log_event(EVENT_DOWNLOAD_COST_PDF, st.session_state.get("current_user", ""), st.session_state.get("analytics_sid", ""), "cost_calc")

    csv_lines = ["Platform,Domain,Crawl Type,Volume/Crawl,Crawls/day,Days,Zipcode,Cost/Crawl (USD),Total Cost (USD)"]
    for r in results:
        csv_lines.append(
            f'{r["display"]},{r["domain"]},{r["crawl_type"]},'
            f'{r["volume_per_crawl"]},{r["freq"]},{r["days"]},{r["zip_mode"]},'
            f'{r["cost_per_crawl"]:.6f},{r["total_cost"]:.6f}'
        )
    csv_lines += ["", f'Grand Total,,,,,,,,{grand_total:.6f}']
    with dl2:
        if st.download_button(
            "⬇️  Download CSV",
            data="\n".join(csv_lines).encode(),
            file_name=f"cost_estimate_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            width="stretch",
        ):
            log_event(EVENT_DOWNLOAD_COST_CSV, st.session_state.get("current_user", ""), st.session_state.get("analytics_sid", ""), "cost_calc")
