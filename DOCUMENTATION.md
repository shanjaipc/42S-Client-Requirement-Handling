# 42Signals — Client Requirement Handling Portal
### Complete Technical & User Documentation

---

## Table of Contents

1. [Overview](#1-overview)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [Architecture](#4-architecture)
5. [How to Run](#5-how-to-run)
6. [Authentication & Security](#6-authentication--security)
7. [Session Management](#7-session-management)
8. [User Roles & Permissions](#8-user-roles--permissions)
9. [Navigation & Pages](#9-navigation--pages)
10. [Page: Dashboard](#10-page-dashboard)
11. [Page: New Requirement Form](#11-page-new-requirement-form)
12. [Page: Submission History](#12-page-submission-history)
13. [Page: Feasibility Assessment](#13-page-feasibility-assessment)
14. [Page: Cost Calculator](#14-page-cost-calculator)
15. [Page: Requirement Flow](#15-page-requirement-flow)
16. [Page: Ops Map](#16-page-ops-map)
17. [Page: Task POC Guide](#17-page-task-poc-guide)
18. [Page: Analytics Dashboard (Admin)](#18-page-analytics-dashboard-admin)
19. [Page: Rate Manager (Admin)](#19-page-rate-manager-admin)
20. [Page: User Management (Admin)](#20-page-user-management-admin)
21. [Data Storage & File System](#21-data-storage--file-system)
22. [Analytics System](#22-analytics-system)
23. [Cost Rate System](#23-cost-rate-system)
24. [PDF Generation](#24-pdf-generation)
25. [Form Templates & Drafts](#25-form-templates--drafts)
26. [UI Design System](#26-ui-design-system)
27. [Key Helper Functions](#27-key-helper-functions)
28. [Deployment Guide](#28-deployment-guide)
29. [Adding & Managing Users](#29-adding--managing-users)
30. [Troubleshooting](#30-troubleshooting)

---

## 1. Overview

The **42Signals Client Requirement Handling Portal** is a multi-page internal web application built with Streamlit. It centralises the entire client onboarding workflow — from capturing crawl requirements and assessing feasibility, to estimating costs, generating PDFs, and tracking submission status.

**What it solves:**
- Standardises how crawl requirements are collected from clients
- Gives the ops/sales team a single place to estimate costs before committing
- Provides managers real-time visibility into what's in progress, in review, or live
- Keeps reference material (workflow maps, POC guides) one click away

**Who uses it:**
- **Viewers** — fill forms, generate PDFs, check costs, use reference pages
- **Admins** — all viewer capabilities + manage users, rates, and view analytics

---

## 2. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend / UI** | Streamlit 1.x | Python-native web UI, handles state & reactivity |
| **PDF Generation** | ReportLab (Platypus) | Requirement form PDFs and cost estimate PDFs |
| **Word Documents** | python-docx | Feasibility assessment .docx export |
| **Data Handling** | pandas | CSV parsing, DataFrame operations |
| **Interactive Maps** | D3.js v7 (bundled) | Requirement flow, ops map, POC guide mind maps |
| **Password Hashing** | hashlib (PBKDF2-HMAC-SHA256, 260k iterations) | Credential security |
| **Persistence** | JSON / JSONL / CSV files | Sessions, submissions, analytics, rates |
| **Browser Storage** | Custom Streamlit component + localStorage | Cross-tab session persistence |
| **Language** | Python 3.9+ | Core runtime |
| **Hosting** | Any Linux VPS | `streamlit run app.py` |

**Python Dependencies:**
```
streamlit
pandas
reportlab
python-docx
```

No database. All state is stored in flat files on disk.

---

## 3. Project Structure

```
42S-Client-Requirement-Handling/
│
├── app.py                        # Main application (5,000+ lines)
├── credentials.py                # User registry + auth functions
├── analytics.py                  # Event logging + aggregation
├── crawl_cost_rates.csv          # Cost rates per domain/platform
├── 42slogo.png                   # Brand logo (sidebar + PDF header)
├── 42slogo_top.png               # Browser tab favicon
├── d3.v7.min.js                  # D3.js bundled locally (no CDN)
├── DOCUMENTATION.md              # This file
│
├── session_component/            # Custom Streamlit component
│   └── ...                       # Handles browser localStorage sync
│
├── submissions/                  # Created automatically on first save
│   └── ClientName_YYYYMMDD_HHMMSS.json
│
├── users_db.json                 # Runtime user additions (auto-created)
├── form_templates.json           # Saved form templates (auto-created)
│
# Runtime files (created by app, not committed):
├── .42s_session.json             # Server-side session token
├── .42s_lockout.json             # Login brute-force tracking
├── .42s_analytics.jsonl          # Event log (newline-delimited JSON)
└── .42s_draft_<username>.json    # Per-user auto-save draft
```

---

## 4. Architecture

### Single-File SPA Pattern

The app uses a **single-page application pattern** inside Streamlit. All pages are Python functions that render into the same Streamlit container. Page routing is controlled by `st.session_state["page"]`.

```
Browser Request
     │
     ▼
Streamlit Runtime (reruns entire script on any interaction)
     │
     ▼
app.py → checks st.session_state["authenticated"]
     │
     ├── Not authenticated → render_login()
     │
     └── Authenticated →
               │
               ├── render_sidebar()   ← always shown
               │
               └── Router:
                     page == "dashboard"   → render_dashboard()
                     page == "main"        → render_main_form()
                     page == "sub_history" → render_submission_history()
                     page == "feasibility" → render_feasibility()
                     page == "cost_calc"   → render_cost_calculator()
                     page == "req_flow"    → render_req_flow()
                     page == "ops_map"     → render_ops_map()
                     page == "poc_guide"   → render_poc_guide()
                     page == "ext_tools"   → render_ext_tools()
                     page == "analytics"   → render_analytics()   [admin]
                     page == "rate_mgr"    → render_rate_manager() [admin]
                     page == "user_mgmt"   → render_user_management() [admin]
```

### State Management

Streamlit reruns the entire script on every user interaction. All persistent state lives in `st.session_state` (in-memory per browser tab) or flat files (cross-session persistence).

```
┌─────────────────────────────────────┐
│         Browser Tab                  │
│  st.session_state (in-memory)        │
│  localStorage (via component)        │
└──────────────┬──────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────┐
│         Streamlit Server             │
│  app.py reruns on each interaction   │
│                                      │
│  File I/O:                           │
│  .42s_session.json    (sessions)     │
│  .42s_lockout.json    (lockout)      │
│  .42s_analytics.jsonl (events)       │
│  .42s_draft_*.json    (drafts)       │
│  submissions/*.json   (submissions)  │
│  crawl_cost_rates.csv (rates)        │
│  users_db.json        (users)        │
└─────────────────────────────────────┘
```

### Session Sync Architecture

A custom Streamlit component bridges browser `localStorage` and server session state:

```
On page load:
  localStorage["42s_token"] → component → st.session_state["ls_token"]
  → server validates token in .42s_session.json
  → if valid: auto-login (no password required)

On login:
  server writes .42s_session.json
  → st.session_state["ls_write_token"] = token
  → component reads it → writes localStorage["42s_token"]

On logout / session expiry:
  st.session_state["ls_clear"] = True
  → component clears localStorage
  → user sees login page with "Session expired" notice
```

---

## 5. How to Run

### Local Development

```bash
# 1. Clone the repo
git clone https://github.com/shanjaipc/42S-Client-Requirement-Handling
cd 42S-Client-Requirement-Handling

# 2. Install dependencies
pip install streamlit pandas reportlab python-docx

# 3. Run
streamlit run app.py

# App opens at http://localhost:8501
```

### Production (VPS)

```bash
# Run in background, log to file
nohup streamlit run app.py --server.port 8501 > streamlit.log 2>&1 &

# Or with explicit host binding for reverse proxy
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

The app at `https://project-planning.42signals.com/` is reverse-proxied (nginx/caddy) to port 8501 on the VPS.

### Restarting on VPS

```bash
# Find process
ps aux | grep streamlit | grep -v grep

# Kill and restart
kill <PID>
cd /home/shanjai/42S-Client-Requirement-Handling
nohup streamlit run app.py --server.port 8501 > streamlit.log 2>&1 &
```

### Deploying Updates

```bash
# From local machine — push to origin
git push origin upd

# On VPS — pull and restart
cd /home/shanjai/42S-Client-Requirement-Handling
git pull origin upd
kill $(pgrep -f "streamlit run")
nohup streamlit run app.py --server.port 8501 > streamlit.log 2>&1 &
```

---

## 6. Authentication & Security

### Password Storage (credentials.py)

Passwords are **never stored in plaintext**. The storage scheme:

```
plaintext password
       │
       ▼
PBKDF2-HMAC-SHA256(password, salt, iterations=260_000)
       │
       ▼
hex digest (stored as "hash" in USERS dict)
```

Each user has a unique random 32-byte hex `salt`. Even identical passwords produce different hashes.

### Login Flow

```
User submits username + password
         │
         ▼
Check server-side lockout (.42s_lockout.json)
  → if locked: show countdown, auto-refresh every 1s, block form
         │
         ▼
Check session-state lockout (covers current tab state)
         │
         ▼
Validate both fields filled
         │
         ▼
verify_password(username, password)
  → constant-time comparison (secrets.compare_digest)
  → also checks user.active flag
         │
    ┌────┴────┐
  Pass      Fail
    │          │
    ▼          ▼
Set auth    Increment attempt counter
state       If attempts >= 5:
Save          Lock for 300 seconds
session       (server-side + session-state)
Log event
Rerun
```

### Brute-Force Protection

- **5 failed attempts** triggers a **5-minute lockout**
- Lockout persists in `.42s_lockout.json` — survives browser refresh and tab changes
- Countdown timer displayed on login screen (refreshes every second)
- Separate tracking per username

### XSS Prevention

All user-supplied values rendered inside `unsafe_allow_html=True` blocks are escaped through `_h(value)` which calls `html.escape(str(value), quote=True)`.

### Safe Filenames

Download filenames are sanitized by `_safe_filename(name, suffix)`:
- Strips `< > : " / \ | ? * \x00`
- Limits to 80 characters
- Appends safe suffix (e.g. `_Requirement_Form.pdf`)

---

## 7. Session Management

### Server-Side Session

A session token (UUID) is stored in `.42s_session.json` with a 7-day TTL:

```json
{
  "token": "uuid-string",
  "username": "shanjai",
  "display_name": "Shanjai",
  "expires": "2026-04-01T10:30:00+00:00"
}
```

### Browser Session (localStorage)

The `session_component` custom Streamlit component:
1. Reads `localStorage["42s_token"]` on page load → sends to Python
2. Python validates the token against `.42s_session.json`
3. If valid and not expired → auto-login without password
4. On new login → Python writes token → component saves to `localStorage`
5. On logout → Python sets `ls_clear=True` → component deletes from `localStorage`

This means:
- **Closing and reopening the browser** → still logged in (for 7 days)
- **Opening a new tab** → auto-logged in
- **Session expired server-side** → shown "Session expired" notice on login page

---

## 8. User Roles & Permissions

| Feature | Viewer | Admin |
|---------|--------|-------|
| Dashboard | ✅ | ✅ |
| New Requirement Form | ✅ | ✅ |
| Submission History | ✅ | ✅ |
| Feasibility Assessment | ✅ | ✅ |
| Cost Calculator | ✅ | ✅ |
| Requirement Flow | ✅ | ✅ |
| Ops Map | ✅ | ✅ |
| Task POC Guide | ✅ | ✅ |
| External Tools | ✅ | ✅ |
| Analytics Dashboard | ❌ | ✅ |
| Rate Manager | ❌ | ✅ |
| User Management | ❌ | ✅ |

**Default Users:**

| Username | Role | Default Password |
|----------|------|-----------------|
| shanjai | Admin | Shanjai@42S |
| admin | Admin | Admin@42S2026 |
| srinivas | Viewer | Srinivas@42S |
| pgupta | Viewer | Pgupta@42S |
| josh | Viewer | Josh@42S |
| ankit | Viewer | Ankit@42S |
| arunashok | Viewer | Arunashok@42S |
| ravindran | Viewer | Ravindran@42S |

> ⚠️ **Change all default passwords before first use in production.**

---

## 9. Navigation & Pages

The sidebar is always visible when logged in. It is divided into three groups:

### Tools (All users)
| Icon | Page | What it does |
|------|------|-------------|
| Grid | Dashboard | Overview of all submissions + quick stats |
| Document | New Requirement Form | Create a new client crawl requirement |
| Clock | Submission History | Browse, filter, edit past submissions |
| Chart | Feasibility Assessment | Generate a feasibility .docx for the tech team |
| Calculator | Cost Calculator | Estimate monthly crawl costs per platform |

### Reference (All users)
| Icon | Page | What it does |
|------|------|-------------|
| Flow | Requirement Flow | Interactive 8-step crawl setup decision tree |
| Map | Ops Map | Day-to-day ops areas and responsibilities |
| Star | Task POC Guide | Who owns what (Dev/Platform/TPM/DS/QA) |
| Globe | External Tools | Links to external resources |

### Admin (Admin users only)
| Icon | Page | What it does |
|------|------|-------------|
| Bar chart | Analytics | Full usage analytics for all users |
| Settings | Rate Manager | Edit crawl cost rates per domain |
| Users | User Management | Add, modify, deactivate users |

Navigation works by setting `st.session_state["page"]` and triggering `st.rerun()`.

---

## 10. Page: Dashboard

The **home screen** after login. Gives a quick snapshot of the team's work.

### Stats Cards

Four colored stat cards at the top:

| Card | What it counts | Color |
|------|---------------|-------|
| Total Submissions | All submissions ever | Dark gray |
| In Review | Submissions with status "In Review" | Amber |
| Live | Submissions with status "Live" | Green |
| This Week | Submissions saved in the last 7 days | Blue |

Clicking **"View →"** on any card goes to Submission History with that status pre-filtered.

### Quick Actions

Four shortcut tiles:
- **New Requirement** → opens the form
- **Feasibility Check** → opens feasibility page
- **Cost Calculator** → opens cost calc
- **Submission History** → opens history

### Recent Submissions

A table of the **8 most recent submissions** showing client name, date, status badge, and an Edit button. A "View all N →" link at the bottom goes to the full history.

---

## 11. Page: New Requirement Form

The core of the application. A long multi-section form that captures everything needed to set up a client crawl.

### Layout

Two columns:
- **Left (wider):** The form itself
- **Right (narrower):** Live summary + progress indicator

### Draft Auto-Save

As soon as you type a client name, the form auto-saves to `.42s_draft_{username}.json`. If you navigate away and come back, an orange banner appears offering to restore your draft.

### Templates

An expander at the top lets you load a previously saved template. Templates are named snapshots of the form state, stored in `form_templates.json`. You can also save the current form as a new template before generating the PDF.

### Form Sections

#### 1. Client Information
- **Client Name** *(required)*
- **Priority Level** (High / Medium / Low)
- **Expected Completion Date** (defaults to today + 4 days)
- **Target Market / Geography** *(required)*

#### 2. Modules to Crawl *(required — pick at least one)*
- Products + Trends
- SOS (Search on Site)
- Reviews
- Price Violation
- Store ID Crawls
- Festive Sale Crawls

> The rest of the form dynamically shows only sections for the modules you selected.

#### 3. Products + Trends Module

Select domains (from predefined list or type custom ones). Then choose a **Crawl Type**:

**Category-based (Category_ES):** Crawls product data by navigating category pages.
- Products / Trends index frequency
- Number of RSS crawls
- Expected data push volume
- Category list status and links

**Input-based (URL/Input-driven):** Crawls using URLs fed by the client.
- Products crawl needed? (Yes/No)
- Input URL samples
- Client inputs status (provided or pending)
- Pincode/Zipcode based crawling?
- Crawl duration (start/end dates)
- Expected daily volume
- Screenshot required?

**Products Only:** Simpler variant of input-based for product data only.

#### 4. SOS (Search on Site) Module

Captures how products rank in on-site search.
- Number of keywords
- Keywords source (client-provided sheet link or sample for testing)
- Domains + per-domain config
- Zipcode requirement
- Crawl depth (pages per keyword, products per keyword)
- Crawl frequency

#### 5. Reviews Module

Captures product reviews.
- Domains + per-domain config
- Input source (from products index / from trends index / from review input URLs / category-based)
- Frequency + optional hourly timings

#### 6. Price Violation Module

Monitors unauthorized price changes.
- Domains + per-domain config
- Product URL list
- Zipcode requirement
- Violation condition/rule
- Sample inputs sheet link
- Screenshot required?

#### 7. Store ID Crawls

Captures store location data.
- Domains + per-domain config
- Specific store locations needed?
- Pincode list available?

#### 8. Festive Sale Crawls

Scheduled crawls during sales events.
- Crawl type (Products+Trends / SOS / Category URL based)
- Domain + URL list
- Schedule (frequency/day, start date, end date)

#### 9. Final Alignment
- **Client Core Objective** *(required)* — the key business goal
- **Expectations From Us** — what the client expects us to deliver

#### 10. Comments & Notes
- Free-text additional comments

### Right Panel: Live Summary

As you fill the form, the right panel updates live:

**Progress Bar:** Shows 5 checks:
1. Client Name entered
2. Target Market entered
3. Module(s) selected
4. At least one domain added
5. Client Objective filled

**Completion Percentage:** Colored bar (red → blue → green based on %).

**Summary Accordion:** Expandable sections showing all filled values, ready to review before generating the PDF.

**Risk Indicator** (Products + Trends only): Calculates crawl load risk from frequency + volume:
- **LOW** — manageable load
- **MODERATE** — needs attention
- **CRITICAL** — high infrastructure impact

### Validation

On clicking Generate PDF, the form validates:
- Target Market is filled
- At least one module selected
- Each module has required fields filled (domains, keyword counts, etc.)
- Client Core Objective is filled

Errors appear as a red list above the button.

### PDF Generation

On passing validation:
1. A PDF is built in memory using ReportLab
2. The submission is saved to `submissions/`
3. The draft is cleared
4. The PDF is downloaded to the browser via JavaScript Blob API
5. A "Generated!" celebration animation plays

PDF contains: header with logo, all form sections with alternating row styling, clickable URLs.

---

## 12. Page: Submission History

Browse and manage all saved requirement submissions.

### Filters

- **Search:** Type to filter by client name
- **Status filter:** All / Submitted / In Review / Live / Draft
- **User filter:** All / specific team member

Clicking a stat card on the Dashboard auto-populates the status filter.

### Table Columns

- Client name
- Modules (comma-separated list)
- Date saved
- Status (colored badge, editable inline)
- Actions

### Actions Per Row

| Button | What it does |
|--------|-------------|
| ✏️ Edit | Loads the submission back into the New Requirement Form for editing |
| 💰 Cost Calc | Jumps to Cost Calculator |
| 🔍 Feasibility | Jumps to Feasibility Assessment |
| 📝 Notes | Toggles an inline notes panel for that submission |
| 🗑️ Delete | Shows inline confirmation before deleting the JSON file |

### Status Tracking

The status dropdown per row saves directly to the submission JSON. A toast notification confirms the change. Status options:
- **Submitted** — just received
- **In Review** — being assessed internally
- **Live** — crawl is running
- **Draft** — incomplete / not yet submitted formally

### Notes

Clicking 📝 Notes expands an inline panel. Type a note and click 💬 Add Note to save it into the submission JSON with a timestamp and author.

---

## 13. Page: Feasibility Assessment

Generates a structured Word document (.docx) to share with the tech/ops team before project kickoff.

### Input Fields

- **Client Name** — required for the document
- **Requestor Name**
- **Number of Domains** (1–50)
- **Domain inputs** (dynamic — shown in a 3-column grid up to 6)
- **Crawl type & special requirements** (multiselect: Category Based, Product URL Input, SOS, Reviews, Festive, Banner, Others)
- **Zipcode handling** (Without / With / Both)
  - If "With" or "Both": City, State, Country
- **Additional notes**

### Right Panel

A "What's included" checklist shows what will appear in the generated document.

### Generate Button

Clicking **"Generate & Download Feasibility Document"** builds the .docx in memory using python-docx and downloads it to the browser. No server-side file is saved.

---

## 14. Page: Cost Calculator

Estimates the monthly/total crawl cost across multiple platforms.

### Step 1: Select Platforms

Three input modes:
1. **Select from list** — multiselect from all domains in `crawl_cost_rates.csv`
2. **Paste comma-separated** — type `amazon.in, flipkart.com, ...`
3. **Upload CSV** — upload a file with a `domain` column

Unknown domains (not in the rates CSV) get a warning but can still be included.

### Step 2: Configure Each Platform

For each selected domain, an expander shows:

**Zipcode Mode** (affects volume multiplier):
- Without Zipcode
- With Zipcode
- Both (calculates separate rows for each variant)

**Crawl Types** (multiselect — pick all that apply):

| Crawl Type | What it costs | Rate used |
|-----------|--------------|-----------|
| Category Based | Categories × SKUs/Category | cat_rate |
| SKU / Product URL Based | Number of SKUs | sku_rate |
| SOS (Share of Search) | Keywords × SKUs/Keyword | kw_rate |
| Reviews | Number of Products | sku_rate × 0.7 |
| Keyword Level | Keywords × SKUs/Keyword | kw_rate |
| Festive Sales Day | Categories × SKUs/Category | cat_rate × 1.2 |
| Banner Crawl | Banner URLs | $0.001/URL/crawl (flat) |

For each crawl type, inputs are:
- Volume numbers (categories/SKUs/keywords/URLs)
- Crawls per day (frequency)
- Duration in days

**Cost formula:**
```
effective_volume = volume × (2 if "Both" zipcode else 1)
cost_per_crawl   = effective_volume × rate
total_cost       = cost_per_crawl × crawls_per_day × duration_days
```

### Step 3: Results

**Grand Total strip:** Total USD, number of platforms, number of crawl configs, calculation date, rates last updated.

**Per-platform tables:** Each domain gets a table showing every crawl type with volumes, frequency, duration, zipcode variant, cost per crawl, and total cost.

**Cost color coding:**
- $0 → green
- < $1 → amber
- < $100 → orange
- ≥ $100 → red

### Scenario Comparison

1. Configure a setup → click **"Save as Scenario"** (give it a name)
2. Change the configuration → save another scenario
3. A comparison table appears side-by-side
4. Useful for "with zipcode vs without" or "daily vs hourly" comparisons

### Downloads

- **PDF** — professional cost estimate document with logo and tables
- **CSV** — raw data for spreadsheet analysis

---

## 15. Page: Requirement Flow

An **interactive D3.js mind map** showing the 8-step process for setting up a new crawl requirement from intake to delivery.

**Steps visualised:**
1. Finalize Domains (QCommerce, ECom, Fashion Retail)
2. Classify Seed URLs (Category / PDP / Listing / Banner / SOS / Reviews)
3. Index Decision (Zipcode, historical data, variants, domain numbering)
4. Feasibility Check (schema, special fields, blocking challenges)
5. Site Setup (domain reuse, naming, mapping JSON)
6. Dev Implementation (Products / Trends / SOS setup)
7. Post-Setup Checks (QA, field validation, indexing)
8. QA & Delivery (Dashboard QA, Kibana comparison, delivery)

**How to use:**
- Click any node to expand/collapse its children
- Scroll to zoom in/out
- Click and drag to pan

**Node colour coding:**
- Blue = Process step
- Orange = Decision point
- Green = Outcome
- Gray = Action item

Uses D3.js v7 bundled locally (`d3.v7.min.js`) — works offline.

---

## 16. Page: Ops Map

A D3.js mind map showing **7 operational areas** and their subtasks.

| Area | Colour | Subtasks |
|------|--------|---------|
| Kibana Monitoring | Blue | Client vs Site analysis, Proxy Status, Disk Time, Extraction Duration, Cost Analytics |
| Input Sheet Management | Teal | Data Request Format, Add/Update URLs, AppScript Automation |
| Cost Analysis | Amber | Clientwise (Monthly), Sitewise (Monthly), InfraCost Input |
| Crawl Health | Purple | Count Mismatch, Failure Logs, Misc & Dep Sites |
| Mapping & Tracking | Red | Client-Site Mapping, Domain Mapping JSON, 42S Schema Sheet |
| Maintenance | Cyan | Weekly Tasks, Monthly Tasks, On-Demand Tasks |
| Automation | Rose | Google App Scripts, Ruby Scripts |

Use this as a reference for "what falls under which area" in day-to-day operations.

---

## 17. Page: Task POC Guide

A D3.js responsibility matrix showing **who owns which task** across the team.

**Teams:**
- Shanjai / Srinivas (dark blue)
- Dev Team (purple)
- Platform Team (amber)
- TPM (red)
- DS / QA / Product (green)

**Task categories:**
- Site Setup (new site, reuse, naming, domain mapping)
- Schema & Fields (field addition, DRL changes, schema review)
- Crawl Issues (not running, count mismatch, proxy failures, extraction errors)
- Client Requirements (new intake, New Balance, RamyBrook, client escalation)
- Cost & Infra (monthly cost report, clientwise, sitewise, InfraCost)
- Maintenance Tasks (weekly, monthly, on-demand)
- Escalation Path (platform change, new site, client SLA)

Use this to quickly check "who do I go to for X."

---

## 18. Page: Analytics Dashboard (Admin)

Tracks all user activity across the application. Only visible to admin users.

### Time Period Selector

Choose: Last 7 days / Last 30 days / Last 90 days / All time.

### KPI Cards (4 + 4 grid)

Row 1: Sessions | Unique Users | Total Logins | Total Events
Row 2: Docs Generated | Avg Pages/Session | Peak Hour | Top Page

### Highlights Strip

5 quick-glance tiles: Most active user, most visited page, peak usage hour, avg pages per session, docs/PDFs generated.

### Charts

- **Activity Over Time** — line chart of events per day
- **Page Views by Section** — bar chart + table with % share
- **Hourly Activity Distribution** — bar chart of events by hour
- **Per-User Breakdown** — table: user / logins / page views / docs generated / last seen
- **Event Type Breakdown** — table: event type / count / % share
- **User Activity (Total Events)** — bar chart per user

### Recent Activity Log

Table of the last 100 events with timestamp, user, event type, and page.

### Exports

- **Export Activity Table (CSV)** — the filtered view
- **Export Full Raw Log (CSV)** — all raw JSONL events

---

## 19. Page: Rate Manager (Admin)

Manages the crawl cost rates used by the Cost Calculator. Only visible to admin users.

### Meta Strip

Shows current state: number of domains, last updated date, total rows.

### Rate Table

An editable grid with columns:

| Column | Type | Description |
|--------|------|-------------|
| domain | Text | e.g. `amazon.in` |
| display_name | Text | e.g. `Amazon India` |
| zipcode | Checkbox | True = this row is the zipcode variant |
| sku_rate | Number | Cost per SKU crawl (USD) |
| cat_rate | Number | Cost per category crawl (USD) |
| kw_rate | Number | Cost per keyword crawl (USD) |
| last_updated | Text | Date string e.g. `24 Mar 2026` |

**Important:** Each domain needs **two rows** — one with Zipcode unchecked (without) and one checked (with). The Cost Calculator uses the matching row based on the user's zipcode selection.

Rates are typically very small numbers (e.g. `0.000821` or scientific `8.21e-04`).

### Bulk Date Stamp

Use the date picker + "Apply to all sites" checkbox to stamp all rows with the same "last updated" date when saving.

### Saving

Click **"💾 Save Changes"**. Validates that no domain is empty, then writes to `crawl_cost_rates.csv`.

---

## 20. Page: User Management (Admin)

Manage team members. Only visible to admin users.

### Current Users Table

Shows all users with role badge (Admin/Viewer in colour) and status badge (Active/Deactivated). Your own row has a "you" tag.

### Tab: ➕ Add User

- Username (lowercase, unique)
- Display Name (shown in UI)
- Password
- Role (viewer or admin)

New user is saved to `users_db.json` (sidecar to `credentials.py`).

### Tab: 🔑 Reset Password

Select a user, enter new password + confirmation. Updates the hash in memory and saves to `users_db.json`.

### Tab: 🎭 Change Role

Select a user (cannot select yourself), choose new role. Guard: cannot demote the last active admin.

### Tab: 🚫 Deactivate / Activate

Select a user (cannot select yourself), toggle their active state. Guard: cannot deactivate the last active admin. Deactivated users cannot log in.

---

## 21. Data Storage & File System

### submissions/

Every generated PDF creates a corresponding JSON file:

```json
{
  "client_name": "Unilever India",
  "saved_at": "2026-03-25T10:30:00+00:00",
  "saved_by": "shanjai",
  "status": "Submitted",
  "notes": [
    { "text": "...", "by": "shanjai", "at": "2026-03-25T11:00:00+00:00" }
  ],
  "form_data": {
    "Client Information": { "Client Name": "...", ... },
    "Modules Selected": { "Selected Modules": [...] },
    "Products + Trends": { ... },
    ...
  },
  "session_state": { "form_client_name": "...", ... }
}
```

Filenames: `{sanitized_client_name}_{YYYYMMDD_HHMMSS}.json`

### .42s_analytics.jsonl

One JSON object per line, one line per event:
```json
{"ts":"2026-03-25T10:00:00+00:00","session_id":"uuid","username":"shanjai","event":"page_view","page":"main","details":{}}
```

### .42s_session.json

```json
{"token":"uuid","username":"shanjai","display_name":"Shanjai","expires":"2026-04-01T10:00:00+00:00"}
```

### users_db.json

```json
{
  "newuser": {
    "salt": "hex-string",
    "hash": "hex-string",
    "display_name": "New User",
    "role": "viewer",
    "active": true
  }
}
```

On startup, `credentials.py` loads this file and merges it into the in-memory `USERS` dict. Users added at runtime persist here; the base users in `credentials.py` are the fallback.

### form_templates.json

```json
{
  "Template Name": {
    "form_client_name": "...",
    "form_target_market": "...",
    ...all form widget keys...
  }
}
```

---

## 22. Analytics System

Every meaningful action is logged via `analytics.log_event()`.

### Events Logged

| Event | When |
|-------|------|
| `login` | Successful sign-in |
| `logout` | Sign-out button clicked |
| `page_view` | Every page navigation |
| `generate_req_pdf` | "Generate & Download PDF" clicked |
| `download_req_pdf` | PDF blob delivered |
| `generate_feas_doc` | Feasibility generate clicked |
| `download_feas_doc` | Feasibility doc downloaded |
| `download_cost_pdf` | Cost estimate PDF downloaded |
| `download_cost_csv` | Cost estimate CSV downloaded |

### Aggregations (get_summary)

`get_summary(days=30)` computes (cached 30 seconds):
- Total sessions (unique session IDs)
- Unique users
- Today's sessions and users
- Login count, total events, docs generated
- Average session depth (page views per session)
- Peak hour, most visited page
- Events per day (for line chart)
- Hourly distribution (for bar chart)
- Per-user breakdown
- Actions breakdown by event type
- Last 100 events for activity log

### Cache Invalidation

After every `log_event()` call:
```python
load_events.clear()
get_summary.clear()
```
This ensures the analytics dashboard reflects the latest activity within 30 seconds.

---

## 23. Cost Rate System

### CSV Schema

```
domain,display_name,zipcode,sku_rate,cat_rate,kw_rate,last_updated
amazon.in,Amazon India,False,0.000821,0.000822,0.0000033,24 Mar 2026
amazon.in,Amazon India,True,0.000821,0.000822,0.0000033,24 Mar 2026
```

### How Rates Are Used

```python
# Rate Manager writes → crawl_cost_rates.csv
# Cost Calculator reads → load via pandas read_csv

# Lookup per domain+zipcode:
matching_row = df[(df.domain == domain) & (df.zipcode == with_zipcode)]
sku_rate = matching_row["sku_rate"].values[0]
cat_rate = matching_row["cat_rate"].values[0]
kw_rate  = matching_row["kw_rate"].values[0]
```

### Rate Application Per Crawl Type

| Crawl Type | Formula |
|-----------|---------|
| Category Based | volume × cat_rate × crawls/day × days |
| SKU Based | volume × sku_rate × crawls/day × days |
| SOS | volume × kw_rate × crawls/day × days |
| Reviews | volume × (sku_rate × 0.7) × crawls/day × days |
| Keyword Level | volume × kw_rate × crawls/day × days |
| Festive Sales | volume × (cat_rate × 1.2) × crawls/day × days |
| Banner | volume × 0.001 × crawls/day × days |

---

## 24. PDF Generation

### Requirement Form PDF

**Library:** ReportLab Platypus
**Template:** SimpleDocTemplate with custom styles

**Structure:**
1. Header row: 42Signals logo (left) + "Client Requirement Form" title (right)
2. Client name + generation date
3. Each form section as a bordered table
4. Alternating row backgrounds (#f8fafc / #ffffff)
5. URLs in values auto-converted to clickable links

**Download mechanism:**
```python
buf = BytesIO()
doc.build(story)
pdf_bytes = buf.getvalue()
b64 = base64.b64encode(pdf_bytes).decode()

# JavaScript blob download (bypasses Streamlit's download_button limitations)
components.html(f"""<script>
  var b = atob("{b64}");
  var blob = new Blob([...], {{type:"application/pdf"}});
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "{filename}";
  a.click();
</script>""", height=0)
```

### Cost Estimate PDF

Similar mechanism but structured as a cost estimate document:
- Grand total summary at top
- Per-platform tables with cost breakdowns
- Rate source + date

---

## 25. Form Templates & Drafts

### Auto-Draft

Triggers when `client_name` is non-empty. Saves `st.session_state` widget values for all form keys (prefixed `form_`, `pt_`, `sos_`, `rev_`, `pv_`, `storeid_`, `festive_`, `final_`).

On next visit:
- Orange banner: "You have an unsaved draft for {client_name}"
- **Resume** button: restores all widget values into `st.session_state`
- **Discard** button: deletes the draft file

### Templates

A template is a named snapshot of the full form state. Useful for recurring client types (e.g. "Standard Amazon + Flipkart SOS Setup").

**Save:** Expander at bottom of form → enter name → "💾 Save Template"
**Load:** Expander at top of form → select template → "⬆️ Load Template"
**Delete:** Same expander → "🗑️ Delete Template"

Templates stored in `form_templates.json` as a dict `{name: session_state_dict}`.

---

## 26. UI Design System

### Typography

| Use case | Size | Weight | Colour |
|----------|------|--------|--------|
| Page titles | 1.65rem | 700 | #0f172a |
| Section headers | 0.875rem | 700 | #1f2937 |
| Card labels (uppercase) | 0.7rem | 700 | #94a3b8 |
| Body text | 0.875rem | 400 | #374151 |
| Secondary text | 0.85rem | 400 | #6b7280 |
| Captions | 0.75rem | 400 | #9ca3af |
| Font family | — | — | Inter, -apple-system, sans-serif |

### Colour Palette

**Neutrals (base):**
- `#0f172a` / `#111827` — primary text
- `#1f2937` / `#374151` — dark UI elements
- `#6b7280` — secondary text
- `#9ca3af` / `#94a3b8` — muted/labels
- `#e5e7eb` / `#f1f5f9` / `#f8fafc` — borders/backgrounds

**Status colours:**
- Success: `#16a34a` (green)
- Warning: `#f59e0b` (amber)
- Error: `#dc2626` (red)
- Info: `#3b82f6` (blue)

**Accent colours:**
- `#6366f1` (indigo) — login page gradient
- `#8b5cf6` (purple) — login shimmer
- `#f97316` (orange) — session expiry / draft banner

### Card Pattern

Most content cards follow:
```css
background: #ffffff;
border-radius: 10px–12px;
border: 1px solid #e5e7eb;
border-left: 4px solid {accent-colour};
box-shadow: 0 1px 4px rgba(0,0,0,0.05);
padding: 14px 16px;
font-family: 'Inter', sans-serif;
```

### Button Styles

**Primary buttons:**
```css
background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
color: #ffffff;
border-radius: 8px–11px;
font-weight: 700;
```

**Secondary buttons:** Streamlit defaults (white background, gray border).

### Alert/Notice Pattern

All alerts use a left-border accent with gradient background:
- Error: `#fef2f2 → #fee2e2`, left `#dc2626`
- Warning: `#fffbeb → #fef9ec`, left `#f59e0b`
- Success: `#f0fdf4 → #dcfce7`, left `#16a34a`
- Info (orange): `#fff7ed → #ffedd5`, left `#f97316`

### Helper Functions (UI)

| Function | Output |
|----------|--------|
| `page_title(title, subtitle)` | Bold title + gradient underline + gray subtitle |
| `section_header(icon, title)` | Icon + bold title on gradient bg with left border |
| `info_row(label, value)` | Uppercase label + value with bottom divider |
| `celebrate(message, sub)` | `st.balloons()` + animated success banner |

---

## 27. Key Helper Functions

### Security

```python
_h(value)                          # HTML-escape for unsafe_allow_html
_safe_filename(name, suffix)       # Sanitize download filenames
_safe_key(s)                       # Safe Streamlit widget key fragment
```

### Lockout

```python
_get_lockout(username)             # → (attempts, lockout_until_ts)
_set_lockout(username, attempts, lockout_until)
_clear_lockout(username)
```

### Session

```python
_save_session(username, display_name)   # → token
_load_session(token)                    # → (username, display_name) or (None, None)
_clear_session()
```

### Draft

```python
_draft_path(username)              # → Path to .42s_draft_username.json
_save_draft(username, form_data)
_load_draft(username)              # → dict or None
_clear_draft(username)
```

### Submissions

```python
save_submission(form_data, client_name, username)
load_submission(filename)
list_submissions()                 # Cached 60s → list of metadata dicts
_update_submission_status(filename, status)
```

### Form Rendering

```python
domain_selector(label, key_prefix)         # Multiselect + custom domain field
frequency_selector(label, key_prefix)      # Frequency dropdown (Daily/Weekly/Monthly/Hourly)
_pt_crawl_config(key_suffix)               # Products+Trends config block → dict
_sos_crawl_config(key_suffix)              # SOS config block → dict
_rev_crawl_config(key_suffix)              # Reviews config block → dict
_pv_crawl_config(key_suffix)               # Price Violation config block → dict
_storeid_crawl_config(key_suffix)          # Store ID config block → dict
_festive_schedule_config(key_suffix)       # Festive schedule block → dict
_apply_domain_config(base, mode_key, doms, fn)  # Apply per-domain or shared config
```

### Validation

```python
validate_required(client_name)             # Show warning + stop if empty
calculate_risk(freq_string, vol_string)    # → "LOW" | "MODERATE" | "CRITICAL"
_validate_form(form_data, modules)         # → list of error strings
```

---

## 28. Deployment Guide

### First-Time Setup on VPS

```bash
# 1. Clone to VPS
git clone https://github.com/shanjaipc/42S-Client-Requirement-Handling /home/shanjai/42S-Client-Requirement-Handling
cd /home/shanjai/42S-Client-Requirement-Handling

# 2. Install Python deps
pip3 install streamlit pandas reportlab python-docx

# 3. Create submissions directory
mkdir -p submissions

# 4. Start app
nohup streamlit run app.py --server.port 8501 > streamlit.log 2>&1 &
```

### Reverse Proxy (nginx example)

```nginx
server {
    listen 443 ssl;
    server_name project-planning.42signals.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

### Environment Notes

- Requires Python **3.9+** (3.10+ for `dict | None` syntax — now patched to use `Optional[dict]`)
- All file paths are relative to the working directory where `streamlit run` is executed
- The `submissions/` directory is created automatically on first save

### Adding New Users (CLI)

```bash
python3 credentials.py
# Follow prompts: username, password, display name
# Copy the output into the USERS dict in credentials.py
```

Or use the **User Management** page in the app (admin login required) — changes persist to `users_db.json` without editing Python files.

---

## 29. Adding & Managing Users

### Via the App (Recommended)

1. Log in as an admin
2. Go to **Admin → User Management**
3. Use the **➕ Add User** tab
4. Fill username, display name, password, role
5. Click "➕ Add User"

The new user can log in immediately. Their credentials are stored in `users_db.json`.

### Via CLI (For First-Time / Hardcoded Users)

```bash
cd /home/shanjai/42S-Client-Requirement-Handling
python3 credentials.py
```

Follow the prompts. Copy the output into `credentials.py` USERS dict. This is needed when you want users that persist even if `users_db.json` is deleted.

### Resetting a Password

1. **Via app:** Admin → User Management → 🔑 Reset Password tab
2. **Via CLI:** Run `python3 credentials.py`, generate new hash, update `credentials.py`

### Deactivating a User

Admin → User Management → 🚫 Deactivate tab. The user cannot log in but their data is preserved.

---

## 30. Troubleshooting

### `ImportError: cannot import name 'add_user' from 'credentials'`

The VPS has an old `credentials.py` without the new functions.

```bash
cd /home/shanjai/42S-Client-Requirement-Handling
git pull origin upd
kill $(pgrep -f "streamlit run")
nohup streamlit run app.py --server.port 8501 > streamlit.log 2>&1 &
```

### `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`

Python 3.9 doesn't support `dict | None` syntax. Fixed in current code (`Optional[dict]` used instead). Pull latest and restart.

### App not loading / blank screen

```bash
tail -50 /home/shanjai/42S-Client-Requirement-Handling/streamlit.log
```

### PDF not downloading

Browser may be blocking popups. Check browser popup blocker settings. The download uses JavaScript Blob API — requires JS enabled.

### "crawl_cost_rates.csv not found"

```bash
cd /home/shanjai/42S-Client-Requirement-Handling
ls crawl_cost_rates.csv   # check it exists
git pull origin upd       # or pull to restore
```

### User locked out (forgot password)

```bash
# Edit .42s_lockout.json to clear the lockout
echo '{}' > .42s_lockout.json
```

Then reset the password via CLI (`python3 credentials.py`) or via User Management if another admin can log in.

### Submissions directory missing

```bash
mkdir -p /home/shanjai/42S-Client-Requirement-Handling/submissions
```

### Session issues (logged out repeatedly)

Check that `.42s_session.json` is writable:
```bash
ls -la .42s_session.json
chmod 644 .42s_session.json
```

---

*Documentation generated: 25 March 2026*
*App version: current (branch: upd)*
*42Signals Internal — Not for external distribution*
