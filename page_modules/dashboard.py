import streamlit as st  # type: ignore
from datetime import date, timedelta
from ui_helpers import _h, section_header
from persistence import list_submissions, load_submission


def render_dashboard():
    _display = st.session_state.get("display_name") or st.session_state.get("current_user") or "there"
    st.markdown(
        f'<h2 style="font-family:\'Inter\',sans-serif;font-size:1.5rem;font-weight:700;'
        f'color:#111827;margin:0 0 4px 0;">Welcome back, {_h(_display)} 👋</h2>'
        f'<p style="color:#6b7280;font-size:0.85rem;margin:0 0 24px 0;">'
        f'{date.today().strftime("%A, %d %B %Y")}</p>',
        unsafe_allow_html=True,
    )

    # ── Stats cards ───────────────────────────────────────────────────────────
    submissions = list_submissions()
    total        = len(submissions)
    in_review    = sum(1 for s in submissions if s.get("status") == "In Review")
    live         = sum(1 for s in submissions if s.get("status") == "Live")
    this_week    = sum(
        1 for s in submissions
        if s.get("saved_at", "") >= (date.today() - timedelta(days=7)).isoformat()
    )

    sc1, sc2, sc3, sc4 = st.columns(4)
    for col, label, value, accent, filter_val in [
        (sc1, "Total Submissions", total,     "#1f2937", "All"),
        (sc2, "In Review",        in_review,  "#f59e0b", "In Review"),
        (sc3, "Live",             live,       "#16a34a", "Live"),
        (sc4, "This Week",        this_week,  "#3b82f6", "All"),
    ]:
        with col:
            st.markdown(
                f'<div style="background:white;border-radius:12px;padding:18px 20px 10px 20px;'
                f'border-left:4px solid {accent};box-shadow:0 2px 8px rgba(0,0,0,0.06);'
                f'font-family:\'Inter\',sans-serif;">'
                f'<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;'
                f'font-weight:700;letter-spacing:0.08em;">{label}</div>'
                f'<div style="font-size:1.8rem;font-weight:800;color:{accent};margin-top:6px;">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("View →", key=f"dash_stat_{label}", width="stretch"):
                st.session_state["hist_status_filter_init"] = filter_val
                st.session_state["page"] = "sub_history"
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Quick actions ─────────────────────────────────────────────────────────
    section_header("⚡", "Quick Actions")
    qa_cols = st.columns(4)
    _quick_actions = [
        ("main",       "📝", "New Requirement",   "Start a new client requirement form"),
        ("feasibility","🔍", "Feasibility Check",  "Evaluate crawl feasibility"),
        ("cost_calc",  "💰", "Cost Calculator",    "Estimate crawl costs"),
        ("sub_history","📂", "Submission History", "View & manage submissions"),
    ]
    for col, (pg, icon, label, desc) in zip(qa_cols, _quick_actions):
        with col:
            st.markdown(
                f'<div style="background:white;border-radius:12px;padding:16px;'
                f'border:1px solid #e5e7eb;text-align:center;font-family:\'Inter\',sans-serif;'
                f'min-height:90px;">'
                f'<div style="font-size:1.5rem;">{icon}</div>'
                f'<div style="font-size:0.82rem;font-weight:600;color:#1f2937;margin-top:6px;">{label}</div>'
                f'<div style="font-size:0.72rem;color:#9ca3af;margin-top:2px;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Open →", key=f"dash_qa_{pg}", width="stretch"):
                st.session_state["page"] = pg
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Recent submissions ────────────────────────────────────────────────────
    section_header("🕐", "Recent Submissions")
    if not submissions:
        st.info("No submissions yet. Create one from the New Requirement Form.")
    else:
        STATUS_COLORS = {"Submitted": "#3b82f6", "In Review": "#f59e0b",
                         "Live": "#16a34a", "Draft": "#94a3b8"}
        rh1, rh2, rh3, rh4 = st.columns([2.5, 1.8, 1.5, 1])
        for col, lbl in zip([rh1, rh2, rh3, rh4], ["Client", "Date", "Status", ""]):
            col.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;color:#6b7280;'
                f'text-transform:uppercase;padding:4px 0;">{lbl}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('<hr style="margin:4px 0 8px 0;border-color:#e5e7eb;">', unsafe_allow_html=True)

        for s in submissions[:8]:
            rc1, rc2, rc3, rc4 = st.columns([2.5, 1.8, 1.5, 1])
            status = s.get("status", "Submitted")
            color  = STATUS_COLORS.get(status, "#94a3b8")
            with rc1:
                st.markdown(
                    f'<div style="font-size:0.85rem;font-weight:600;color:#1f2937;padding:5px 0;">'
                    f'{_h(s["client_name"])}</div>',
                    unsafe_allow_html=True,
                )
            with rc2:
                st.markdown(
                    f'<div style="font-size:0.8rem;color:#6b7280;padding:5px 0;">'
                    f'{_h(s.get("saved_at","")[:10])}</div>',
                    unsafe_allow_html=True,
                )
            with rc3:
                st.markdown(
                    f'<span style="background:{color};color:#fff;border-radius:4px;'
                    f'padding:2px 8px;font-size:0.72rem;font-weight:600;">{_h(status)}</span>',
                    unsafe_allow_html=True,
                )
            with rc4:
                if st.button("Edit", key=f"dash_edit_{s['filename']}", width="stretch"):
                    load_submission(s["filename"])
                    st.session_state["page"] = "main"
                    st.rerun()
            st.markdown('<hr style="margin:2px 0;border-color:#f8fafc;">', unsafe_allow_html=True)

        if total > 8:
            if st.button(f"View all {total} submissions →", key="dash_view_all"):
                st.session_state["page"] = "sub_history"
                st.rerun()
