import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import html as _html_mod
from datetime import date, datetime
from io import BytesIO

from ui_helpers import page_title, section_header, _h

_CATS = [
    "Volume Drop", "Missing Uploads", "Data Issues", "New Site",
    "New Requirement", "Delivery Delay", "Other / Technical",
]

_OPEN_STATUSES = ["Open", "In Progress", "Blocked", "Pending Client"]

_CLOSED_STATUSES = {
    "Done & Closed",
    "Done, Client Informed & Closed",
    "No Action Required",
    "Done, Awaiting Feedback",
}


def _init():
    defs = {
        "mr_client": "", "mr_period": "", "mr_prepared_by": "",
        "mr_poc": "", "mr_target": 90, "mr_avg_days": 0,
        "mr_open_14": 0, "mr_carryover": 0,
        "mr_highlights": "", "mr_risks": "", "mr_changes": "", "mr_next_focus": "",
    }
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v



def _kpi_card(label, value, accent="#1f2937", sub=""):
    sub_html = (
        f'<div style="font-size:0.7rem;color:#9ca3af;margin-top:3px;">{_h(sub)}</div>'
        if sub else ""
    )
    return (
        f'<div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;'
        f'padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,.05);'
        f'font-family:\'Inter\',sans-serif;border-top:3px solid {accent};">'
        f'<div style="font-size:0.68rem;font-weight:700;color:#9ca3af;text-transform:uppercase;'
        f'letter-spacing:0.08em;margin-bottom:6px;">{_h(label)}</div>'
        f'<div style="font-size:1.6rem;font-weight:700;color:{accent};line-height:1;">{_h(str(value))}</div>'
        f'{sub_html}</div>'
    )


def _verdict_badge(rate, target):
    if rate is None:
        return '<span style="background:#f4f6f8;color:#5a6b7c;border-radius:12px;padding:4px 12px;font-size:12px;font-weight:700;">Enter data</span>'
    if rate >= target:
        return (
            f'<span style="background:#dcfce7;color:#16803c;border-radius:12px;'
            f'padding:4px 12px;font-size:12px;font-weight:700;">'
            f'YES — {rate:.1f}% meets {target}% target</span>'
        )
    return (
        f'<span style="background:#fde2e2;color:#b42318;border-radius:12px;'
        f'padding:4px 12px;font-size:12px;font-weight:700;">'
        f'NO — {rate:.1f}% below {target}% target</span>'
    )


