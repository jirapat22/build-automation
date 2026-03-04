"""
jira_service.py - All JIRA Cloud REST API v3 logic.

Handles creating parent tasks, sub-tasks, and updating descriptions
using Atlassian Document Format (ADF).
"""

import json
import requests
from requests.auth import HTTPBasicAuth


class JiraService:
    def __init__(self, config: dict):
        self.base_url = config["JIRA_BASE_URL"]
        self.project_key = config["JIRA_PROJECT_KEY"]
        self.subtask_type = config["JIRA_SUBTASK_TYPE"]
        self._auth = HTTPBasicAuth(config["JIRA_EMAIL"], config["JIRA_API_TOKEN"])
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def create_parent_task(
        self,
        work_order: str,
        product_name: str,
        customer: str,
        num_units: int,
        serial_numbers: list[str],
    ) -> dict:
        """Create the parent Work Order Task. Returns {id, key, url}."""
        sn_list = ", ".join(serial_numbers)
        description = self._build_adf(
            [
                ("Work Order", work_order),
                ("Product Name", product_name),
                ("Customer", customer),
                ("Total Units", str(num_units)),
                ("Serial Numbers", sn_list),
            ]
        )
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": f"{work_order} - {product_name} - {customer}",
                "issuetype": {"name": "Task"},
                "description": description,
            }
        }
        return self._post_issue(payload, context="parent task")

    def create_subtask(
        self,
        parent_id: str,
        serial_number: str,
        work_order: str,
        product_name: str,
        customer: str,
    ) -> dict:
        """Create a sub-task under the parent. Returns {id, key, url}."""
        description = self._build_adf(
            [
                ("Serial Number", serial_number),
                ("Work Order", work_order),
                ("Product Name", product_name),
                ("Customer", customer),
                ("Drive Folder", "Pending…"),
            ]
        )
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "parent": {"id": parent_id},
                "summary": f"{serial_number} - {product_name}",
                "issuetype": {"name": self.subtask_type},
                "description": description,
            }
        }
        return self._post_issue(payload, context=f"sub-task ({serial_number})")

    def update_subtask_with_drive_link(
        self,
        issue_id: str,
        serial_number: str,
        work_order: str,
        product_name: str,
        customer: str,
        drive_link: str,
    ) -> None:
        """Patch a sub-task's description to include the Drive folder link."""
        description = self._build_adf(
            [
                ("Serial Number", serial_number),
                ("Work Order", work_order),
                ("Product Name", product_name),
                ("Customer", customer),
            ],
            drive_link=drive_link,
        )
        payload = {"fields": {"description": description}}
        self._put_issue(issue_id, payload, context=f"sub-task {issue_id}")

    def update_parent_description(
        self,
        issue_id: str,
        work_order: str,
        product_name: str,
        customer: str,
        num_units: int,
        serial_numbers: list[str],
        drive_links: dict,          # {serial_number: drive_link | None}
    ) -> None:
        """Update the parent task description with all SNs and Drive links."""
        sn_list = ", ".join(serial_numbers)
        description = self._build_adf(
            [
                ("Work Order", work_order),
                ("Product Name", product_name),
                ("Customer", customer),
                ("Total Units", str(num_units)),
                ("Serial Numbers", sn_list),
            ],
            drive_links=drive_links,
        )
        payload = {"fields": {"description": description}}
        self._put_issue(issue_id, payload, context=f"parent task {issue_id}")

    # ------------------------------------------------------------------ #
    # ADF builder                                                          #
    # ------------------------------------------------------------------ #

    def _build_adf(
        self,
        fields: list[tuple[str, str]],
        drive_link: str | None = None,
        drive_links: dict | None = None,
    ) -> dict:
        """
        Build an Atlassian Document Format document.

        fields      - list of (label, value) pairs rendered as a monospaced block
        drive_link  - single Drive URL to append (for sub-tasks)
        drive_links - dict of {sn: url} to append as a bullet list (for parent)
        """
        # ---- Field table rendered as a code block for monospace alignment ----
        max_label = max(len(label) for label, _ in fields)
        lines = []
        for label, value in fields:
            padding = max_label - len(label)
            lines.append(f"{label}:{' ' * (padding + 3)}{value}")
        code_text = "\n".join(lines)

        content: list[dict] = [
            {
                "type": "codeBlock",
                "attrs": {"language": ""},
                "content": [{"type": "text", "text": code_text}],
            }
        ]

        # ---- Single Drive link (sub-task) ----
        if drive_link:
            content.append(
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Drive Folder:   "},
                        {
                            "type": "text",
                            "text": drive_link,
                            "marks": [
                                {"type": "link", "attrs": {"href": drive_link}}
                            ],
                        },
                    ],
                }
            )

        # ---- Drive links bullet list (parent task) ----
        if drive_links:
            content.append(
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Drive Folders:", "marks": [{"type": "strong"}]}
                    ],
                }
            )
            items = []
            for sn, link in drive_links.items():
                if link:
                    para_content = [
                        {"type": "text", "text": f"{sn}:  "},
                        {
                            "type": "text",
                            "text": link,
                            "marks": [{"type": "link", "attrs": {"href": link}}],
                        },
                    ]
                else:
                    para_content = [{"type": "text", "text": f"{sn}:  (failed — no link)"}]

                items.append(
                    {
                        "type": "listItem",
                        "content": [
                            {"type": "paragraph", "content": para_content}
                        ],
                    }
                )
            content.append({"type": "bulletList", "content": items})

        return {"version": 1, "type": "doc", "content": content}

    # ------------------------------------------------------------------ #
    # HTTP helpers                                                         #
    # ------------------------------------------------------------------ #

    def _api(self, path: str) -> str:
        return f"{self.base_url}/rest/api/3/{path}"

    def _post_issue(self, payload: dict, context: str) -> dict:
        resp = requests.post(
            self._api("issue"),
            auth=self._auth,
            headers=self._headers,
            data=json.dumps(payload),
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"JIRA: failed to create {context} "
                f"(HTTP {resp.status_code}): {resp.text}"
            )
        data = resp.json()
        return {
            "id": data["id"],
            "key": data["key"],
            "url": f"{self.base_url}/browse/{data['key']}",
        }

    def _put_issue(self, issue_id: str, payload: dict, context: str) -> None:
        resp = requests.put(
            self._api(f"issue/{issue_id}"),
            auth=self._auth,
            headers=self._headers,
            data=json.dumps(payload),
            timeout=30,
        )
        if resp.status_code not in (200, 204):
            raise RuntimeError(
                f"JIRA: failed to update {context} "
                f"(HTTP {resp.status_code}): {resp.text}"
            )
