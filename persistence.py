import streamlit as st  # type: ignore
import json
import re
import uuid
from pathlib import Path
from datetime import date, datetime
from typing import Optional
from ui_helpers import _h, _safe_filename, celebrate, section_header

_SUBMISSIONS_DIR = Path("submissions")
_FORM_KEY_PREFIXES = (
    "form_", "pt_", "sos_", "rev_", "pv_", "storeid_", "festive_", "final_",
)
_TEMPLATES_FILE = Path("form_templates.json")


def _json_default(obj):
    """JSON serialiser for types not handled natively (date, set, etc.)."""
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, set):
        return list(obj)
    return str(obj)


def save_submission(form_data: dict, client_name: str, username: str) -> None:
    _SUBMISSIONS_DIR.mkdir(exist_ok=True)
    editing_file = st.session_state.get("_editing_submission_file")
    if editing_file and (_SUBMISSIONS_DIR / editing_file).exists():
        filename = editing_file
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", client_name or "unknown")
        filename = f"{safe_name}_{timestamp}.json"
    snapshot = {
        k: v for k, v in st.session_state.items()
        if isinstance(k, str) and k.startswith(_FORM_KEY_PREFIXES)
    }
    payload = {
        "client_name": client_name,
        "saved_at": datetime.now().isoformat(),
        "saved_by": username,
        "status": st.session_state.get(f"_sub_status_{filename}", "Submitted"),
        "form_data": form_data,
        "session_state": snapshot,
    }
    with open(_SUBMISSIONS_DIR / filename, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=_json_default)
    st.session_state["_editing_submission_file"] = filename
    list_submissions.clear()


@st.cache_data(ttl=60)
def list_submissions() -> list[dict]:
    if not _SUBMISSIONS_DIR.exists():
        return []
    result = []
    for p in sorted(_SUBMISSIONS_DIR.glob("*.json"), reverse=True):
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            _mods = data.get("form_data", {}).get("Modules Selected", {}).get("Selected Modules", [])
            _mods_str = ", ".join(_mods) if isinstance(_mods, list) else str(_mods) if _mods else "—"
            result.append({
                "filename":    p.name,
                "client_name": data.get("client_name", p.stem),
                "saved_at":    data.get("saved_at", ""),
                "saved_by":    data.get("saved_by", ""),
                "modules":     _mods_str,
                "status":      data.get("status", "Submitted"),
            })
        except Exception:
            pass
    return result


def load_submission(filename: str) -> None:
    path = _SUBMISSIONS_DIR / filename
    if not path.exists():
        st.error("Submission file not found.")
        return
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    _ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for k, v in data.get("session_state", {}).items():
        if isinstance(v, str) and _ISO_DATE_RE.match(v):
            try:
                v = date.fromisoformat(v)
            except ValueError:
                pass
        st.session_state[k] = v
    st.session_state["_editing_submission_file"] = filename
    st.rerun()


def _update_submission_status(filename: str, status: str) -> None:
    path = _SUBMISSIONS_DIR / filename
    if not path.exists():
        return
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        data["status"] = status
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=_json_default)
        list_submissions.clear()
    except (OSError, json.JSONDecodeError):
        pass


def _draft_path(username: str) -> Path:
    safe = re.sub(r"[^a-z0-9_]", "", username.lower())
    return Path(f".42s_draft_{safe}.json")


def _save_draft(username: str, form_data: dict) -> None:
    try:
        snapshot = {k: v for k, v in st.session_state.items()
                    if isinstance(k, str) and k.startswith(_FORM_KEY_PREFIXES)}
        payload = {
            "form_data": form_data,
            "session_state": snapshot,
            "saved_at": datetime.now().isoformat(),
        }
        _draft_path(username).write_text(json.dumps(payload, default=_json_default))
    except OSError:
        pass


def _load_draft(username: str) -> Optional[dict]:
    p = _draft_path(username)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _clear_draft(username: str) -> None:
    try:
        _draft_path(username).unlink(missing_ok=True)
    except OSError:
        pass


def _field_filled(section, field):
    val = section.get(field)
    if isinstance(val, list):
        return bool(val)
    if val:
        return True
    return any(v for k, v in section.items() if k.endswith(f"\u2014 {field}") and v)


def _validate_form(form_data, modules):
    errors = []
    if not form_data.get("Client Information", {}).get("Target Market"):
        errors.append("**Client Information** \u2014 Target Market / Geography is required.")
    if not modules:
        errors.append("**Modules** \u2014 Select at least one module.")
    if "Products + Trends" in modules:
        if not form_data.get("Products + Trends", {}).get("Domains"):
            errors.append("**Products + Trends** \u2014 At least one domain is required.")
    if "SOS (Search on Site)" in modules:
        sos = form_data.get("SOS (Search on Site)", {})
        if not sos.get("Domains"):
            errors.append("**SOS** \u2014 At least one domain is required.")
        if not int(sos.get("No. of Keywords", 0)):
            errors.append("**SOS** \u2014 Number of Keywords must be greater than 0.")
    if "Reviews" in modules:
        rev = form_data.get("Reviews", {})
        if not rev.get("Domains"):
            errors.append("**Reviews** \u2014 At least one domain is required.")
        if not _field_filled(rev, "Input Sources"):
            errors.append("**Reviews** \u2014 At least one input source must be selected.")
    if "Price Violation" in modules:
        pv = form_data.get("Price Violation", {})
        if not pv.get("Domains"):
            errors.append("**Price Violation** \u2014 At least one domain is required.")
        if not _field_filled(pv, "Product URL List"):
            errors.append("**Price Violation** \u2014 Product URL list is required.")
    if "Store ID Crawls" in modules:
        if not form_data.get("Store ID Crawls", {}).get("Domains"):
            errors.append("**Store ID Crawls** \u2014 At least one domain is required.")
    if "Festive Sale Crawls" in modules:
        festive = form_data.get("Festive Sale Crawls", {})
        if festive.get("Crawl Type") == "Products + Trends Based" and not festive.get("Domains"):
            errors.append("**Festive Sale Crawls** \u2014 Domains required for Products + Trends Based type.")
    if not form_data.get("Final Alignment", {}).get("Client Core Objective"):
        errors.append("**Final Alignment** \u2014 Client Core Objective is required.")
    return errors


