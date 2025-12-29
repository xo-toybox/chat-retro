# Chat Retrospective

Your AI conversation history is more revealing than you realize. Not just what you asked, but what you asked repeatedly, what you avoided. This tool surfaces those patterns: the shape of how you think.

## Why This Exists

ChatGPT's "Your Year with ChatGPT" summarizes usage into themed cards: topics by volume, limericks from keywords, broad archetypes. It's charming, but personalized to activity, not identity. This tool goes somewhere different: emergent dimensions (depth-vs-breadth, theory-vs-practice, consumption-vs-creation), contradictions between aspiration and practice, gaps you haven't noticed. The value isn't seeing what you talked about. It's seeing how you think.

## Status

First functional version complete for self-exploration. Built with continuous feedback loop (test → issue → implement) and iterative optimization for token costs and content reuse. No plans for further polish.

Note: SDK-reported `total_cost_usd` seems unreliable (seeing lots of overstatement). Maybe cache_read discount not applied? 

## Design Decisions

**Emergent over prescribed.** Fixed classification finds only patterns it anticipates. The agent proposes what it sees; you guide where to look deeper. Categories emerge from collaboration, not configuration.

**Agentic search over embeddings.** For bounded datasets, Claude reasoning over grep/jq outperforms RAG pipelines. Simpler stack, better results. Reasoning over raw data surfaces correlations embeddings miss: repeated topics across sessions, source-type progressions, quantity-as-signal patterns.

**Production-grade privacy.** Derived patterns reveal things source conversations don't explicitly contain: topic clusters, temporal habits, recurring avoidances. This derived layer needs its own privacy model. All state stays local, but that's insufficient when the agent has Write/Edit capabilities. Three layers of protection:
1. subagents are defined with read-only tools;
2. a PreToolUse hook validates all write paths against an allowlist, using resolved paths to prevent traversal;
3. audit logging hashes file paths to preserve privacy while enabling debugging.

**Human gates at judgment points.** Automation should be autonomous for mechanical steps, but pause for human approval at judgment calls. The issue workflow pipeline embodies this: triage and clustering run automatically; prioritization ranking and low-confidence resolution plans require sign-off. This is an opinionated stance—full automation is possible but trades away accountability.

**Eval-based iteration over intuitive editing.** Agent output is non-deterministic; comparing outputs requires running both versions against the same data. Register prompt variants as separate templates, evaluate on explicit criteria, promote or discard. This preserves baselines, enables A/B testing, and prevents the loss of working prompts to speculative edits.

## Usage
```bash
uv sync
uv run chat-retro conversations.json                       # Free exploration
uv run chat-retro conversations.json -t self-portrait      # Guided analysis with template
uv run chat-retro conversations.json --resume SESSION_ID   # Resume session
```

Supports ChatGPT and Claude (planned) export formats.

## Features

Uses Claude Agent SDK with built-in tools (Read, Grep, Glob, Bash, Write, Edit). Agent explores raw JSON exports directly with no preprocessing. State persists locally in `.chat-retro-runtime/`. Generated artifacts are self-contained HTML with inlined D3.js.

[Specialized subagents](docs/reference/agents.md) for topic extraction, sentiment tracking, pattern detection, temporal analysis, and insight generation.

**Visualizations**: Timeline (D3.js area chart), heatmap (hour/weekday), topic clusters (force-directed graph), length distribution.

**Interactive artifacts**: Filter panel, full-text search, click-to-expand detail, annotations.

**Feedback collection**: Quality prompts, pattern ratings, gap detection.

## Issue Workflow

Automated issue management via agentic pipeline:
```bash
issue-workflow report-bug    # Create draft issue interactively
issue-workflow drafts        # View pending drafts
issue-workflow process       # Run full pipeline (triage → cluster → prioritize → resolve)
```

See [ADR-005](docs/foundations/adr/adr-005-agentic-issue-workflow.md) for architecture details.

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
│   ├── agents.py            # Agent definitions
│   ├── runner.py            # Claude Code CLI runner
│   ├── workflow.py          # Pipeline orchestration
│   └── cli.py               # CLI entry point
└── shared/                  # Common types
```

Runtime files: `.chat-retro-runtime/` (see [runtime-files.md](docs/reference/runtime-files.md))

## Development
```bash
uv sync                    # Install dependencies
uv run pytest              # Run tests
uv run pyright             # Type check
```

## Documentation

**Foundations**: [Spec](docs/foundations/spec.md) · [ADRs](docs/foundations/adr/)

**Iteration**: [Design](docs/iteration/design.md) · [Implementation Plan](docs/iteration/impl-plan.md) · [Design Review](docs/iteration/design-review-checklist.md) · [Self-Portrait v2 Eval](docs/iteration/self-portrait-v2-eval.md)

**Reference**: [Agents](docs/reference/agents.md) · [Hooks](docs/reference/hooks.md) · [Runtime Files](docs/reference/runtime-files.md) · [Issue Reporting](docs/reference/issue-reporting.md)