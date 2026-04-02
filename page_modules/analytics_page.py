import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
from datetime import datetime

from ui_helpers import section_header, page_title
from analytics import (
    log_event,
    get_summary,
    load_events,
    PAGE_LABELS,
    EVENT_LABELS,
)


def render_analytics():
    page_title("Analytics Dashboard", "Real-time usage insights across all users and features.")

    # ── Controls ───────────────────────────────────────────────────────────────
    period_options = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90, "All time": 3650}
    ctrl1, ctrl2 = st.columns([3, 1])
    with ctrl1:
        period_label = st.selectbox("Time period", list(period_options.keys()), index=1, key="analytics_period")
    with ctrl2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🔄  Refresh", width="stretch"):
            st.rerun()
    days = period_options[period_label]
    summary = get_summary(days)

    # ── KPI cards ──────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)

    def _kpi(label, value, sub=""):
        sub_html = f'<div style="font-size:0.72rem;color:#9ca3af;margin-top:3px;">{sub}</div>' if sub else ""
        return f"""
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px 18px;
                    box-shadow:0 1px 4px rgba(0,0,0,0.05);font-family:'Inter',sans-serif;">
            <div style="font-size:0.72rem;font-weight:600;color:#9ca3af;text-transform:uppercase;
                        letter-spacing:0.08em;margin-bottom:6px;">{label}</div>
            <div style="font-size:1.7rem;font-weight:700;color:#1f2937;line-height:1;">{value}</div>
            {sub_html}
        </div>"""

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(_kpi("Sessions",          summary["total_sessions"],      f"Today: {summary['today_sessions']}"), unsafe_allow_html=True)
    k2.markdown(_kpi("Unique Users",      summary["unique_users"],        f"Today: {summary['today_users']}"),    unsafe_allow_html=True)
    k3.markdown(_kpi("Total Logins",      summary["login_count"]),                                                unsafe_allow_html=True)
    k4.markdown(_kpi("Total Events",      summary["total_events"]),                                               unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    k5, k6, k7, k8 = st.columns(4)
    k5.markdown(_kpi("Docs Generated",    summary["docs_generated"],      "PDFs & feasibility"),                  unsafe_allow_html=True)
    k6.markdown(_kpi("Avg Pages/Session", summary["avg_session_depth"]),                                          unsafe_allow_html=True)
    k7.markdown(_kpi("Peak Hour",         summary["peak_hour_label"],     "Most active"),                         unsafe_allow_html=True)
    k8.markdown(_kpi("Top Page",          summary["most_visited"]),                                               unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Highlights strip ───────────────────────────────────────────────────────
    recent = summary["recent_events"]
    ua = summary["user_activity"]
    top_user = max(ua, key=lambda u: ua[u]) if ua else "—"
    pv = summary["page_views"]
    top_page = list(pv.keys())[0] if pv else "—"
    highlight_items = [
        ("🏆", "Most active user", top_user),
        ("📄", "Most visited page", top_page),
        ("⏰", "Peak usage hour", summary["peak_hour_label"]),
        ("📊", "Avg pages per session", str(summary["avg_session_depth"])),
        ("📝", "Docs / PDFs generated", str(summary["docs_generated"])),
    ]
    cols_h = st.columns(len(highlight_items))
    for col, (icon, label, val) in zip(cols_h, highlight_items):
        col.markdown(f"""
        <div style="background:linear-gradient(135deg,#f8fafc 0%,#f1f5f9 100%);
                    border:1px solid #e5e7eb;border-radius:8px;padding:12px 14px;
                    font-family:'Inter',sans-serif;text-align:center;">
            <div style="font-size:1.3rem;">{icon}</div>
            <div style="font-size:0.7rem;color:#9ca3af;text-transform:uppercase;
                        letter-spacing:0.08em;margin:4px 0 2px 0;font-weight:600;">{label}</div>
            <div style="font-size:0.88rem;font-weight:700;color:#1f2937;">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Activity over time ─────────────────────────────────────────────────────
    section_header("📈", "Activity Over Time")
    epd = summary["events_per_day"]
    if epd:
        df_epd = pd.DataFrame({"Date": list(epd.keys()), "Events": list(epd.values())}).set_index("Date")
        st.line_chart(df_epd, width="stretch", height=200)
    else:
        st.info("No activity recorded yet.")

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2, gap="large")

    # ── Page views ────────────────────────────────────────────────────────────
    with col_left:
        section_header("📄", "Page Views by Section")
        if pv:
            df_pv = pd.DataFrame({"Page": list(pv.keys()), "Views": list(pv.values())}).set_index("Page")
            st.bar_chart(df_pv, width="stretch", height=220)
            total_pv = sum(pv.values())
            rows_pv = [{"Page": k, "Views": v, "Share": f"{v/total_pv*100:.0f}%"} for k, v in pv.items()]
            st.dataframe(pd.DataFrame(rows_pv), width="stretch", hide_index=True)
        else:
            st.info("No page views recorded yet.")

    # ── Hourly heatmap ────────────────────────────────────────────────────────
    with col_right:
        section_header("🕐", "Hourly Activity Distribution")
        hd = summary["hourly_distribution"]
        df_hd = pd.DataFrame({"Hour": list(hd.keys()), "Events": list(hd.values())}).set_index("Hour")
        active_hours = df_hd[df_hd["Events"] > 0]
        if not active_hours.empty:
            st.bar_chart(active_hours, width="stretch", height=220)
            peak_h = active_hours["Events"].idxmax()
            st.caption(f"Peak hour: **{peak_h}** with **{active_hours.loc[peak_h, 'Events']}** events")
        else:
            st.info("No hourly data yet.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Per-user breakdown ────────────────────────────────────────────────────
    section_header("👥", "Per-User Breakdown")
    ub = summary["user_breakdown"]
    if ub:
        df_ub = pd.DataFrame(ub)
        st.dataframe(df_ub, width="stretch", hide_index=True)
    else:
        st.info("No user data yet.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Actions breakdown ─────────────────────────────────────────────────────
    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        section_header("⚡", "Event Type Breakdown")
        actions = summary["actions"]
        if actions:
            total_acts = sum(actions.values())
            rows_act = [{"Event": k, "Count": v, "Share": f"{v/total_acts*100:.0f}%"} for k, v in actions.items()]
            st.dataframe(pd.DataFrame(rows_act), width="stretch", hide_index=True)
        else:
            st.info("No actions recorded yet.")

    with col_b:
        section_header("📊", "User Activity (Total Events)")
        if ua:
            df_ua = pd.DataFrame({"User": list(ua.keys()), "Events": list(ua.values())}).set_index("User")
            st.bar_chart(df_ua, width="stretch", height=220)
        else:
            st.info("No user activity yet.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Recent activity log ───────────────────────────────────────────────────
    section_header("🕐", "Recent Activity Log")
    if recent:
        rows = []
        for e in recent:
            ts_str = e.get("ts", "")
            try:
                ts_str = datetime.fromisoformat(ts_str).astimezone().strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass
            rows.append({
                "Timestamp": ts_str,
                "User":      e.get("username", "—"),
                "Event":     EVENT_LABELS.get(e.get("event", ""), e.get("event", "—")),
                "Page":      PAGE_LABELS.get(e.get("page", ""), e.get("page", "—")) if e.get("page") else "—",
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

        _dl1, _dl2 = st.columns([1, 1])
        with _dl1:
            _filtered_csv = pd.DataFrame(rows).to_csv(index=False).encode()
            st.download_button(
                "⬇️  Export Activity Table (CSV)",
                data=_filtered_csv,
                file_name=f"analytics_{period_label.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                key="analytics_dl_filtered",
            )
        with _dl2:
            raw_events = load_events(days)
            if raw_events:
                csv_data = pd.DataFrame(raw_events).to_csv(index=False).encode()
                st.download_button(
                    "⬇️  Export Full Raw Log (CSV)",
                    data=csv_data,
                    file_name=f"analytics_raw_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="analytics_dl_raw",
                )
    else:
        st.info("No activity recorded yet.")
