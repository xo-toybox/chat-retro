# ADR-005: Agentic Issue Workflow

| Status | Date |
|--------|------|
| Accepted | 2025-12-28 |

## Context

The project needed issue tracking for bug reports and improvements. Initial design was a simple single-issue workflow with manual steps.

**Requirements changed:**
- Need batch processing across multiple issues
- Want automated deduplication and clustering
- Prefer minimal human involvement (gates only for key decisions)
- Issues contain sensitive context that shouldn't be committed

## Decision Drivers

1. **Batch efficiency**: Processing issues one-by-one is slow and misses connections
2. **Pattern detection**: Related issues should be grouped for efficient resolution
3. **Privacy model**: Raw drafts may contain sensitive data; public issues must be sanitized
4. **Automation level**: Maximize agent autonomy while preserving human control for design decisions

## Decision

Implement an agentic issue workflow as a **separate tool** with shared schema, using specialized agents for each lifecycle stage with selective human gates.

## Approach

### Separate Tool with Shared Schema

```
src/
├── chat_retro/           # Product (online)
│   └── eval.py           # Creates drafts using shared schema
├── issue_workflow/       # Separate tool (offline)
│   ├── agents.py         # Specialized workflow agents
│   ├── workflow.py       # Pipeline orchestration
│   └── cli.py            # Standalone CLI
└── shared/               # Common types
    └── issue_types.py    # Issue, IssueCluster, IssueState
```

**Why separate:**
- Workflow runs offline, product runs online — different modes
- Only coupling is the Issue schema (shared types)
- Subcommand architecture doesn't benefit non-dev users
- Clearer separation of concerns

### Lifecycle Stages

```
draft → triaged → clustered → prioritized → in_progress → resolved
                                         ↘ deferred / wont_fix
```

| Stage | Agent | Human Gate |
|-------|-------|------------|
| draft → triaged | Triage Agent | No |
| triaged → clustered | Clustering Agent | No |
| clustered → prioritized | Prioritization Agent | **Yes** - approve ranking |
| prioritized → in_progress | - | **Yes** - select clusters |
| in_progress → resolved | Resolution Agent | Conditional |

### Specialized Agents

Four focused agents handle the workflow:

| Agent | Responsibility | Tools |
|-------|----------------|-------|
| **Triage** | Sanitize, deduplicate, identify affected files | Read, Grep, Glob |
| **Clustering** | Group by affected files, generate themes | Read, Grep, Glob |
| **Prioritization** | Score severity, complexity, compute rankings | Read, Grep, Glob |
| **Resolution** | Analyze root cause, implement or propose fixes | Read, Grep, Glob, Write, Edit, Bash |

### Confidence-Based Resolution

Resolution agent decides autonomy level:
- **High confidence** (clear bug, obvious fix): Auto-implement
- **Low confidence** (design choices, unclear scope): Generate plan for human approval

### Privacy Model

Two-tier storage:
- `issue-drafts/` — Raw drafts with sensitive context (gitignored)
- `issues/` — Sanitized public issues (tracked)

Sanitization removes:
- User-specific paths (`/Users/xxx/`)
- Conversation excerpts
- PII and personal data

### Clustering Strategy

Primary signal: **affected files**
- Issues touching same files cluster together
- Secondary: error patterns, category overlap
- Threshold configurable (default 0.7 similarity)

### CLI Design

Single pipeline command for typical use:

```bash
issue-workflow process       # Full pipeline with human gates
```

Management commands for manual control:

```bash
issue-workflow list [--status X]
issue-workflow clusters
issue-workflow approve <cluster-id>
issue-workflow defer <id>
issue-workflow wontfix <id>
issue-workflow report-bug    # Interactive draft creation
issue-workflow drafts        # View pending drafts
```

## Consequences

### Positive

- **Batch efficiency**: Process all drafts in one run
- **Connection discovery**: Clustering finds related issues automatically
- **Privacy preservation**: Drafts stay private, public issues are sanitized
- **Minimal friction**: Human gates only at decision points
- **Clean separation**: Product and workflow are independent tools

### Negative

- **Complexity**: More code than simple issue storage
- **Agent cost**: Each pipeline step uses API calls
- **Learning curve**: Users must understand lifecycle stages
- **Two tools**: Separate CLI commands for product vs workflow

### Neutral

- **Human gates required**: Can't fully automate due to design decisions
- **Clustering heuristics**: May need tuning for different codebases

## Alternatives Considered

| Option | Verdict |
|--------|---------|
| Subcommand in chat-retro | Rejected: workflow is offline/dev-only, doesn't belong in product |
| Single-issue workflow | Rejected: doesn't scale, misses connections |
| Full automation (no gates) | Rejected: design decisions need human input |
| Manual clustering | Rejected: tedious and error-prone |
| External issue tracker | Rejected: adds dependency, loses local-first model |
| Draft creation in chat-retro | Moved: `report-bug`/`drafts` moved to issue-workflow for cohesion |

## References

- [ADR-001: Agentic Architecture](adr-001-agentic-architecture.md) - Foundation for agent-based design
- [ADR-002: Local State Only](adr-002-local-state-only.md) - Privacy model foundation
