# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                        # Install dependencies
uv run pytest tests/test_state.py -k test_name # Single test
uv run pytest                                  # All tests
uv run pyright                                 # Type check
```

## Architecture

### Data Flow

```
User input → SessionManager → ClaudeSDKClient → Agent explores export with built-in tools
                                              → StateManager persists patterns to state.json
                                              → ArtifactBuilder generates HTML to outputs/
```

### Key Modules

- `session.py:SessionManager` — Wraps ClaudeSDKClient, manages interaction loop
- `state.py:AnalysisState` — Pydantic model with pattern merging and migration
- `prompts.py:SYSTEM_PROMPT` — Agent instructions for analysis behavior
- `artifacts.py` — HTML bundler that inlines D3.js
- `hooks.py:HOOK_MATCHERS` — SDK hook configuration for audit logging

### Design Decisions (docs/adr/)

1. **Agentic over deterministic** (ADR-001): SDK built-in tools on raw exports. No custom MCP tools.
2. **Local state only** (ADR-002): All state in project directory. No Claude memory integration.
3. **Self-contained artifacts** (ADR-003): HTML outputs inline D3.js. No network requests.

## Development Principle

"Measure before changing." Agent output is non-deterministic. "it seems better" is not evidence.
