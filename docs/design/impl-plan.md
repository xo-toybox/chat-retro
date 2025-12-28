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

| # | Phase | Type | Mode | Parallel Work | Status |
|---|-------|------|------|---------------|--------|
| 1 | Project setup | Mechanical | Direct | - | pending |
| 2 | State schema (Pydantic models) | Mechanical | Ralph | Tester subagent | pending |
| 3 | Hooks (audit + write protection) | Mechanical | Ralph | Tester subagent | pending |
| 4 | Session manager | **Judgment** | Human gate | - | pending |
| 5 | CLI entry point | Mechanical | Ralph | - | pending |
| 6 | Artifact generator | Mechanical | Ralph | Tester subagent | pending |
| 7 | System prompts | **Judgment** | Human gate | - | pending |
| 8 | Integration test | **Judgment** | Human gate | - | pending |

## Phase Details

### Phase 1: Project setup
- Fix pyproject.toml (remove unused deps, add claude-agent-sdk)
- Create src/chat_retro/__init__.py, __main__.py
- Create tests/ directory structure
- Ensure structure matches design doc

### Phase 2: State schema (Ralph-able)
- Pydantic models: `AnalysisState`, `StateMeta`, `Pattern`, `UserPreferences`, `SnapshotRef`
- Validation with schema_version and migration support
- Atomic save with tmp file rename
- Corruption recovery with backup
- **Completion:** `uv run pytest tests/test_state.py` exits 0

### Phase 3: Hooks (Ralph-able)
- `audit_logger` - log tool usage without content
- `block_external_writes` - prevent writes outside allowed paths
- `state_mutation_logger` - track Edit operations on state.json
- **Completion:** `uv run pytest tests/test_hooks.py` exits 0

### Phase 4: Session manager (Human gate)
- ClaudeSDKClient wrapper
- Session resumption via stored session_id
- Interaction loop with streaming responses
- Cost tracking from ResultMessage
- Error handling with user-friendly messages
- **Gate:** Review session.py draft before proceeding

### Phase 5: CLI entry point (Ralph-able)
- argparse: `chat-retro <export_path> [--resume <session_id>]`
- Wire together session manager + state manager
- Graceful interrupt handling (Ctrl+C)
- **Completion:** `uv run python -m chat_retro --help` exits 0

### Phase 6: Artifact generator (Ralph-able)
- D3.js bundling (~250KB minified)
- HTML template with data embedding
- Markdown templates for reflections
- **Completion:** `uv run pytest tests/test_artifacts.py` exits 0

### Phase 7: System prompts (Human gate)
- Agent persona from design doc section 4.1
- Tool usage instructions
- Analysis approach guidance
- **Gate:** Review prompt before embedding

### Phase 8: Integration test (Human gate)
- End-to-end with sample export from __data__/
- Verify session resumption works
- Verify artifact generation works
- **Gate:** Human verifies experience feels collaborative

## Infrastructure

### Subagents (created during build)

**tester**
- Purpose: Write tests in parallel while implementing
- Tools: [Read, Grep, Write, Bash]
- Model: haiku

### Skills (created if needed)

**claude-agent-sdk**
- SDK patterns, message types, common idioms
- Created during Phase 4 if SDK usage proves complex

### Hooks

None for orchestration - hooks in the product are what we're building, not for building it.

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

## Notes

- Design doc (design.md) has detailed code samples for each component
- Current pyproject.toml has old deps from abandoned deterministic pipeline
- Ralph Wiggum plugin already installed
- Estimated ~400 lines total per design doc

## Progress Log

<!-- Update this section as phases complete -->

| Date | Phase | Notes |
|------|-------|-------|
| - | - | - |
