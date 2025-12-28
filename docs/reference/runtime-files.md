# Runtime Files

All runtime data lives in `.chat-retro-runtime/`.

## Overview

| File | Purpose | Lifecycle | Git |
|------|---------|-----------|-----|
| `state/analysis.json` | Analysis state | Persistent | Ignored |
| `logs/debug_audit.jsonl` | Tool traces | Append | Ignored |
| `logs/debug.jsonl` | Full I/O | Per session | Ignored |
| `logs/metrics.jsonl` | Costs | Append | Tracked |
| `resume-session.json` | Resume | Overwritten | Ignored |
| `issue-drafts/` | Raw issue drafts | Persistent | Ignored |
| `issues/` | Public issues | Persistent | Tracked |
| `issue-state.json` | Workflow state | Persistent | Ignored |
| `feedback/` | Ratings | Persistent | Ignored |
| `outputs/` | Artifacts | User-managed | Ignored |
| `tmp/` | Temporary scripts | Ephemeral | Ignored |

## Directory Structure

```
.chat-retro-runtime/
├── state/
│   ├── analysis.json         # Pydantic-validated state
│   └── analysis.json.corrupt # Backup on validation failure
├── logs/
│   ├── debug_audit.jsonl     # Tool traces (public, not tracked)
│   ├── debug.jsonl           # Full I/O (CHAT_RETRO_DEBUG=1)
│   └── metrics.jsonl         # Session costs
├── resume-session.json       # Current session ID
├── issue-drafts/             # Raw drafts (private)
│   └── draft_*.json
├── issues/                   # Public issues (sanitized)
│   ├── issue_*.json
│   └── CHANGELOG.md
├── issue-state.json          # Workflow state
├── feedback/                 # Quality ratings
├── outputs/                  # Generated HTML artifacts
└── tmp/                      # Temporary analysis scripts
```

## Privacy Model

**Privacy-first:** The `.gitignore` ignores all runtime data by default, then whitelists only safe files.

Pattern: whitelist dir → ignore contents → whitelist safe files only.

### What's tracked

| Files | Why safe |
|-------|----------|
| `logs/metrics.jsonl` | Cost/token counts only |
| `issues/issue_*.json` | Sanitized (no PII/context) |
| `issues/CHANGELOG.md` | Resolution history |
| `*/.gitkeep` | Structure preservation |

### Public but excluded

Files prefixed with `debug_` are safe to share but not useful for collaboration:

| Files | Why excluded |
|-------|--------------|
| `logs/debug_*.jsonl` | Tool traces — useful for local debugging, not for sharing |

### What's ignored

Everything else, including:
- `state/` — conversation analysis
- `logs/debug.jsonl` — full tool I/O
- `resume-session.json` — session IDs
- `issue-drafts/*` — raw drafts with sensitive context
- `issue-state.json` — workflow state with cluster info
- `outputs/*`, `feedback/*` — may contain sensitive context

## File Details

### state/analysis.json

Core analysis state. Pydantic-validated, schema version 1.

```json
{"schema_version": 1, "meta": {...}, "patterns": [...], "user_preferences": {...}}
```

See `src/chat_retro/state.py` for full schema.

### Logs

All logs use JSONL format (one JSON object per line).

**debug_audit.jsonl** — Tool traces (public but not tracked)
```json
{"timestamp": "...", "tool": "Read", "session": "..."}
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

### Issue Workflow

Issues follow a draft → public workflow:

```
draft → triaged → clustered → prioritized → resolved
```

**issue-drafts/** — Raw drafts with sensitive context (private)
```json
{"id": "abc123", "title": "...", "description": "...", "context": {...}}
```

**issues/** — Sanitized public issues (tracked)
```json
{"id": "abc123", "title": "...", "description": "...", "severity": "high"}
```

**issues/CHANGELOG.md** — Resolution history
```markdown
## 2025-01-15
- **abc123**: Fixed state validation for schema v2
```

**issue-state.json** — Workflow state (clusters, rankings)

See `src/shared/issue_types.py` for full schema.

CLI: `issue-workflow process` (separate tool)

### feedback/

User feedback and quality ratings. Created by eval module.

Review content before committing — may contain sensitive context.
