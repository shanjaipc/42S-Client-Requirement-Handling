import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
from datetime import date
from pathlib import Path

from ui_helpers import section_header, page_title


def render_rate_manager():
    page_title(
        "Rate Manager",
        "Add, edit, or remove crawl cost rates for any platform. Changes are saved directly to crawl_cost_rates.csv.",
    )

    _RATES_CSV = Path("crawl_cost_rates.csv")
    _COLS      = ["domain", "display_name", "zipcode", "sku_rate", "cat_rate", "kw_rate", "last_updated"]

    if not _RATES_CSV.exists():
        st.warning("crawl_cost_rates.csv not found — a new one will be created when you save.")
        df = pd.DataFrame(columns=_COLS)
    else:
        df = pd.read_csv(_RATES_CSV)
        for c in _COLS:
            if c not in df.columns:
                df[c] = "" if c in ("domain", "display_name", "last_updated") else False if c == "zipcode" else 0.0

    # ── Meta bar ─────────────────────────────────────────────────────────────
    last_updated = str(df["last_updated"].iloc[0]).strip() if len(df) > 0 else date.today().strftime("%d %b %Y")
    m1, m2, m3 = st.columns([2, 2, 2])
    with m1:
        st.markdown(f"""
        <div style="background:white;border-radius:10px;padding:14px 16px;border-left:4px solid #1f2937;
        box-shadow:0 1px 4px rgba(0,0,0,0.06);font-family:'Inter',sans-serif;">
            <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;font-weight:700;">Domains</div>
            <div style="font-size:1.1rem;font-weight:700;color:#0f172a;margin-top:4px;">{df['domain'].nunique()}</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div style="background:white;border-radius:10px;padding:14px 16px;border-left:4px solid #0369a1;
        box-shadow:0 1px 4px rgba(0,0,0,0.06);font-family:'Inter',sans-serif;">
            <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;font-weight:700;">Rates Last Updated</div>
            <div style="font-size:1.1rem;font-weight:700;color:#0f172a;margin-top:4px;">{last_updated}</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div style="background:white;border-radius:10px;padding:14px 16px;border-left:4px solid #16a34a;
        box-shadow:0 1px 4px rgba(0,0,0,0.06);font-family:'Inter',sans-serif;">
            <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;font-weight:700;">Rate Rows</div>
            <div style="font-size:1.1rem;font-weight:700;color:#0f172a;margin-top:4px;">{len(df)}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Editable rate table ───────────────────────────────────────────────────
    section_header("📋", "Rate Table")
    st.markdown(
        '<p style="font-size:0.8rem;color:#64748b;margin:0 0 8px 0;font-family:\'Inter\',sans-serif;">'
        'Edit cells directly. Use the <b>+</b> row at the bottom to add a new entry. '
        'Each domain needs <b>two rows</b> — one with Zipcode <b>unchecked</b> (without) and one <b>checked</b> (with).</p>',
        unsafe_allow_html=True,
    )

    edit_df = df[["domain", "display_name", "zipcode", "sku_rate", "cat_rate", "kw_rate", "last_updated"]].copy()
    edit_df["zipcode"] = edit_df["zipcode"].astype(str).str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    ).fillna(False).astype(bool)
    for col in ("sku_rate", "cat_rate", "kw_rate"):
        edit_df[col] = pd.to_numeric(edit_df[col], errors="coerce").fillna(0.0)
    edit_df["last_updated"] = edit_df["last_updated"].astype(str).replace("nan", "").fillna("")

    edited = st.data_editor(
        edit_df,
        num_rows="dynamic",
        width="stretch",
        key="rate_mgr_editor",
        column_config={
            "domain":       st.column_config.TextColumn("Domain",        help="e.g. amazon.in",    width="medium"),
            "display_name": st.column_config.TextColumn("Display Name",  help="e.g. Amazon India", width="medium"),
            "zipcode":      st.column_config.CheckboxColumn("With Zipcode", help="Check for the zipcode variant of this domain"),
            "sku_rate":     st.column_config.NumberColumn("SKU Rate",    help="Cost per SKU crawl",      format="%.10f", min_value=0.0),
            "cat_rate":     st.column_config.NumberColumn("Category Rate", help="Cost per category crawl", format="%.10f", min_value=0.0),
            "kw_rate":      st.column_config.NumberColumn("Keyword Rate", help="Cost per keyword crawl",  format="%.10f", min_value=0.0),
            "last_updated": st.column_config.TextColumn("Last Updated",  help="e.g. 24 Mar 2026",  width="medium"),
        },
    )

    # ── Apply global date to all rows ─────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,#f0f9ff 0%,#e0f2fe 100%);
                border:1px solid #bae6fd;border-left:4px solid #0369a1;
                border-radius:10px;padding:14px 18px;margin:16px 0 8px 0;
                font-family:'Inter',sans-serif;">
        <div style="font-size:0.78rem;font-weight:700;color:#0c4a6e;margin-bottom:2px;">
            📅 Bulk Date Stamp
        </div>
        <div style="font-size:0.78rem;color:#0369a1;">
            Pick a date and check the box to apply it to all rows on save.
        </div>
    </div>""", unsafe_allow_html=True)

    date_col, toggle_col, _ = st.columns([2, 2, 2])
    with date_col:
        picked_date = st.date_input("Stamp date", value=date.today(), key="rate_mgr_date_stamp", label_visibility="collapsed")
    with toggle_col:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        apply_all = st.checkbox("Apply to all sites", key="rate_mgr_apply_all")
    apply_date_str = picked_date.strftime("%d %b %Y") if apply_all else ""
    if apply_all:
        st.markdown(f"""<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;
                         padding:9px 14px;font-size:0.8rem;color:#166534;font-family:'Inter',sans-serif;">
            ✅ All rows will be stamped with <strong>{apply_date_str}</strong> when you save.
        </div>""", unsafe_allow_html=True)

    # ── Save ─────────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    save_col, _ = st.columns([1, 3])
    with save_col:
        if st.button("💾  Save Changes", type="primary", width="stretch"):
            if edited.empty:
                st.error("Cannot save an empty rate table.")
            else:
                missing = edited[edited["domain"].astype(str).str.strip() == ""]
                if not missing.empty:
                    st.error(f"{len(missing)} row(s) have an empty Domain — fill them in before saving.")
                else:
                    save_df = edited.copy()
                    if apply_date_str:
                        save_df["last_updated"] = apply_date_str
                    save_df["zipcode"] = save_df["zipcode"].astype(bool)
                    save_df.to_csv(_RATES_CSV, index=False)
                    st.success(f"Saved {len(save_df)} rows to crawl_cost_rates.csv")
                    st.rerun()
