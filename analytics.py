"""
analytics.py — Visitor & activity analytics for the 42Signals Requirement Handling app.

Events are appended as newline-delimited JSON (JSONL) to .42s_analytics.jsonl.
Each record is a single JSON object with these fields:
    ts          — ISO-8601 UTC timestamp
    session_id  — UUID assigned per browser session (persists across reruns)
    username    — authenticated username (empty string for unauthenticated events)
    event       — event type string (see EVENT_* constants below)
    page        — page key at time of event (may be empty for login/logout)
    details     — optional dict with extra context
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

_ANALYTICS_FILE = Path(".42s_analytics.jsonl")

# Human-readable labels for page keys
PAGE_LABELS: Dict[str, str] = {
    "main":        "New Requirement Form",
    "feasibility": "Feasibility Assessment",
    "req_flow":    "Requirement Flow",
    "ops_map":     "Day-to-Day Ops Map",
    "poc_guide":   "Task POC Guide",
    "cost_calc":   "Cost Calculator",
    "analytics":   "Analytics Dashboard",
    "ext_tools":   "External Tools",
    "notebooklm":  "NotebookLM",
    "login":       "Login",
}

# Event type constants
EVENT_LOGIN            = "login"
EVENT_LOGOUT           = "logout"
EVENT_PAGE_VIEW        = "page_view"
EVENT_GENERATE_REQ_PDF = "generate_req_pdf"
EVENT_DOWNLOAD_REQ_PDF = "download_req_pdf"
EVENT_GENERATE_FEAS    = "generate_feas_doc"
EVENT_DOWNLOAD_FEAS    = "download_feas_doc"
EVENT_DOWNLOAD_COST_PDF = "download_cost_pdf"
EVENT_DOWNLOAD_COST_CSV = "download_cost_csv"

# Friendly display labels for event types
EVENT_LABELS: Dict[str, str] = {
    EVENT_LOGIN:             "Login",
    EVENT_LOGOUT:            "Logout",
    EVENT_PAGE_VIEW:         "Page View",
    EVENT_GENERATE_REQ_PDF:  "Generate Req. PDF",
    EVENT_DOWNLOAD_REQ_PDF:  "Download Req. PDF",
    EVENT_GENERATE_FEAS:     "Generate Feasibility Doc",
    EVENT_DOWNLOAD_FEAS:     "Download Feasibility Doc",
    EVENT_DOWNLOAD_COST_PDF: "Download Cost PDF",
    EVENT_DOWNLOAD_COST_CSV: "Download Cost CSV",
}


# ─────────────────────────────────────────────────────────────────────────────
# WRITE
# ─────────────────────────────────────────────────────────────────────────────

def log_event(
    event: str,
    username: str = "",
    session_id: str = "",
    page: str = "",
    details: Optional[Dict] = None,
) -> None:
    """Append a single analytics event to the JSONL log file.
    Silently ignores write errors so analytics never breaks the main app."""
    record = {
        "ts":         datetime.now(timezone.utc).isoformat(),
        "session_id": session_id or "",
        "username":   username or "",
        "event":      event,
        "page":       page or "",
        "details":    details or {},
    }
    try:
        with _ANALYTICS_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────────────────────────────────────

def load_events(days: int = 30) -> List[Dict]:
    """Load all events logged within the last *days* days (UTC).
    Malformed lines are silently skipped."""
    if not _ANALYTICS_FILE.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events: List[Dict] = []
    try:
        with _ANALYTICS_FILE.open("r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                    ts = datetime.fromisoformat(rec.get("ts", ""))
                    if ts >= cutoff:
                        events.append(rec)
                except (ValueError, KeyError, TypeError):
                    continue
    except OSError:
        pass
    return events


# ─────────────────────────────────────────────────────────────────────────────
# AGGREGATE
# ─────────────────────────────────────────────────────────────────────────────

def get_summary(days: int = 30) -> dict:
    """Return an aggregated analytics summary dict for the given look-back window."""
    events = load_events(days)

    today = datetime.now(timezone.utc).date()
    today_events = [
        e for e in events
        if datetime.fromisoformat(e["ts"]).date() == today
    ]

    # ── Unique sessions / users ───────────────────────────────────────────────
    total_sessions   = len({e["session_id"] for e in events      if e.get("session_id")})
    unique_users     = len({e["username"]   for e in events      if e.get("username")})
    today_sessions   = len({e["session_id"] for e in today_events if e.get("session_id")})
    today_users      = len({e["username"]   for e in today_events if e.get("username")})

    # ── Page views ────────────────────────────────────────────────────────────
    page_views: Dict[str, int] = defaultdict(int)
    for e in events:
        if e.get("event") == EVENT_PAGE_VIEW and e.get("page"):
            label = PAGE_LABELS.get(e["page"], e["page"])
            page_views[label] += 1

    # ── Events per day ────────────────────────────────────────────────────────
    events_per_day: Dict[str, int] = defaultdict(int)
    for e in events:
        day = datetime.fromisoformat(e["ts"]).date().isoformat()
        events_per_day[day] += 1

    # ── User activity (total events per user) ─────────────────────────────────
    user_activity: Dict[str, int] = defaultdict(int)
    for e in events:
        if e.get("username"):
            user_activity[e["username"]] += 1

    # ── Actions breakdown ─────────────────────────────────────────────────────
    actions: Dict[str, int] = defaultdict(int)
    for e in events:
        label = EVENT_LABELS.get(e.get("event", ""), e.get("event", "unknown"))
        actions[label] += 1

    # ── Logins ────────────────────────────────────────────────────────────────
    login_count = sum(1 for e in events if e.get("event") == EVENT_LOGIN)

    # ── Docs generated ────────────────────────────────────────────────────────
    doc_events = {EVENT_GENERATE_REQ_PDF, EVENT_GENERATE_FEAS, EVENT_DOWNLOAD_COST_PDF}
    docs_generated = sum(1 for e in events if e.get("event") in doc_events)

    # ── Hourly distribution ───────────────────────────────────────────────────
    hourly: Dict[int, int] = defaultdict(int)
    for e in events:
        try:
            h = datetime.fromisoformat(e["ts"]).astimezone().hour
            hourly[h] += 1
        except (ValueError, TypeError):
            pass
    hourly_distribution = {f"{h:02d}:00": hourly[h] for h in range(24)}

    # ── Peak hour ─────────────────────────────────────────────────────────────
    peak_hour = max(hourly, key=lambda h: hourly[h], default=None)
    peak_hour_label = f"{peak_hour:02d}:00–{peak_hour+1:02d}:00" if peak_hour is not None else "—"

    # ── Session depth (avg page views per session) ────────────────────────────
    session_pages: Dict[str, int] = defaultdict(int)
    for e in events:
        if e.get("event") == EVENT_PAGE_VIEW and e.get("session_id"):
            session_pages[e["session_id"]] += 1
    avg_session_depth = round(sum(session_pages.values()) / len(session_pages), 1) if session_pages else 0

    # ── Most visited page ─────────────────────────────────────────────────────
    most_visited = max(page_views, key=lambda k: page_views[k]) if page_views else "—"

    # ── Per-user breakdown ────────────────────────────────────────────────────
    user_logins: Dict[str, int] = defaultdict(int)
    user_page_views: Dict[str, int] = defaultdict(int)
    user_docs: Dict[str, int] = defaultdict(int)
    user_last_seen: Dict[str, str] = {}
    for e in events:
        u = e.get("username", "")
        if not u:
            continue
        ev = e.get("event", "")
        ts = e.get("ts", "")
        if ev == EVENT_LOGIN:
            user_logins[u] += 1
        if ev == EVENT_PAGE_VIEW:
            user_page_views[u] += 1
        if ev in doc_events:
            user_docs[u] += 1
        if not user_last_seen.get(u) or ts > user_last_seen[u]:
            user_last_seen[u] = ts

    user_breakdown = []
    for u in set(list(user_logins.keys()) + list(user_page_views.keys())):
        last = user_last_seen.get(u, "")
        try:
            last = datetime.fromisoformat(last).astimezone().strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            last = "—"
        user_breakdown.append({
            "User":        u,
            "Logins":      user_logins[u],
            "Page Views":  user_page_views[u],
            "Docs Generated": user_docs[u],
            "Last Seen":   last,
        })
    user_breakdown.sort(key=lambda r: r["Page Views"], reverse=True)

    # ── Recent events (newest first, capped at 100) ───────────────────────────
    recent = events[-100:]
    recent.reverse()

    return {
        "total_sessions":      total_sessions,
        "unique_users":        unique_users,
        "today_sessions":      today_sessions,
        "today_users":         today_users,
        "total_events":        len(events),
        "login_count":         login_count,
        "docs_generated":      docs_generated,
        "avg_session_depth":   avg_session_depth,
        "peak_hour_label":     peak_hour_label,
        "most_visited":        most_visited,
        "page_views":          dict(sorted(page_views.items(), key=lambda x: x[1], reverse=True)),
        "events_per_day":      dict(sorted(events_per_day.items())),
        "hourly_distribution": hourly_distribution,
        "user_activity":       dict(sorted(user_activity.items(), key=lambda x: x[1], reverse=True)),
        "user_breakdown":      user_breakdown,
        "actions":             dict(sorted(actions.items(), key=lambda x: x[1], reverse=True)),
        "recent_events":       recent,
    }
