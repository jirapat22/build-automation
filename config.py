"""
config.py - Load and validate environment variables from .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "JIRA_BASE_URL",
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
    "JIRA_PROJECT_KEY",
    "GDRIVE_ROOT_FOLDER_ID",
    "SHEETS_TEMPLATE_FILE_ID",
    "DOCS_TEMPLATE_FILE_ID",
]


def load_config() -> dict:
    """Load and validate all required environment variables.

    Returns a config dict. Raises ValueError listing any missing vars.
    """
    config = {}
    missing = []

    for var in REQUIRED_VARS:
        value = os.getenv(var, "").strip()
        if not value:
            missing.append(var)
        else:
            config[var] = value

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Copy .env.example to .env and fill in all values."
        )

    # Optional vars with defaults
    config["JIRA_SUBTASK_TYPE"] = os.getenv("JIRA_SUBTASK_TYPE", "Subtask").strip()

    # Normalise base URL
    config["JIRA_BASE_URL"] = config["JIRA_BASE_URL"].rstrip("/")

    return config
