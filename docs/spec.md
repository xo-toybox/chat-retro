# Chat Retrospective

## Overview

Your conversation history captures your curiosities, uncertainties, and working problems.

Chat Retrospective explores your exported conversations with you, surfacing patterns in what you reached for, how you framed problems, and what threads you kept returning to.

### What You Can Get

The output is whatever serves your goals:

**Visualization**: An explorable artifact showing conversation patterns over time, topic clusters, usage trends.

**Reflection**: 
- AI usage: Archetype describing how you use AI. Awards for distinctive patterns. Top themes ranked.
- Life narrative: What you were working on each quarter. How your interests shifted. Challenges you faced and how you approached them. Evolution of your thinking on topics you kept returning to.
- Creative: A poem capturing your year. A letter to your past or future self.

**Learning**: Communication patterns you could improve. Prompting habits that work well or poorly. Wisdom distilled from your interactions, formatted as notes to bring back into your chat workflow.

The agent works like an analyst: it proposes what it sees, you redirect based on what matters to you, and the output reflects that collaboration.

## Interaction Model

1. User provides export file
2. Agent samples, explores, proposes initial patterns
3. User guides: "focus here" / "go deeper" / "what about?"
4. Agent refines analysis and generates outputs
5. User requests specific artifacts (visualization, poem, insights, etc.)

### Session Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| First analysis | No prior state | Full exploration |
| Incremental update | New data + existing state | "What's new" + update patterns |
| Full refresh | User request or significant drift | Fresh analysis, compare to prior |

## Agent Capabilities

Uses Claude Agent SDK built-in tools (Read, Grep, Glob, Bash, Write, Edit) for all core functionality. No custom MCP tools required.

See [ADR-001](adr/adr-001-agentic-architecture.md) for tooling rationale, examples, and custom component list.

### Supported Export Formats

- ChatGPT: `conversations.json` from data export
- Claude: Export format from claude.ai

Agent detects format and adapts parsing accordingly.

## Constraints

### Privacy

| Data | Handling |
|------|----------|
| Conversation exports | Local only; sent to Claude API ephemerally during analysis |
| Analysis state | Local only (`./state.json`) |
| Artifacts | Local only; user controls sharing |

Claude's memory system is explicitly not used. See [ADR-002](adr/adr-002-local-state-only.md).

### Scale

Designed for up to 10,000 conversations. Agent should sample before committing to expensive operations.

### Multi-Export Handling

Latest export is canonical. No merge logic for multiple exports; user provides most recent export each session.

## Output

| Type | Format | Examples |
|------|--------|----------|
| Visualization | HTML (self-contained) | Timeline, clusters, trends |
| Reflection | Markdown | Archetype, narrative, poem |
| Learning | Markdown | Communication insights, prompting notes |

For HTML artifacts: single file, fully self-contained, no external network requests, works offline forever. See [ADR-003](adr/adr-003-offline-artifacts.md).

### State

```
./
├── state.json      # Patterns, preferences, metadata
└── outputs/        # Generated artifacts
```

State tracks discovered patterns, user preferences, and output history across sessions.

## Invocation

```bash
chat-retro ./path/to/conversations.json
```

Python CLI using Claude Agent SDK. User interacts via terminal with streaming responses.

## Success Criteria

| Criterion | Measure |
|-----------|---------|
| Non-obvious insights | User learns something they didn't know about their patterns |
| Actionable output | Outputs serve user's stated goal, whether exploration, reflection, or learning |
| Interpretable | Agent explains its reasoning; patterns make sense |
| Collaborative | Process feels like working with an analyst, not running a script |

## Development Approach

Measure before changing. Decisions about optimization, scaffolding, or quality improvements require data, not intuition.

| Change Type | Requires First |
|-------------|----------------|
| Performance optimization | Measurements showing the bottleneck |
| Caching, batching, retries | Failure/latency data justifying complexity |
| Quality improvements | Eval criteria + baseline measurements |
| New features | Usage data or clear user need |

Agent output is non-deterministic. "It seems better" is not evidence.

## Design Decisions

See `/docs/adr/` for architectural decisions:

| ADR | Decision |
|-----|----------|
| [001](adr/adr-001-agentic-architecture.md) | Agentic architecture; SDK built-in tools |
| [002](adr/adr-002-local-state-only.md) | Local state only; no Claude memory integration |
| [003](adr/adr-003-offline-artifacts.md) | Self-contained offline HTML artifacts |
| [004](adr/adr-004-modal-data-safety.md) | Modal for GPU compute (contingent) |

## What This Is Not

- **Not a batch script**: Requires interaction to produce good results
- **Not a fixed taxonomy**: Patterns emerge from data, not prescribed categories
- **Not a cloud service**: Everything runs locally except Claude API calls
- **Not a replacement for reading your chats**: A tool for seeing patterns, not reproducing content

---

*See [archive/spec-v1-deterministic-pipeline.md](archive/spec-v1-deterministic-pipeline.md) for prior approach.*