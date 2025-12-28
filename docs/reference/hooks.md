# Hooks Reference

Chat-retro uses Claude Agent SDK hooks for audit logging and write protection.

## Configuration

Hooks are configured in `src/chat_retro/hooks.py` via `HOOK_MATCHERS`:

```python
HOOK_MATCHERS = {
    "PreToolUse": [
        HookMatcher(matcher="Write|Edit", hooks=[block_external_writes]),
    ],
    "PostToolUse": [
        HookMatcher(hooks=[audit_logger, state_mutation_logger]),
        # debug_logger added when CHAT_RETRO_DEBUG=1
    ],
}
```

## Available Hooks

### audit_logger (PostToolUse)

Privacy-safe logging of tool usage. Logs to `.chat-retro-runtime/logs/debug_audit.jsonl`.

**Output format:**
```json
{
  "timestamp": "2025-12-28T11:06:42.868772",
  "tool": "Read",
  "session": "d72c97bd-953d-47f7-bfb0-86f9eed5e73a",
  "file_hash": "f63808aa"
}
```

**Privacy guarantees:**
- File paths are SHA256-hashed (first 8 chars)
- Tool input/output content is NOT logged
- Session ID logged for correlation only

### block_external_writes (PreToolUse)

Prevents writes outside allowed paths. Applied to `Write` and `Edit` tools.

**Allowed paths:**
- `./.chat-retro-runtime/` - All runtime data (state, outputs, logs, tmp)

Uses `Path.resolve()` and `is_relative_to()` to prevent path traversal attacks.

### state_mutation_logger (PostToolUse)

Tracks Edit operations on state.json for efficiency analysis.
Logs to `.chat-retro-runtime/logs/state-mutations.jsonl`.

**Output format:**
```json
{
  "timestamp": "2025-12-28T11:09:25.618501",
  "session": "d72c97bd-953d-47f7-bfb0-86f9eed5e73a",
  "old_string_len": 150,
  "new_string_len": 200,
  "tool_use_id": "toolu_01234"
}
```

### debug_logger (PostToolUse, optional)

Full tool input/output capture for debugging. Enable via environment variable:

```bash
CHAT_RETRO_DEBUG=1 chat-retro ./conversations.json
```

**WARNING:** Contains potentially sensitive data. Only use during development.

Logs to `.chat-retro-runtime/logs/debug.jsonl` with full `tool_input` and `tool_response`.

## Adding Custom Hooks

Hook function signature:

```python
async def my_hook(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    # For PostToolUse: return {} (no-op)
    # For PreToolUse: return {} to allow, or:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Explanation here",
        }
    }
```

Add to `HOOK_MATCHERS` in `hooks.py`:

```python
HOOK_MATCHERS = {
    "PreToolUse": [
        HookMatcher(matcher="ToolName", hooks=[my_hook]),
    ],
    ...
}
```

See [Claude Agent SDK documentation](https://docs.anthropic.com/en/docs/claude-code/hooks) for full hook API.
