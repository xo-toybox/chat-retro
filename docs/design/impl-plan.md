---
derived_from: [design.md, .claude/skills/agentic-implementation/SKILL.md]
status: approved
---

# Implementation Plan

## Summary

~400 line Python CLI wrapping the Claude Agent SDK for conversational chat history analysis.

**Components:**
- Session manager (SDK client wrapper)
- State manager (Pydantic models for `state.json`)
- Hooks (audit logging, write protection)
- Artifact generator (HTML bundler with D3.js inlining)
- CLI entry point

## Phases

| # | Phase | Type | Mode | Status |
|---|-------|------|------|--------|
| 1 | Project setup | Mechanical | Direct | pending |
| 2 | State schema | Mechanical | Ralph | pending |
| 3 | Hooks | Mechanical | Ralph | pending |
| 4 | Session manager | **Judgment** | Human gate | pending |
| 5 | CLI entry point | Mechanical | Ralph | pending |
| 6 | Artifact generator | Mechanical | Ralph | pending |
| 7 | System prompts | **Judgment** | Human gate | pending |
| 8 | Integration test | **Judgment** | Human gate | pending |

## Feature List

Features tracked in `feature_list.json`. Each feature has verification steps and pass/fail status.

### Phase 1: Project setup
| ID | Description | Verification |
|----|-------------|--------------|
| proj-setup | Fix pyproject.toml, create package structure | `uv sync` succeeds, `__init__.py` exists |

### Phase 2: State schema
| ID | Description | Verification |
|----|-------------|--------------|
| state-models | Pydantic models for AnalysisState, StateMeta, Pattern, etc. | Import succeeds, validates sample JSON |
| state-manager | StateManager with load/save/merge, atomic writes, corruption recovery | `pytest tests/test_state.py` exits 0 |

### Phase 3: Hooks
| ID | Description | Verification |
|----|-------------|--------------|
| hook-audit-logger | Log tool usage without content, hash file paths | Function callable, returns expected format |
| hook-block-writes | Prevent writes outside allowed paths | Deny for external, empty for allowed |
| hook-state-mutation | Track Edit operations on state.json | `pytest tests/test_hooks.py` exits 0 |

### Phase 4: Session manager
| ID | Description | Verification |
|----|-------------|--------------|
| usage-report | UsageReport dataclass, update_from_result(), summary() | Import succeeds, summary format correct |
| session-manager-basic | ClaudeSDKClient wrapper, capture session_id | Import succeeds, matches design doc 3.1 |
| session-interaction-loop | Streaming responses, user input loop | Method exists with async handling |
| session-resumption | Resume via stored session_id | Accepts resume_id, persists to .chat-retro/ |

### Phase 5: CLI entry point
| ID | Description | Verification |
|----|-------------|--------------|
| cli-argparse | argparse with export_path, --resume | `python -m chat_retro --help` exits 0 |
| cli-wire-components | Wire session + state managers, Ctrl+C handling | Loads state.json, graceful shutdown |

### Phase 6: Artifact generator
| ID | Description | Verification |
|----|-------------|--------------|
| artifact-html-template | Self-contained HTML per ADR-003 | Valid HTML, no external requests |
| artifact-d3-bundling | D3.js minified inlined (~250KB) | Works from file:// protocol |
| artifact-generator-class | ArtifactGenerator with generate_html/markdown | `pytest tests/test_artifacts.py` exits 0 |

### Phase 7: System prompts
| ID | Description | Verification |
|----|-------------|--------------|
| system-prompt | Agent persona from design doc 4.1 | Exists in prompts.py, covers all sections |
| error-handling | User-friendly messages, RateLimiter | USER_ERRORS dict, RateLimiter class |

### Phase 8: Integration & polish
| ID | Description | Verification |
|----|-------------|--------------|
| runtime-dirs | Create .chat-retro/, outputs/ on first run | Dirs created, no errors on repeat |
| integration-test | E2E with sample export | State saves, artifact renders |
| claude-export-format | Support Claude export format | Agent identifies format correctly |

**Total: 20 features**

## Human Gates

| After Phase | What's Needed |
|-------------|---------------|
| Phase 4 | Review session.py - SDK usage correct? Error handling OK? |
| Phase 7 | Review system prompt - Agent persona matches vision? |
| Phase 8 | Integration test - Experience feels like "working with an analyst"? |

## Ralph Configurations

| Phase | Completion Criteria | Max Iterations |
|-------|---------------------|----------------|
| 2 | `uv run pytest tests/test_state.py` exits 0 | 10 |
| 3 | `uv run pytest tests/test_hooks.py` exits 0 | 10 |
| 5 | `uv run python -m chat_retro --help` exits 0 | 10 |
| 6 | `uv run pytest tests/test_artifacts.py` exits 0 | 10 |

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Claude Agent SDK API differs from design doc | Phase 4 is human gate; verify SDK docs first |
| D3.js bundling complexity | Start simple inline, iterate |
| pyproject.toml has wrong deps | Phase 1 fixes first |

## Progress Log

| Date | Phase | Notes |
|------|-------|-------|
| 2025-12-27 | Init | Created scaffolding: feature_list.json, PROGRESS.md, init.sh |
