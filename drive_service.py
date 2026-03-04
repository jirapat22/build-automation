"""
drive_service.py - All Google Drive API v3 logic.

Handles OAuth2 authentication, folder creation, and file copying.
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"


class DriveService:
    def __init__(self, config: dict):
        self.root_folder_id = config["GDRIVE_ROOT_FOLDER_ID"]
        self.sheets_template_id = config["SHEETS_TEMPLATE_FILE_ID"]
        self.docs_template_id = config["DOCS_TEMPLATE_FILE_ID"]
        self._service = self._authenticate()

    # ------------------------------------------------------------------ #
    # Authentication                                                       #
    # ------------------------------------------------------------------ #

    def _authenticate(self):
        """Run OAuth2 flow (opens browser on first run, then uses token.json)."""
        creds = None

        if os.path.exists(TOKEN_PATH):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            except Exception:
                creds = None  # corrupted token — re-auth

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None  # refresh failed — re-auth

            if not creds:
                if not os.path.exists(CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f"'{CREDENTIALS_PATH}' not found.\n"
                        "Download it from the Google Cloud Console and place it in "
                        "the project root. See README.md for instructions."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(TOKEN_PATH, "w") as fh:
                fh.write(creds.to_json())

        return build("drive", "v3", credentials=creds)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def setup_serial_number(
        self, serial_number: str, work_order: str, product_name: str
    ) -> str:
        """
        Create the full Drive folder structure and copy both templates.

        Structure created inside the root folder:
          {serial_number}/
            {work_order}/
              {serial_number}_{work_order}_{product_name}  (Sheet copy)
              {serial_number}_{work_order}_{product_name}  (Doc copy)

        Returns the shareable URL of the work order subfolder.
        """
        # 1. Serial Number folder (inside root)
        sn_folder_id = self._create_folder(serial_number, self.root_folder_id)

        # 2. Work Order subfolder
        wo_folder_id = self._create_folder(work_order, sn_folder_id)

        # 3. Copy templates
        file_name = f"{serial_number}_{work_order}_{product_name}"
        self._copy_file(self.sheets_template_id, file_name, wo_folder_id)
        self._copy_file(self.docs_template_id, file_name, wo_folder_id)

        return self._folder_url(wo_folder_id)

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _create_folder(self, name: str, parent_id: str) -> str:
        """Create a folder and return its ID."""
        try:
            metadata = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            folder = (
                self._service.files()
                .create(
                    body=metadata,
                    fields="id",
                    supportsAllDrives=True,
                )
                .execute()
            )
            return folder["id"]
        except HttpError as exc:
            raise RuntimeError(
                f"Drive: failed to create folder '{name}' "
                f"(HTTP {exc.status_code}): {exc.reason}"
            ) from exc

    def _copy_file(self, file_id: str, new_name: str, parent_id: str) -> tuple[str, str]:
        """
        Copy a template file to parent_id with new_name.
        Returns (new_file_id, webViewLink).
        """
        try:
            metadata = {"name": new_name, "parents": [parent_id]}
            copied = (
                self._service.files()
                .copy(
                    fileId=file_id,
                    body=metadata,
                    fields="id,webViewLink",
                    supportsAllDrives=True,
                )
                .execute()
            )
            return copied["id"], copied.get("webViewLink", "")
        except HttpError as exc:
            raise RuntimeError(
                f"Drive: failed to copy file '{file_id}' as '{new_name}' "
                f"(HTTP {exc.status_code}): {exc.reason}"
            ) from exc

    @staticmethod
    def _folder_url(folder_id: str) -> str:
        return f"https://drive.google.com/drive/folders/{folder_id}"
