import streamlit as st  # type: ignore
import json
from datetime import datetime

from ui_helpers import _h, page_title
from persistence import (
    list_submissions, load_submission,
    _update_submission_status, _extract_domains_from_submission,
    _json_default, _SUBMISSIONS_DIR,
)


def render_submission_history():
    page_title("Submission History", "Browse, filter, and manage all saved client requirement submissions.")

    submissions = list_submissions()
    if not submissions:
        st.markdown("""
        <div style="background:#fff;border:2px dashed #e5e7eb;border-radius:14px;
                    padding:56px 20px;text-align:center;font-family:'Inter',sans-serif;margin-top:20px;">
            <div style="font-size:2.5rem;margin-bottom:12px;">📋</div>
            <div style="font-size:1rem;font-weight:700;color:#111827;margin-bottom:6px;">No submissions yet</div>
            <div style="font-size:0.85rem;color:#6b7280;max-width:360px;margin:0 auto;">
                Generate a PDF from the <strong>New Requirement Form</strong> to create your first submission.
                It will appear here for tracking and reference.
            </div>
        </div>""", unsafe_allow_html=True)
        return

    VALID_STATUSES = ["Submitted", "In Review", "Live", "Draft"]
    STATUS_COLORS  = {
        "Submitted":  "#3b82f6",
        "In Review":  "#f59e0b",
        "Live":       "#16a34a",
        "Draft":      "#94a3b8",
    }

    # ── Search / filter bar ───────────────────────────────────────────────────
    _status_preset = st.session_state.pop("hist_status_filter_init", "All")
    _all_statuses  = ["All"] + VALID_STATUSES
    _preset_idx    = _all_statuses.index(_status_preset) if _status_preset in _all_statuses else 0

    f1, f2, f3 = st.columns([3, 2, 2])
    with f1:
        _search = st.text_input("Search by client name", placeholder="Type to filter…", key="hist_search", label_visibility="collapsed")
    with f2:
        _status_filter = st.selectbox("Filter by status", _all_statuses, index=_preset_idx, key="hist_status_filter", label_visibility="collapsed")
    with f3:
        _saved_by_filter = st.selectbox(
            "Filter by user",
            ["All"] + sorted({s["saved_by"] for s in submissions if s.get("saved_by")}),
            key="hist_user_filter",
            label_visibility="collapsed",
        )

    fd1, fd2, _ = st.columns([2, 2, 3])
    with fd1:
        st.caption("Submitted from")
        _date_from = st.date_input("From date", value=None, key="hist_date_from", label_visibility="collapsed")
    with fd2:
        st.caption("Submitted to")
        _date_to = st.date_input("To date", value=None, key="hist_date_to", label_visibility="collapsed")

    filtered = [
        s for s in submissions
        if (_search.lower() in s["client_name"].lower() if _search else True)
        and (_status_filter == "All" or s.get("status") == _status_filter)
        and (_saved_by_filter == "All" or s.get("saved_by") == _saved_by_filter)
        and (not _date_from or s.get("saved_at", "")[:10] >= str(_date_from))
        and (not _date_to   or s.get("saved_at", "")[:10] <= str(_date_to))
    ]

    st.markdown(f'<p style="font-size:0.78rem;color:#94a3b8;margin:4px 0 12px 0;">{len(filtered)} of {len(submissions)} submissions</p>', unsafe_allow_html=True)

    if not filtered:
        st.markdown("""
        <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px;
                    padding:40px 20px;text-align:center;font-family:'Inter',sans-serif;margin-top:8px;">
            <div style="font-size:2rem;margin-bottom:10px;">🔍</div>
            <div style="font-size:0.95rem;font-weight:700;color:#374151;margin-bottom:4px;">No results found</div>
            <div style="font-size:0.82rem;color:#9ca3af;">Try adjusting your search term or filters above.</div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Table header ──────────────────────────────────────────────────────────
    hc1, hc2, hc3, hc4, hc5 = st.columns([2.5, 1.8, 2.5, 1.5, 3])
    for col, label in zip([hc1, hc2, hc3, hc4, hc5],
                          ["Client", "Date", "Modules", "Status", "Actions"]):
        col.markdown(f'<div style="font-size:0.72rem;font-weight:700;color:#6b7280;text-transform:uppercase;padding:4px 0;">{label}</div>', unsafe_allow_html=True)

    st.markdown('<hr style="margin:4px 0 8px 0;border-color:#e5e7eb;">', unsafe_allow_html=True)

    # ── Rows ──────────────────────────────────────────────────────────────────
    for s in filtered:
        rc1, rc2, rc3, rc4, rc5 = st.columns([2.5, 1.8, 2.5, 1.5, 3])
        status_now = s.get("status", "Submitted")
        color      = STATUS_COLORS.get(status_now, "#94a3b8")
        _fkey      = s["filename"]

        with rc1:
            st.markdown(f'<div style="font-size:0.85rem;font-weight:600;color:#1f2937;padding:6px 0;">{_h(s["client_name"])}</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.72rem;color:#9ca3af;">by {_h(s.get("saved_by","—"))}</div>', unsafe_allow_html=True)
        with rc2:
            _dt = s.get("saved_at","")[:16].replace("T"," ")
            st.markdown(f'<div style="font-size:0.82rem;color:#374151;padding:6px 0;">{_h(_dt)}</div>', unsafe_allow_html=True)
        with rc3:
            st.markdown(f'<div style="font-size:0.78rem;color:#64748b;padding:6px 0;">{_h(s.get("modules","—"))}</div>', unsafe_allow_html=True)
        with rc4:
            new_status = st.selectbox(
                "status",
                VALID_STATUSES,
                index=VALID_STATUSES.index(status_now) if status_now in VALID_STATUSES else 0,
                key=f"hist_status_{_fkey}",
                label_visibility="collapsed",
            )
            if new_status != status_now:
                _update_submission_status(_fkey, new_status)
                _sub_path = _SUBMISSIONS_DIR / _fkey
                if _sub_path.exists():
                    try:
                        _sub_data = json.loads(_sub_path.read_text())
                        _sub_data.setdefault("notes", []).append({
                            "author":    "system",
                            "timestamp": datetime.now().isoformat(),
                            "text":      f"Status changed from {status_now} → {new_status} by {st.session_state.get('current_user', '—')}",
                        })
                        _sub_path.write_text(json.dumps(_sub_data, indent=2, default=_json_default))
                        list_submissions.clear()
                    except (OSError, json.JSONDecodeError):
                        pass
                st.toast(f"Status updated to **{new_status}**", icon="✅")
                st.rerun()
            st.markdown(
                f'<span style="background:{color};color:#fff;border-radius:4px;padding:2px 8px;'
                f'font-size:0.72rem;font-weight:600;">{_h(status_now)}</span>',
                unsafe_allow_html=True,
            )
        with rc5:
            a1, a2, a3 = st.columns(3)
            a4, a5, _  = st.columns(3)
            with a1:
                if st.button("✏️ Edit", key=f"hist_edit_{_fkey}", width="stretch"):
                    load_submission(_fkey)
            with a2:
                if st.button("💰 Cost Calc", key=f"hist_cost_{_fkey}", width="stretch"):
                    _sub_path = _SUBMISSIONS_DIR / _fkey
                    if _sub_path.exists():
                        try:
                            _sub_data = json.loads(_sub_path.read_text())
                            _domains  = _extract_domains_from_submission(_sub_data.get("form_data", {}))
                            if _domains:
                                st.session_state["cc_selected_domains"] = _domains
                                st.session_state["cc_domain_input_mode"] = "Select from list"
                        except (OSError, json.JSONDecodeError):
                            pass
                    st.session_state["page"] = "cost_calc"
                    st.rerun()
            with a3:
                if st.button("🔍 Feasibility", key=f"hist_feas_{_fkey}", width="stretch"):
                    _sub_path = _SUBMISSIONS_DIR / _fkey
                    if _sub_path.exists():
                        try:
                            _sub_data = json.loads(_sub_path.read_text())
                            _fd       = _sub_data.get("form_data", {})
                            _domains  = _extract_domains_from_submission(_fd)
                            st.session_state["feas_client"]      = _sub_data.get("client_name", "")
                            st.session_state["feas_num_domains"] = max(len(_domains), 1)
                            for _i, _d in enumerate(_domains):
                                st.session_state[f"feas_domain_{_i}"] = _d
                        except (OSError, json.JSONDecodeError):
                            pass
                    st.session_state["page"] = "feasibility"
                    st.rerun()
            with a4:
                if st.button("📝 Notes", key=f"hist_note_{_fkey}", width="stretch"):
                    st.session_state[f"_show_notes_{_fkey}"] = not st.session_state.get(f"_show_notes_{_fkey}", False)
            with a5:
                if st.button("🗑️ Delete", key=f"hist_del_{_fkey}", width="stretch"):
                    st.session_state[f"_confirm_del_{_fkey}"] = True

        # ── Inline Notes ──────────────────────────────────────────────────────
        if st.session_state.get(f"_show_notes_{_fkey}"):
            _sub_path = _SUBMISSIONS_DIR / _fkey
            _notes = []
            if _sub_path.exists():
                try:
                    _sub_data = json.loads(_sub_path.read_text())
                    _notes = _sub_data.get("notes", [])
                except (OSError, json.JSONDecodeError):
                    pass

            with st.container():
                st.markdown('<div style="background:#f8fafc;border-radius:8px;padding:12px 16px;border:1px solid #e5e7eb;margin:4px 0 8px 0;">', unsafe_allow_html=True)

                if _notes:
                    for _n in _notes:
                        _n_ts   = _n.get("timestamp","")[:16].replace("T"," ")
                        _n_auth = _n.get("author","—")
                        _n_txt  = _n.get("text","")
                        st.markdown(
                            f'<div style="margin-bottom:8px;font-family:\'Inter\',sans-serif;">'
                            f'<span style="font-size:0.72rem;color:#6b7280;">'
                            f'{_h(_n_auth)} · {_h(_n_ts)}</span><br>'
                            f'<span style="font-size:0.83rem;color:#1f2937;">{_h(_n_txt)}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("No notes yet.")

                _note_input = st.text_input(
                    "Add a note",
                    placeholder="e.g. Client confirmed zipcode on 20 Mar",
                    key=f"note_input_{_fkey}",
                    label_visibility="collapsed",
                )
                if st.button("💬  Add Note", key=f"note_save_{_fkey}") and _note_input.strip():
                    if _sub_path.exists():
                        try:
                            _sub_data = json.loads(_sub_path.read_text())
                            _sub_data.setdefault("notes", []).append({
                                "author":    st.session_state.get("current_user",""),
                                "timestamp": datetime.now().isoformat(),
                                "text":      _note_input.strip(),
                            })
                            _sub_path.write_text(json.dumps(_sub_data, indent=2, default=_json_default))
                            list_submissions.clear()
                        except (OSError, json.JSONDecodeError):
                            pass
                    st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

        # ── Inline delete confirmation ─────────────────────────────────────────
        if st.session_state.get(f"_confirm_del_{_fkey}"):
            conf_col, cancel_col, _ = st.columns([1, 1, 4])
            with conf_col:
                if st.button("Confirm Delete", key=f"hist_del_confirm_{_fkey}", type="primary"):
                    try:
                        (_SUBMISSIONS_DIR / _fkey).unlink(missing_ok=True)
                        list_submissions.clear()
                    except OSError:
                        pass
                    st.session_state.pop(f"_confirm_del_{_fkey}", None)
                    st.rerun()
            with cancel_col:
                if st.button("Cancel", key=f"hist_del_cancel_{_fkey}"):
                    st.session_state.pop(f"_confirm_del_{_fkey}", None)
                    st.rerun()

        st.markdown('<hr style="margin:2px 0;border-color:#f1f5f9;">', unsafe_allow_html=True)
