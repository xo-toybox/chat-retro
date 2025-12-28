"""State management for chat-retro analysis sessions."""

from __future__ import annotations

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
    """Read/write local state.json with migration support."""

    CURRENT_VERSION: int = 1

    state_path: Path = field(default_factory=lambda: Path("state.json"))

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
        except (json.JSONDecodeError, ValidationError):
            backup = self.state_path.with_suffix(".json.corrupt")
            self.state_path.rename(backup)
            return None

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
    ) -> AnalysisState:
        """Create a new initial state."""
        now = datetime.now()
        return AnalysisState(
            schema_version=self.CURRENT_VERSION,
            meta=StateMeta(
                created=now,
                last_updated=now,
                conversation_count=conversation_count,
                export_format=export_format,
            ),
        )
