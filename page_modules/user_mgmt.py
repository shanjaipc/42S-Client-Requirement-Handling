import streamlit as st  # type: ignore

from ui_helpers import section_header, page_title
from credentials import (
    add_user, set_password, set_role, set_active, list_users, save_users,
)


def render_user_management():
    page_title("User Management", "Add users, reset passwords, change roles, and deactivate accounts.")

    # ── Current users table ───────────────────────────────────────────────────
    section_header("👥", "Current Users")
    _users = list_users()
    _me = st.session_state.get("current_user", "")
    _admins = [u for u in _users if u["role"] == "admin" and u["active"]]

    # styled user cards table
    st.markdown("""
    <div style="display:grid;grid-template-columns:1fr 1fr 120px 100px;
                gap:0;background:#f1f5f9;border-radius:10px 10px 0 0;
                padding:9px 16px;font-family:'Inter',sans-serif;">
        <div style="font-size:0.7rem;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;">Username</div>
        <div style="font-size:0.7rem;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;">Display Name</div>
        <div style="font-size:0.7rem;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;">Role</div>
        <div style="font-size:0.7rem;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;">Status</div>
    </div>""", unsafe_allow_html=True)
    for _u in _users:
        _role_color  = "#6366f1" if _u["role"] == "admin" else "#64748b"
        _role_bg     = "#eef2ff" if _u["role"] == "admin" else "#f1f5f9"
        _stat_color  = "#16a34a" if _u["active"] else "#dc2626"
        _stat_bg     = "#f0fdf4" if _u["active"] else "#fef2f2"
        _stat_label  = "Active"  if _u["active"] else "Deactivated"
        _you_badge   = f'<span style="font-size:0.62rem;background:#fef9c3;color:#854d0e;border-radius:4px;padding:1px 6px;margin-left:6px;font-weight:600;">you</span>' if _u["username"] == _me else ""
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr 120px 100px;
                    gap:0;background:#fff;border-left:1px solid #e5e7eb;border-right:1px solid #e5e7eb;
                    border-bottom:1px solid #f1f5f9;padding:11px 16px;
                    font-family:'Inter',sans-serif;align-items:center;">
            <div style="font-size:0.85rem;font-weight:600;color:#111827;">{_u['username']}{_you_badge}</div>
            <div style="font-size:0.85rem;color:#374151;">{_u['display_name']}</div>
            <div><span style="background:{_role_bg};color:{_role_color};border-radius:5px;
                              padding:2px 9px;font-size:0.72rem;font-weight:700;">{_u['role'].capitalize()}</span></div>
            <div><span style="background:{_stat_bg};color:{_stat_color};border-radius:5px;
                              padding:2px 9px;font-size:0.72rem;font-weight:700;">{_stat_label}</span></div>
        </div>""", unsafe_allow_html=True)
    st.markdown('<div style="border:1px solid #e5e7eb;border-top:none;border-radius:0 0 10px 10px;height:6px;background:#fff;"></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab_add, tab_pwd, tab_role, tab_deact = st.tabs(
        ["➕ Add User", "🔑 Reset Password", "🎭 Change Role", "🚫 Deactivate / Activate"]
    )

    # ── Add User ──────────────────────────────────────────────────────────────
    with tab_add:
        with st.form("um_add_form"):
            a1, a2 = st.columns(2)
            with a1:
                _new_uname  = st.text_input("Username *", placeholder="e.g. priya")
                _new_disp   = st.text_input("Display Name *", placeholder="e.g. Priya")
            with a2:
                _new_pwd    = st.text_input("Password *", type="password")
                _new_role   = st.selectbox("Role", ["viewer", "admin"])
            if st.form_submit_button("➕  Add User", type="primary"):
                if not _new_uname.strip() or not _new_pwd.strip() or not _new_disp.strip():
                    st.error("Username, Display Name and Password are required.")
                elif add_user(_new_uname.strip(), _new_pwd.strip(), _new_disp.strip(), _new_role):
                    save_users()
                    st.success(f"User '{_new_uname.strip()}' added successfully.")
                    st.rerun()
                else:
                    st.error(f"Username '{_new_uname.strip()}' already exists.")

    # ── Reset Password ────────────────────────────────────────────────────────
    with tab_pwd:
        with st.form("um_pwd_form"):
            _pwd_uname = st.selectbox("Select user", [u["username"] for u in _users])
            _new_pwd2  = st.text_input("New Password *", type="password")
            _conf_pwd  = st.text_input("Confirm Password *", type="password")
            if st.form_submit_button("🔑  Reset Password", type="primary"):
                if not _new_pwd2.strip():
                    st.error("Password cannot be empty.")
                elif _new_pwd2 != _conf_pwd:
                    st.error("Passwords do not match.")
                elif set_password(_pwd_uname, _new_pwd2.strip()):
                    save_users()
                    st.success(f"Password updated for '{_pwd_uname}'.")
                else:
                    st.error("Failed to update password.")

    # ── Change Role ───────────────────────────────────────────────────────────
    with tab_role:
        with st.form("um_role_form"):
            _role_users = [u for u in _users if u["username"] != _me]
            if _role_users:
                _role_uname   = st.selectbox("Select user", [u["username"] for u in _role_users])
                _current_role = next((u["role"] for u in _users if u["username"] == _role_uname), "viewer")
                _new_role2    = st.selectbox("New role", ["viewer", "admin"],
                                             index=0 if _current_role == "viewer" else 1)
                if st.form_submit_button("🎭  Update Role", type="primary"):
                    _target_admins = [u for u in _users if u["role"] == "admin" and u["active"] and u["username"] != _role_uname]
                    if _new_role2 == "viewer" and not _target_admins:
                        st.error("Cannot demote the last active admin.")
                    elif set_role(_role_uname, _new_role2):
                        save_users()
                        st.success(f"'{_role_uname}' is now a {_new_role2}.")
                    else:
                        st.error("Failed to update role.")
            else:
                st.info("No other users to manage roles for.")

    # ── Deactivate / Activate ─────────────────────────────────────────────────
    with tab_deact:
        with st.form("um_deact_form"):
            _deact_others = [u for u in _users if u["username"] != _me]
            if _deact_others:
                _deact_uname  = st.selectbox("Select user", [u["username"] for u in _deact_others])
                _is_active    = next((u["active"] for u in _users if u["username"] == _deact_uname), True)
                _action_label = "🚫  Deactivate" if _is_active else "✅  Activate"
                if st.form_submit_button(_action_label, type="primary"):
                    if _is_active:
                        _remaining_admins = [u for u in _admins if u["username"] != _deact_uname]
                        _deact_role = next((u["role"] for u in _users if u["username"] == _deact_uname), "viewer")
                        if _deact_role == "admin" and not _remaining_admins:
                            st.error("Cannot deactivate the last active admin.")
                        else:
                            set_active(_deact_uname, False)
                            save_users()
                            st.success(f"'{_deact_uname}' has been deactivated.")
                            st.rerun()
                    else:
                        set_active(_deact_uname, True)
                        save_users()
                        st.success(f"'{_deact_uname}' has been re-activated.")
                        st.rerun()
            else:
                st.info("No other users to manage.")
