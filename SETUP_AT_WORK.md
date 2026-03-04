# Setting Up at Work

Follow these steps on your **work computer** to get the tool running.

---

## Step 1 — Check if Python is installed

Open **Command Prompt** (press `Win + R`, type `cmd`, hit Enter) and run:

```
python --version
```

- If you see `Python 3.10` or higher → skip to Step 2
- If you get an error or a lower version → go to **python.org/downloads**, download
  the Windows installer, run it, and **tick "Add Python to PATH"** during install

---

## Step 2 — Check if Git is installed

In the same Command Prompt run:

```
git --version
```

- If you see a version number → skip to Step 3
- If you get an error → go to **git-scm.com/download/win**, download and install it
  (all default options are fine)

---

## Step 3 — Clone the repo

Pick a folder where you want the project to live (e.g. your Desktop), then run:

```
cd %USERPROFILE%\Desktop
git clone https://github.com/jirapat22/build-automation.git
cd build-automation
```

This downloads all the code into a `build-automation` folder.

---

## Step 4 — Create a Python virtual environment and install dependencies

Still inside the `build-automation` folder, run these one at a time:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

You should see packages downloading and installing. This only needs to be done once.

---

## Step 5 — Create your .env file

The `.env` file holds all your secret credentials. It is **not** included in the repo — you must create it manually.

```
copy .env.example .env
```

Then open `.env` with Notepad:

```
notepad .env
```

Fill in every value. Here is what each one means:

```
JIRA_BASE_URL          = https://your-company.atlassian.net
JIRA_EMAIL             = the email you use to log in to JIRA
JIRA_API_TOKEN         = your JIRA API token (see below how to get it)
JIRA_PROJECT_KEY       = the short key for your project, e.g. HW
JIRA_SUBTASK_TYPE      = Subtask   (or "Sub-task" — check your JIRA project)

GDRIVE_ROOT_FOLDER_ID      = ID from the root Drive folder URL
SHEETS_TEMPLATE_FILE_ID    = ID from the Sheets template file URL
DOCS_TEMPLATE_FILE_ID      = ID from the Docs template file URL
```

### How to get your JIRA API token

1. Go to: https://id.atlassian.net/manage-profile/security/api-tokens
2. Click **Create API token**
3. Give it a name (e.g. "Build Automation"), click **Create**
4. Copy the token and paste it into `.env` as `JIRA_API_TOKEN`

### How to find Drive/file IDs from URLs

| What you need | Where to find the ID in the URL |
|---|---|
| Root Drive folder | `drive.google.com/drive/folders/` **`THIS_PART`** |
| Sheets template | `docs.google.com/spreadsheets/d/` **`THIS_PART`** `/edit` |
| Docs template | `docs.google.com/document/d/` **`THIS_PART`** `/edit` |

---

## Step 6 — Add your Google credentials file

You need a file called `credentials.json` in the project folder.

To get it:

1. Go to https://console.cloud.google.com/
2. Select your project → **APIs & Services** → **Credentials**
3. Find the OAuth 2.0 Client ID you created → click the download icon
4. Save the file as `credentials.json` and place it inside the `build-automation` folder

---

## Step 7 — Run the tool

Make sure you are in the `build-automation` folder with the venv active:

```
.venv\Scripts\activate
```

**CLI mode** (step-by-step prompts in the terminal):

```
python main.py
```

**Web form mode** (form in your browser):

```
python main.py --ui
```

Then open your browser and go to: **http://localhost:5000**

> The first time you run it, a browser tab will open asking you to sign in to Google
> and grant access. After you approve, it saves a `token.json` file and won't ask again.

---

## Step 8 — Activate the venv next time you open a new terminal

Every time you open a new Command Prompt to use the tool, run this first:

```
cd %USERPROFILE%\Desktop\build-automation
.venv\Scripts\activate
```

Then run `python main.py` as normal.

---

## Getting updates (if changes were made at home)

If the code was updated and pushed from another machine, pull the latest version:

```
git pull
```

If new packages were added, also run:

```
pip install -r requirements.txt
```

---

## Quick reference — files you need to add manually

These are secret/local files not included in the repo. You need to create them yourself:

| File | What it is | How to get it |
|---|---|---|
| `.env` | Your credentials and IDs | Copy `.env.example`, fill it in |
| `credentials.json` | Google OAuth credentials | Download from Google Cloud Console |
| `token.json` | Google auth token | Created automatically on first run |
