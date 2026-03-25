# 42Signals — Requirement Handling Portal
## User Guide for the Team

---

> **What is this app?**
> It's the internal portal where we capture everything about a new client's crawl setup — what they want crawled, on which websites, how often, and how much it will cost. Think of it as a structured intake form that automatically generates PDFs, tracks status, and keeps everyone on the same page.

---

## Getting Started

### How do I open the app?

Go to: **https://project-planning.42signals.com/**

### How do I log in?

Enter your **username** and **password** and click **Sign In**.

If you've logged in before on this device, the app will remember you and sign you in automatically (for up to 7 days).

### What if I enter the wrong password too many times?

After 5 wrong attempts, your account is locked for **5 minutes**. A countdown timer will appear on screen. Once it reaches zero, you can try again.

### How do I log out?

Click the **Sign Out** button at the bottom of the left sidebar.

---

## The Sidebar (Left Menu)

The left sidebar has all the pages you can visit. They are grouped into three sections:

### Tools
These are the pages you'll use day-to-day:

| Page | What it's for |
|------|--------------|
| **Dashboard** | Your home screen — see recent submissions and quick stats |
| **New Requirement Form** | Fill in a new client's crawl requirements and generate a PDF |
| **Submission History** | See all past submissions, update their status, add notes |
| **Feasibility Assessment** | Generate a quick document to share with the tech team |
| **Cost Calculator** | Estimate how much a crawl setup will cost |

### Reference
Pages you visit when you need to look something up:

| Page | What it's for |
|------|--------------|
| **Requirement Flow** | Step-by-step flowchart of the crawl setup process |
| **Ops Map** | What falls under which operational area |
| **Task POC Guide** | Who is responsible for what task |
| **External Tools** | Links to tools we use |

### Admin *(only visible to admins)*
| Page | What it's for |
|------|--------------|
| **Analytics** | See who is using the app and what they're doing |
| **Rate Manager** | Update crawl cost rates per website |
| **User Management** | Add new team members, reset passwords, deactivate users |

---

## Dashboard

This is the **first screen** you see after logging in. It gives you a quick overview:

**Four stat boxes at the top:**
- **Total Submissions** — how many requirement forms have been submitted ever
- **In Review** — how many are currently being reviewed internally
- **Live** — how many clients are already live/running
- **This Week** — how many new submissions came in this week

Click **"View →"** on any of these boxes to jump straight to that filtered list in Submission History.

**Quick action buttons** in the middle let you jump to common tasks with one click.

**Recent submissions** at the bottom shows the last 8 submissions with a quick Edit button next to each.

---

## New Requirement Form

This is where you capture everything about a new client's requirements. Once you fill it in and click Generate, it creates a PDF that can be shared with the team.

### Step 1 — Fill in Client Information

- **Client Name** *(required)* — the company name
- **Priority** — High, Medium, or Low urgency
- **Expected Completion Date** — automatically set to 4 days from today, but you can change it
- **Target Market / Geography** *(required)* — where the client operates (e.g. "India", "UK", "US")

### Step 2 — Select Modules

Tick all the types of crawls this client needs:

| Module | What it means |
|--------|--------------|
| **Products + Trends** | Crawl product listings, prices, availability |
| **SOS (Search on Site)** | Track how products rank in on-site search |
| **Reviews** | Collect product reviews |
| **Price Violation** | Alert when a seller sells below allowed price |
| **Store ID Crawls** | Collect store location data |
| **Festive Sale Crawls** | One-time crawls during sales events |

Only the sections for the modules you select will appear below.

### Step 3 — Fill in the details for each module

Each module asks for specifics. Common things you'll be asked:

- **Which websites (domains)?** — pick from the list or type a custom one
- **How often to crawl?** — Daily, Weekly, Monthly, or Hourly
- **How many products/keywords/categories?** — the volume
- **Do they need zipcode-based data?** — Yes or No
- **Has the client sent their list of URLs/keywords?** — Yes (with a link) or Not Yet

Don't worry if you don't have every detail — fill in what you know and the summary panel on the right shows your progress.

### Step 4 — Final Alignment

