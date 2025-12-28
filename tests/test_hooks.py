"""Tests for hooks module."""

import json
from pathlib import Path

import pytest

from chat_retro.hooks import (
    _hash_path,
    audit_logger,
    block_external_writes,
    debug_logger,
    state_mutation_logger,
    validate_state_json_write,
    HOOK_MATCHERS,
)


class TestHashPath:
    """Test path hashing utility."""

    def test_hash_produces_8_chars(self):
        """Hash output is exactly 8 characters."""
        result = _hash_path("/some/path/file.txt")
        assert len(result) == 8

    def test_hash_is_deterministic(self):
        """Same path always produces same hash."""
        path = "/foo/bar/baz.json"
        assert _hash_path(path) == _hash_path(path)

    def test_different_paths_different_hashes(self):
        """Different paths produce different hashes."""
        assert _hash_path("/path/a") != _hash_path("/path/b")


class TestAuditLogger:
    """Test audit_logger hook."""

    @pytest.fixture
    def log_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Set up temporary log directory."""
        logs_dir = tmp_path / ".chat-retro-runtime" / "logs"
        monkeypatch.chdir(tmp_path)
        return logs_dir

    @pytest.mark.asyncio
    async def test_logs_tool_name(self, log_dir: Path):
        """Logs tool name."""
        input_data = {
            "tool_name": "Read",
            "session_id": "session-123",
            "tool_input": {"file_path": "/some/file.txt"},
        }

        result = await audit_logger(input_data, "tool-use-1", None)

        assert result == {}
        log_file = log_dir / "debug_audit.jsonl"
        assert log_file.exists()

        log_entry = json.loads(log_file.read_text().strip())
        assert log_entry["tool"] == "Read"
        assert log_entry["session"] == "session-123"

    @pytest.mark.asyncio
    async def test_hashes_file_path(self, log_dir: Path):
        """File paths are hashed, not logged verbatim."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/secret/path/file.txt"},
        }

        await audit_logger(input_data, None, None)

        log_file = log_dir / "debug_audit.jsonl"
        log_entry = json.loads(log_file.read_text().strip())

        # Should have file_hash, not file_path
        assert "file_hash" in log_entry
        assert len(log_entry["file_hash"]) == 8
        # Verify the actual path is not in the log
        assert "/secret/path" not in log_file.read_text()

    @pytest.mark.asyncio
    async def test_handles_path_key(self, log_dir: Path):
        """Handles 'path' key in addition to 'file_path'."""
        input_data = {
            "tool_name": "Glob",
            "tool_input": {"path": "/some/directory"},
        }

        await audit_logger(input_data, None, None)

        log_file = log_dir / "debug_audit.jsonl"
        log_entry = json.loads(log_file.read_text().strip())
        assert "file_hash" in log_entry

    @pytest.mark.asyncio
    async def test_includes_timestamp(self, log_dir: Path):
        """Log entries include timestamp."""
        input_data = {"tool_name": "Bash", "tool_input": {}}

        await audit_logger(input_data, None, None)

        log_file = log_dir / "debug_audit.jsonl"
        log_entry = json.loads(log_file.read_text().strip())
        assert "timestamp" in log_entry


