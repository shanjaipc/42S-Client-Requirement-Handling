import streamlit as st  # type: ignore
import streamlit.components.v1 as components  # type: ignore
import base64
import html as _html_mod
import re
import os
from io import BytesIO
from datetime import date, timedelta
from pathlib import Path

from ui_helpers import (
    _h, _safe_filename, celebrate, section_header, page_title, info_row,
    frequency_selector, calculate_risk, _section_label, domain_selector,
    _safe_key, PREDEFINED_DOMAINS,
)
from persistence import (
    save_submission, list_submissions, load_submission,
    _load_draft, _save_draft, _clear_draft,
    _validate_form, _load_form_templates, _save_form_template, _delete_form_template,
    _FORM_KEY_PREFIXES,
)
from analytics import (
    log_event,
    EVENT_GENERATE_REQ_PDF, EVENT_DOWNLOAD_REQ_PDF,
)

LOGO_PATH = str(Path(__file__).parent.parent / "42slogo.png")


# ─────────────────────────────────────────────────────────────────────────────
# Per-module crawl-config helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pt_crawl_config(key_suffix=""):
    cfg = {}
    crawl_type = st.radio(
        "Crawl Type", ["Category-based (Category_ES)", "Input-based (URL/Input driven)", "Products Only"],
        horizontal=True, key=f"pt_crawl_type{key_suffix}"
    )
    cfg["Crawl Type"] = crawl_type

    if crawl_type == "Products Only":
        st.markdown("---")
        st.markdown("##### C) Products Only Configuration")

        st.markdown("**Products Crawl Frequency**")
        pf, ph, pd = frequency_selector("Products Crawl", f"pt_prodonly{key_suffix}")
        cfg["Products Crawl Frequency"] = f"{pf} ({ph} times/day)" if ph else (f"{pf} ({pd}x/day)" if pd and pd > 1 else pf)
        if ph:
            cfg["Hourly Crawl Timings"] = st.text_input(
                "Specify crawl hours", placeholder="e.g., 9 AM, 12 PM, 3 PM, 6 PM",
                key=f"pt_prodonly_hourly_timings{key_suffix}"
            )

        st.markdown("**Inputs**")
        cfg["Sample Input URLs"] = st.text_area("Sample Product URLs", placeholder="If client inputs not available, provide testing URLs", key=f"pt_prodonly_sample_urls{key_suffix}")
        inp_status = st.radio("Client Inputs Status", ["Not Yet Provided", "Available — See Sheet Link Below"], key=f"pt_prodonly_inputs_status{key_suffix}", horizontal=True)
        if inp_status == "Not Yet Provided":
            cfg["Client Inputs Expected Date"] = str(st.date_input("Expected delivery date for inputs", key=f"pt_prodonly_inputs_expected_date{key_suffix}"))
        else:
            cfg["Client Inputs Sheet Link"] = st.text_input("Sheet Link with client inputs", key=f"pt_prodonly_inputs_sheet_link{key_suffix}")

        st.markdown("**Location Dependency**")
        is_pincode = st.radio("Pincode / Zipcode based?", ["Yes", "No"], key=f"pt_prodonly_pincode_based{key_suffix}", horizontal=True)
        cfg["Pincode Based"] = is_pincode
        if is_pincode == "Yes":
            c1, c2 = st.columns(2)
            with c1:
                cfg["Sample Pincode"] = st.text_input("Sample Pincode", placeholder="e.g., 110001, 560001", key=f"pt_prodonly_sample_pincode{key_suffix}")
            with c2:
                cfg["Client Pincode List Link"] = st.text_input("Pincode list link (if available)", key=f"pt_prodonly_pincode_list_link{key_suffix}")

        st.markdown("**Volume & Output**")
        c1, c2 = st.columns(2)
        with c1:
            cfg["Expected Volume"] = st.text_input("Expected Volume / day", placeholder="e.g., 50,000 products", key=f"pt_prodonly_expected_volume{key_suffix}")
        with c2:
            cfg["Screenshot Required"] = st.radio("Screenshot Required?", ["Yes", "No"], index=1, key=f"pt_prodonly_screenshot{key_suffix}", horizontal=True)

    elif crawl_type == "Category-based (Category_ES)":
        st.markdown("---")
        st.markdown("##### A) Category_ES Configuration")

        st.markdown("**Index Frequency**")
        c1, c2 = st.columns(2)
        with c1:
            pf, ph, pd = frequency_selector("Products Index", f"pt_prod{key_suffix}")
            cfg["Products Index Frequency"] = f"{pf} ({ph} times/day)" if ph else (f"{pf} ({pd}x/day)" if pd and pd > 1 else pf)
        with c2:
            tf, th, td = frequency_selector("Trends Index", f"pt_trend{key_suffix}")
            cfg["Trends Index Frequency"] = f"{tf} ({th} times/day)" if th else (f"{tf} ({td}x/day)" if td and td > 1 else tf)

        if ph or th:
            cfg["Hourly Crawl Timings"] = st.text_input(
                "Specify crawl hours", placeholder="e.g., 9 AM, 12 PM, 3 PM, 6 PM",
                key=f"pt_hourly_timings{key_suffix}"
            )

        st.markdown("**Trends Configuration**")
        c1, c2 = st.columns(2)
        with c1:
            cfg["No of RSS Crawls"] = st.number_input("Number of RSS crawls into Trends", min_value=0, key=f"pt_rss_crawls{key_suffix}")
        with c2:
            cfg["Expected Data Push Volume"] = st.text_input("Products volume to push into Trends", key=f"pt_data_push_volume{key_suffix}")

        st.markdown("**Category Details**")
        cfg["Sample Category List"] = st.text_area(
            "Sample Category List", placeholder="e.g., Electronics, Fashion, Home & Kitchen",
            key=f"pt_sample_category_list{key_suffix}"
        )
        cat_status = st.radio("Is final category list available?", ["Yes", "No"], key=f"pt_category_status{key_suffix}", horizontal=True)
        if cat_status == "Yes":
            cfg["Client Category Sheet Link"] = st.text_input("Category Sheet Link", key=f"pt_category_sheet_link{key_suffix}")
        else:
            cfg["Client Category Expected Date"] = str(st.date_input("Expected date for category list", key=f"pt_category_expected_date{key_suffix}"))

    elif crawl_type == "Input-based (URL/Input driven)":
        st.markdown("---")
        st.markdown("##### B) Input-Based Configuration")

        st.markdown("**Products Crawl**")
        need_product = st.radio("Products crawl required?", ["Yes", "No"], key=f"pt_input_products_needed{key_suffix}", horizontal=True)
        cfg["Products Crawl Needed"] = need_product
        if need_product == "Yes":
            pf, ph, pd = frequency_selector("Products Crawl", f"pt_input_prod{key_suffix}")
            cfg["Products Crawl Frequency"] = f"{pf} ({ph} times/day)" if ph else (f"{pf} ({pd}x/day)" if pd and pd > 1 else pf)

        st.markdown("**Trends Crawl**")
        tf, th, td = frequency_selector("Trends Crawl", f"pt_input_trend{key_suffix}")
        cfg["Trends Crawl Frequency"] = f"{tf} ({th} times/day)" if th else (f"{tf} ({td}x/day)" if td and td > 1 else tf)
        if th:
            cfg["Trends Hourly Timings"] = st.text_input(
                "Specify timing if hourly", placeholder="e.g., 10 AM, 2 PM, 6 PM, 10 PM",
                key=f"pt_trends_hourly_timings{key_suffix}"
            )

        st.markdown("**Inputs**")
        cfg["Sample Input URLs"] = st.text_area("Sample Input URLs", placeholder="If client inputs not available, provide testing URLs", key=f"pt_sample_input_urls{key_suffix}")
        inp_status = st.radio("Client Inputs Status", ["Not Yet Provided", "Available — See Sheet Link Below"], key=f"pt_inputs_status{key_suffix}", horizontal=True)
        if inp_status == "Not Yet Provided":
            cfg["Client Inputs Expected Date"] = str(st.date_input("Expected delivery date for inputs", key=f"pt_inputs_expected_date{key_suffix}"))
        else:
            cfg["Client Inputs Sheet Link"] = st.text_input("Sheet Link with client inputs", key=f"pt_inputs_sheet_link{key_suffix}")

        st.markdown("**Location Dependency**")
        is_pincode = st.radio("Pincode / Zipcode based?", ["Yes", "No"], key=f"pt_pincode_based{key_suffix}", horizontal=True)
        cfg["Pincode Based"] = is_pincode
        if is_pincode == "Yes":
            c1, c2 = st.columns(2)
            with c1:
                cfg["Sample Pincode"] = st.text_input("Sample Pincode", placeholder="e.g., 110001, 560001", key=f"pt_sample_pincode{key_suffix}")
            with c2:
                cfg["Client Pincode List Link"] = st.text_input("Pincode list link (if available)", key=f"pt_pincode_list_link{key_suffix}")

        st.markdown("**Crawl Duration**")
        c1, c2 = st.columns(2)
        with c1:
            cfg["Crawl Start Date"] = str(st.date_input("Start Date", key=f"pt_crawl_start_date{key_suffix}"))
        with c2:
            cfg["Crawl End Date"] = str(st.date_input("End Date", key=f"pt_crawl_end_date{key_suffix}"))

        st.markdown("**Volume & Output**")
        c1, c2 = st.columns(2)
        with c1:
            cfg["Expected Volume"] = st.text_input("Expected Volume / day", placeholder="e.g., 50,000 products", key=f"pt_expected_volume{key_suffix}")
        with c2:
            cfg["Screenshot Required"] = st.radio("Screenshot Required?", ["Yes", "No"], index=1, key=f"pt_screenshot{key_suffix}", horizontal=True)

    return cfg


