"""Issue reporting for auto and manual issue creation.

Provides IssueReporter class used by both chat-retro (auto-reports) and
issue-workflow (manual reports, draft management).
"""

import json
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlencode

from .issue_types import Issue, IssueSeverity, IssueStatus


@dataclass
class IssueReporter:
    """Creates and manages issue drafts.

    Drafts are saved to .chat-retro-runtime/issue-drafts/ and processed
    by the issue-workflow tool's agentic pipeline.
    """

    repo_url: str = "https://github.com/example/chat-retro"
    drafts_dir: Path = field(
        default_factory=lambda: Path(".chat-retro-runtime/issue-drafts")
    )

    def __post_init__(self) -> None:
        self.drafts_dir.mkdir(parents=True, exist_ok=True)

    def save_draft_issue(
        self,
        title: str,
        description: str,
        category: str = "bug",
        context: dict | None = None,
        severity: IssueSeverity | None = None,
    ) -> Path:
        """Save draft issue for processing by issue-workflow.

        Uses shared Issue schema for compatibility with the workflow pipeline.
        Pass severity for known-critical issues (e.g., data corruption) to
        enable fast-tracking in the workflow.
        """
        issue = Issue(
            title=title,
            description=description,
            category=category,
            context=context or {},
            status=IssueStatus.draft,
            severity=severity,
        )

        filename = f"draft_{issue.created.strftime('%Y%m%d_%H%M%S')}_{issue.id}.json"
        filepath = self.drafts_dir / filename
        filepath.write_text(issue.model_dump_json(indent=2))
        return filepath

    def get_pending_drafts(self) -> list[dict]:
        """Get draft issues that haven't been triaged."""
        drafts = []
        for f in self.drafts_dir.glob("draft_*.json"):
            try:
                draft = json.loads(f.read_text())
                if draft.get("status") == "draft":
                    draft["file"] = str(f)
                    drafts.append(draft)
            except (json.JSONDecodeError, ValueError):
                continue
        return drafts

    def create_github_issue_url(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> str:
        """Generate a GitHub issue URL with pre-filled content."""
        params: dict[str, str] = {
            "title": title,
            "body": body,
        }
        if labels:
            params["labels"] = ",".join(labels)

        return f"{self.repo_url}/issues/new?{urlencode(params)}"

    def open_github_issue(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> str:
        """Open browser to create GitHub issue."""
        url = self.create_github_issue_url(title, body, labels)
        webbrowser.open(url)
        return url
