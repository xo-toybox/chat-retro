"""State management for chat-retro analysis sessions."""


import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class StateMeta(BaseModel):
    """Metadata about the analysis."""

    created: datetime
    last_updated: datetime
    conversation_count: int = 0
    date_range: tuple[str, str] | None = None
    export_format: Literal["chatgpt", "claude"] | None = None
    export_file_hash: str | None = None  # SHA256 for cache invalidation


class TemporalInfo(BaseModel):
    """Temporal information for a pattern."""

    peak_month: str | None = None
    frequency: str | None = None


class Pattern(BaseModel):
    """A discovered pattern in conversation data."""

    id: str
    type: Literal["theme", "temporal", "behavioral", "other"]
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    conversation_ids: list[str] = Field(default_factory=list)
    temporal: TemporalInfo | None = None


class UserPreferences(BaseModel):
    """User preferences for analysis focus."""

    focus_areas: list[str] = Field(default_factory=list)
    excluded_topics: list[str] = Field(default_factory=list)
    preferred_viz: str | None = None


class SnapshotRef(BaseModel):
    """Reference to a generated artifact snapshot."""

    date: str
    artifact: str


class AnalysisState(BaseModel):
    """Complete analysis state persisted between sessions."""

    schema_version: int = 1
    meta: StateMeta
    patterns: list[Pattern] = Field(default_factory=list)
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)
    snapshots: list[SnapshotRef] = Field(default_factory=list)


@dataclass
class StateManager:
    """Read/write local analysis.json with migration support."""

    CURRENT_VERSION: int = 1

    state_path: Path = field(
        default_factory=lambda: Path(".chat-retro-runtime/state/analysis.json")
    )
    report_corruption: bool = True  # Set False in tests to avoid leaking drafts

    def load(self) -> AnalysisState | None:
        """Load existing state with migration and corruption recovery."""
        if not self.state_path.exists():
            return None

        try:
            data = json.loads(self.state_path.read_text())
            version = data.get("schema_version", 0)
            if version < self.CURRENT_VERSION:
                data = self._migrate(data, version)
            return AnalysisState.model_validate(data)
        except json.JSONDecodeError as e:
            self._report_corruption("Invalid JSON", str(e))
            backup = self.state_path.with_suffix(".json.corrupt")
            self.state_path.rename(backup)
            return None
        except ValidationError as e:
            self._report_corruption("Schema validation failed", str(e))
            backup = self.state_path.with_suffix(".json.corrupt")
            self.state_path.rename(backup)
            return None

    def _report_corruption(self, error_type: str, error_detail: str) -> None:
        """Auto-create issue when state.json fails validation."""
        if not self.report_corruption:
            return

        from shared import IssueReporter, IssueSeverity

        # Capture preview of corrupt content for debugging
        state_preview = ""
        try:
            state_preview = self.state_path.read_text()[:500]
        except Exception:
            pass

        reporter = IssueReporter()
        reporter.save_draft_issue(
            title=f"State corruption: {error_type}",
            description=(
                f"state.json failed to load and was renamed to .corrupt.\n\n"
                f"Error: {error_detail[:500]}\n\n"
                f"State preview:\n```\n{state_preview}\n```"
            ),
            category="bug",
            context={
                "error_type": error_type,
                "state_path": str(self.state_path),
            },
            severity=IssueSeverity.critical,  # Fast-track corruption issues
        )

    def save(self, state: AnalysisState) -> None:
        """Persist state atomically."""
        # Update last_updated timestamp
        state.meta.last_updated = datetime.now()

        tmp = self.state_path.with_suffix(".json.tmp")
        tmp.write_text(state.model_dump_json(indent=2))
        tmp.rename(self.state_path)

    def merge_patterns(
        self,
        existing: list[Pattern],
        new: list[Pattern],
    ) -> list[Pattern]:
        """Merge patterns from incremental analysis."""
        existing_ids = {p.id for p in existing}
        merged = list(existing)

        for pattern in new:
            if pattern.id not in existing_ids:
                merged.append(pattern)
            else:
                # Update existing pattern
                for i, p in enumerate(merged):
                    if p.id == pattern.id:
                        merged[i] = pattern
                        break

        return merged

    def _migrate(self, data: dict, from_version: int) -> dict:
        """Migrate state from older schema versions."""
        # Future migrations go here
        # For now, just ensure schema_version is set
        data["schema_version"] = self.CURRENT_VERSION
        return data

    def create_initial_state(
        self,
        conversation_count: int = 0,
        export_format: Literal["chatgpt", "claude"] | None = None,
        export_path: Path | None = None,
    ) -> AnalysisState:
        """Create a new initial state."""
        now = datetime.now()
        file_hash = self.compute_export_hash(export_path) if export_path else None
        return AnalysisState(
            schema_version=self.CURRENT_VERSION,
            meta=StateMeta(
                created=now,
                last_updated=now,
                conversation_count=conversation_count,
                export_format=export_format,
                export_file_hash=file_hash,
            ),
        )

    @staticmethod
    def compute_export_hash(export_path: Path) -> str | None:
        """Compute SHA256 hash of export file for cache invalidation.

        Uses first 1MB only to avoid hashing 400MB files.
        """
        if not export_path or not export_path.exists():
            return None

        hasher = hashlib.sha256()
        with export_path.open("rb") as f:
            # Read first 1MB for fast hashing of large files
            chunk = f.read(1024 * 1024)
            hasher.update(chunk)
            # Also hash file size for extra validation
            f.seek(0, 2)  # Seek to end
            hasher.update(str(f.tell()).encode())
        return hasher.hexdigest()[:16]  # Short hash is sufficient

    def is_cache_valid(self, export_path: Path) -> bool:
        """Check if cached analysis is still valid for given export file."""
        state = self.load()
        if state is None:
            return False

        if state.meta.export_file_hash is None:
            return False

        current_hash = self.compute_export_hash(export_path)
        return state.meta.export_file_hash == current_hash

    def get_cached_summary(self, export_path: Path | None = None) -> dict | None:
        """Get cached analysis summary if valid, None otherwise.

        Returns a lightweight dict with key metrics for subagent context:
        - meta: creation date, conversation count, date range
        - patterns: list of pattern summaries
        - topic_clusters: loaded from topics.json if available

        If export_path is provided, validates cache against file hash.
        """
        state = self.load()
        if state is None:
            return None

        # Validate cache if export path provided
        if export_path and not self.is_cache_valid(export_path):
            return None

        # Load topics.json if available
        topics_path = self.state_path.parent / "topics.json"
        topics = None
        if topics_path.exists():
            try:
                topics = json.loads(topics_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        return {
            "meta": {
                "created": state.meta.created.isoformat(),
                "last_updated": state.meta.last_updated.isoformat(),
                "conversation_count": state.meta.conversation_count,
                "date_range": state.meta.date_range,
                "export_format": state.meta.export_format,
            },
            "patterns": [
                {
                    "id": p.id,
                    "type": p.type,
                    "label": p.label,
                    "confidence": p.confidence,
                }
                for p in state.patterns
            ],
            "topic_clusters": topics.get("topics") if topics else None,
            "cache_valid": True,
        }