def _sos_crawl_config(key_suffix=""):
    cfg = {}
    cfg["Zipcode Required"] = st.radio("Zipcode required?", ["Yes", "No"], horizontal=True, key=f"sos_zipcode_required{key_suffix}")
    if cfg["Zipcode Required"] == "Yes":
        cfg["Pincode List"] = st.text_area(
            "Pincode list (comma-separated or sheet link)",
            placeholder="e.g., 110001, 560001, 400001",
            key=f"sos_pincode_list{key_suffix}"
        )
        st.caption("Format: comma-separated pincodes (e.g., 110001, 560001) or paste a sheet link.")

    st.markdown("**Crawl Depth**")
    c1, c2 = st.columns(2)
    with c1:
        cfg["No. of Pages per Keyword"] = st.number_input("Pages per keyword", min_value=1, value=1, key=f"sos_pages{key_suffix}")
    with c2:
        cfg["No. of Products per Keyword"] = st.number_input("Products per keyword", min_value=1, value=10, key=f"sos_products{key_suffix}")

    st.markdown("**Crawl Frequency**")
    freq, hourly, daily = frequency_selector("SOS Crawl", f"sos{key_suffix}")
    cfg["Frequency"] = f"{freq} ({hourly} times/day)" if hourly else (f"{freq} ({daily}x/day)" if daily and daily > 1 else freq)
    return cfg


