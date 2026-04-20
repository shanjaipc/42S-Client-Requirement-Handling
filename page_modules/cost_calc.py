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
from persistence import (
    save_cost_estimate, list_cost_estimates, load_cost_estimate, delete_cost_estimate,
)

LOGO_PATH = str(Path(__file__).parent.parent / "42slogo_top.png")
SCREENSHOT_RATE_DEFAULT = 0.00044   # $/page — editable per site in the UI


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
                       fx=1.0, symbol="$", period="As configured", period_factor_fn=None, pdf_note=""):
    """Invoice-style PDF cost estimate."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable, KeepTogether, Flowable  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
    from reportlab.lib import pagesizes  # type: ignore
    from reportlab.lib.units import inch  # type: ignore
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT  # type: ignore
    from reportlab.lib.colors import HexColor, white, black  # type: ignore

    # ── Page setup ────────────────────────────────────────────────────────────
    L_MARGIN = 0.65 * inch
    R_MARGIN = 0.65 * inch
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=pagesizes.A4,
        topMargin=0.5 * inch, bottomMargin=0.55 * inch,
        leftMargin=L_MARGIN, rightMargin=R_MARGIN,
    )
    PAGE_W = pagesizes.A4[0] - L_MARGIN - R_MARGIN  # ≈ 6.87"

    # ── Colour palette (minimal — one accent, neutral grays) ─────────────────
    C_INK      = HexColor("#111827")   # primary text
    C_SUBINK   = HexColor("#374151")   # secondary text
    C_MUTED    = HexColor("#6b7280")   # labels / captions
    C_ACCENT   = HexColor("#1d4ed8")   # single blue accent
    C_RULE     = HexColor("#e5e7eb")   # subtle borders
    C_THHDR    = HexColor("#1e293b")   # table column header bg (dark slate)
    C_ROWEVEN  = white
    C_ROWODD   = HexColor("#f9fafb")   # alternating row tint
    C_SUBTOT   = HexColor("#f3f4f6")   # subtotal row
    C_AMOUNT   = HexColor("#111827")
    C_AMOUNT_B = HexColor("#374151")

    # ── Styles ────────────────────────────────────────────────────────────────
    S = getSampleStyleSheet()
    def _ps(name, **kw):
        return ParagraphStyle(name, parent=S["Normal"], **kw)

    # Header styles
    inv_title_s    = _ps("IT",  fontSize=16, fontName="Helvetica-Bold",
                          textColor=white, leading=21, alignment=TA_LEFT)
    inv_sub_s      = _ps("IS",  fontSize=7.5, textColor=HexColor("#94a3b8"),
                          leading=11, alignment=TA_LEFT)
    inv_meta_lbl_s = _ps("IML", fontSize=6.5, fontName="Helvetica-Bold",
                          textColor=HexColor("#94a3b8"), leading=9,
                          alignment=TA_RIGHT)
    inv_meta_val_s = _ps("IMV", fontSize=8.5, textColor=white,
                          leading=12, alignment=TA_RIGHT)

    # Section label (platform name above its table)
    plat_s      = _ps("PL", fontSize=10, fontName="Helvetica-Bold",
                      textColor=C_INK, leading=14, spaceBefore=4)
    plat_sub_s  = _ps("PS", fontSize=8.5, textColor=C_MUTED, leading=12)

    # Column headers
    th_l_s      = _ps("THL", fontSize=8, fontName="Helvetica-Bold",
                      textColor=white, leading=11)
    th_c_s      = _ps("THC", fontSize=8, fontName="Helvetica-Bold",
                      textColor=white, leading=11, alignment=TA_CENTER)
    th_r_s      = _ps("THR", fontSize=8, fontName="Helvetica-Bold",
                      textColor=white, leading=11, alignment=TA_RIGHT)

    # Table body
    td_s        = _ps("TD",  fontSize=9,   textColor=C_INK,    leading=12)
    tdc_s       = _ps("TDC", fontSize=9,   textColor=C_SUBINK, leading=12, alignment=TA_CENTER)
    tdr_s       = _ps("TDR", fontSize=9,   fontName="Helvetica-Bold",
                      textColor=C_AMOUNT, leading=12, alignment=TA_RIGHT)
    cpm_s       = _ps("CPM", fontSize=8.5, textColor=C_MUTED,  leading=12, alignment=TA_RIGHT)

    # Subtotal row
    sub_lbl_s   = _ps("SBL", fontSize=9, fontName="Helvetica-Bold",
                      textColor=C_SUBINK, leading=12)
    sub_val_s   = _ps("SBV", fontSize=9, fontName="Helvetica-Bold",
                      textColor=C_INK, leading=12, alignment=TA_RIGHT)

    # Screenshot row
    C_SS = HexColor("#0369a1")   # steel blue for screenshot line
    ss_lbl_s    = _ps("SSL", fontSize=8.5, fontName="Helvetica-Oblique",
                      textColor=C_SS, leading=12)
    ss_val_s    = _ps("SSV", fontSize=8.5, fontName="Helvetica-Bold",
                      textColor=C_SS, leading=12, alignment=TA_RIGHT)
    ss_cpm_s    = _ps("SSC", fontSize=8, textColor=C_SS, leading=12, alignment=TA_RIGHT)

    # Summary / grand total
    sum_th_s    = _ps("STH", fontSize=8.5, fontName="Helvetica-Bold",
                      textColor=white, leading=12)
    sum_td_s    = _ps("STD", fontSize=9.5, textColor=C_INK, leading=13)
    sum_val_s   = _ps("STV", fontSize=9.5, fontName="Helvetica-Bold",
                      textColor=C_INK, leading=13, alignment=TA_RIGHT)
    gt_lbl_s    = _ps("GTL", fontSize=11.5, fontName="Helvetica-Bold",
                      textColor=white, leading=16)
    gt_val_s    = _ps("GTV", fontSize=14, fontName="Helvetica-Bold",
                      textColor=white, leading=18, alignment=TA_RIGHT)
    foot_s      = _ps("FT",  fontSize=7.5, textColor=C_MUTED,
                      alignment=TA_CENTER, leading=11)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _pf(usd, days=None):
        pf = period_factor_fn(days) if (period_factor_fn and days is not None) else 1.0
        v  = usd * fx * pf
        if v == 0:      return f"{symbol}0.00"
        if v < 0.0001:  return f"{symbol}{v:.6f}"
        if v < 1:       return f"{symbol}{v:.4f}"
        if v < 10000:   return f"{symbol}{v:,.2f}"
        return          f"{symbol}{v:,.0f}"

    def _cpm_str(cost_per_crawl, volume):
        if not volume: return "—"
        v = (cost_per_crawl / volume) * 1000 * fx
        if v == 0:    return f"{symbol}0.00"
        if v < 0.001: return f"{symbol}{v:.6f}"
        if v < 1:     return f"{symbol}{v:.4f}"
        return        f"{symbol}{v:,.4f}"

    _period_lbl = {"As configured": "Total", "Monthly": "Monthly", "Annual": "Annual"}.get(period, "Total")
    _gt_avg_days = (sum(r["total_cost"] * r["days"] for r in results) / grand_total) if grand_total else 30

    el = []

    # ─── Custom canvas-drawn Flowables ────────────────────────────────────────
    _logo_path_ref = LOGO_PATH
    _inch = inch

    class _HeaderFlowable(Flowable):
        def __init__(self, logo_path, meta_items, pw):
            super().__init__()
            self.logo_path  = logo_path
            self.meta_items = meta_items
            self.width  = pw
            self.height = 1.00 * _inch

        def draw(self):
            c, w, h = self.canv, self.width, self.height

            # ── White background (clean page)
            c.setFillColorRGB(1.0, 1.0, 1.0)
            c.rect(0, 0, w, h, fill=1, stroke=0)

            # ── Logo (left-aligned, vertically centred)
            LP = 0.80 * _inch
            LW = 0.52 * _inch
            LH = LW * (0.48 / 0.60)
            try:
                if os.path.exists(self.logo_path):
                    c.drawImage(self.logo_path, (LP - LW) / 2, (h - LH) / 2,
                                width=LW, height=LH, mask='auto')
            except Exception:
                pass

            # ── Thin vertical rules (column dividers)
            c.setStrokeColorRGB(0.898, 0.910, 0.922)   # #e5e7eb
            c.setLineWidth(0.5)
            META_W = 1.65 * _inch
            c.line(LP,       h * 0.14, LP,       h * 0.86)
            c.line(w - META_W, h * 0.14, w - META_W, h * 0.86)

            # ── Title block (middle column)
            TX = LP + 16
            c.setFont("Helvetica-Bold", 22)
            c.setFillColorRGB(0.067, 0.098, 0.153)     # #111827
            c.drawString(TX, h * 0.57, "Cost Estimate")
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(0.420, 0.447, 0.502)     # #6b7280
            c.drawString(TX, h * 0.32, "42Signals  \u00b7  Analytics Platform")

            # ── Meta (right column): label right-aligned | value left-aligned
            MX  = w - META_W + 14
            n   = len(self.meta_items)
            RH  = (h * 0.72) / max(n, 1)
            LBX = MX + META_W * 0.38           # label right-edge
            VLX = LBX + 7                      # value left-edge
            for i, (lbl, val) in enumerate(self.meta_items):
                ry = h * 0.84 - (i + 0.55) * RH
                c.setFont("Helvetica", 6.5)
                c.setFillColorRGB(0.420, 0.447, 0.502)
                c.drawRightString(LBX, ry, lbl.upper())
                c.setFont("Helvetica-Bold", 8.5)
                c.setFillColorRGB(0.067, 0.098, 0.153)
                c.drawString(VLX, ry, val)

            # ── Single blue accent line at bottom (the only colour element)
            c.setFillColorRGB(0.114, 0.306, 0.847)     # #1d4ed8
            c.rect(0, 0, w, 2.5, fill=1, stroke=0)

    class _PlatformBannerFlowable(Flowable):
        def __init__(self, display_name, domain, total_str, pw):
            super().__init__()
            self.display_name = display_name
            self.domain       = domain
            self.total_str    = total_str
            self.width  = pw
            self.height = 0.36 * _inch

        def draw(self):
            c, w, h = self.canv, self.width, self.height

            # ── Very light gray background
            c.setFillColorRGB(0.973, 0.976, 0.980)     # #f8f9fa
            c.rect(0, 0, w, h, fill=1, stroke=0)

            # ── 3 pt blue left accent bar (only decoration)
            c.setFillColorRGB(0.114, 0.306, 0.847)     # #1d4ed8
            c.rect(0, 0, 3, h, fill=1, stroke=0)

            # ── Bottom border (connects to table header below)
            c.setStrokeColorRGB(0.898, 0.910, 0.922)   # #e5e7eb
            c.setLineWidth(0.4)
            c.line(0, 0, w, 0)

            # ── Platform name + domain
            _TY = h / 2 - 10 * 0.36               # visual centre for 10pt text
            c.setFont("Helvetica-Bold", 10)
            c.setFillColorRGB(0.067, 0.098, 0.153) # #111827
            c.drawString(12, _TY, self.display_name)
            nw = c.stringWidth(self.display_name, "Helvetica-Bold", 10)
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(0.420, 0.447, 0.502) # #6b7280
            c.drawString(12 + nw + 6, _TY, f"({self.domain})")

            # ── Platform Total (right-aligned, dark text)
            tv  = self.total_str
            tvw = c.stringWidth(tv, "Helvetica-Bold", 9.5)
            GAP = 5
            vx  = w - 12
            lx  = vx - tvw - GAP
            c.setFont("Helvetica", 7)
            c.setFillColorRGB(0.420, 0.447, 0.502)
            c.drawRightString(lx, _TY, "Platform Total:")
            c.setFont("Helvetica-Bold", 9.5)
            c.setFillColorRGB(0.067, 0.098, 0.153)
            c.drawRightString(vx, _TY, tv)

    class _GrandTotalFlowable(Flowable):
        def __init__(self, label, value, pw):
            super().__init__()
            self.label = label
            self.value = value
            self.width  = pw
            self.height = 0.55 * _inch

        def draw(self):
            c, w, h = self.canv, self.width, self.height

            # ── Dark slate background (rounded)
            c.setFillColorRGB(0.118, 0.161, 0.231)     # #1e293b
            c.roundRect(0, 0, w, h, 6, fill=1, stroke=0)

            # ── Label (left, muted white)
            lbl_y = h / 2 - 11 * 0.36
            c.setFont("Helvetica-Bold", 11)
            c.setFillColorRGB(0.820, 0.851, 0.902)     # #d1d9e6
            c.drawString(16, lbl_y, self.label)

            # ── Value (right, pure white, larger)
            val_y = h / 2 - 15 * 0.36
            c.setFont("Helvetica-Bold", 15)
            c.setFillColorRGB(1.0, 1.0, 1.0)
            c.drawRightString(w - 16, val_y, self.value)

    # ── Canvas-drawn header ───────────────────────────────────────────────────
    _meta_items = [("DATE", date.today().strftime('%d %b %Y'))]
    if rates_last_updated:
        _meta_items.append(("RATES", rates_last_updated))
    _meta_items += [("CURRENCY", symbol), ("PERIOD", _period_lbl)]
    el.append(_HeaderFlowable(_logo_path_ref, _meta_items, PAGE_W))
    el.append(Spacer(1, 0.20 * inch))

    # ── Column widths: 7 cols ─────────────────────────────────────────────────
    # Crawl Type | Vol/Crawl | Freq×Days | Zipcode | CPM | Cost/Crawl | Period Total
    CW = [1.96*inch, 0.86*inch, 0.96*inch, 0.70*inch, 0.72*inch, 0.88*inch, 0.87*inch]

    # ── Per-platform sections ─────────────────────────────────────────────────
    for domain in selected_domains:
        domain_results = [r for r in results if r["domain"] == domain]
        if not domain_results:
            continue
        display_name   = platform_display.get(domain, domain)
        dom_crawl_usd  = sum(r["total_cost"] for r in domain_results)
        dom_ss_usd     = sum(r.get("screenshot_total", 0) for r in domain_results)
        dom_total_usd  = dom_crawl_usd + dom_ss_usd
        _dom_avg_days  = (sum(r["total_cost"] * r["days"] for r in domain_results) / dom_crawl_usd) if dom_crawl_usd else 30
        dom_total_str  = _pf(dom_total_usd, _dom_avg_days)

        # Canvas-drawn platform banner
        plat_hdr = _PlatformBannerFlowable(display_name, domain, dom_total_str, PAGE_W)
        plat_hdr.spaceAfter = 0

        # Data rows
        header_row = [
            Paragraph("Crawl Type",              th_l_s),
            Paragraph("Vol/Crawl",               th_c_s),
            Paragraph("Freq \u00d7 Days",        th_c_s),
            Paragraph("Zip",                     th_c_s),
            Paragraph(f"CPM ({symbol})",         th_r_s),
            Paragraph("Cost/Crawl",              th_r_s),
            Paragraph(f"{_period_lbl} Cost",     th_r_s),
        ]
        rows = [header_row]
        for r in domain_results:
            rows.append([
                Paragraph(_html_mod.escape(r["crawl_type"]), td_s),
                Paragraph(f"{r['volume_per_crawl']:,}", tdc_s),
                Paragraph(f"{r['freq']}×/day × {r['days']}d", tdc_s),
                Paragraph(r["zip_mode"].replace(" Zipcode", ""), tdc_s),
                Paragraph(_cpm_str(r["cost_per_crawl"], r["volume_per_crawl"]), cpm_s),
                Paragraph(_pf(r["cost_per_crawl"]), tdr_s),
                Paragraph(_pf(r["total_cost"], r["days"]), tdr_s),
            ])
        # Screenshot row (shown before subtotal when rate > 0)
        if dom_ss_usd > 0:
            _ss_rate_val = domain_results[0].get("screenshot_rate", SCREENSHOT_RATE_DEFAULT)
            _ss_cpm_str  = f"{symbol}{_ss_rate_val * 1000:.4f}"
            _ss_total_pages = sum(r.get("screenshot_total", 0) / r.get("screenshot_rate", SCREENSHOT_RATE_DEFAULT) for r in domain_results if r.get("screenshot_rate", 0) > 0)
            rows.append([
                Paragraph("  \u2937  Screenshots", ss_lbl_s),
                Paragraph(f"{int(_ss_total_pages):,}", tdc_s),
                Paragraph("", tdc_s),
                Paragraph("", tdc_s),
                Paragraph(_ss_cpm_str, ss_cpm_s),
                Paragraph("", tdc_s),
                Paragraph(_pf(dom_ss_usd, _dom_avg_days), ss_val_s),
            ])

        # Subtotal (crawl + screenshot)
        rows.append([
            Paragraph("Platform Total", sub_lbl_s),
            Paragraph("", tdc_s), Paragraph("", tdc_s), Paragraph("", tdc_s),
            Paragraph("", tdc_s), Paragraph("", tdc_s),
            Paragraph(dom_total_str, sub_val_s),
        ])

        data_t = Table(rows, colWidths=CW, repeatRows=1)
        data_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),   C_THHDR),
            ("ROWBACKGROUNDS",(0,1), (-1,-2),  [C_ROWEVEN, C_ROWODD]),
            ("BACKGROUND",    (0,-1),(-1,-1),  C_SUBTOT),
            ("LINEBELOW",     (0,0), (-1,0),   0.5, C_RULE),
            ("LINEABOVE",     (0,-1),(-1,-1),  0.5, C_RULE),
            ("LINEBELOW",     (0,-1),(-1,-1),  0.5, C_RULE),
            ("INNERGRID",     (0,1), (-1,-2),  0.3, C_RULE),
            ("VALIGN",        (0,0), (-1,-1),  "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1),  6),
            ("BOTTOMPADDING", (0,0), (-1,-1),  6),
            ("LEFTPADDING",   (0,0), (-1,-1),  8),
            ("RIGHTPADDING",  (0,0), (-1,-1),  8),
        ]))
        data_t.spaceBefore = 0

        el.append(KeepTogether([plat_hdr, data_t]))
        el.append(Spacer(1, 0.22 * inch))

    # ── Platform summary ──────────────────────────────────────────────────────
    el.append(HRFlowable(width="100%", thickness=0.5, color=C_RULE, spaceAfter=10))
    sum_rows = [[
        Paragraph("Platform Summary", sum_th_s),
        Paragraph(f"{_period_lbl} Cost ({symbol})", sum_th_s),
    ]]
    for domain in selected_domains:
        _dr  = [r for r in results if r["domain"] == domain]
        _du  = sum(r["total_cost"] + r.get("screenshot_total", 0) for r in _dr)
        if _du == 0: continue
        _crawl_usd = sum(r["total_cost"] for r in _dr)
        _ad  = (sum(r["total_cost"] * r["days"] for r in _dr) / _crawl_usd) if _crawl_usd else 30
        sum_rows.append([
            Paragraph(_html_mod.escape(platform_display.get(domain, domain)), sum_td_s),
            Paragraph(_pf(_du, _ad), sum_val_s),
        ])
    sum_t = Table(sum_rows, colWidths=[PAGE_W * 0.72, PAGE_W * 0.28])
    sum_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  C_THHDR),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_ROWEVEN, C_ROWODD]),
        ("INNERGRID",     (0,1),(-1,-1), 0.3, C_RULE),
        ("LINEBELOW",     (0,0),(-1,0),  0.5, C_RULE),
        ("LINEBELOW",     (0,-1),(-1,-1),0.5, C_RULE),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
    ]))
    el.append(sum_t)
    el.append(Spacer(1, 0.14 * inch))

    # ── Canvas-drawn grand total ──────────────────────────────────────────────
    el.append(_GrandTotalFlowable(
        f"Grand Total  \u00b7  {_period_lbl}",
        _pf(grand_total, _gt_avg_days),
        PAGE_W,
    ))
    el.append(Spacer(1, 0.18 * inch))
    el.append(HRFlowable(width="100%", thickness=0.4, color=C_RULE, spaceAfter=6))
    el.append(Paragraph(
        "Rates are benchmarks derived from internal crawl cost data. "
        "Actual costs may vary based on site complexity, proxy usage and infrastructure load. "
        "This estimate is for internal planning purposes only.  "
        f"CPM = cost per 1,000 records.",
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
            _cc_widget_keys = {
                "cc_gen_top", "cc_currency", "cc_period", "cc_fx_rate",
                "cc_domain_input_mode", "cc_bulk_paste", "cc_bulk_csv",
                "cc_scenario_name", "cc_show_results", "cc_saved_scenarios",
            }
            for _k in list(st.session_state.keys()):
                if isinstance(_k, str) and _k.startswith("cc_") and _k not in _cc_widget_keys:
                    del st.session_state[_k]
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
                        st.number_input("📸 Rate ($/page)", min_value=0.0,
                                        value=float(st.session_state.get(f"cc_{domain}_ss_rate", SCREENSHOT_RATE_DEFAULT)),
                                        step=0.000001, format="%.6f",
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


    # ── Generate / Scenario buttons ───────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    g1, g2, g3 = st.columns([2, 1, 2])
    with g1:
        st.text_input(
            "Client name (for saving)",
            placeholder="e.g. Hindustan Unilever",
            key="cc_client_name",
            label_visibility="collapsed",
        )
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
                            "cc_scenario_name", "cc_gen_top",
                            "cc_currency", "cc_period", "cc_fx_rate",
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
        ss_mode   = st.session_state.get(f"cc_ss_mode_{domain}", "Without Screenshot")
        ss_vol    = st.session_state.get(f"cc_ss_vol_{domain}", 0)
        ss_rate   = st.session_state.get(f"cc_{domain}_ss_rate", SCREENSHOT_RATE_DEFAULT)
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
        st.info("All configured crawl types have a $0 rate. Check that the platforms and crawl types are correct, or update the rates in crawl_cost_rates.csv.")

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
            _ss_pages    = sum(r["volume_per_crawl"] * r["freq"] * r["days"] for r in domain_results)
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

    # ── Save Estimate ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("💾", "Save Estimate")
    _save_client = st.session_state.get("cc_client_name", "").strip()
    _sv1, _sv2, _sv3 = st.columns([3, 1, 2])
    with _sv1:
        if not _save_client:
            st.caption("Enter a client name in the field above to save this estimate.")
        else:
            st.markdown(
                f'<div style="font-size:0.88rem;color:#475569;font-family:Inter,sans-serif;margin-top:6px;">'
                f'Saving as: <b>{_html_mod.escape(_save_client)}</b>'
                + (f' · Updating existing estimate' if st.session_state.get("_editing_cost_file") else '')
                + '</div>',
                unsafe_allow_html=True,
            )
    with _sv2:
        if st.button("💾  Save", key="_cc_save_btn", width="stretch",
                     type="primary", disabled=not _save_client):
            _snap = {k: v for k, v in st.session_state.items()
                     if isinstance(k, str) and k.startswith("cc_")
                     and k not in ("cc_show_results", "cc_saved_scenarios",
                                   "cc_domain_input_mode", "cc_bulk_paste", "cc_bulk_csv",
                                   "cc_gen_top", "cc_currency", "cc_period", "cc_fx_rate")}
            _fname = save_cost_estimate(
                _save_client,
                st.session_state.get("current_user", ""),
                results,
                grand_total_usd,
                _snap,
            )
            st.success(f"Saved! ({_fname})")
    with _sv3:
        if st.session_state.get("_editing_cost_file"):
            if st.button("✚ Save as New Copy", key="_cc_save_new_btn", width="stretch"):
                st.session_state.pop("_editing_cost_file", None)
                _snap = {k: v for k, v in st.session_state.items()
                         if isinstance(k, str) and k.startswith("cc_")
                         and k not in ("cc_show_results", "cc_saved_scenarios",
                                       "cc_domain_input_mode", "cc_bulk_paste", "cc_bulk_csv",
                                       "cc_gen_top", "cc_currency", "cc_period", "cc_fx_rate")}
                _fname = save_cost_estimate(
                    _save_client or "copy",
                    st.session_state.get("current_user", ""),
                    results, grand_total_usd, _snap,
                )
                st.success(f"Saved new copy: {_fname}")

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📥", "Download Estimate")
    dl1, dl2, _ = st.columns([1, 1, 2])

    _cur_label = _currency.split()[0]
    _pdf_note  = f"Currency: {_cur_label}" + (f" (1 USD = {_sym}{_fx:,.2f})" if _use_inr else "") + f"  ·  Period: {_period}"
    pdf_bytes = _generate_cost_pdf(
        results, grand_total_usd, selected_domains, PLATFORM_DISPLAY, _rates_last_updated,
        fx=_fx, symbol=_sym, period=_period, period_factor_fn=_period_factor, pdf_note=_pdf_note,
    )
    with dl1:
        if st.download_button(
            "⬇️  Download PDF",
            data=pdf_bytes,
            file_name=f"cost_estimate_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            width="stretch",
        ):
            log_event(EVENT_DOWNLOAD_COST_PDF, st.session_state.get("current_user", ""), st.session_state.get("analytics_sid", ""), "cost_calc")

    _csv_cur  = _cur_label
    _csv_hdr  = f"Platform,Domain,Crawl Type,Volume/Crawl,Crawls/day,Days,Zipcode,CPM ({_csv_cur}),Cost/Crawl ({_csv_cur}),{_period_label} Cost ({_csv_cur})"
    csv_lines = [_csv_hdr]
    for r in results:
        _pf   = _period_factor(r["days"])
        _cpc  = r["cost_per_crawl"] * _fx
        _tot  = r["total_cost"] * _fx * _pf
        _cpm_v = (r["cost_per_crawl"] / r["volume_per_crawl"] * 1000 * _fx) if r["volume_per_crawl"] else 0
        csv_lines.append(
            f'{r["display"]},{r["domain"]},{r["crawl_type"]},'
            f'{r["volume_per_crawl"]},{r["freq"]},{r["days"]},{r["zip_mode"]},'
            f'{_cpm_v:.6f},{_cpc:.6f},{_tot:.6f}'
        )
    _gt_csv = sum(r["total_cost"] * _fx * _period_factor(r["days"]) for r in results)
    csv_lines += ["", f'Grand Total,,,,,,,,,{_gt_csv:.6f}']
    with dl2:
        if st.download_button(
            "⬇️  Download CSV",
            data="\n".join(csv_lines).encode(),
            file_name=f"cost_estimate_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            width="stretch",
        ):
            log_event(EVENT_DOWNLOAD_COST_CSV, st.session_state.get("current_user", ""), st.session_state.get("analytics_sid", ""), "cost_calc")
