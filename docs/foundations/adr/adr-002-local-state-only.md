# ADR-002: Local State Only

| Status | Date |
|--------|------|
| Accepted | 2025-12-27 |

## Context

The project needs to persist state between analysis sessions:
- Discovered patterns and their metadata
- User preferences (focus areas, visualization preferences)
- Historical snapshots for comparison

Claude's memory system could store some of this automatically. This ADR documents the explicit decision not to use it.

## Decision

All analysis state is stored locally on the user's machine. Claude's memory system is not used.

## Rationale

### Data Sovereignty

Patterns derived from personal conversations are sensitive data. Examples:
- Topic clusters reveal interests and concerns
- Temporal patterns reveal work habits
- Thread detection reveals ongoing projects

User should control retention and deletion of this derived data.

### Transparency

| Storage | Inspectability |
|---------|----------------|
| Local JSON file | User can open, read, edit, delete |
| Claude memory | Opaque; user cannot easily audit |

### Portability

Local state can be:
- Backed up with other personal data
- Version controlled (if desired)
- Deleted completely and verifiably
- Migrated to different tools

### Session Isolation

Each project's analysis is self-contained. No risk of cross-contamination between different users or different analysis projects.

## Implementation

### Storage Location

Project-local (in the working directory where `chat-retro` is invoked):

```
./
├── state.json              # Analysis state
├── .chat-retro/            # Internal files
│   └── sessions/           # Session resumption data
└── outputs/
    ├── 2025-06.html        # Versioned artifacts
    └── 2025-09.html
```

### State Schema

```json
{
  "meta": {
    "created": "2025-06-15",
    "last_updated": "2025-09-20",
    "conversation_count": 847,
    "date_range": ["2024-01-01", "2025-09-15"]
  },
  "patterns": [...],
  "user_preferences": {
    "focus_areas": [],
    "preferred_viz": null
  },
  "snapshots": [...]
}
```

### Session Start

Agent loads state file explicitly at session start. No automatic memory retrieval.

## Trade-offs Accepted

| Trade-off | Mitigation |
|-----------|------------|
| No automatic recall across sessions | State file loaded explicitly |
| User must maintain state file | Standard filesystem; familiar pattern |
| Preferences not shared across projects | By design; each analysis is isolated |

## Alternatives Considered

### Hybrid: Memory for Preferences, Local for Patterns

Could store lightweight preferences (e.g., "prefers timeline view") in Claude memory while keeping sensitive pattern data local.

**Rejected because:**
- Adds complexity (two storage systems)
- Preferences are lightweight enough to store alongside patterns
- Unclear boundary between "sensitive" and "non-sensitive" derived data

### Full Claude Memory Integration

**Rejected because:**
- Derived patterns are sensitive
- User cannot inspect or delete selectively
- Violates data sovereignty principle

## Consequences

### Positive

- User has full control over derived data
- Transparent, inspectable storage
- Portable and deletable
- No dependency on Claude memory system

### Negative

- Agent doesn't "just remember" across sessions
- User responsible for state file (backup, migration)
- Slightly more friction at session start

## References

- [ADR-001: Agentic Architecture](adr-001-agentic-architecture.md)