def _rev_crawl_config(key_suffix=""):
    cfg = {}
    st.markdown("**Review Source Type**")
    cfg["Input Sources"] = st.multiselect(
        "Where to pull review inputs from *",
        ["From Products Index", "From Trends Index", "From Review Input URLs", "Category-based Reviews Crawl"],
        key=f"rev_source{key_suffix}",
    )
    if "From Review Input URLs" in cfg["Input Sources"]:
        cfg["Sample Review URLs"] = st.text_area("Sample review page URLs", placeholder="Provide product review page URLs", key=f"rev_sample_urls{key_suffix}")

    st.markdown("**Frequency**")
    c1, c2 = st.columns(2)
    with c1:
        freq, hourly, daily = frequency_selector("Reviews Crawl", f"rev{key_suffix}")
        cfg["Frequency"] = f"{freq} ({hourly} times/day)" if hourly else (f"{freq} ({daily}x/day)" if daily and daily > 1 else freq)
    if hourly:
        with c2:
            cfg["Hourly Timings"] = st.text_input("Timing if hourly", placeholder="e.g., 8 AM, 12 PM, 6 PM, 10 PM", key=f"rev_hourly_timings{key_suffix}")
    return cfg


def _pv_crawl_config(key_suffix=""):
    cfg = {}
    st.markdown("**Frequency**")
    freq, hourly, daily = frequency_selector("Price Violation Crawl", f"pv{key_suffix}")
    cfg["Frequency"] = f"{freq} ({hourly} times/day)" if hourly else (f"{freq} ({daily}x/day)" if daily and daily > 1 else freq)

    st.markdown("**Inputs**")
    cfg["Product URL List"] = st.text_area("Product URL list to monitor *", placeholder="Sample product URLs", key=f"pv_product_url_list{key_suffix}")

    cfg["Zipcode Required"] = st.radio("Zipcode required?", ["Yes", "No"], horizontal=True, key=f"pv_zipcode_required{key_suffix}")
    if cfg["Zipcode Required"] == "Yes":
        cfg["Zipcode List"] = st.text_area("Zipcode list", placeholder="e.g., 110001, 560001, 400001", key=f"pv_zipcode_list{key_suffix}")

    cfg["Price Violation Condition"] = st.text_area(
        "Violation condition / rule",
        placeholder="e.g., MRP > X, Discount < Y%, price diff > 15%",
        key=f"pv_violation_condition{key_suffix}"
    )
    c1, c2 = st.columns(2)
    with c1:
        cfg["Sample Inputs Sheet Link"] = st.text_input("Sample inputs sheet link", placeholder="Link to sample data", key=f"pv_sample_inputs_link{key_suffix}")
    with c2:
        cfg["Screenshot Required"] = st.radio("Screenshot Required?", ["Yes", "No"], index=1, key=f"pv_screenshot{key_suffix}", horizontal=True)
    return cfg


