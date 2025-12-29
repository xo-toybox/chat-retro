"""Hooks for audit logging and write protection."""


from claude_agent_sdk import HookMatcher

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def _hash_path(path: str) -> str:
    """Hash a file path for privacy-safe logging."""
    return hashlib.sha256(path.encode()).hexdigest()[:8]


async def audit_logger(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    """Log tool usage without exposing conversation content.

    Logs tool names, timestamps, and hashed file paths only.
    Never logs actual content or message text.
    """
    event: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "tool": input_data.get("tool_name"),
        "session": input_data.get("session_id"),
    }

    # Privacy: hash file paths, don't log content
    tool_input = input_data.get("tool_input", {})
    if "file_path" in tool_input:
        event["file_hash"] = _hash_path(tool_input["file_path"])
    elif "path" in tool_input:
        event["file_hash"] = _hash_path(tool_input["path"])

    # Write to audit log
    log_dir = Path(".chat-retro-runtime/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "debug_audit.jsonl"

    with open(log_file, "a") as f:
        f.write(json.dumps(event) + "\n")

    return {}


async def block_external_writes(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    """Prevent writes outside project directory.

    Only allows writes to ./.chat-retro-runtime/.
    Uses resolved paths to prevent traversal attacks.
    """
    # Only check PreToolUse events
    if input_data.get("hook_event_name") != "PreToolUse":
        return {}

    tool_name = input_data.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        return {}

    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")

    if not file_path:
        return {}

    # Resolve to absolute path to prevent traversal attacks
    project_root = Path.cwd().resolve()
    resolved = (project_root / file_path).resolve()

    # Allowed destinations (resolved)
    allowed_paths = [
        project_root / ".chat-retro-runtime",
    ]

    # Check if resolved path is within allowed locations
    is_allowed = any(
        resolved == allowed or resolved.is_relative_to(allowed)
        for allowed in allowed_paths
    )

    if not is_allowed:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Write blocked: {file_path} resolves outside allowed paths",
            }
        }

    return {}


async def state_mutation_logger(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    """Log Edit operations on state.json for efficiency analysis.

    Tracks edit sizes to understand state update patterns.
    """
    if input_data.get("tool_name") != "Edit":
        return {}

    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")

    if "analysis.json" not in str(file_path):
        return {}

    event = {
        "timestamp": datetime.now().isoformat(),
        "session": input_data.get("session_id"),
        "old_string_len": len(tool_input.get("old_string", "")),
        "new_string_len": len(tool_input.get("new_string", "")),
        "tool_use_id": tool_use_id,
    }

    # Write to state mutations log
    log_dir = Path(".chat-retro-runtime/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "state-mutations.jsonl"

    with open(log_file, "a") as f:
        f.write(json.dumps(event) + "\n")

    return {}


async def debug_logger(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    """Log full tool input/output for debugging.

    WARNING: Contains potentially sensitive data.
    Enable via CHAT_RETRO_DEBUG=1 environment variable.
    """
    event: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "tool": input_data.get("tool_name"),
        "session": input_data.get("session_id"),
        "tool_use_id": tool_use_id,
        "tool_input": input_data.get("tool_input"),
        "tool_response": input_data.get("tool_response"),
    }

    # Include unhashed file path for debugging
    tool_input = input_data.get("tool_input", {})
    if "file_path" in tool_input:
        event["file_path"] = tool_input["file_path"]
    elif "path" in tool_input:
        event["file_path"] = tool_input["path"]

    log_dir = Path(".chat-retro-runtime/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "debug.jsonl"

    with open(log_file, "a") as f:
        f.write(json.dumps(event, default=str) + "\n")

    return {}


async def persist_task_results(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    """Auto-persist structured analysis results from Task tool completions.

    When a subagent (Task tool) completes with analysis results,
    attempts to extract and persist structured data to state files.
    This enables cache reuse in subsequent runs.
    """
    if input_data.get("tool_name") != "Task":
        return {}

    tool_response = input_data.get("tool_response", "")
    if not tool_response or not isinstance(tool_response, str):
        return {}

    # Log task completion for analysis
    log_dir = Path(".chat-retro-runtime/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    task_log = {
        "timestamp": datetime.now().isoformat(),
        "session": input_data.get("session_id"),
        "tool_use_id": tool_use_id,
        "response_length": len(tool_response),
        "has_json": "{" in tool_response and "}" in tool_response,
    }

    log_file = log_dir / "task-completions.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(task_log) + "\n")

    # Attempt to extract JSON from response
    # Look for JSON blocks (common in agent outputs)
    import re

    json_pattern = re.compile(r"```json\s*([\s\S]*?)\s*```|(\{[\s\S]*\})")
    matches = json_pattern.findall(tool_response)

    for match in matches:
        json_str = match[0] or match[1]
        if not json_str:
            continue

        try:
            data = json.loads(json_str)

            # Check if this looks like topic/pattern data
            if isinstance(data, dict):
                if "topics" in data or "topic_clusters" in data:
                    _persist_topics(data)
                elif "patterns" in data:
                    _persist_patterns(data)
        except json.JSONDecodeError:
            continue

    return {}


def _persist_topics(data: dict[str, Any]) -> None:
    """Persist extracted topic data to topics.json."""
    state_dir = Path(".chat-retro-runtime/state")
    state_dir.mkdir(parents=True, exist_ok=True)

    topics_file = state_dir / "topics.json"

    # Merge with existing if present
    existing = {}
    if topics_file.exists():
        try:
            existing = json.loads(topics_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # Update with new data
    existing.update(data)
    existing["last_updated"] = datetime.now().isoformat()

    topics_file.write_text(json.dumps(existing, indent=2, default=str))


def _persist_patterns(data: dict[str, Any]) -> None:
    """Persist extracted pattern data to analysis.json."""
    from chat_retro.state import Pattern, StateManager

    manager = StateManager()
    state = manager.load()
    if state is None:
        return

    # Parse and merge patterns
    new_patterns = []
    for p in data.get("patterns", []):
        try:
            pattern = Pattern.model_validate(p)
            new_patterns.append(pattern)
        except Exception:
            continue

    if new_patterns:
        state.patterns = manager.merge_patterns(state.patterns, new_patterns)
        manager.save(state)


# Environment variable toggle for debug logging
_DEBUG_LOGGING = os.environ.get("CHAT_RETRO_DEBUG", "").lower() in ("1", "true", "yes")

# Hook matchers for SDK configuration
_post_hooks = [audit_logger, state_mutation_logger, persist_task_results]
if _DEBUG_LOGGING:
    _post_hooks.append(debug_logger)

HOOK_MATCHERS = {
    "PreToolUse": [
        HookMatcher(matcher="Write|Edit", hooks=[block_external_writes]),
    ],
    "PostToolUse": [
        HookMatcher(hooks=_post_hooks),
    ],
}
