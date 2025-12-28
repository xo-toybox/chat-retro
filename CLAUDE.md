# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Map

- Entry: `__main__.py` → `session.py:SessionManager`
- State: `state.py` (Pydantic models)
- Agent config: `agents.py`, `insights.py`
- Hooks: `hooks.py:HOOK_MATCHERS`

## Design Constraints

- **Agentic**: SDK built-in tools on raw exports. No custom MCP tools.
- **Local state**: All state in project directory. No Claude memory integration.
- **Offline artifacts**: HTML outputs inline D3.js. No network requests.

## Development Principles

- "Measure before changing." Agent output is non-deterministic. "it seems better" is not evidence.
- "Dogfood relentlessly." Real usage beats synthetic tests.

## Checklist

When adding or modifying SDK constructs (agents, hooks, skills) or runtime definitions (state schema, log formats) → update `docs/reference/`

## Security Patterns

<!-- Promote to LEARNINGS.md if any of the learnings sections grows beyond 5 total items together -->

- **Path validation**: Never use string prefix checks for path access control. Always resolve to absolute paths first with `Path.resolve()`, then use `is_relative_to()` for containment checks. See `hooks.py:block_external_writes()`.

## Known Deficiencies

<!-- Anti-patterns to avoid -->

- **JSON schema in prompt**: Embedding JSON schemas in system prompts to steer agent output is fragile. Use structured outputs instead.
- **Legacy Python compatibility**: Python 3.12+ only. Do not use `from __future__ import annotations`, `typing.Dict`, `typing.List`, etc. Use native syntax: `dict`, `list`, `X | None`.
- **Legacy Pydantic syntax**: Pydantic v2+ only. Do not use v1 patterns like `class Config`, `@validator`. Use `model_config`, `@field_validator`.
