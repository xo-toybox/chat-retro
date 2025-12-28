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
| 1 | Project setup | Mechanical | Direct | done |
| 2 | State schema | Mechanical | Ralph | done |
| 3 | Hooks | Mechanical | Ralph | done |
| 4 | Session manager | **Judgment** | Human gate | done |
| 5 | CLI entry point | Mechanical | Ralph | done |
| 6 | Artifact generator | Mechanical | Ralph | done |
| 7 | System prompts | **Judgment** | Human gate | done |
| 8 | Integration test | **Judgment** | Human gate | done |
| 9 | Visualization templates | Mechanical | Ralph | pending |
| 10 | Analysis subagents | **Judgment** | Human gate | pending |
| 11 | Actionable insights | **Judgment** | Human gate | pending |
| 12 | Interactive artifacts | Mechanical | Ralph | pending |
| 13 | Question-based eval | **Judgment** | Human gate | pending |

## Feature List

Features tracked in `build-log/feature_list.json`. Each feature has verification steps and pass/fail status.

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

### Phase 9: Visualization templates
| ID | Description | Verification |
|----|-------------|--------------|
| viz-timeline | Conversation frequency over time (line/area chart) | HTML renders, shows time axis |
| viz-heatmap | Usage by hour/weekday (heatmap grid) | Shows 7×24 grid with intensity |
| viz-topic-clusters | Force-directed topic graph | Nodes draggable, clusters visible |
| viz-length-distribution | Histogram of conversation lengths | Bar chart with bins |

### Phase 10: Analysis subagents
| ID | Description | Verification |
|----|-------------|--------------|
| agent-topic-extractor | Extract and cluster topics from conversations | Agent returns structured topic list |
| agent-sentiment-tracker | Track emotional tone evolution | Agent returns sentiment timeline |
| agent-pattern-detector | Identify prompting patterns and anti-patterns | Agent returns pattern observations |
| agent-temporal-analyst | Time-based usage patterns | Agent returns temporal insights |

### Phase 11: Actionable insights
| ID | Description | Verification |
|----|-------------|--------------|
| insight-prompt-improvements | Suggestions for better prompting | Markdown output with before/after |
| insight-repetition-detection | Identify repetitive queries to template | List of repeated patterns |
| insight-usage-optimization | Time/context recommendations | Actionable bullet points |

### Phase 12: Interactive artifacts
| ID | Description | Verification |
|----|-------------|--------------|
| interact-filter-panel | Filter by date range, topic, sentiment | Filter controls work in browser |
| interact-search | Full-text search within artifact | Search box returns results |
| interact-detail-view | Click pattern → see example conversations | Modal or expandable details |
| interact-annotations | User can add notes to patterns | Notes persist in localStorage |

### Phase 13: Question-based eval
| ID | Description | Verification |
|----|-------------|--------------|
| eval-quality-prompts | After analysis, ask targeted questions | Prompts appear, responses captured |
| eval-rating-system | Rate patterns/insights (1-5 or thumbs) | Ratings persisted to state.json |
| eval-gap-detection | User flags missing expected features | Gaps logged for improvement |
| eval-feedback-aggregation | Aggregate feedback across sessions | Summary report available |
| eval-issue-reporter | Quick path to report bugs/issues | Opens issue template or logs locally |

**Total: 40 features (20 v1 + 20 v2)**

## Human Gates

| After Phase | What's Needed |
|-------------|---------------|
| Phase 7 | Review system prompt - Agent persona matches vision? |
| Phase 8 | Integration test - Experience feels like "working with an analyst"? |
| Phase 9 | Do visualizations look good? Render correctly in browser? |
| Phase 10 | Are subagent outputs useful? Accurate analysis? |
| Phase 11 | Are insights actionable? Not generic fluff? |
| Phase 12 | Does interactivity feel natural? Performant? |
| Phase 13 | Does eval flow feel natural? Is feedback useful for iteration? |

## Ralph Configurations

| Phase | Completion Criteria | Max Iterations |
|-------|---------------------|----------------|
| 2 | `uv run pytest tests/test_state.py` exits 0 | 10 |
| 3 | `uv run pytest tests/test_hooks.py` exits 0 | 10 |
| 5 | `uv run python -m chat_retro --help` exits 0 | 10 |
| 6 | `uv run pytest tests/test_artifacts.py` exits 0 | 10 |
| 9 | `uv run pytest tests/test_viz.py` exits 0 | 10 |
| 12 | `uv run pytest tests/test_interactive.py` exits 0 | 10 |


## Progress Log

| Date | Phase | Notes |
|------|-------|-------|
| 2025-12-27 | Init | Created scaffolding: feature_list.json, PROGRESS.md, init.sh |
| 2025-12-27 | 1-8 | v1 complete: all 20 features passing |
| 2025-12-27 | v2 Init | Added phases 9-13 (21 features) for functional expansion |
