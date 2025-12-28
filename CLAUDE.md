# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chat Retrospective is a personal analysis tool that explores exported AI conversation history (ChatGPT, Claude) using an agentic approach. The agent proposes patterns, the user guides focus, and output emerges from collaboration.

**Current state**: Design phase. No implementation code yet.

## Commands

```bash
# Package management
uv sync                    # Install dependencies
uv run python -m chat_retro ./conversations.json  # Run (once implemented)

# Run single test
uv run pytest tests/test_state.py -k test_name

# Type checking
uv run pyright
```

## Architecture

### Key Design Decisions (see docs/adr/)

1. **Agentic over deterministic** (ADR-001): Uses Claude Agent SDK built-in tools (Read, Grep, Glob, Bash, Write, Edit, Task) directly on raw JSON exports. No custom MCP tools. Agent explores data with jq/grep rather than pre-processing.

2. **Local state only** (ADR-002): All state stored in project directory (`./state.json`, `./.chat-retro/`). No Claude memory integration. User controls all derived data.

3. **Self-contained artifacts** (ADR-003): HTML outputs inline all dependencies (D3.js ~250KB). No external network requests. Works offline forever.

### Planned Structure

```
src/chat_retro/
├── cli.py          # Entry point, user interaction loop
├── session.py      # ClaudeSDKClient wrapper, session resumption
├── state.py        # Pydantic models for state.json
├── hooks.py        # Audit logging, write protection
├── artifacts.py    # HTML bundler with D3.js inlining
└── prompts.py      # System prompts
```

Custom code is ~400 lines. Everything else is SDK built-in tools.

### Runtime Files (project-local)

```
./state.json              # Analysis state (patterns, preferences)
./.chat-retro/            # Sessions, audit logs
./outputs/                # Generated artifacts
```

## Documentation Hierarchy

- `docs/spec.md` - What we're building (source of truth)
- `docs/adr/` - Why decisions were made (source of truth)
- `docs/design/` - How we're building it (derived from spec, regenerate if approach changes)

## Development Principles

From spec.md: "Measure before changing." Optimizations, caching, quality improvements require data, not intuition. Agent output is non-deterministic—"it seems better" is not evidence.