- **Client Core Objective** *(required)* — in a sentence or two, what is the client actually trying to achieve? (e.g. "Track competitor pricing on Amazon and Flipkart daily")
- **Expectations From Us** — anything specific they've asked for

### Step 5 — Generate the PDF

Click **"⬇️ Generate & Download PDF"**. The PDF will download automatically to your computer.

The form is also saved in the app so you can find it in Submission History later.

---

## Helpful Features in the Form

### Your progress is always visible

The panel on the right shows a **checklist** of the 5 key things needed:
- Client name ✓
- Target market ✓
- Module selected ✓
- Domain added ✓
- Client objective ✓

A progress bar fills up as you complete them. The bar turns green when all 5 are done.

### Your work is auto-saved

As soon as you type a client name, the app silently saves a draft. If you accidentally close the tab or navigate away, the next time you visit the form you'll see an orange banner:

> **"You have an unsaved draft for [Client Name] — Resume or Discard?"**

Click **Resume** to pick up where you left off.

### Templates

If you find yourself filling in very similar requirements for multiple clients, you can **save a template**:
1. Fill the form with the common settings
2. Click the "Save as Template" expander near the bottom
3. Give it a name (e.g. "Standard Amazon + Flipkart Setup")
4. Click Save

Next time, load that template from the expander at the top of the form — it pre-fills everything for you. You just change the client name and whatever's different.

### Editing a past submission

In **Submission History**, click ✏️ **Edit** next to any submission. The form will open with all the values pre-filled from that submission. Make your changes and generate a new PDF.

---

## Submission History

This is your list of all submissions ever saved.

### Filtering

Three filter options at the top:
- **Search** — type part of a client name to narrow the list
- **Status** — filter by Submitted / In Review / Live / Draft
- **By User** — see only submissions made by a specific team member

### Statuses

| Status | Meaning |
|--------|---------|
| **Submitted** | Form filled and PDF generated, awaiting review |
| **In Review** | Being assessed internally by the team |
| **Live** | Crawl is running for this client |
| **Draft** | Incomplete — not formally submitted yet |

You can change the status directly from the list. The change saves immediately and shows a brief confirmation message.

### Actions

Each row in the list has these buttons:

| Button | What it does |
|--------|-------------|
| ✏️ Edit | Open the form pre-filled with this submission's data |
| 💰 Cost Calc | Jump to Cost Calculator |
| 🔍 Feasibility | Jump to Feasibility Assessment |
| 📝 Notes | Add or view internal notes for this submission |
| 🗑️ Delete | Permanently delete this submission (asks for confirmation first) |

### Adding Notes

Click 📝 **Notes** to expand a notes panel for that submission. Type a note and click **💬 Add Note**. Notes are timestamped and show who added them. Good for tracking things like "Client confirmed category list on 20 March" or "Waiting on pincode list from client."

---

## Feasibility Assessment

Use this when you need to send the tech team a structured brief before they start setting up the crawl.

Fill in:
- Client name and your name
- The domains (websites) involved
- What type of crawl is needed
- Whether zipcode-based data is required
- Any extra notes

Click **"📄 Generate & Download Feasibility Document"** — it creates a Word document (.docx) that you can email directly to the tech team.

The right panel shows a checklist of what will be included in the document.

---

## Cost Calculator

Use this to estimate how much a client's crawl setup will cost before committing.

### Step 1 — Pick the platforms (websites)

Choose how to add platforms:
- **Select from list** — pick from the dropdown (all known platforms)
- **Paste names** — type `amazon.in, flipkart.com, swiggy.com` (comma-separated)
- **Upload a CSV** — if you have a spreadsheet

### Step 2 — Configure each platform

For each platform, you set:
- **Zipcode mode** — Without zipcode / With zipcode / Both
- **Crawl types** — what kind of data (Products, SOS, Reviews, etc.)
- For each crawl type:
  - How many products/keywords/categories
  - How many times per day
  - How many days

### Step 3 — Get the estimate

Click **"📊 Generate Estimate ↓"**. The results show:
- A grand total in USD
- A breakdown per platform and per crawl type
- Cost per crawl, total cost per config