def _generate_pdf(identity, kpis, cat_df, open_df, wait_df, narrative):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
    from reportlab.lib import pagesizes  # type: ignore
    from reportlab.lib.units import inch  # type: ignore
    from reportlab.lib.colors import HexColor  # type: ignore

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=pagesizes.letter,
        leftMargin=0.6*inch, rightMargin=0.6*inch,
        topMargin=0.7*inch, bottomMargin=0.7*inch,
    )

    styles = getSampleStyleSheet()
    navy   = HexColor("#1F3A5F")
    teal   = HexColor("#00B4D8")
    light  = HexColor("#EAF3F8")
    grey   = HexColor("#F4F6F8")
    ink    = HexColor("#1A2B3C")
    mid    = HexColor("#5A6B7C")
    line   = HexColor("#C9D4DE")

    title_s = ParagraphStyle("T", parent=styles["Normal"], fontSize=16, textColor=HexColor("#ffffff"),
                              fontName="Helvetica-Bold", spaceAfter=0)
    sec_s   = ParagraphStyle("H", parent=styles["Normal"], fontSize=10, textColor=HexColor("#ffffff"),
                              fontName="Helvetica-Bold", spaceAfter=0)
    lbl_s   = ParagraphStyle("L", parent=styles["Normal"], fontSize=8, textColor=mid,
                              fontName="Helvetica-Bold")
    val_s   = ParagraphStyle("V", parent=styles["Normal"], fontSize=9, textColor=ink)
    th_s    = ParagraphStyle("TH", parent=styles["Normal"], fontSize=8, textColor=HexColor("#ffffff"),
                              fontName="Helvetica-Bold")
    td_s    = ParagraphStyle("TD", parent=styles["Normal"], fontSize=8, textColor=ink)
    note_s  = ParagraphStyle("N", parent=styles["Normal"], fontSize=8, textColor=mid, fontName="Helvetica-Oblique")

    W = 7.3 * inch

    def p(text, style=None):
        style = style or val_s
        return Paragraph(_html_mod.escape(str(text)), style)

    def sec_header(txt):
        t = Table([[p(txt, sec_s)]], colWidths=[W])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), navy),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
        ]))
        return t

    def kv_table(pairs):
        rows = []
        for i in range(0, len(pairs), 2):
            row = []
            for j in range(2):
                if i + j < len(pairs):
                    k, v = pairs[i + j]
                    row += [p(k, lbl_s), p(v)]
                else:
                    row += [p(""), p("")]
            rows.append(row)
        cw = [W*0.2, W*0.3, W*0.2, W*0.3]
        t = Table(rows, colWidths=cw)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,-1), light),
            ("BACKGROUND", (2,0), (2,-1), light),
            ("GRID", (0,0), (-1,-1), 0.5, line),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
        ]))
        return t

    el = []

    # Title banner
    title_t = Table([[p("MONTHLY REVIEW REPORT", title_s)]], colWidths=[W])
    title_t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), navy),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
    ]))
    el.append(title_t)
    el.append(Spacer(1, 4))

    # Identity
    el.append(sec_header("REPORT IDENTITY"))
    el.append(kv_table([
        ("Client / Project", identity["client"]),
        ("Reporting Period", identity["period"]),
        ("Prepared By", identity["prepared_by"]),
        ("Report Date", identity["report_date"]),
        ("Primary POC", identity["poc"]),
        ("Closure Rate Target", f"{identity['target']}%"),
    ]))
    el.append(Spacer(1, 8))

    # KPIs
    el.append(sec_header("1  SNAPSHOT KPIs"))
    el.append(kv_table([
        ("Total Issues", str(kpis["total"])),
        ("Closed", str(kpis["closed"])),
        ("Open (carried fwd)", str(kpis["open"])),
        ("Closure Rate", kpis["rate_str"]),
        ("Target Met?", kpis["verdict_str"]),
        ("Avg. Days to Close", str(identity["avg_days"])),
        ("Open > 14 Days", str(identity["open_14"])),
        ("Carry-over from Prior", str(identity["carryover"])),
    ]))
    el.append(Spacer(1, 8))

    # Category table
    el.append(sec_header("2  ISSUES BY CATEGORY"))
    cat_hdr = ["Category", "Total", "Closed", "Open", "% of Total"]
    cat_rows = [[p(h, th_s) for h in cat_hdr]]
    for _, row in cat_df.iterrows():
        cat_rows.append([
            p(str(row["Category"]), td_s),
            p(str(int(row["Total"])), td_s),
            p(str(int(row["Closed"])), td_s),
            p(str(int(row["Open"])), td_s),
            p(str(row["% of Total"]), td_s),
        ])
    gt = cat_df["Total"].sum()
    gc = cat_df["Closed"].sum()
    cat_rows.append([
        p("TOTAL", ParagraphStyle("B", parent=styles["Normal"], fontSize=8, fontName="Helvetica-Bold", textColor=ink)),
        p(str(int(gt)), td_s), p(str(int(gc)), td_s),
        p(str(int(gt - gc)), td_s),
        p("100%" if gt else "—", td_s),
    ])
    cw = [W*0.38, W*0.15, W*0.15, W*0.15, W*0.17]
    cat_t = Table(cat_rows, colWidths=cw)
    cat_t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), teal),
        ("BACKGROUND", (0,-1), (-1,-1), grey),
        ("BACKGROUND", (0,1), (0,-2), light),
        ("GRID", (0,0), (-1,-1), 0.5, line),
        ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
    ]))
    el.append(cat_t)
    el.append(Spacer(1, 8))

    # Open issues
    if not open_df.empty:
        el.append(sec_header("3  OPEN ISSUES — DETAIL & ACTION PLAN"))
        oi_hdr = list(open_df.columns)
        oi_rows = [[p(h, th_s) for h in oi_hdr]]
        for _, row in open_df.iterrows():
            oi_rows.append([p(str(row[c] or ""), td_s) for c in oi_hdr])
        cw_oi = [W*0.1, W*0.12, W*0.24, W*0.24, W*0.14, W*0.16]
        oi_t = Table(oi_rows, colWidths=cw_oi)
        oi_t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), teal),
            ("GRID", (0,0), (-1,-1), 0.5, line),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        el.append(oi_t)
        el.append(Spacer(1, 8))

    # Waiting items
    if not wait_df.empty:
        el.append(sec_header("4  ITEMS AWAITING CLIENT FEEDBACK / ACTION"))
        wt_hdr = list(wait_df.columns)
        wt_rows = [[p(h, th_s) for h in wt_hdr]]
        for _, row in wait_df.iterrows():
            wt_rows.append([p(str(row[c] or ""), td_s) for c in wt_hdr])
        cw_wt = [W*0.12, W*0.38, W*0.3, W*0.2]
        wt_t = Table(wt_rows, colWidths=cw_wt)
        wt_t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), teal),
            ("GRID", (0,0), (-1,-1), 0.5, line),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        el.append(wt_t)
        el.append(Spacer(1, 8))

    # Narrative
    el.append(sec_header("5  NARRATIVE"))
    narr_pairs = [
        ("Highlights / Wins", narrative["highlights"]),
        ("Risks / Concerns", narrative["risks"]),
        ("Changes This Month", narrative["changes"]),
        ("Next Month Focus", narrative["next_focus"]),
    ]
    narr_rows = []
    for k, v in narr_pairs:
        narr_rows.append([p(k, lbl_s), p(v or "—")])
    narr_t = Table(narr_rows, colWidths=[W*0.25, W*0.75])
    narr_t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), light),
        ("GRID", (0,0), (-1,-1), 0.5, line),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    el.append(narr_t)

    doc.build(el)
    return buf.getvalue()


