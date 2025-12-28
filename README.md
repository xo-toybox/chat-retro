# Chat Retrospective

Explore your AI conversation history with an agentic approach. The agent proposes patterns, you guide focus, output emerges from collaboration.

## Usage

```bash
uv sync
uv run chat-retro ./conversations.json
uv run chat-retro ./conversations.json --resume SESSION_ID
```

Supports ChatGPT and Claude (planned) export formats.

## Features

Agentic analysis with [specialized subagents](docs/reference/agents.md): topic extraction, sentiment tracking, pattern detection, temporal analysis, and insight generation.

### Visualizations
- **Timeline**: D3.js area chart of conversation frequency
- **Heatmap**: 7x24 grid showing usage by hour/weekday
- **Topic Clusters**: Force-directed graph of topic relationships
- **Length Distribution**: Histogram with statistics

### Interactive Artifacts
- Filter panel (date, topic, sentiment)
- Full-text search with highlighting
- Click-to-expand detail view
- Annotations with localStorage persistence

### Feedback Collection
- Quality prompts after analysis
- Pattern rating (1-5 or thumbs)
- Gap detection for missing features

## How It Works

Uses Claude Agent SDK with built-in tools (Read, Grep, Glob, Bash, Write, Edit). Agent explores raw JSON exports directly with no preprocessing. State persists locally in `.chat-retro-runtime/`. Generated artifacts are self-contained HTML with inlined D3.js.

## Issue Workflow

Automated issue management via agentic pipeline:

```bash
issue-workflow report-bug    # Create draft issue interactively
issue-workflow drafts        # View pending drafts
issue-workflow process       # Run full pipeline (triage → cluster → prioritize → resolve)
```

Human gates at prioritization and low-confidence resolution. See [ADR-005](docs/foundations/adr/adr-005-agentic-issue-workflow.md). See reference doc for additional commands and details.

## Structure

```
src/
├── chat_retro/              # Product
│   ├── __main__.py          # CLI entry point
│   ├── session.py           # Claude SDK wrapper
│   ├── state.py             # Pydantic models
│   ├── prompts.py           # System prompts
│   ├── agents.py            # Analysis subagents
│   ├── insights.py          # Insight generators
│   ├── eval.py              # Feedback collection
│   └── viz_templates/       # D3.js visualizations
├── issue_workflow/          # Issue pipeline tool
│   ├── agents.py            # Triage/cluster/prioritize/resolve
│   ├── workflow.py          # Pipeline orchestration
│   └── cli.py               # CLI entry point
└── shared/                  # Common types
    ├── issue_types.py       # Issue, IssueCluster, IssueState
    └── issue_reporter.py    # Auto/manual issue reporting
```

Runtime files: `.chat-retro-runtime/` (see [runtime-files.md](docs/reference/runtime-files.md))

## Development

```bash
uv sync                    # Install dependencies
uv run pytest              # Run tests (253 passing)
uv run pyright             # Type check
```

## Documentation

**Foundations** — Curated decisions (stable)
- [Spec](docs/foundations/spec.md) - Product requirements
- [ADRs](docs/foundations/adr/) - Architecture decisions

**Iteration** — Current development phase (evolving)
- [Design](docs/iteration/design.md) - System design
- [Implementation Plan](docs/iteration/impl-plan.md) - Build phases
- [Design Review](docs/iteration/design-review-checklist.md) - Review checklist

**Reference** — API docs (update with code)
- [Agents](docs/reference/agents.md) - Subagent definitions
- [Hooks](docs/reference/hooks.md) - SDK hooks
- [Runtime Files](docs/reference/runtime-files.md) - Logs and state
- [Issue Reporting](docs/reference/issue-reporting.md) - Auto/manual issue drafts
