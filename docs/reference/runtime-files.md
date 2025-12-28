# Runtime Files Reference

Chat-retro creates runtime files in `.chat-retro/` and `outputs/`.

## Directory Structure

```
./
├── state.json              # Analysis state (patterns, preferences)
├── state.json.corrupt      # Backup of invalid state (if corruption detected)
├── .chat-retro/
│   ├── audit.log           # Privacy-safe tool usage log
│   ├── state-mutations.log # Edit operations on state.json
│   ├── debug.log           # Full debug log (if CHAT_RETRO_DEBUG=1)
│   ├── metrics.jsonl       # Session usage metrics
│   ├── sessions/
│   │   └── latest.json     # Most recent session ID
│   ├── issues/             # Local issue reports
│   │   └── issue_*.json
│   └── feedback/           # User feedback data
│       └── feedback_*.json
└── outputs/                # Generated artifacts
    └── *.html, *.md
```

## Log Files

### audit.log

JSONL format. One entry per tool call. Privacy-safe (hashed paths).

```json
{"timestamp": "...", "tool": "Read", "session": "...", "file_hash": "f63808aa"}
```

See [hooks.md](hooks.md#audit_logger-posttooluse).

### state-mutations.log

JSONL format. Tracks Edit calls to state.json.
Useful for understanding state update efficiency.

```json
{"timestamp": "...", "session": "...", "old_string_len": 150, "new_string_len": 200}
```

### debug.log

JSONL format. Full tool input/output. Created when `CHAT_RETRO_DEBUG=1`.

**Contains sensitive data.** Do not commit.

```json
{"timestamp": "...", "tool": "Read", "tool_input": {...}, "tool_response": {...}}
```

### metrics.jsonl

JSONL format. Session usage metrics. Written at end of each session.

```json
{
  "session_id": "...",
  "cost_usd": 1.20,
  "tokens": {"input": 100, "output": 1804, "cache_read": 50000},
  "turns": 5,
  "errors": []
}
```

## Session Storage

### sessions/latest.json

```json
{"session_id": "d72c97bd-953d-47f7-bfb0-86f9eed5e73a"}
```

Used for `--resume` functionality.

## Issues and Feedback

### issues/issue_*.json

Local issue reports created by `--report-bug` or auto-generated on state corruption.

```json
{
  "title": "Bug title",
  "description": "Description",
  "category": "bug",
  "context": {},
  "timestamp": "2025-12-28T10:00:00",
  "reported": false
}
```

List with: `chat-retro --list-issues`

### feedback/feedback_*.json

User feedback collected during sessions via the eval module.

## State File

### state.json

Pydantic-validated analysis state. Schema version 1.

```json
{
  "schema_version": 1,
  "meta": {
    "created": "2025-01-01T00:00:00",
    "last_updated": "2025-01-01T12:00:00",
    "conversation_count": 100,
    "export_format": "chatgpt"
  },
  "patterns": [...],
  "user_preferences": {...},
  "snapshots": [...]
}
```

See `src/chat_retro/state.py` for full schema.

### state.json.corrupt

Created when state.json fails validation. Contains the original invalid content for debugging. An issue is auto-created in `.chat-retro/issues/`.
