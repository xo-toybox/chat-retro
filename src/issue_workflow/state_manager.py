"""Issue state management for the workflow."""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from shared import Issue, IssueState, IssueStatus

# Centralized runtime paths - single source of truth
RUNTIME_BASE = Path(".chat-retro-runtime")
RUNTIME_PATHS = {
    "base": RUNTIME_BASE,
    "drafts": RUNTIME_BASE / "issue-drafts",
    "issues": RUNTIME_BASE / "issues",
    "state": RUNTIME_BASE / "issue-state.json",
}


@dataclass
class IssueStateManager:
    """Read/write issue state with migration support."""

    CURRENT_VERSION: int = 2

    state_path: Path = field(default_factory=lambda: RUNTIME_PATHS["state"])
    drafts_dir: Path = field(default_factory=lambda: RUNTIME_PATHS["drafts"])
    issues_dir: Path = field(default_factory=lambda: RUNTIME_PATHS["issues"])

    def __post_init__(self) -> None:
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.issues_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> IssueState:
        """Load existing state or create new."""
        if not self.state_path.exists():
            return IssueState()

        try:
            data = json.loads(self.state_path.read_text())
            version = data.get("schema_version", 0)
            if version < self.CURRENT_VERSION:
                data = self._migrate(data, version)
            return IssueState.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            backup = self.state_path.with_suffix(".json.corrupt")
            self.state_path.rename(backup)
            print(
                f"WARNING: Issue state file was corrupted ({type(e).__name__}). "
                f"Backed up to {backup} and starting fresh.",
                file=sys.stderr,
            )
            return IssueState()

    def save(self, state: IssueState) -> None:
        """Persist state atomically."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".json.tmp")
        tmp.write_text(state.model_dump_json(indent=2))
        tmp.rename(self.state_path)

    def _migrate(self, data: dict, from_version: int) -> dict:
        """Migrate state from older schema versions."""
        # v1 → v2: Remove sanitized_* fields, move content to title/description
        if from_version < 2:
            for issue_data in data.get("issues", {}).values():
                if issue_data.get("sanitized_title"):
                    # Preserve raw in context, use sanitized as title
                    if issue_data.get("title") != issue_data["sanitized_title"]:
                        issue_data.setdefault("context", {})["raw_title"] = issue_data.get("title")
                    issue_data["title"] = issue_data["sanitized_title"]
                if issue_data.get("sanitized_description"):
                    if issue_data.get("description") != issue_data["sanitized_description"]:
                        issue_data.setdefault("context", {})["raw_description"] = issue_data.get("description")
                    issue_data["description"] = issue_data["sanitized_description"]
                # Remove deprecated fields
                issue_data.pop("sanitized_title", None)
                issue_data.pop("sanitized_description", None)

        data["schema_version"] = self.CURRENT_VERSION
        return data

    # Draft management

    def save_draft(
        self,
        title: str,
        description: str,
        category: str = "bug",
        context: dict | None = None,
    ) -> Issue:
        """Save a new draft issue."""
        issue = Issue(
            title=title,
            description=description,
            category=category,
            context=context or {},
            status=IssueStatus.draft,
        )

        # Save to drafts directory
        filename = f"draft_{issue.created.strftime('%Y%m%d_%H%M%S')}_{issue.id}.json"
        filepath = self.drafts_dir / filename
        filepath.write_text(issue.model_dump_json(indent=2))

        # Add to state
        state = self.load()
        state.issues[issue.id] = issue
        self.save(state)

        return issue

    def get_drafts(self) -> list[Issue]:
        """Get all draft issues."""
        state = self.load()
        return [i for i in state.issues.values() if i.status == IssueStatus.draft]

    def get_issues_by_status(self, status: IssueStatus) -> list[Issue]:
        """Get issues by status."""
        state = self.load()
        return [i for i in state.issues.values() if i.status == status]

    # Draft import (with cleanup)

    def import_draft(self, draft_path: Path) -> Issue:
        """Import a draft file into state, then delete the file.

        Atomic: state is saved before file is deleted, so a crash
        leaves the draft file intact for retry.
        """
        data = json.loads(draft_path.read_text())

        # Extract ID from filename (e.g., draft_20251228_115557_80e98398.json)
        filename = draft_path.stem
        parts = filename.split("_")
        issue_id = parts[-1] if len(parts) >= 4 else None

        created = None
        if "created" in data:
            created = datetime.fromisoformat(data["created"])

        issue = Issue(
            id=issue_id or data.get("id"),
            title=data["title"],
            description=data["description"],
            category=data.get("category", "bug"),
            context=data.get("context", {}),
            status=IssueStatus.draft,
            created=created or datetime.now(),
        )

        state = self.load()
        state.issues[issue.id] = issue
        self.save(state)  # Commit to state first
        draft_path.unlink()  # Then delete source
        return issue

    def import_all_drafts(self) -> list[Issue]:
        """Import all draft files from issue-drafts directory.

        Returns list of imported issues. Already-imported issues are skipped.
        """
        imported = []
        state = self.load()

        for path in self.drafts_dir.glob("draft_*.json"):
            # Extract ID from filename
            parts = path.stem.split("_")
            if len(parts) >= 4:
                issue_id = parts[-1]
                # Skip if already in state
                if issue_id in state.issues:
                    path.unlink()  # Clean up duplicate file
                    continue

            imported.append(self.import_draft(path))

        return imported

    # Public issue management

    def publish_issue(self, issue: Issue) -> Path:
        """Save issue to public issues directory.

        Post-triage, title/description contain sanitized content.
        """
        if issue.status == IssueStatus.draft:
            raise ValueError("Issue must be triaged before publishing")

        sev = issue.severity
        public_data = {
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "category": issue.category,
            "tags": issue.tags,
            "affected_files": issue.affected_files,
            "severity": str(sev.value if hasattr(sev, "value") else sev) if sev else "unknown",
            "frequency": issue.frequency,
            "created": issue.created.isoformat(),
        }

        filename = f"issue_{issue.id}.json"
        filepath = self.issues_dir / filename
        filepath.write_text(json.dumps(public_data, indent=2))
        return filepath

    def resolve_issue(self, issue_id: str, notes: str, resolved_by: str) -> None:
        """Mark issue as resolved and update changelog."""
        state = self.load()
        if issue_id not in state.issues:
            raise ValueError(f"Issue {issue_id} not found")

        issue = state.issues[issue_id]
        issue.status = IssueStatus.resolved
        issue.resolution_notes = notes
        issue.resolved_by = resolved_by
        issue.updated = datetime.now()
        self.save(state)

        self._append_changelog(issue, notes)

        # Remove from public issues dir
        public_file = self.issues_dir / f"issue_{issue_id}.json"
        if public_file.exists():
            public_file.unlink()

    def _append_changelog(self, issue: Issue, notes: str) -> None:
        """Append resolution to CHANGELOG.md."""
        changelog_path = self.issues_dir / "CHANGELOG.md"

        today = datetime.now().strftime("%Y-%m-%d")
        entry = f"- **{issue.id}**: {notes}\n"

        if changelog_path.exists():
            content = changelog_path.read_text()
            if f"## {today}" in content:
                parts = content.split(f"## {today}\n", 1)
                content = f"{parts[0]}## {today}\n{entry}{parts[1]}"
            else:
                lines = content.split("\n", 2)
                if len(lines) >= 2:
                    content = f"{lines[0]}\n\n## {today}\n{entry}\n{lines[2] if len(lines) > 2 else ''}"
                else:
                    content = f"# Issue Changelog\n\n## {today}\n{entry}"
        else:
            content = f"# Issue Changelog\n\n## {today}\n{entry}"

        changelog_path.write_text(content)