class TestBlockExternalWrites:
    """Test block_external_writes hook."""

    @pytest.fixture(autouse=True)
    def use_tmp_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Run tests in a temporary directory for path resolution."""
        (tmp_path / ".chat-retro-runtime").mkdir()
        (tmp_path / ".chat-retro-runtime" / "outputs").mkdir()
        monkeypatch.chdir(tmp_path)

    @pytest.mark.asyncio
    async def test_allows_outputs_directory(self):
        """Allows writes to .chat-retro-runtime/outputs/."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro-runtime/outputs/report.html"},
        }

        result = await block_external_writes(input_data, None, None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_allows_state_json(self):
        """Allows writes to analysis.json."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "./.chat-retro-runtime/state/analysis.json"},
        }

        result = await block_external_writes(input_data, None, None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_allows_chat_retro_runtime_directory(self):
        """Allows writes to ./.chat-retro-runtime/."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro-runtime/resume-session.json"},
        }

        result = await block_external_writes(input_data, None, None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_blocks_external_path(self):
        """Blocks writes outside allowed paths."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "/etc/passwd"},
        }

        result = await block_external_writes(input_data, None, None)

        assert "hookSpecificOutput" in result
        output = result["hookSpecificOutput"]
        assert output["permissionDecision"] == "deny"
        assert "/etc/passwd" in output["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_blocks_parent_directory_escape(self):
        """Blocks writes attempting parent directory escape."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "../outside/file.txt"},
        }

        result = await block_external_writes(input_data, None, None)
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_blocks_traversal_within_allowed_prefix(self):
        """Blocks path traversal attacks that start with allowed prefix."""
        # This would pass a naive prefix check but resolves outside allowed dirs
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": ".chat-retro-runtime/../secret.txt"},
        }

        result = await block_external_writes(input_data, None, None)
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_blocks_deep_traversal_attack(self):
        """Blocks deep traversal attacks."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro-runtime/../../../etc/passwd"},
        }

        result = await block_external_writes(input_data, None, None)
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_ignores_non_write_tools(self):
        """Ignores non-Write/Edit tools."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/etc/passwd"},
        }

        result = await block_external_writes(input_data, None, None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_ignores_non_pretooluse_events(self):
        """Ignores non-PreToolUse events."""
        input_data = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "/etc/passwd"},
        }

        result = await block_external_writes(input_data, None, None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_handles_path_key(self):
        """Handles 'path' key in addition to 'file_path'."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"path": "/forbidden/path"},
        }

        result = await block_external_writes(input_data, None, None)
        assert "hookSpecificOutput" in result


class TestStateMutationLogger:
    """Test state_mutation_logger hook."""

    @pytest.fixture
    def log_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Set up temporary log directory."""
        logs_dir = tmp_path / ".chat-retro-runtime" / "logs"
        monkeypatch.chdir(tmp_path)
        return logs_dir

    @pytest.mark.asyncio
    async def test_logs_analysis_json_edits(self, log_dir: Path):
        """Logs Edit operations on analysis.json."""
        input_data = {
            "tool_name": "Edit",
            "session_id": "session-456",
            "tool_input": {
                "file_path": "./.chat-retro-runtime/state/analysis.json",
                "old_string": "old content",
                "new_string": "new content here",
            },
        }

        result = await state_mutation_logger(input_data, "tool-use-2", None)

        assert result == {}
        log_file = log_dir / "state-mutations.jsonl"
        assert log_file.exists()

        log_entry = json.loads(log_file.read_text().strip())
        assert log_entry["session"] == "session-456"
        assert log_entry["old_string_len"] == len("old content")
        assert log_entry["new_string_len"] == len("new content here")
        assert log_entry["tool_use_id"] == "tool-use-2"

    @pytest.mark.asyncio
    async def test_ignores_non_edit_tools(self, log_dir: Path):
        """Ignores non-Edit tools."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro-runtime/state/analysis.json"},
        }

        result = await state_mutation_logger(input_data, None, None)

        assert result == {}
        log_file = log_dir / "state-mutations.jsonl"
        assert not log_file.exists()

    @pytest.mark.asyncio
    async def test_ignores_non_state_files(self, log_dir: Path):
        """Ignores edits to files other than analysis.json."""
        input_data = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "./.chat-retro-runtime/outputs/report.html",
                "old_string": "x",
                "new_string": "y",
            },
        }

        result = await state_mutation_logger(input_data, None, None)

        assert result == {}
        log_file = log_dir / "state-mutations.jsonl"
        assert not log_file.exists()


class TestHookMatchers:
    """Test HOOK_MATCHERS configuration."""

    def test_has_pretooluse_hooks(self):
        """PreToolUse hooks are configured."""
        assert "PreToolUse" in HOOK_MATCHERS
        assert len(HOOK_MATCHERS["PreToolUse"]) > 0

    def test_has_posttooluse_hooks(self):
        """PostToolUse hooks are configured."""
        assert "PostToolUse" in HOOK_MATCHERS
        assert len(HOOK_MATCHERS["PostToolUse"]) > 0

    def test_pretooluse_has_block_writes(self):
        """PreToolUse includes block_external_writes."""
        hooks = HOOK_MATCHERS["PreToolUse"]
        hook_funcs = []
        for matcher in hooks:
            hook_funcs.extend(matcher.hooks)
        assert block_external_writes in hook_funcs

    def test_posttooluse_has_audit_logger(self):
        """PostToolUse includes audit_logger."""
        hooks = HOOK_MATCHERS["PostToolUse"]
        hook_funcs = []
        for matcher in hooks:
            hook_funcs.extend(matcher.hooks)
        assert audit_logger in hook_funcs
        assert state_mutation_logger in hook_funcs


class TestDebugLogger:
    """Test debug_logger hook."""

    @pytest.fixture
    def log_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Set up temp directory for debug logs."""
        logs_dir = tmp_path / ".chat-retro-runtime" / "logs"
        monkeypatch.chdir(tmp_path)
        return logs_dir

    @pytest.mark.asyncio
    async def test_logs_full_tool_input(self, log_dir: Path):
        """Debug log includes full tool_input."""
        input_data = {
            "tool_name": "Edit",
            "session_id": "session-123",
            "tool_input": {
                "file_path": "./.chat-retro-runtime/state/analysis.json",
                "old_string": "old content",
                "new_string": "new content",
            },
        }

        await debug_logger(input_data, "tool-1", None)

        log_file = log_dir / "debug.jsonl"
        assert log_file.exists()
        entry = json.loads(log_file.read_text().strip())
        assert entry["tool_input"]["old_string"] == "old content"
        assert entry["tool_input"]["new_string"] == "new content"
        assert entry["file_path"] == "./.chat-retro-runtime/state/analysis.json"
        assert entry["tool_use_id"] == "tool-1"

    @pytest.mark.asyncio
    async def test_logs_tool_response(self, log_dir: Path):
        """Debug log includes tool_response."""
        input_data = {
            "tool_name": "Read",
            "session_id": "session-456",
            "tool_response": {"content": "file contents here", "lines": 50},
        }

        await debug_logger(input_data, None, None)

        log_file = log_dir / "debug.jsonl"
        assert log_file.exists()
        entry = json.loads(log_file.read_text().strip())
        assert entry["tool_response"]["content"] == "file contents here"
        assert entry["tool_response"]["lines"] == 50

    @pytest.mark.asyncio
    async def test_logs_unhashed_path(self, log_dir: Path):
        """Debug log includes unhashed file path."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"path": "/full/path/to/file.py"},
        }

        await debug_logger(input_data, None, None)

        log_file = log_dir / "debug.jsonl"
        entry = json.loads(log_file.read_text().strip())
        # Debug log should have full path, not hashed
        assert entry["file_path"] == "/full/path/to/file.py"

    @pytest.mark.asyncio
    async def test_handles_non_serializable_values(self, log_dir: Path):
        """Debug log handles non-JSON-serializable values via default=str."""
        from datetime import datetime

        input_data = {
            "tool_name": "Test",
            "tool_input": {"timestamp": datetime(2025, 1, 1, 12, 0, 0)},
        }

        # Should not raise, uses default=str
        await debug_logger(input_data, None, None)

        log_file = log_dir / "debug.jsonl"
        assert log_file.exists()
        entry = json.loads(log_file.read_text().strip())
        assert "2025-01-01" in entry["tool_input"]["timestamp"]


class TestValidateStateJsonWrite:
    """Test validate_state_json_write hook."""

    @pytest.mark.asyncio
    async def test_allows_valid_analysis_json(self):
        """Allows valid analysis.json write."""
        valid_content = json.dumps({
            "schema_version": 1,
            "meta": {
                "created": "2025-01-01T00:00:00",
                "last_updated": "2025-01-01T00:00:00",
            },
            "patterns": [
                {"id": "p1", "type": "theme", "label": "Test", "confidence": 0.8}
            ],
        })
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro-runtime/state/analysis.json", "content": valid_content},
        }

        result = await validate_state_json_write(input_data, None, None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_blocks_invalid_json(self):
        """Blocks write with invalid JSON content."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro-runtime/state/analysis.json", "content": "not valid json"},
        }

        result = await validate_state_json_write(input_data, None, None)
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "not valid JSON" in result["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_blocks_missing_schema_version(self):
        """Blocks write missing schema_version."""
        content = json.dumps({"meta": {}, "patterns": []})
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro-runtime/state/analysis.json", "content": content},
        }

        result = await validate_state_json_write(input_data, None, None)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "schema_version" in result["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_blocks_patterns_as_dict(self):
        """Blocks write where patterns is a dict instead of list."""
        content = json.dumps({
            "schema_version": 1,
            "meta": {},
            "patterns": {"p1": {"label": "Test"}},  # Dict, not list!
        })
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro-runtime/state/analysis.json", "content": content},
        }

        result = await validate_state_json_write(input_data, None, None)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "must be a list" in result["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_blocks_confidence_out_of_range(self):
        """Blocks write with confidence > 1.0."""
        content = json.dumps({
            "schema_version": 1,
            "meta": {},
            "patterns": [{"id": "p1", "confidence": 1.5}],
        })
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro-runtime/state/analysis.json", "content": content},
        }

        result = await validate_state_json_write(input_data, None, None)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "between 0.0 and 1.0" in result["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_blocks_invalid_pattern_type(self):
        """Blocks write with invalid pattern type."""
        content = json.dumps({
            "schema_version": 1,
            "meta": {},
            "patterns": [{"id": "p1", "type": "invalid_type"}],
        })
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro-runtime/state/analysis.json", "content": content},
        }

        result = await validate_state_json_write(input_data, None, None)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "must be one of" in result["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_ignores_non_analysis_json_writes(self):
        """Ignores writes to other files."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro-runtime/outputs/report.html", "content": "not json"},
        }

        result = await validate_state_json_write(input_data, None, None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_ignores_edit_tool(self):
        """Ignores Edit operations (only validates Write)."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "./.chat-retro-runtime/state/analysis.json", "content": "invalid"},
        }

        result = await validate_state_json_write(input_data, None, None)
        assert result == {}
