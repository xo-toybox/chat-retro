"""Hooks for audit logging, write protection, and state mutation tracking."""

from __future__ import annotations

import hashlib
import json
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
    log_dir = Path(".chat-retro")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "audit.log"

    with open(log_file, "a") as f:
        f.write(json.dumps(event) + "\n")

    return {}


async def block_external_writes(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    """Prevent writes outside project directory.

    Only allows writes to:
    - ./outputs/
    - ./state.json
    - ./.chat-retro/
    """
    # Only check PreToolUse events
    if input_data.get("hook_event_name") != "PreToolUse":
        return {}

    tool_name = input_data.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        return {}

    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")

    # Normalize path for comparison
    file_path = str(file_path)

    allowed_prefixes = (
        "./outputs/",
        "outputs/",
        "./state.json",
        "state.json",
        "./.chat-retro/",
        ".chat-retro/",
    )

    if not any(file_path.startswith(p) for p in allowed_prefixes):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Write blocked: {file_path} outside allowed paths",
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

    if "state.json" not in str(file_path):
        return {}

    event = {
        "timestamp": datetime.now().isoformat(),
        "session": input_data.get("session_id"),
        "old_string_len": len(tool_input.get("old_string", "")),
        "new_string_len": len(tool_input.get("new_string", "")),
        "tool_use_id": tool_use_id,
    }

    # Write to state mutations log
    log_dir = Path(".chat-retro")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "state-mutations.log"

    with open(log_file, "a") as f:
        f.write(json.dumps(event) + "\n")

    return {}


# Hook matchers for SDK configuration
HOOK_MATCHERS = {
    "PreToolUse": [
        {"matcher": "Write|Edit", "hooks": [block_external_writes]},
    ],
    "PostToolUse": [
        {"hooks": [audit_logger, state_mutation_logger]},
    ],
}
