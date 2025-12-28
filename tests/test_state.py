"""Tests for state management."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from chat_retro.state import (
    AnalysisState,
    Pattern,
    SnapshotRef,
    StateManager,
    StateMeta,
    TemporalInfo,
    UserPreferences,
)


class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_state_meta_creation(self):
        """StateMeta validates correctly."""
        meta = StateMeta(
            created=datetime.now(),
            last_updated=datetime.now(),
            conversation_count=100,
            export_format="chatgpt",
        )
        assert meta.conversation_count == 100
        assert meta.export_format == "chatgpt"

    def test_pattern_creation(self):
        """Pattern validates with required fields."""
        pattern = Pattern(
            id="p1",
            type="theme",
            label="Python debugging",
            confidence=0.85,
            conversation_ids=["c1", "c2"],
        )
        assert pattern.id == "p1"
        assert pattern.confidence == 0.85

    def test_pattern_confidence_bounds(self):
        """Pattern confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            Pattern(id="p1", type="theme", label="test", confidence=1.5)

        with pytest.raises(ValueError):
            Pattern(id="p1", type="theme", label="test", confidence=-0.1)

    def test_pattern_with_temporal(self):
        """Pattern can include temporal information."""
        pattern = Pattern(
            id="p1",
            type="temporal",
            label="Weekly coding",
            confidence=0.9,
            temporal=TemporalInfo(peak_month="2025-03", frequency="weekly"),
        )
        assert pattern.temporal is not None
        assert pattern.temporal.peak_month == "2025-03"

    def test_analysis_state_creation(self):
        """AnalysisState validates with nested models."""
        now = datetime.now()
        state = AnalysisState(
            schema_version=1,
            meta=StateMeta(created=now, last_updated=now),
            patterns=[
                Pattern(id="p1", type="theme", label="test", confidence=0.5)
            ],
            user_preferences=UserPreferences(focus_areas=["work"]),
            snapshots=[SnapshotRef(date="2025-06", artifact="outputs/2025-06.html")],
        )
        assert state.schema_version == 1
        assert len(state.patterns) == 1
        assert state.user_preferences.focus_areas == ["work"]

    def test_analysis_state_defaults(self):
        """AnalysisState has sensible defaults."""
        now = datetime.now()
        state = AnalysisState(
            meta=StateMeta(created=now, last_updated=now),
        )
        assert state.schema_version == 1
        assert state.patterns == []
        assert state.user_preferences.focus_areas == []
        assert state.snapshots == []


class TestStateManager:
    """Test StateManager load/save operations."""

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        """Loading nonexistent state returns None."""
        manager = StateManager(state_path=tmp_path / "state.json")
        assert manager.load() is None

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        """State can be saved and loaded."""
        state_path = tmp_path / "state.json"
        manager = StateManager(state_path=state_path)

        state = manager.create_initial_state(
            conversation_count=50,
            export_format="chatgpt",
        )
        state.patterns.append(
            Pattern(id="p1", type="theme", label="coding", confidence=0.8)
        )

        manager.save(state)
        assert state_path.exists()

        loaded = manager.load()
        assert loaded is not None
        assert loaded.meta.conversation_count == 50
        assert loaded.meta.export_format == "chatgpt"
        assert len(loaded.patterns) == 1
        assert loaded.patterns[0].id == "p1"

    def test_atomic_save(self, tmp_path: Path):
        """Save is atomic (uses tmp file rename)."""
        state_path = tmp_path / "state.json"
        manager = StateManager(state_path=state_path)

        state = manager.create_initial_state()
        manager.save(state)

        # tmp file should not exist after save
        tmp_path_file = state_path.with_suffix(".json.tmp")
        assert not tmp_path_file.exists()
        assert state_path.exists()

    def test_corruption_recovery(self, tmp_path: Path):
        """Corrupted state is backed up and None returned."""
        state_path = tmp_path / "state.json"
        state_path.write_text("not valid json {{{")

        manager = StateManager(state_path=state_path, report_corruption=False)
        result = manager.load()

        assert result is None
        backup = state_path.with_suffix(".json.corrupt")
        assert backup.exists()
        assert backup.read_text() == "not valid json {{{"

    def test_invalid_schema_recovery(self, tmp_path: Path):
        """Invalid schema triggers corruption recovery."""
        state_path = tmp_path / "state.json"
        # Valid JSON but invalid schema
        state_path.write_text('{"schema_version": 1, "meta": "not an object"}')

        manager = StateManager(state_path=state_path, report_corruption=False)
        result = manager.load()

        assert result is None
        backup = state_path.with_suffix(".json.corrupt")
        assert backup.exists()

    def test_merge_patterns_new(self):
        """Merge adds new patterns."""
        manager = StateManager()
        existing = [
            Pattern(id="p1", type="theme", label="old", confidence=0.5)
        ]
        new = [
            Pattern(id="p2", type="theme", label="new", confidence=0.7)
        ]

        merged = manager.merge_patterns(existing, new)
        assert len(merged) == 2
        assert {p.id for p in merged} == {"p1", "p2"}

    def test_merge_patterns_update(self):
        """Merge updates existing patterns."""
        manager = StateManager()
        existing = [
            Pattern(id="p1", type="theme", label="old", confidence=0.5)
        ]
        new = [
            Pattern(id="p1", type="theme", label="updated", confidence=0.9)
        ]

        merged = manager.merge_patterns(existing, new)
        assert len(merged) == 1
        assert merged[0].label == "updated"
        assert merged[0].confidence == 0.9

    def test_migration_sets_version(self, tmp_path: Path):
        """Migration updates schema_version."""
        state_path = tmp_path / "state.json"
        now = datetime.now().isoformat()
        old_state = {
            "schema_version": 0,
            "meta": {
                "created": now,
                "last_updated": now,
            },
        }
        state_path.write_text(json.dumps(old_state))

        manager = StateManager(state_path=state_path)
        loaded = manager.load()

        assert loaded is not None
        assert loaded.schema_version == manager.CURRENT_VERSION

    def test_create_initial_state(self):
        """create_initial_state produces valid state."""
        manager = StateManager()
        state = manager.create_initial_state(
            conversation_count=100,
            export_format="claude",
        )

        assert state.schema_version == 1
        assert state.meta.conversation_count == 100
        assert state.meta.export_format == "claude"
        assert state.patterns == []

    def test_save_updates_last_updated(self, tmp_path: Path):
        """Saving updates the last_updated timestamp."""
        state_path = tmp_path / "state.json"
        manager = StateManager(state_path=state_path)

        state = manager.create_initial_state()
        original_updated = state.meta.last_updated

        # Small delay to ensure timestamp changes
        import time
        time.sleep(0.01)

        manager.save(state)
        loaded = manager.load()

        assert loaded is not None
        assert loaded.meta.last_updated > original_updated
