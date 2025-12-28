# Hooks Reference

Chat-retro uses Claude Agent SDK hooks for audit logging, write protection, and schema validation.

## Configuration

Hooks are configured in `src/chat_retro/hooks.py` via `HOOK_MATCHERS`:

```python
HOOK_MATCHERS = {
    "PreToolUse": [
        HookMatcher(matcher="Write|Edit", hooks=[block_external_writes]),
        HookMatcher(matcher="Write", hooks=[validate_state_json_write]),
    ],
    "PostToolUse": [
        HookMatcher(hooks=[audit_logger, state_mutation_logger]),
        # debug_logger added when CHAT_RETRO_DEBUG=1
    ],
}
```

## Available Hooks

### audit_logger (PostToolUse)

Privacy-safe logging of tool usage. Logs to `.chat-retro/audit.log`.

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
- `./outputs/` - Generated artifacts
- `./state.json` - Analysis state
- `./.chat-retro/` - Runtime data

Uses `Path.resolve()` and `is_relative_to()` to prevent path traversal attacks.

### validate_state_json_write (PreToolUse)

Validates state.json content before allowing writes. Catches schema violations at write time.

**Checks:**
- Valid JSON syntax
- Required `schema_version` key
- Required `meta` key
- `patterns` is a list (not dict)
- Pattern `confidence` between 0.0 and 1.0
- Pattern `type` is one of: theme, temporal, behavioral, other

### state_mutation_logger (PostToolUse)

Tracks Edit operations on state.json for efficiency analysis.
Logs to `.chat-retro/state-mutations.log`.

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

Logs to `.chat-retro/debug.log` with full `tool_input` and `tool_response`.

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