def _storeid_crawl_config(key_suffix=""):
    cfg = {}
    c1, _ = st.columns(2)
    with c1:
        cfg["Specific Location Required"] = st.radio(
            "Specific store locations needed?", ["No", "Yes"], horizontal=True, key=f"storeid_location{key_suffix}"
        )
    if cfg["Specific Location Required"] == "Yes":
        cfg["Location Details"] = st.text_area("Location details", placeholder="e.g., Bangalore, Mumbai, Delhi", key=f"storeid_location_details{key_suffix}")

    storeid_status = st.radio("Specific Pincode list available?", ["Yes", "No"], horizontal=True, key=f"storeid_list_status{key_suffix}")
    if storeid_status == "Yes":
        cfg["Specific Pincode List Link"] = st.text_input("Pincode list link", key=f"storeid_pincode_list_link{key_suffix}")
    return cfg


def _festive_schedule_config(key_suffix=""):
    cfg = {}
    c1, c2, c3 = st.columns(3)
    with c1:
        cfg["Frequency Per Day"] = st.number_input("Frequency / day", min_value=1, value=1, key=f"festive_freq{key_suffix}")
    with c2:
        cfg["Start Date"] = str(st.date_input("Start Date", key=f"festive_start{key_suffix}"))
    with c3:
        cfg["End Date"] = str(st.date_input("End Date", key=f"festive_end{key_suffix}"))
    return cfg


