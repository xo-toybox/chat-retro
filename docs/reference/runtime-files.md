# Runtime Files

All runtime data lives in `.chat-retro-runtime/`.

## Overview

| File | Purpose | Lifecycle | Git |
|------|---------|-----------|-----|
| `state/analysis.json` | Analysis state | Persistent | Ignored |
| `logs/audit.jsonl` | Tool usage | Append | Tracked |
| `logs/debug.jsonl` | Full I/O | Per session | Ignored |
| `logs/metrics.jsonl` | Costs | Append | Tracked |
| `resume-session.json` | Resume | Overwritten | Ignored |
| `issues/` | Bug reports | Persistent | Ignored |
| `feedback/` | Ratings | Persistent | Ignored |
| `outputs/` | Artifacts | User-managed | Ignored |

## Directory Structure

```
.chat-retro-runtime/
├── state/
│   ├── analysis.json         # Pydantic-validated state
│   └── analysis.json.corrupt # Backup on validation failure
├── logs/
│   ├── audit.jsonl           # Tool usage (hashed paths)
│   ├── debug.jsonl           # Full I/O (CHAT_RETRO_DEBUG=1)
│   └── metrics.jsonl         # Session costs
├── resume-session.json       # Current session ID
├── issues/                   # Bug reports
├── feedback/                 # Quality ratings
└── outputs/                  # Generated HTML artifacts
```

## Privacy Model

**Privacy-first:** The `.gitignore` ignores all runtime data by default, then whitelists only safe files.

Pattern: whitelist dir → ignore contents → whitelist safe files only.

### What's tracked

| Files | Why safe |
|-------|----------|
| `logs/audit.jsonl` | Hashed paths, no content |
| `logs/metrics.jsonl` | Cost/token counts only |
| `*/.gitkeep` | Structure preservation |

### What's ignored

Everything else, including:
- `state/` — conversation analysis
- `logs/debug.jsonl` — full tool I/O
- `resume-session.json` — session IDs
- `outputs/*`, `issues/*`, `feedback/*` — may contain sensitive context

## File Details

### state/analysis.json

Core analysis state. Pydantic-validated, schema version 1.

```json
{"schema_version": 1, "meta": {...}, "patterns": [...], "user_preferences": {...}}
```

See `src/chat_retro/state.py` for full schema.

### Logs

All logs use JSONL format (one JSON object per line).

**audit.jsonl** — Tool usage with hashed paths
```json
{"timestamp": "...", "tool": "Read", "session": "...", "file_hash": "f63808aa"}
```

**debug.jsonl** — Full tool I/O (requires `CHAT_RETRO_DEBUG=1`)
```json
{"timestamp": "...", "tool": "Read", "tool_input": {...}, "tool_response": {...}}
```

**metrics.jsonl** — Session costs
```json
{"session_id": "...", "cost_usd": 1.20, "tokens": {"input": 100, "output": 1804}}
```

### resume-session.json

Current session ID for `--resume` functionality.

```json
{"session_id": "d72c97bd-953d-47f7-bfb0-86f9eed5e73a"}
```

### issues/, feedback/

Bug reports and user feedback. Created by `--report-bug` or eval module.

Review content before committing — may contain sensitive context.