Costs are colour coded:
- 🟢 **Green** = $0 (free tier)
- 🟡 **Amber** = less than $1
- 🟠 **Orange** = less than $100
- 🔴 **Red** = $100 or more

### Comparing scenarios

Want to compare "with zipcode vs without zipcode" or "daily vs weekly"?

1. Set up the first scenario → click **"💾 Save as Scenario"** (give it a name like "Without Zipcode")
2. Change the settings → click **"💾 Save as Scenario"** again (name it "With Zipcode")
3. A side-by-side comparison table appears automatically

### Downloading

- **PDF** — professional cost estimate document to share with clients or management
- **CSV** — spreadsheet you can open in Excel or Google Sheets

---

## Requirement Flow

A visual flowchart of the **8 steps** involved in setting up any crawl requirement — from first receiving the requirement to final delivery.

**How to use it:**
- Click on any box to expand or collapse its details
- Scroll up/down to zoom in or out
- Click and drag to move around the diagram

Use this as a reference when you're not sure what the next step is in the process.

---

## Ops Map

A visual overview of the **7 operational areas** the team works across — Kibana monitoring, input sheet management, cost analysis, crawl health, mapping & tracking, maintenance, and automation.

Click on any node to see the sub-tasks under it. Use this as a reference for "what kind of task is this and where does it belong?"

---

## Task POC Guide

A visual guide showing **who is responsible for what**. Colour-coded by team:
- Sales/PM team
- Dev Team
- Platform Team
- TPM
- DS / QA / Product

Use this when you're not sure who to go to for a specific task (e.g. "who do I ask about proxy failures?" or "who handles new site setup?").

---

## Admin Features

*These pages are only visible if you have an admin account.*

### Analytics

Shows a full picture of how the team is using the app:
- How many logins, page views, and documents generated
- Which pages are visited most
- When is the busiest time of day
- What each team member has been doing

You can export the data as a CSV for further analysis.

### Rate Manager

This is where you update the crawl cost rates for each platform. When a platform's pricing changes, an admin updates it here and it immediately reflects in the Cost Calculator.

Each platform has two rows — one for crawls **without zipcode** and one **with zipcode**, since the cost can differ.

To update a date across all platforms at once:
1. Pick the date using the date picker
2. Tick "Apply to all sites"
3. Click Save

### User Management

Add new team members, reset forgotten passwords, change someone's role, or deactivate an account when someone leaves.

**Adding a new user:**
1. Go to Admin → User Management
2. Click the ➕ **Add User** tab
3. Fill in username (lowercase, no spaces), display name, password, and role
4. Click Add User — they can log in immediately

**Resetting a password:**
1. Click the 🔑 **Reset Password** tab
2. Select the user from the dropdown
3. Enter and confirm the new password
4. Click Reset Password

**Deactivating a user** (when someone leaves the team):
1. Click the 🚫 **Deactivate / Activate** tab
2. Select the user
3. Click Deactivate

They will no longer be able to log in, but all their past submissions are preserved.

---

## Common Questions

**Q: I generated the PDF but nothing downloaded.**
The download uses your browser. Check if your browser blocked a popup — look for a notification in the address bar and allow it.

**Q: I accidentally navigated away from the form — did I lose my work?**
No. The app auto-saves your draft as you type. When you go back to the form, click **Resume** on the orange banner.

**Q: Can two people work on the same client submission at the same time?**
Not recommended. The last person to save will overwrite the other. Coordinate with your team before editing a submission.

**Q: The cost calculator shows $0 for a platform — is that right?**
It means the cost rate for that platform hasn't been set yet in the Rate Manager. Ask an admin to add the correct rates.

**Q: I can't see the Analytics / Rate Manager / User Management pages.**
These are admin-only pages. Contact Shanjai or another admin if you need access.

**Q: How do I change my own password?**
Ask an admin to reset it for you via the User Management page.

**Q: My account is locked — what do I do?**
Wait 5 minutes for the lockout to expire. The login screen shows a countdown. If you've forgotten your password, ask an admin to reset it.

---

*For technical issues, contact Shanjai.*
*Last updated: March 2026*