def _apply_domain_config(base_dict, config_mode_key, domain_list, config_fn):
    """
    If multiple domains: ask same/different. Render config once (common) or per domain.
    Merges results into base_dict (per-domain keys prefixed with domain name).
    """
    if len(domain_list) > 1:
        config_mode = st.radio(
            "Crawl configuration",
            ["Same config for all domains", "Different config per domain"],
            key=f"{config_mode_key}_mode",
            horizontal=True,
        )
    else:
        config_mode = "Same config for all domains"

    if config_mode == "Same config for all domains":
        cfg = config_fn("")
        base_dict.update(cfg)
    else:
        for domain in domain_list:
            sk = _safe_key(domain)
            with st.expander(f"Config for: **{domain}**", expanded=True):
                cfg = config_fn(f"_{sk}")
            for k, v in cfg.items():
                base_dict[f"{domain} — {k}"] = v


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
    # ── Progress indicator ────────────────────────────────────────────────────
    _REQUIRED_CHECKS = [
        ("Client Name",       lambda d: bool(d.get("Client Information", {}).get("Client Name", "").strip())),
        ("Target Market",     lambda d: bool(d.get("Client Information", {}).get("Target Market", "").strip())),
        ("Modules Selected",  lambda d: bool(d.get("Modules Selected", {}).get("Selected Modules"))),
        ("Domain(s) added",   lambda d: any(
            bool(sec.get("Domains")) for k, sec in d.items()
            if isinstance(sec, dict) and k not in ("Client Information", "Modules Selected",
                                                    "Final Alignment", "Comments & Notes")
        )),
        ("Client Objective",  lambda d: bool(d.get("Final Alignment", {}).get("Client Core Objective", "").strip())),
    ]
    _done  = sum(1 for _, fn in _REQUIRED_CHECKS if fn(data))
    _total = len(_REQUIRED_CHECKS)
    _pct   = int(_done / _total * 100)
    _color = "#16a34a" if _pct == 100 else "#3b82f6" if _pct >= 60 else "#f59e0b"

    _checks_html = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;font-size:0.73rem;'
        f'color:{"#16a34a" if fn(data) else "#94a3b8"};margin-bottom:3px;">'
        f'{"✓" if fn(data) else "○"} {lbl}</div>'
        for lbl, fn in _REQUIRED_CHECKS
    )
    st.markdown(
        f'<div style="background:white;border-radius:10px;padding:14px 16px;'
        f'border:1px solid #e5e7eb;margin-bottom:14px;font-family:\'Inter\',sans-serif;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'<span style="font-size:0.75rem;font-weight:700;color:#374151;">Form Progress</span>'
        f'<span style="font-size:0.75rem;font-weight:700;color:{_color};">{_done}/{_total}</span>'
        f'</div>'
        f'<div style="background:#f1f5f9;border-radius:99px;height:6px;overflow:hidden;margin-bottom:10px;">'
        f'<div style="background:{_color};width:{_pct}%;height:100%;border-radius:99px;'
        f'transition:width 0.3s ease;"></div></div>'
        f'{_checks_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

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
            background:white; border-radius:12px; border:2px dashed #d1d5db;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        ">
            <div style="font-size:2.4rem; margin-bottom:12px; opacity:0.55;">📝</div>
            <div style="font-size:0.875rem; font-weight:600; color:#64748b; margin-bottom:5px; font-family:'Inter',sans-serif;">Nothing here yet</div>
            <div style="font-size:0.78rem; color:#6b7280; line-height:1.6; font-family:'Inter',sans-serif;">
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
        # Support both common config ("Overall Frequency") and per-domain config ("domain — Overall Frequency")
        _overall_freq = pt.get("Overall Frequency") or next(
            (v for k, v in pt.items() if k.endswith("Overall Frequency")), None
        )
        _expected_vol = pt.get("Expected Volume") or next(
            (v for k, v in pt.items() if k.endswith("Expected Volume")), None
        )
        risk = calculate_risk(_overall_freq, _expected_vol)
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
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
    from reportlab.lib import pagesizes  # type: ignore
    from reportlab.lib.units import inch  # type: ignore
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY  # type: ignore
    from reportlab.lib.colors import HexColor  # type: ignore
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=pagesizes.A4,
        topMargin=0.5*inch, bottomMargin=0.6*inch,
        leftMargin=0.6*inch, rightMargin=0.6*inch,
        title=f"{client_name} — Requirement Handling Form",
        author="42Signals",
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

    def _val_paragraph(v):
        if not v:
            return Paragraph("—", val_s)
        s = str(v)
        # detect URLs and render as clickable hyperlinks
        import re as _re
        url_pat = _re.compile(r'(https?://\S+)')
        parts = url_pat.split(s)
        if len(parts) == 1:
            return Paragraph(_html_mod.escape(s), val_s)
        xml = ""
        for part in parts:
            if url_pat.match(part):
                esc_url = _html_mod.escape(part, quote=True)
                xml += f'<a href="{esc_url}" color="#2563eb">{esc_url}</a>'
            else:
                xml += _html_mod.escape(part)
        return Paragraph(xml, val_s)

    row_colors = [HexColor("#f9fafb"), HexColor("#ffffff")]
    ci = 0
    for section, content in data.items():
        el.append(Paragraph(f"  {_html_mod.escape(str(section))}", sec_s))
        el.append(Spacer(1, 0.04*inch))
        rows = [
            [Paragraph(_html_mod.escape(str(k)), key_s),
             _val_paragraph(v)]
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
# PAGE RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render_main_form():
    page_title(
        "New Requirement Form",
        "Capture complete client crawl requirements for project planning and scoping."
    )

    _form_username = st.session_state.get("current_user", "")

    # ── Auto-draft restore prompt ──────────────────────────────────────────
    _draft = _load_draft(_form_username)
    if _draft and not st.session_state.get("_draft_dismissed") and not st.session_state.get("_editing_submission_file"):
        _draft_time = _draft.get("saved_at", "")[:16].replace("T", " ")
        st.markdown(
            f'<div style="background:#fffbeb;border:1px solid #f59e0b;border-left:4px solid #f59e0b;'
            f'border-radius:8px;padding:12px 16px;margin-bottom:12px;font-family:\'Inter\',sans-serif;">'
            f'<span style="font-size:0.88rem;font-weight:700;color:#92400e;">📋 Unsaved draft found</span>'
            f'<span style="font-size:0.82rem;color:#78350f;margin-left:8px;">Last saved {_h(_draft_time)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        _dc1, _dc2, _ = st.columns([1, 1, 4])
        with _dc1:
            if st.button("Resume Draft", key="_resume_draft_btn"):
                _ISO_DATE_RE2 = re.compile(r"^\d{4}-\d{2}-\d{2}$")
                for k, v in _draft.get("session_state", {}).items():
                    if isinstance(v, str) and _ISO_DATE_RE2.match(v):
                        try: v = date.fromisoformat(v)
                        except ValueError: pass
                    st.session_state[k] = v
                st.session_state["_draft_dismissed"] = True
                st.rerun()
        with _dc2:
            if st.button("Discard Draft", key="_discard_draft_btn"):
                _clear_draft(_form_username)
                st.session_state["_draft_dismissed"] = True
                st.rerun()

    # ── Load Template ─────────────────────────────────────────────────────────
    _tpls = _load_form_templates()
    if _tpls:
        with st.expander("📋  Load a template", expanded=False):
            _tpl_choice = st.selectbox(
                "Select template",
                list(_tpls.keys()),
                key="_tpl_select",
                label_visibility="collapsed",
            )
            tc1, tc2, _ = st.columns([1, 1, 3])
            with tc1:
                if st.button("⬆️  Load Template", key="_tpl_load_btn"):
                    _ISO_DATE_RE3 = re.compile(r"^\d{4}-\d{2}-\d{2}$")
                    for k, v in _tpls[_tpl_choice]["snapshot"].items():
                        if isinstance(v, str) and _ISO_DATE_RE3.match(v):
                            try: v = date.fromisoformat(v)
                            except ValueError: pass
                        st.session_state[k] = v
                    st.session_state["_editing_submission_file"] = None
                    st.rerun()
            with tc2:
                if st.button("🗑️  Delete Template", key="_tpl_del_btn"):
                    _delete_form_template(_tpl_choice)
                    st.rerun()

    # ── Load Previous Submission ───────────────────────────────────────────
    _saved = list_submissions()
    if _saved:
        with st.expander("📂  Load a previous submission", expanded=False):
            _options = {
                f"{s['client_name']}  ·  {s['saved_at'][:16].replace('T', ' ')}  (by {s['saved_by']})": s["filename"]
                for s in _saved
            }
            _chosen_label = st.selectbox(
                "Select submission to load",
                list(_options.keys()),
                key="_load_submission_select",
                label_visibility="collapsed",
            )
            btn_col1, _ = st.columns([1, 3])
            with btn_col1:
                if st.button("⬆️  Load & Edit", key="_load_submission_btn"):
                    load_submission(_options[_chosen_label])

    # If editing a loaded submission, show a banner + allow starting fresh
    if st.session_state.get("_editing_submission_file"):
        info_col, btn_col = st.columns([4, 1])
        with btn_col:
            if st.button("✚  New Form", key="_new_form_btn", width="stretch"):
                st.session_state["_editing_submission_file"] = None
                for k in list(st.session_state.keys()):
                    if isinstance(k, str) and k.startswith(_FORM_KEY_PREFIXES):
                        del st.session_state[k]
                st.rerun()

    left, right = st.columns([2, 1], gap="large")
    form_data = {}

    with left:

        st.markdown('<div style="font-size:0.75rem;color:#6b7280;margin-bottom:8px;"><span style="color:#dc2626;font-weight:700;">*</span> Required field</div>', unsafe_allow_html=True)

        # ── 1. Client Information ──────────────────────────────────────────
        section_header("👤", "1. Client Information")

        c1, c2 = st.columns([2, 1])
        with c1:
            client_name = st.text_input("Client Name *", placeholder="e.g., Unilever India", key="form_client_name")
            if not client_name and st.session_state.get("_form_touched"):
                st.markdown('<p style="color:#ef4444;font-size:0.75rem;margin:-8px 0 4px 0;">Required — enter the client name</p>', unsafe_allow_html=True)
        with c2:
            priority = st.selectbox("Priority Level", ["High", "Medium", "Low"], key="form_priority")

        c3, c4 = st.columns(2)
        with c3:
            default_date = date.today() + timedelta(days=4)
            completion_date = st.date_input(
                "Expected Completion Date",
                value=default_date,
                key="form_completion_date"
            )
        with c4:
            expected_market = st.text_input("Target Market / Geography *", placeholder="e.g., India, Southeast Asia", key="form_target_market")
            if not expected_market and st.session_state.get("_form_touched"):
                st.markdown('<p style="color:#ef4444;font-size:0.75rem;margin:-8px 0 4px 0;">Required — enter the target market</p>', unsafe_allow_html=True)

        # Mark form as "touched" once any field is non-empty, to enable inline hints
        if client_name or expected_market:
            st.session_state["_form_touched"] = True

        form_data["Client Information"] = {
            "Client Name":            client_name,
            "Priority Level":         priority,
            "Expected Completion":    str(completion_date),
            "Target Market":          expected_market,
        }

        # Auto-save draft whenever client name is present
        if client_name:
            _save_draft(_form_username, form_data)

        validate_required(client_name)

        # ── 2. Modules to Crawl ───────────────────────────────────────────
        section_header("🧩", "2. Modules to Crawl")

        modules = st.multiselect(
            "Select the modules required for this client *",
            ["Products + Trends", "SOS (Search on Site)", "Reviews",
             "Price Violation", "Store ID Crawls", "Festive Sale Crawls"],
            key="form_modules",
        )
        if not modules:
            st.info("Select at least one module above to configure its settings.")

        form_data["Modules Selected"] = {
            "Selected Modules": ", ".join(modules) if modules else "None"
        }

        # ── 3. Products + Trends ──────────────────────────────────────────
        if "Products + Trends" in modules:
            _pt_done = bool(st.session_state.get("pt_domains") or st.session_state.get("pt_custom_domain", "").strip())
            with st.expander(("✅  " if _pt_done else "") + "📦  Products + Trends", expanded=not _pt_done):
                pt = {}
                pt["Domains"], _pt_domains = domain_selector("Domains *", "pt")
                _apply_domain_config(pt, "pt", _pt_domains, _pt_crawl_config)
                st.markdown("**Specific Fields to Capture**")
                pt["Specific Fields"] = st.text_area(
                    "Any additional fields to extract",
                    placeholder="e.g., seller name, discount %, stock status, rating breakdown, delivery time",
                    key="pt_specific_fields",
                )
                form_data["Products + Trends"] = pt

        # ── 4. SOS Module ─────────────────────────────────────────────────
        if "SOS (Search on Site)" in modules:
            _sos_done = bool(st.session_state.get("sos_domains") or st.session_state.get("sos_custom_domain", "").strip())
            with st.expander(("✅  " if _sos_done else "") + "🔍  SOS (Search On Site)", expanded=not _sos_done):
                sos = {}
                st.markdown("**Keywords**")
                c1, c2 = st.columns(2)
                with c1:
                    sos["No. of Keywords"] = st.number_input("Number of Keywords *", min_value=0, key="sos_keyword_count")
                with c2:
                    keywords_source = st.radio("Keywords source", ["Client Provided", "Provide Sample for Testing"], key="sos_keywords_source")
                if keywords_source == "Client Provided":
                    sos["SOS Keywords Sheet Link"] = st.text_input("Link to client keywords sheet", key="sos_keywords_sheet_link")
                else:
                    sos["Sample Keywords"] = st.text_area("Sample keywords for testing", placeholder="e.g., laptop, shoes, home appliances", key="sos_sample_keywords")
                sos["Domains"], _sos_domains = domain_selector("Domains *", "sos")
                _apply_domain_config(sos, "sos", _sos_domains, _sos_crawl_config)
                form_data["SOS (Search on Site)"] = sos

        # ── 5. Reviews Module ─────────────────────────────────────────────
        if "Reviews" in modules:
            _rev_done = bool(st.session_state.get("reviews_domains") or st.session_state.get("reviews_custom_domain", "").strip())
            with st.expander(("✅  " if _rev_done else "") + "⭐  Reviews", expanded=not _rev_done):
                rev = {}
                rev["Domains"], _rev_domains = domain_selector("Domains *", "reviews")
                _apply_domain_config(rev, "rev", _rev_domains, _rev_crawl_config)
                form_data["Reviews"] = rev

        # ── 6. Price Violation Module ─────────────────────────────────────
        if "Price Violation" in modules:
            _pv_done = bool(st.session_state.get("pv_domains") or st.session_state.get("pv_custom_domain", "").strip())
            with st.expander(("✅  " if _pv_done else "") + "💰  Price Violation", expanded=not _pv_done):
                pv = {}
                pv["Domains"], _pv_domains = domain_selector("Domains *", "pv")
                _apply_domain_config(pv, "pv", _pv_domains, _pv_crawl_config)
                form_data["Price Violation"] = pv

        # ── 7. Store ID Crawls ────────────────────────────────────────────
        if "Store ID Crawls" in modules:
            _sid_done = bool(st.session_state.get("storeid_domains") or st.session_state.get("storeid_custom_domain", "").strip())
            with st.expander(("✅  " if _sid_done else "") + "🏪  Store ID Crawl", expanded=not _sid_done):
                storeid = {}
                storeid["Domains"], _storeid_domains = domain_selector("Domains *", "storeid")
                _apply_domain_config(storeid, "storeid", _storeid_domains, _storeid_crawl_config)
                form_data["Store ID Crawls"] = storeid

        # ── 8. Festive Sale Crawls ────────────────────────────────────────
        if "Festive Sale Crawls" in modules:
            _fest_done = bool(st.session_state.get("festive_domains") or st.session_state.get("festive_custom_domain", "").strip())
            with st.expander(("✅  " if _fest_done else "") + "🎉  Festive Sale Crawls", expanded=not _fest_done):
                festive = {}
                festive["Crawl Type"] = st.radio(
                    "Crawl Type",
                    ["Products + Trends Based", "SOS Type", "Category URL Based"],
                    key="festive_type", horizontal=True,
                )
                if festive["Crawl Type"] == "Products + Trends Based":
                    festive["Domains"], _festive_domains = domain_selector("Domains *", "festive")
                    festive["URL List"] = st.text_area("URL List", placeholder="Provide product/trend URLs for festive crawl", key="festive_pt_urls")
                    st.markdown("**Schedule**")
                    _apply_domain_config(festive, "festive", _festive_domains, _festive_schedule_config)
                elif festive["Crawl Type"] == "Category URL Based":
                    festive["Domains"], _festive_domains = domain_selector("Domains *", "festive")
                    festive["URL List"] = st.text_area("URL List", placeholder="Provide additional URLs for festive crawl", key="festive_cat_urls")
                    st.markdown("**Schedule**")
                    festive.update(_festive_schedule_config())
                else:
                    festive["Domains"], _festive_domains = domain_selector("Domains *", "festive")
                    festive["URL List"] = st.text_area("URL List", placeholder="Provide URLs for festive SOS crawl", key="festive_sos_urls")
                    st.markdown("**Schedule**")
                    festive.update(_festive_schedule_config())
                form_data["Festive Sale Crawls"] = festive

        # ── 9. Final Alignment ────────────────────────────────────────────
        section_header("🎯", "9. Final Alignment")
        form_data["Final Alignment"] = {
            "Client Core Objective": st.text_area(
                "What is the client's core objective? *",
                placeholder="e.g., Market gap analysis, brand monitoring, competitive pricing intelligence, demand trends…",
                key="final_objective",
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

        # ── Save as Template ──────────────────────────────────────────────────
        with st.expander("💾  Save current form as a template", expanded=False):
            _tpl_name_input = st.text_input(
                "Template name",
                placeholder="e.g. Standard QCommerce Setup",
                key="_save_tpl_name",
                label_visibility="collapsed",
            )
            if st.button("💾  Save Template", key="_save_tpl_btn"):
                if not _tpl_name_input.strip():
                    st.error("Give the template a name.")
                else:
                    _tpl_snapshot = {
                        k: v for k, v in st.session_state.items()
                        if isinstance(k, str) and k.startswith(_FORM_KEY_PREFIXES)
                    }
                    _save_form_template(_tpl_name_input.strip(), _tpl_snapshot)
                    st.success(f"Template '{_tpl_name_input.strip()}' saved.")

        st.markdown("<br>", unsafe_allow_html=True)

        # PDF Generation + Download (single button)
        if st.button("⬇️  Generate & Download PDF", type="primary", width="stretch"):
            if not client_name:
                st.error("Enter a Client Name before generating the PDF.")
                st.stop()
            _errors = _validate_form(form_data, modules)
            if _errors:
                st.error("Please fix the following before generating the PDF:")
                for _e in _errors:
                    st.markdown(f"- {_e}")
                st.stop()
            log_event(EVENT_GENERATE_REQ_PDF, st.session_state.get("current_user", ""), st.session_state.get("analytics_sid", ""), "main", {"client": client_name})
            try:
                with st.spinner("Building PDF…"):
                    _pdf_bytes = generate_pdf(form_data, client_name).read()
            except Exception as e:
                st.error(f"PDF generation failed — please try again or contact your admin. ({type(e).__name__})")
                st.stop()
            try:
                save_submission(form_data, client_name, st.session_state.get("current_user", ""))
                _clear_draft(_form_username)
                st.session_state["_draft_dismissed"] = False
            except Exception:
                pass
            log_event(EVENT_DOWNLOAD_REQ_PDF, st.session_state.get("current_user", ""), st.session_state.get("analytics_sid", ""), "main")
            celebrate(message="Downloading PDF…", sub=f"{_h(client_name)} Requirement Form is downloading.")
            _pdf_b64  = base64.b64encode(_pdf_bytes).decode()
            _pdf_name = _safe_filename(client_name, "_Requirement_Form.pdf")
            components.html(f"""<script>
            (function(){{
                var b = atob("{_pdf_b64}");
                var a = new Uint8Array(b.length);
                for(var i=0;i<b.length;i++) a[i]=b.charCodeAt(i);
                var blob = new Blob([a],{{type:"application/pdf"}});
                var url  = URL.createObjectURL(blob);
                var el   = window.parent.document.createElement("a");
                el.href  = url; el.download = "{_pdf_name}";
                window.parent.document.body.appendChild(el);
                el.click();
                window.parent.document.body.removeChild(el);
                URL.revokeObjectURL(url);
            }})();
            </script>""", height=0)

    with right:
        render_summary(form_data)