def render_monthly_review():
    _init()
    page_title("Monthly Client Review", "One form per client per month — tracks issues, closure rates, and next steps.")

    # ── Reset button ──────────────────────────────────────────────────────────
    if st.button("+ New Review", key="mr_reset"):
        for k in list(st.session_state.keys()):
            if k.startswith("mr_"):
                del st.session_state[k]
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Report Identity ───────────────────────────────────────────────────────
    section_header("📋", "Report Identity")
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.session_state["mr_client"] = st.text_input(
            "Client / Project", value=st.session_state["mr_client"],
            placeholder="e.g., FastFashion", key="mr_client_inp")
    with r1c2:
        st.session_state["mr_period"] = st.text_input(
            "Reporting Period", value=st.session_state["mr_period"],
            placeholder="e.g., June 2026", key="mr_period_inp")
    with r1c3:
        st.session_state["mr_prepared_by"] = st.text_input(
            "Prepared By", value=st.session_state["mr_prepared_by"],
            placeholder="Team / name", key="mr_prep_inp")

    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        _rd = st.date_input("Report Date", value=date.today(), key="mr_report_date_inp")
    with r2c2:
        st.session_state["mr_poc"] = st.text_input(
            "Primary POC", value=st.session_state["mr_poc"], key="mr_poc_inp")
    with r2c3:
        st.session_state["mr_target"] = st.number_input(
            "Closure Rate Target (%)", min_value=0, max_value=100,
            value=int(st.session_state["mr_target"]), key="mr_target_inp")

    # ── Issues by Category ────────────────────────────────────────────────────
    section_header("2️⃣", "Issues by Category")
    st.caption("Enter Total and Closed per category — Open and % fill automatically.")

    # Column headers
    _th_style = (
        'font-size:0.72rem;font-weight:700;color:#6b7280;text-transform:uppercase;'
        'letter-spacing:0.08em;padding:4px 0 6px 0;'
    )
    hc1, hc2, hc3, hc4, hc5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
    hc1.markdown(f'<div style="{_th_style}">Category</div>', unsafe_allow_html=True)
    hc2.markdown(f'<div style="{_th_style}text-align:center;">Total</div>', unsafe_allow_html=True)
    hc3.markdown(f'<div style="{_th_style}text-align:center;">Closed</div>', unsafe_allow_html=True)
    hc4.markdown(f'<div style="{_th_style}text-align:center;">Open</div>', unsafe_allow_html=True)
    hc5.markdown(f'<div style="{_th_style}text-align:center;">% of Total</div>', unsafe_allow_html=True)

    st.markdown('<hr style="margin:0 0 6px 0;border-color:#e5e7eb;">', unsafe_allow_html=True)

    # Pre-read totals for % computation (uses previous render's values — updates on next rerun)
    _grand_for_pct = sum(int(st.session_state.get(f"mr_cat_tot_{i}", 0)) for i in range(len(_CATS))) or 1

    cat_rows = []
    for i, cat in enumerate(_CATS):
        rc1, rc2, rc3, rc4, rc5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
        with rc1:
            st.markdown(
                f'<div style="font-size:0.85rem;font-weight:500;color:#1f2937;'
                f'padding:10px 0 6px 0;">{_h(cat)}</div>',
                unsafe_allow_html=True,
            )
        with rc2:
            tot = st.number_input(
                "Total", min_value=0, step=1,
                value=int(st.session_state.get(f"mr_cat_tot_{i}", 0)),
                key=f"mr_cat_tot_{i}", label_visibility="collapsed",
            )
        with rc3:
            clo = st.number_input(
                "Closed", min_value=0, max_value=int(tot), step=1,
                value=min(int(st.session_state.get(f"mr_cat_clo_{i}", 0)), int(tot)),
                key=f"mr_cat_clo_{i}", label_visibility="collapsed",
            )
        opn = int(tot) - int(clo)
        pct = f"{100 * int(tot) / _grand_for_pct:.1f}%" if _grand_for_pct > 0 and int(tot) > 0 else "—"
        with rc4:
            st.markdown(
                f'<div style="font-size:0.85rem;color:#f59e0b;font-weight:600;'
                f'text-align:center;padding:10px 0;">{opn}</div>',
                unsafe_allow_html=True,
            )
        with rc5:
            st.markdown(
                f'<div style="font-size:0.85rem;color:#6b7280;'
                f'text-align:center;padding:10px 0;">{pct}</div>',
                unsafe_allow_html=True,
            )
        cat_rows.append({"Category": cat, "Total": int(tot), "Closed": int(clo),
                         "Open": opn, "% of Total": pct})
        st.markdown('<hr style="margin:0;border-color:#f1f5f9;">', unsafe_allow_html=True)

    edited_cat = pd.DataFrame(cat_rows)
    grand_total  = int(edited_cat["Total"].sum())
    grand_closed = int(edited_cat["Closed"].sum())
    grand_open   = grand_total - grand_closed

    # Totals summary row
    rate = (100.0 * grand_closed / grand_total) if grand_total else None
    target = int(st.session_state["mr_target"])

    st.markdown(
        f'<div style="background:#f4f6f8;border:1px solid #c9d4de;border-radius:6px;'
        f'padding:8px 14px;margin:4px 0 0 0;font-family:\'Inter\',sans-serif;'
        f'display:flex;gap:24px;font-size:0.82rem;font-weight:600;">'
        f'<span>TOTAL: {grand_total}</span>'
        f'<span style="color:#16a34a;">Closed: {grand_closed}</span>'
        f'<span style="color:#f59e0b;">Open: {grand_open}</span>'
        f'<span style="color:#3b82f6;">Closure Rate: {"—" if rate is None else f"{rate:.1f}%"}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Snapshot KPIs ─────────────────────────────────────────────────────────
    section_header("1️⃣", "Snapshot KPIs")
    st.caption("Totals computed from the category table above.")

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(_kpi_card("Total Issues",        grand_total,  "#1f2937"), unsafe_allow_html=True)
    k2.markdown(_kpi_card("Closed",              grand_closed, "#16a34a"), unsafe_allow_html=True)
    k3.markdown(_kpi_card("Open (carried fwd)",  grand_open,   "#f59e0b"), unsafe_allow_html=True)
    k4.markdown(_kpi_card("Closure Rate", "—" if rate is None else f"{rate:.1f}%",
                           "#3b82f6"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    k5, k6, k7, k8 = st.columns(4)
    with k5:
        st.markdown(
            f'<div style="margin-top:2px;">{_verdict_badge(rate, target)}</div>',
            unsafe_allow_html=True,
        )
        st.caption("Target met?")
    with k6:
        st.session_state["mr_avg_days"] = st.number_input(
            "Avg. days to close", min_value=0.0, step=0.1,
            value=float(st.session_state.get("mr_avg_days", 0)),
            key="mr_avg_days_inp")
    with k7:
        st.session_state["mr_open_14"] = st.number_input(
            "Issues open > 14 days", min_value=0,
            value=int(st.session_state.get("mr_open_14", 0)),
            key="mr_open14_inp")
    with k8:
        st.session_state["mr_carryover"] = st.number_input(
            "Carry-over from prior months", min_value=0,
            value=int(st.session_state.get("mr_carryover", 0)),
            key="mr_carryover_inp")

    # ── Open Issues ───────────────────────────────────────────────────────────
    section_header("3️⃣", "Open Issues — Detail & Action Plan")
    st.caption("One row per open issue.")

    if "mr_open_count" not in st.session_state:
        st.session_state["mr_open_count"] = 2

    _th = _th_style  # reuse header style from above
    oh1, oh2, oh3, oh4, oh5, oh6 = st.columns([1, 1.2, 2.5, 2.5, 1.2, 1.2])
    for _col, _lbl in zip([oh1, oh2, oh3, oh4, oh5, oh6],
                           ["Issue ID", "Status", "Site(s) / Description", "Action Plan", "Owner", "Target Date"]):
        _col.markdown(f'<div style="{_th_style}">{_lbl}</div>', unsafe_allow_html=True)
    st.markdown('<hr style="margin:0 0 4px 0;border-color:#e5e7eb;">', unsafe_allow_html=True)

    open_rows = []
    for i in range(int(st.session_state["mr_open_count"])):
        oc1, oc2, oc3, oc4, oc5, oc6 = st.columns([1, 1.2, 2.5, 2.5, 1.2, 1.2])
        with oc1:
            iid = st.text_input("ID", value=st.session_state.get(f"mr_oi_id_{i}", ""),
                                 key=f"mr_oi_id_{i}", label_visibility="collapsed", placeholder="e.g. OI-01")
        with oc2:
            sta = st.selectbox("Status", _OPEN_STATUSES,
                                index=_OPEN_STATUSES.index(st.session_state.get(f"mr_oi_st_{i}", "Open")),
                                key=f"mr_oi_st_{i}", label_visibility="collapsed")
        with oc3:
            des = st.text_input("Description", value=st.session_state.get(f"mr_oi_des_{i}", ""),
                                 key=f"mr_oi_des_{i}", label_visibility="collapsed", placeholder="Site / description")
        with oc4:
            act = st.text_input("Action Plan", value=st.session_state.get(f"mr_oi_act_{i}", ""),
                                 key=f"mr_oi_act_{i}", label_visibility="collapsed", placeholder="Action plan")
        with oc5:
            own = st.text_input("Owner", value=st.session_state.get(f"mr_oi_own_{i}", ""),
                                 key=f"mr_oi_own_{i}", label_visibility="collapsed", placeholder="Owner")
        with oc6:
            tdt = st.text_input("Date", value=st.session_state.get(f"mr_oi_dt_{i}", ""),
                                 key=f"mr_oi_dt_{i}", label_visibility="collapsed", placeholder="YYYY-MM-DD")
        open_rows.append({"Issue ID": iid, "Status": sta, "Site(s) / Description": des,
                           "Action Plan": act, "Owner": own, "Target Date": tdt})
        st.markdown('<hr style="margin:0;border-color:#f1f5f9;">', unsafe_allow_html=True)

    oa, ob = st.columns([1, 5])
    with oa:
        if st.button("+ Add Row", key="mr_open_add"):
            st.session_state["mr_open_count"] += 1
            st.rerun()
    with ob:
        if int(st.session_state["mr_open_count"]) > 1 and st.button("− Remove Last", key="mr_open_rem"):
            st.session_state["mr_open_count"] -= 1
            st.rerun()

    open_df = pd.DataFrame(open_rows)

    # ── Awaiting Client Feedback ──────────────────────────────────────────────
    section_header("4️⃣", "Items Awaiting Client Feedback / Action")

    if "mr_wait_count" not in st.session_state:
        st.session_state["mr_wait_count"] = 2

    wh1, wh2, wh3, wh4 = st.columns([1.2, 3, 2.5, 1.5])
    for _col, _lbl in zip([wh1, wh2, wh3, wh4],
                            ["Issue ID", "What was Delivered / Resolved", "Awaiting from Client", "Since (Date)"]):
        _col.markdown(f'<div style="{_th_style}">{_lbl}</div>', unsafe_allow_html=True)
    st.markdown('<hr style="margin:0 0 4px 0;border-color:#e5e7eb;">', unsafe_allow_html=True)

    wait_rows = []
    for i in range(int(st.session_state["mr_wait_count"])):
        wc1, wc2, wc3, wc4 = st.columns([1.2, 3, 2.5, 1.5])
        with wc1:
            wid = st.text_input("ID", value=st.session_state.get(f"mr_wi_id_{i}", ""),
                                  key=f"mr_wi_id_{i}", label_visibility="collapsed", placeholder="e.g. OI-03")
        with wc2:
            wdl = st.text_input("Delivered", value=st.session_state.get(f"mr_wi_dl_{i}", ""),
                                  key=f"mr_wi_dl_{i}", label_visibility="collapsed", placeholder="What was delivered / resolved")
        with wc3:
            waw = st.text_input("Awaiting", value=st.session_state.get(f"mr_wi_aw_{i}", ""),
                                  key=f"mr_wi_aw_{i}", label_visibility="collapsed", placeholder="Awaiting from client")
        with wc4:
            wdt = st.text_input("Since", value=st.session_state.get(f"mr_wi_dt_{i}", ""),
                                  key=f"mr_wi_dt_{i}", label_visibility="collapsed", placeholder="YYYY-MM-DD")
        wait_rows.append({"Issue ID": wid, "What was Delivered / Resolved": wdl,
                           "Awaiting from Client": waw, "Since (Date)": wdt})
        st.markdown('<hr style="margin:0;border-color:#f1f5f9;">', unsafe_allow_html=True)

    wa, wb = st.columns([1, 5])
    with wa:
        if st.button("+ Add Row", key="mr_wait_add"):
            st.session_state["mr_wait_count"] += 1
            st.rerun()
    with wb:
        if int(st.session_state["mr_wait_count"]) > 1 and st.button("− Remove Last", key="mr_wait_rem"):
            st.session_state["mr_wait_count"] -= 1
            st.rerun()

    wait_df = pd.DataFrame(wait_rows)

    # ── Narrative ─────────────────────────────────────────────────────────────
    section_header("5️⃣", "Narrative")
    nc1, nc2 = st.columns(2)
    with nc1:
        st.session_state["mr_highlights"] = st.text_area(
            "Highlights / Wins",
            value=st.session_state["mr_highlights"],
            placeholder="e.g., All volume-drop issues closed within SLA.",
            key="mr_highlights_inp", height=100)
        st.session_state["mr_changes"] = st.text_area(
            "Changes This Month",
            value=st.session_state["mr_changes"],
            placeholder="e.g., Added macys.com; updated schema for price fields.",
            key="mr_changes_inp", height=100)
    with nc2:
        st.session_state["mr_risks"] = st.text_area(
            "Risks / Concerns",
            value=st.session_state["mr_risks"],
            placeholder="e.g., Variant-page price gaps pending parser fix.",
            key="mr_risks_inp", height=100)
        st.session_state["mr_next_focus"] = st.text_area(
            "Next Month Focus",
            value=st.session_state["mr_next_focus"],
            placeholder="e.g., macys.com go-live, fresh QA baseline.",
            key="mr_next_inp", height=100)

    # ── PDF Download ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1px solid #e5e7eb;margin:4px 0 20px 0;">', unsafe_allow_html=True)

    pdf_col, _ = st.columns([1, 3])
    with pdf_col:
        client_val   = st.session_state.get("mr_client_inp", "") or st.session_state.get("mr_client", "")
        period_val   = st.session_state.get("mr_period_inp", "") or st.session_state.get("mr_period", "")
        prep_val     = st.session_state.get("mr_prepared_by", "")
        poc_val      = st.session_state.get("mr_poc", "")
        target_val   = int(st.session_state.get("mr_target", 90))
        avg_days_val = float(st.session_state.get("mr_avg_days", 0))
        open14_val   = int(st.session_state.get("mr_open_14", 0))
        carry_val    = int(st.session_state.get("mr_carryover", 0))

        identity = {
            "client":      client_val,
            "period":      period_val,
            "prepared_by": prep_val,
            "report_date": str(_rd),
            "poc":         poc_val,
            "target":      target_val,
            "avg_days":    avg_days_val,
            "open_14":     open14_val,
            "carryover":   carry_val,
        }
        kpis = {
            "total":      grand_total,
            "closed":     grand_closed,
            "open":       grand_open,
            "rate_str":   "—" if rate is None else f"{rate:.1f}%",
            "verdict_str": ("—" if rate is None else
                            (f"YES — {rate:.1f}% meets {target_val}% target"
                             if rate >= target_val
                             else f"NO — {rate:.1f}% below {target_val}% target")),
        }
        narrative = {
            "highlights": st.session_state.get("mr_highlights", ""),
            "risks":      st.session_state.get("mr_risks", ""),
            "changes":    st.session_state.get("mr_changes", ""),
            "next_focus": st.session_state.get("mr_next_focus", ""),
        }

        import re as _re
        _safe = lambda s: _re.sub(r"[^\w-]+", "_", s.strip()) or "Review"
        fname = f"Monthly_Review_{_safe(client_val)}_{_safe(period_val)}.pdf"

        try:
            pdf_bytes = _generate_pdf(identity, kpis, edited_cat, open_df, wait_df, narrative)
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=fname,
                mime="application/pdf",
                key="mr_dl_pdf",
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")
