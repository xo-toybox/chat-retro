"""Tests for hooks module."""

import json
from pathlib import Path

import pytest

from chat_retro.hooks import (
    _hash_path,
    audit_logger,
    block_external_writes,
    state_mutation_logger,
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
        chat_retro_dir = tmp_path / ".chat-retro"
        monkeypatch.chdir(tmp_path)
        return chat_retro_dir

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
        log_file = log_dir / "audit.log"
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

        log_file = log_dir / "audit.log"
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

        log_file = log_dir / "audit.log"
        log_entry = json.loads(log_file.read_text().strip())
        assert "file_hash" in log_entry

    @pytest.mark.asyncio
    async def test_includes_timestamp(self, log_dir: Path):
        """Log entries include timestamp."""
        input_data = {"tool_name": "Bash", "tool_input": {}}

        await audit_logger(input_data, None, None)

        log_file = log_dir / "audit.log"
        log_entry = json.loads(log_file.read_text().strip())
        assert "timestamp" in log_entry


class TestBlockExternalWrites:
    """Test block_external_writes hook."""

    @pytest.mark.asyncio
    async def test_allows_outputs_directory(self):
        """Allows writes to ./outputs/."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./outputs/report.html"},
        }

        result = await block_external_writes(input_data, None, None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_allows_state_json(self):
        """Allows writes to state.json."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "./state.json"},
        }

        result = await block_external_writes(input_data, None, None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_allows_chat_retro_directory(self):
        """Allows writes to ./.chat-retro/."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./.chat-retro/sessions/abc.json"},
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
        chat_retro_dir = tmp_path / ".chat-retro"
        monkeypatch.chdir(tmp_path)
        return chat_retro_dir

    @pytest.mark.asyncio
    async def test_logs_state_json_edits(self, log_dir: Path):
        """Logs Edit operations on state.json."""
        input_data = {
            "tool_name": "Edit",
            "session_id": "session-456",
            "tool_input": {
                "file_path": "./state.json",
                "old_string": "old content",
                "new_string": "new content here",
            },
        }

        result = await state_mutation_logger(input_data, "tool-use-2", None)

        assert result == {}
        log_file = log_dir / "state-mutations.log"
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
            "tool_input": {"file_path": "./state.json"},
        }

        result = await state_mutation_logger(input_data, None, None)

        assert result == {}
        log_file = log_dir / "state-mutations.log"
        assert not log_file.exists()

    @pytest.mark.asyncio
    async def test_ignores_non_state_files(self, log_dir: Path):
        """Ignores edits to files other than state.json."""
        input_data = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "./outputs/report.html",
                "old_string": "x",
                "new_string": "y",
            },
        }

        result = await state_mutation_logger(input_data, None, None)

        assert result == {}
        log_file = log_dir / "state-mutations.log"
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
            hook_funcs.extend(matcher.get("hooks", []))
        assert block_external_writes in hook_funcs

    def test_posttooluse_has_audit_logger(self):
        """PostToolUse includes audit_logger."""
        hooks = HOOK_MATCHERS["PostToolUse"]
        hook_funcs = []
        for matcher in hooks:
            hook_funcs.extend(matcher.get("hooks", []))
        assert audit_logger in hook_funcs
        assert state_mutation_logger in hook_funcs
