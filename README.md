# Hardware Build Automation

A Python CLI tool (with an optional local web form) that automates:

1. Creating a **JIRA Task** (Work Order) with one **Sub-task per Serial Number**
2. Creating a **Google Drive folder structure** for each Serial Number and copying template files
3. Posting the Drive folder link back into each JIRA Sub-task

---

## Project Structure

```
build-automation/
├── main.py              # Entry point — CLI prompts + Flask web UI
├── jira_service.py      # JIRA Cloud REST API v3 logic
├── drive_service.py     # Google Drive API v3 logic
├── config.py            # Loads and validates .env variables
├── templates/
│   ├── form.html        # Web form (Bootstrap 5)
│   └── results.html     # Results page
├── requirements.txt
├── .env.example         # Copy this to .env and fill in your values
└── README.md
```

---

## Setup Guide

### 1. Python environment

Requires **Python 3.10+**.

```bash
cd build-automation
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

### 2. Google Cloud project & Drive API

#### a. Create a project and enable the Drive API

1. Go to <https://console.cloud.google.com/> and sign in.
2. Click **Select a project → New Project**, give it a name, click **Create**.
3. In the left menu go to **APIs & Services → Library**.
4. Search for **Google Drive API**, click it, then click **Enable**.

#### b. Create OAuth 2.0 credentials

1. Go to **APIs & Services → Credentials**.
2. Click **+ Create Credentials → OAuth client ID**.
3. If prompted, configure the OAuth consent screen first:
   - User type: **External** (or Internal if using Google Workspace)
   - Fill in App name, support email, developer email → Save.
   - Under **Scopes**, add `.../auth/drive` (or proceed without extra scopes for now; the app requests it at runtime).
   - Add your own Google account as a **Test user**.
4. Back on Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: anything (e.g. "Build Automation")
   - Click **Create**.
5. Click **Download JSON**, rename the file to **`credentials.json`**, and place it in the project root next to `main.py`.

#### c. First-run OAuth consent (generating token.json)

On the very first run, the tool will open your browser and ask you to sign in and grant access.
After you accept, a `token.json` file is written to the project root — **keep it safe and do not commit it**.

Subsequent runs use `token.json` automatically (refreshing it when needed).

---

### 3. Find Google Drive folder and file IDs from URLs

| Resource | Example URL | ID location |
|---|---|---|
| Folder | `drive.google.com/drive/folders/`**`1aBcD…xyz`** | After `/folders/` |
| Google Sheet | `docs.google.com/spreadsheets/d/`**`1aBcD…xyz`**`/edit` | After `/d/` |
| Google Doc | `docs.google.com/document/d/`**`1aBcD…xyz`**`/edit` | After `/d/` |

---

### 4. JIRA API token

1. Go to <https://id.atlassian.net/manage-profile/security/api-tokens>.
2. Click **Create API token**, give it a label, copy the token.
3. Store it in `.env` as `JIRA_API_TOKEN`.

> **Note:** The API token is used together with your JIRA login email for HTTP Basic Auth (`email:token`).

---

### 5. Find your JIRA project key

The project key is the prefix before the issue number.
Example: in issue **`HW-42`**, the project key is **`HW`**.

You can also find it in **Project Settings → Details → Key**.

---

### 6. .env file

Copy `.env.example` to `.env` and fill in every value:

```bash
cp .env.example .env   # macOS/Linux
copy .env.example .env # Windows
```

```ini
# .env

# JIRA
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=HW
JIRA_SUBTASK_TYPE=Subtask        # or "Sub-task" — check your project

# Google Drive
GDRIVE_ROOT_FOLDER_ID=1aBcDeFgHiJkLmNoPqRsTuVwXyZ
SHEETS_TEMPLATE_FILE_ID=1aBcDeFgHiJkLmNoPqRsTuVwXyZ
DOCS_TEMPLATE_FILE_ID=1aBcDeFgHiJkLmNoPqRsTuVwXyZ
```

> **Important:** Never commit `.env`, `credentials.json`, or `token.json` to version control.
> Add them to `.gitignore`.

---

### 7. Running the tool

#### CLI mode (default)

```bash
python main.py
```

You will be prompted step-by-step for all inputs. Serial numbers can be entered one-by-one or pasted as a comma/newline-separated list.

**Example session:**

```
=== Hardware Build Automation ===

Product Name [e.g. POWER-1501-2-FA-PXIE]: POWER-1501-2-FA-PXIE
Work Order Number (8 digits): 12345678
Customer Name: Acme Corp
Number of Units: 4

How would you like to enter Serial Numbers?
  1) One by one
  2) Paste a comma- or newline-separated list
Choice [1 or 2]: 2

Paste your serial numbers, then press Enter twice:
QP-260906, QP-260907, QP-260908, QP-260909

Running…
  Created parent task: HW-55 (https://…)
  [QP-260906] Creating JIRA sub-task…
  …

============================================================
  ✅ Work Order:  12345678
  📦 Product:     POWER-1501-2-FA-PXIE
  👤 Customer:    Acme Corp
  🎫 JIRA Task:   HW-55  https://your-domain.atlassian.net/browse/HW-55

  Serial Number   Sub-task   Drive Folder
  ─────────────────────────────────────────────────────────
  QP-260906       HW-56      https://drive.google.com/drive/folders/…  ✅
  QP-260907       HW-57      https://drive.google.com/drive/folders/…  ✅
  QP-260908       HW-58      https://drive.google.com/drive/folders/…  ✅
  QP-260909       HW-59      https://drive.google.com/drive/folders/…  ✅
============================================================
```

#### Web form mode

```bash
python main.py --ui
```

Opens a local web server at **http://localhost:5000**.
Fill in the form and click **Run Automation** — a results page shows all links.

> On first run, Google OAuth will open a browser tab before the Flask server starts. Complete the sign-in, then browse to http://localhost:5000.

---

## Notes & Troubleshooting

| Issue | Resolution |
|---|---|
| `credentials.json not found` | Download from Google Cloud Console → Credentials and place in project root |
| `Missing required environment variables` | Copy `.env.example` to `.env` and fill in all values |
| JIRA returns 404 on sub-task creation | Check `JIRA_SUBTASK_TYPE` matches the exact name in your project (e.g. `Subtask` vs `Sub-task`) |
| Drive permission error on copy | Ensure your Google account has **Viewer** (or higher) access to the template files |
| OAuth opens browser repeatedly | `token.json` may be corrupted — delete it and re-authenticate |
| Sub-task count warning | The tool warns if Serial Number count ≠ Number of Units but still proceeds |

---

## Security

- Do **not** commit `.env`, `credentials.json`, or `token.json`.
- Recommended `.gitignore` additions:

```
.env
credentials.json
token.json
.venv/
__pycache__/
*.pyc
```