def _load_form_templates() -> dict:
    if not _TEMPLATES_FILE.exists():
        return {}
    try:
        return json.loads(_TEMPLATES_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_form_template(name: str, snapshot: dict) -> None:
    tpls = _load_form_templates()
    tpls[name] = {"snapshot": snapshot, "saved_at": datetime.now().isoformat()}
    try:
        _TEMPLATES_FILE.write_text(json.dumps(tpls, indent=2, default=_json_default))
    except OSError:
        pass


def _delete_form_template(name: str) -> None:
    tpls = _load_form_templates()
    tpls.pop(name, None)
    try:
        _TEMPLATES_FILE.write_text(json.dumps(tpls, indent=2, default=_json_default))
    except OSError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Cost estimate persistence
# ─────────────────────────────────────────────────────────────────────────────

_COST_ESTIMATES_DIR = Path("cost_estimates")
_CC_KEY_PREFIXES = ("cc_",)


def save_cost_estimate(client_name: str, username: str, results: list, grand_total: float, session_snapshot: dict) -> str:
    """Save a cost estimate to disk. Returns the filename."""
    _COST_ESTIMATES_DIR.mkdir(exist_ok=True)
    editing_file = st.session_state.get("_editing_cost_file")
    if editing_file and (_COST_ESTIMATES_DIR / editing_file).exists():
        filename = editing_file
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", client_name or "unknown")
        filename = f"{safe_name}_{timestamp}.json"
    payload = {
        "client_name": client_name,
        "saved_at": datetime.now().isoformat(),
        "saved_by": username,
        "grand_total": grand_total,
        "results": results,
        "session_state": session_snapshot,
    }
    with open(_COST_ESTIMATES_DIR / filename, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=_json_default)
    st.session_state["_editing_cost_file"] = filename
    list_cost_estimates.clear()
    return filename


@st.cache_data(ttl=60)
def list_cost_estimates() -> list[dict]:
    if not _COST_ESTIMATES_DIR.exists():
        return []
    result = []
    for p in sorted(_COST_ESTIMATES_DIR.glob("*.json"), reverse=True):
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            result.append({
                "filename":    p.name,
                "client_name": data.get("client_name", p.stem),
                "saved_at":    data.get("saved_at", ""),
                "saved_by":    data.get("saved_by", ""),
                "grand_total": data.get("grand_total", 0.0),
            })
        except Exception:
            pass
    return result


def load_cost_estimate(filename: str) -> None:
    """Restore session state from a saved cost estimate."""
    path = _COST_ESTIMATES_DIR / filename
    if not path.exists():
        st.error("Cost estimate file not found.")
        return
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    # Keys that belong to Streamlit button/radio widgets — cannot be set via session_state
    _CC_BLOCKED_KEYS = {
        "cc_gen_top", "cc_currency", "cc_period", "cc_fx_rate",
        "cc_domain_input_mode", "cc_bulk_paste", "cc_bulk_csv",
        "cc_scenario_name", "cc_show_results", "cc_saved_scenarios",
        "cc_clear_scenarios",
        "_cc_save_btn", "_cc_save_new_btn", "_cc_new_btn",
    }
    _CC_BLOCKED_PREFIXES = ("cc_ct_", "cc_zip_")

    for k, v in data.get("session_state", {}).items():
        if k in _CC_BLOCKED_KEYS or any(k.startswith(p) for p in _CC_BLOCKED_PREFIXES):
            continue
        st.session_state[k] = v

    # Also purge any blocked keys that may have been saved by older snapshots
    for k in list(st.session_state.keys()):
        if k in _CC_BLOCKED_KEYS or any(k.startswith(p) for p in _CC_BLOCKED_PREFIXES):
            st.session_state.pop(k, None)

    st.session_state["_editing_cost_file"] = filename
    st.session_state["cc_show_results"] = True
    st.rerun()


def delete_cost_estimate(filename: str) -> None:
    path = _COST_ESTIMATES_DIR / filename
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    list_cost_estimates.clear()


def _extract_domains_from_submission(form_data: dict) -> list[str]:
    domains: list[str] = []
    for _section in form_data.values():
        if isinstance(_section, dict):
            _d = _section.get("Domains")
            if isinstance(_d, list):
                domains.extend(_d)
    return list(dict.fromkeys(d for d in domains if d))
