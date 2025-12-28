"""Hooks for audit logging, write protection, and state mutation tracking."""


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
    log_file = log_dir / "audit.jsonl"

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


def _deny_write(reason: str) -> dict[str, Any]:
    """Helper to create a deny response for PreToolUse hooks."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


async def validate_state_json_write(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    """Validate state.json writes match expected schema before allowing.

    Catches schema violations at write time rather than on next load.
    """
    if input_data.get("hook_event_name") != "PreToolUse":
        return {}

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Write":
        return {}

    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")

    if "analysis.json" not in str(file_path):
        return {}

    content = tool_input.get("content", "")
    if not content:
        return {}

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return _deny_write(f"analysis.json content is not valid JSON: {e}")

    # Validate required top-level structure
    if "schema_version" not in data:
        return _deny_write("analysis.json missing required 'schema_version' key")

    if "meta" not in data:
        return _deny_write("analysis.json missing required 'meta' key")

    if "patterns" in data and not isinstance(data["patterns"], list):
        return _deny_write(
            "analysis.json 'patterns' must be a list, not a "
            f"{type(data['patterns']).__name__}"
        )

    # Validate patterns if present
    patterns = data.get("patterns", [])
    for i, pattern in enumerate(patterns):
        if not isinstance(pattern, dict):
            return _deny_write(f"analysis.json patterns[{i}] must be an object")

        confidence = pattern.get("confidence")
        if confidence is not None:
            if not isinstance(confidence, (int, float)):
                return _deny_write(
                    f"analysis.json patterns[{i}].confidence must be a number"
                )
            if not (0.0 <= confidence <= 1.0):
                return _deny_write(
                    f"analysis.json patterns[{i}].confidence={confidence} "
                    "must be between 0.0 and 1.0"
                )

        pattern_type = pattern.get("type")
        valid_types = ("theme", "temporal", "behavioral", "other")
        if pattern_type is not None and pattern_type not in valid_types:
            return _deny_write(
                f"analysis.json patterns[{i}].type='{pattern_type}' "
                f"must be one of: {valid_types}"
            )

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


# Environment variable toggle for debug logging
_DEBUG_LOGGING = os.environ.get("CHAT_RETRO_DEBUG", "").lower() in ("1", "true", "yes")

# Hook matchers for SDK configuration
_post_hooks = [audit_logger, state_mutation_logger]
if _DEBUG_LOGGING:
    _post_hooks.append(debug_logger)

HOOK_MATCHERS = {
    "PreToolUse": [
        HookMatcher(matcher="Write|Edit", hooks=[block_external_writes]),
        HookMatcher(matcher="Write", hooks=[validate_state_json_write]),
    ],
    "PostToolUse": [
        HookMatcher(hooks=_post_hooks),
    ],
}
