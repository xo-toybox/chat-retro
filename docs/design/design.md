---
derived_from: [spec.md, adr/*, design-review-checklist.md]
edit_policy: regenerate
---

# Chat Retrospective: Design Document

## 1. Overview

Chat Retrospective is a personal analysis tool that explores exported conversation history (ChatGPT, Claude) to surface patterns in how users interact with AI. It produces visualizations, reflections, and actionable insights through collaborative, agentic analysis.

**Core Philosophy**: Work like an analyst, not a script. The agent proposes patterns, the user guides focus, and output emerges from that collaboration.

## 2. Architecture

### 2.1 System Context

```
┌─────────────────────────────────────────────────────────────┐
│                        User Terminal                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    chat-retro CLI                            │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐        │
│  │   Session   │   │    State    │   │   Artifact  │        │
│  │   Manager   │──▶│   Manager   │──▶│   Writer    │        │
│  └─────────────┘   └─────────────┘   └─────────────┘        │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Claude Agent SDK Client                 │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │  Tools   │  │  Hooks   │  │ Subagents│          │    │
│  │  └──────────┘  └──────────┘  └──────────┘          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Claude API                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
User Export (JSON)           Local State              Claude API
      │                          │                        │
      ▼                          ▼                        │
 ┌─────────┐              ┌───────────┐                   │
 │  Parse  │──────────────▶│  Enrich  │◀──────────────────┤
 └─────────┘              └───────────┘                   │
                               │                          │
                               ▼                          │
                         ┌───────────┐                    │
                         │  Analyze  │◀───────────────────┤
                         └───────────┘                    │
                               │                          │
                               ▼                          │
                         ┌───────────┐                    │
                         │  Refine   │◀───── User Input ──┤
                         └───────────┘                    │
                               │                          │
                               ▼                          │
                         ┌───────────┐                    │
                         │  Render   │                    │
                         └───────────┘                    │
                               │                          │
                               ▼                          │
                     Local Artifacts (HTML/MD)
```

## 3. Component Design

### 3.1 Session Manager

Handles agent lifecycle using `ClaudeSDKClient` for interactive multi-turn conversations.

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, ResultMessage
from pathlib import Path

@dataclass
class Session:
    session_id: str | None
    state: AnalysisState | None
    export_path: Path
    cost_usd: float = 0.0

class SessionManager:
    """Manages chat-retro sessions with Claude Agent SDK."""

    def __init__(self, options: ClaudeAgentOptions):
        self.client = ClaudeSDKClient(options)
        self.session_id: str | None = None

    async def start_session(
        self,
        export_path: Path,
        resume_id: str | None = None
    ) -> Session:
        """Initialize new or resume existing session."""
        if resume_id:
            self.client = ClaudeSDKClient(
                ClaudeAgentOptions(resume=resume_id, **self.base_options)
            )
        await self.client.connect()
        return Session(session_id=resume_id, export_path=export_path)

    async def run_interaction_loop(self, session: Session) -> None:
        """Main loop: user input → agent response → repeat."""
        async with self.client:
            await self.client.query(f"Analyze {session.export_path}")

            async for message in self.client.receive_response():
                if hasattr(message, 'subtype') and message.subtype == 'init':
                    session.session_id = message.data.get('session_id')

                if isinstance(message, ResultMessage):
                    session.cost_usd += message.total_cost_usd or 0

                if isinstance(message, AssistantMessage):
                    self._display_response(message)

            while True:
                user_input = input("You: ")
                if user_input.lower() in ('exit', 'quit'):
                    break

                await self.client.query(user_input)
                async for message in self.client.receive_response():
                    if isinstance(message, ResultMessage):
                        session.cost_usd += message.total_cost_usd or 0
                    if isinstance(message, AssistantMessage):
                        self._display_response(message)

    async def interrupt(self) -> None:
        """Stop current agent execution."""
        await self.client.interrupt()
```

**Session Resumption**: The SDK handles session persistence automatically. Capture `session_id` from the init message, store it locally, and pass to `ClaudeAgentOptions(resume=session_id)` to resume with full context.

**Session Modes**:

| Mode | Trigger | Behavior |
|------|---------|----------|
| First analysis | No prior state | Full exploration |
| Incremental update | New data + existing state | "What's new" + update patterns |
| Full refresh | User request or significant drift | Fresh analysis, compare to prior |

### 3.2 State Manager

Local-only state per ADR-002. No Claude memory integration.

```python
@dataclass
class AnalysisState:
    """Persisted analysis state between sessions."""
    schema_version: int
    meta: StateMeta
    patterns: list[Pattern]
    user_preferences: UserPreferences
    snapshots: list[SnapshotRef]

class StateManager:
    """Read/write local state.json with migration support."""

    CURRENT_VERSION = 1

    def load(self, path: Path) -> AnalysisState | None:
        """Load existing state with migration and corruption recovery."""
        try:
            data = json.loads(path.read_text())
            version = data.get("schema_version", 0)
            if version < self.CURRENT_VERSION:
                data = self._migrate(data, version)
            return AnalysisState.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            backup = path.with_suffix(".json.corrupt")
            path.rename(backup)
            print(f"State corrupted, backed up to {backup}. Starting fresh.")
            return None

    def save(self, state: AnalysisState, path: Path) -> None:
        """Persist state atomically."""
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(state.model_dump_json(indent=2))
        tmp.rename(path)

    def merge_patterns(
        self,
        existing: list[Pattern],
        new: list[Pattern]
    ) -> list[Pattern]:
        """Merge patterns from incremental analysis."""
```

**State Schema**:
```json
{
  "schema_version": 1,
  "meta": {
    "created": "2025-06-15T00:00:00Z",
    "last_updated": "2025-09-20T00:00:00Z",
    "conversation_count": 847,
    "date_range": ["2024-01-01", "2025-09-15"],
    "export_format": "chatgpt"
  },
  "patterns": [
    {
      "id": "p1",
      "type": "theme",
      "label": "Python debugging",
      "confidence": 0.85,
      "conversation_ids": ["c1", "c2", "c3"],
      "temporal": {"peak_month": "2025-03", "frequency": "weekly"}
    }
  ],
  "user_preferences": {
    "focus_areas": ["work", "learning"],
    "excluded_topics": [],
    "preferred_viz": "timeline"
  },
  "snapshots": [
    {"date": "2025-06", "artifact": "outputs/2025-06.html"}
  ]
}
```

### 3.3 Tool Strategy

Per ADR-001: Use SDK built-in tools exclusively. No custom MCP tools.

**Built-in tools** (provided by SDK):

| Tool | Purpose | Example |
|------|---------|---------|
| `Read` | Load file contents | Read conversations.json, state.json |
| `Grep` | Content search (ripgrep) | Find conversations mentioning "python" |
| `Glob` | File pattern matching | Discover export files |
| `Bash` | Shell commands | `jq` queries, data transforms |
| `Write` | Create files | Generate artifacts in outputs/ |
| `Edit` | Modify files | Update state.json |
| `Task` | Launch subagents | Deep-dive on specific topics |

**State Management via Built-in Tools**:
```bash
# Read current state
Read: file_path="./state.json"

# Update state (agent edits JSON directly)
Edit: file_path="./state.json" old_string="..." new_string="..."

# Or use jq for atomic updates
Bash: jq '.patterns += [{"id": "p1", "label": "Python debugging"}]' state.json > tmp && mv tmp state.json
```

**SDK Configuration**:
```python
options = ClaudeAgentOptions(
    allowed_tools=[
        "Read", "Glob", "Grep", "Write", "Edit", "Bash",
        "Task"
    ],
    permission_mode="acceptEdits",
    cwd=str(project_dir)
)
```

### 3.4 Artifact Generator

Produces self-contained outputs per ADR-003.

```python
class ArtifactGenerator:
    """Generate offline-capable HTML and markdown artifacts."""

    def generate_html(
        self,
        template: str,
        data: dict,
        libraries: list[str]  # e.g., ["d3"]
    ) -> str:
        """Generate self-contained HTML with inlined dependencies."""

    def generate_markdown(
        self,
        content: str,
        metadata: dict
    ) -> str:
        """Generate markdown reflection/learning output."""
```

**HTML Artifact Structure** (per ADR-003):
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Chat Retrospective - 2025-09</title>
  <style>/* All CSS inlined */</style>
</head>
<body>
  <div id="app"></div>
  <script>/* D3.js inlined (~250KB) */</script>
  <script>const DATA = { /* Analysis data */ };</script>
  <script>/* Visualization code */</script>
</body>
</html>
```

## 4. Agent Design

### 4.1 System Prompt

```
You are a chat retrospective analyst. You help users understand patterns
in their AI conversation history.

## Your Role
Work collaboratively with the user like a data analyst:
1. Explore: Sample and scan the data to understand its shape
2. Propose: Identify initial patterns and present them
3. Listen: Accept user guidance on what matters
4. Refine: Deepen analysis in areas of interest
5. Deliver: Generate artifacts that serve user's goals

## Available Tools (All Built-in)

### Data Access
- Read: Load conversations.json, state.json, any local file
- Grep: Search conversation content with regex patterns
- Glob: Find files by pattern
- Bash: Use jq for complex JSON queries

### State & Output
- Edit: Update state.json (add patterns, update preferences)
- Write: Create HTML/markdown artifacts in ./outputs/

### Delegation
- Task: Launch subagents for deep-dive analysis

## Analysis Approach
Start with agentic search (direct text analysis). The export file is JSON -
read it directly, grep for patterns, use jq for filtering.

Example workflow:
1. Read conversations.json to understand structure
2. Grep for topic keywords to find relevant conversations
3. Use jq to count, filter, and extract metadata
4. Propose patterns based on findings

Only suggest embeddings/clustering when:
- Dataset is very large (>5000 conversations)
- User requests semantic grouping
- Text search isn't surfacing meaningful patterns

## Output Types
- Visualization: Interactive HTML showing patterns over time
- Reflection: Markdown narratives about usage patterns
- Learning: Actionable insights about prompting habits

## Constraints
- Never persist raw conversation text externally
- All artifacts must be self-contained (no external dependencies)
- Explain your reasoning; patterns should be interpretable
- Only write to ./outputs/ and ./state.json

Note: For very long sessions, earlier context may be summarized
automatically. If you notice missing context, re-read state.json.
```

### 4.2 Interaction Flow

```
Session Start
     │
     ▼
┌─────────────────────────────────────┐
│  Load state.json (if exists)        │
│  Load export file                   │
│  Sample conversations               │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  Initial Analysis                   │
│  - Metadata overview                │
│  - Propose 3-5 initial patterns     │
│  - Ask: "What interests you?"       │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  Refinement Loop                    │◀────┐
│  - User provides direction          │     │
│  - Agent deepens analysis           │     │
│  - Update patterns in state         │     │
│  - Propose next steps               │─────┘
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  Artifact Generation                │
│  - User requests specific output    │
│  - Agent generates artifact         │
│  - Save to outputs/                 │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  Session End                        │
│  - Save updated state               │
│  - Offer session resumption         │
└─────────────────────────────────────┘
```

### 4.3 Subagent Strategy

For complex analysis tasks, use focused subagents to preserve main context:

```python
from claude_agent_sdk import AgentDefinition

agents = {
    "deep-dive": AgentDefinition(
        description="Analyze a specific topic cluster in depth.",
        prompt="""You are a deep-dive analyst examining conversations about a specific topic.

Your task:
1. Read the relevant conversations thoroughly
2. Identify patterns within this topic cluster
3. Note evolution of the topic over time
4. Surface non-obvious insights

Be thorough but concise. Return findings as structured observations.""",
        tools=["Read", "Grep", "Glob"],
        model="sonnet"
    ),
    "temporal-analyst": AgentDefinition(
        description="Analyze usage patterns and conversation frequency over time.",
        prompt="""You are a temporal pattern analyst.

Examine conversation metadata to identify:
- Usage trends (daily, weekly, monthly patterns)
- Burst periods vs quiet periods
- Correlation between time and topics
- Seasonal or cyclical patterns

Return findings with specific date ranges and frequencies.""",
        tools=["Read", "Grep"],
        model="haiku"
    )
}
```

**Subagent Mechanics**:
- Invoked via `Task` tool (main agent must have `Task` in allowed_tools)
- Run in isolated context - don't pollute main conversation
- Results returned to main agent as tool result
- Cannot spawn their own subagents (no `Task` in their tools)
- `parent_tool_use_id` field identifies messages from subagents

### 4.4 Hooks for Logging & Safety

Use SDK hooks for audit logging and write protection.

```python
from claude_agent_sdk import HookMatcher, HookContext
from typing import Any
from datetime import datetime
import hashlib

async def audit_logger(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    """Log tool usage without exposing conversation content."""
    event = {
        "timestamp": datetime.now().isoformat(),
        "tool": input_data.get("tool_name"),
        "session": input_data.get("session_id"),
    }

    # Privacy: hash file paths, don't log content
    if "file_path" in input_data.get("tool_input", {}):
        path = input_data["tool_input"]["file_path"]
        event["file_hash"] = hashlib.sha256(path.encode()).hexdigest()[:8]

    with open(".chat-retro/audit.log", "a") as f:
        f.write(json.dumps(event) + "\n")

    return {}

async def block_external_writes(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    """Prevent writes outside project directory."""
    if input_data["hook_event_name"] != "PreToolUse":
        return {}

    file_path = input_data.get("tool_input", {}).get("file_path", "")
    allowed_prefixes = ["./outputs/", "./state.json", "./.chat-retro/"]

    if input_data["tool_name"] in ("Write", "Edit"):
        if not any(file_path.startswith(p) for p in allowed_prefixes):
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Write blocked: {file_path} outside allowed paths"
                }
            }
    return {}

async def state_mutation_logger(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    """Log Edit operations on state.json for efficiency analysis."""
    if input_data.get("tool_name") != "Edit":
        return {}

    file_path = input_data.get("tool_input", {}).get("file_path", "")
    if "state.json" not in file_path:
        return {}

    event = {
        "timestamp": datetime.now().isoformat(),
        "session": input_data.get("session_id"),
        "old_string_len": len(input_data["tool_input"].get("old_string", "")),
        "new_string_len": len(input_data["tool_input"].get("new_string", "")),
        "tool_use_id": tool_use_id,
    }

    with open(".chat-retro/state-mutations.log", "a") as f:
        f.write(json.dumps(event) + "\n")

    return {}

# Configure hooks
hooks = {
    "PreToolUse": [
        HookMatcher(matcher="Write|Edit", hooks=[block_external_writes]),
    ],
    "PostToolUse": [
        HookMatcher(hooks=[audit_logger, state_mutation_logger]),
    ],
}
```

**Privacy-Aware Logging**:
- Never log conversation content or message text
- Hash file paths instead of logging verbatim
- Audit log stays local (never transmitted)
- Log tool names, timestamps, session IDs only

**Note**: Python SDK hooks do not support `SessionStart`, `SessionEnd`, or `Notification` events (TypeScript only). Use `Stop` hook for cleanup on session end.

### 4.5 Resilience & Error Handling

```python
from claude_agent_sdk import (
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
    ClaudeSDKClient,
    ClaudeAgentOptions
)

USER_ERRORS = {
    CLINotFoundError: (
        "Claude Code CLI not found.\n"
        "Install: npm install -g @anthropic-ai/claude-code\n"
        "Then run: claude --version"
    ),
    ProcessError: (
        "Agent process failed. This may be temporary.\n"
        "Your progress is saved. Run again to resume."
    ),
    FileNotFoundError: (
        "Export file not found: {path}\n"
        "Check the path and try again."
    ),
}

class ResilientSession:
    """Session wrapper with retry and recovery."""

    def __init__(self, options: ClaudeAgentOptions):
        self.options = options
        self.client: ClaudeSDKClient | None = None
        self.rate_limiter = RateLimiter(calls_per_minute=50)

    async def run_with_retry(self, prompt: str, max_retries: int = 3):
        for attempt in range(max_retries):
            try:
                await self.rate_limiter.wait()
                async with ClaudeSDKClient(self.options) as client:
                    self.client = client
                    await client.query(prompt)
                    async for msg in client.receive_response():
                        yield msg
                    return
            except ProcessError as e:
                if e.exit_code == 1 and attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except CLINotFoundError:
                raise RuntimeError(USER_ERRORS[CLINotFoundError])

    async def interrupt_gracefully(self):
        """Interrupt with state preservation."""
        if self.client:
            await self.client.interrupt()

    async def rewind_to_checkpoint(self, message_uuid: str):
        """Restore files to previous state."""
        if self.client:
            await self.client.rewind_files(message_uuid)

class RateLimiter:
    """Simple rate limiter for API calls."""
    def __init__(self, calls_per_minute: int = 50):
        self.interval = 60 / calls_per_minute
        self.last_call = 0

    async def wait(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.interval:
            await asyncio.sleep(self.interval - elapsed)
        self.last_call = time.time()
```

**Graceful Degradation**:

| Failure | Behavior |
|---------|----------|
| API unreachable | Save current state, offer retry later |
| Export too large | Sample and warn, offer full scan option |
| D3 bundle missing | Generate data-only JSON, skip viz |
| State locked | Read-only mode, warn user |

**Checkpoint Frequency**: Save state after each complete user turn via `ResultMessage` handler.

### 4.6 Cost Tracking

```python
from dataclasses import dataclass, field
from claude_agent_sdk import ResultMessage

@dataclass
class UsageReport:
    """Track costs and tokens across session."""
    session_id: str
    total_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    turns: int = 0
    processed_message_ids: set[str] = field(default_factory=set)

    def update_from_result(self, msg: ResultMessage) -> None:
        """Update from ResultMessage (contains cumulative totals)."""
        self.total_cost_usd = msg.total_cost_usd or 0
        self.turns = msg.num_turns
        if msg.usage:
            self.input_tokens = msg.usage.get("input_tokens", 0)
            self.output_tokens = msg.usage.get("output_tokens", 0)
            self.cache_read_tokens = msg.usage.get("cache_read_input_tokens", 0)

    def summary(self) -> str:
        return (
            f"Session {self.session_id}: "
            f"${self.total_cost_usd:.4f} | "
            f"{self.input_tokens + self.output_tokens:,} tokens | "
            f"{self.turns} turns"
        )
```

**Usage Tracking Notes**:
- `ResultMessage` contains cumulative usage for entire session
- Multiple messages with same ID report identical usage (deduplicate)
- `total_cost_usd` is authoritative for billing

## 5. Project Structure

```
chat-retro/
├── pyproject.toml
├── src/
│   └── chat_retro/
│       ├── __init__.py
│       ├── cli.py              # Entry point, argument parsing
│       ├── session.py          # SessionManager, ClaudeSDKClient wrapper
│       ├── state.py            # State schema validation (Pydantic)
│       ├── hooks.py            # Audit logging, write protection
│       ├── artifacts.py        # HTML bundler with D3.js inlining
│       ├── usage.py            # UsageReport, cost tracking
│       └── prompts.py          # System prompts
├── tests/
│   ├── test_state.py
│   ├── test_hooks.py
│   ├── test_artifacts.py
│   └── fixtures/
│       ├── chatgpt_sample.json
│       └── claude_sample.json
└── docs/
    ├── spec.md
    ├── design.md
    └── adr/
```

**Runtime directories** (created on first run, project-local):
```
./
├── state.json                  # Analysis state
├── .chat-retro/
│   ├── sessions/               # Session ID storage
│   │   └── {session_id}.json
│   ├── audit.log               # Privacy-safe audit log
│   └── state-mutations.log     # Edit efficiency tracking
└── outputs/                    # Generated artifacts
    └── retrospective-2025-12.html
```

**Estimated code size** (~400 lines total):
- CLI wrapper: ~200 lines
- HTML bundler: ~100 lines
- State schema: ~50 lines
- Hooks: ~50 lines

## 6. Dependencies

```toml
# pyproject.toml
[project]
requires-python = ">=3.12"
dependencies = [
    "claude-agent-sdk>=0.1.0,<1.0",
    "pydantic>=2.0,<3.0",
]
```

## 7. Implementation Plan

### Phase 1: Foundation
1. Project setup (uv, pyproject.toml, structure)
2. State schema validation (Pydantic models)
3. Basic CLI with argparse
4. Hooks: audit logging + write protection

### Phase 2: Agent Integration
5. ClaudeSDKClient wrapper with session capture
6. System prompt engineering
7. Session resumption via stored session_id
8. UsageReport tracking from ResultMessage

### Phase 3: Interactive Loop
9. User input loop with interrupt handling
10. Graceful error recovery
11. State initialization on first run
12. Cost display per session

### Phase 4: Artifact Generation
13. D3.js minified bundle (~250KB)
14. HTML template with data embedding
15. Markdown templates for reflections
16. Snapshot tracking in state.json

### Phase 5: Polish
17. Claude export format support
18. Large export handling (pre-sample first 100 + random 100 to estimate patterns)
19. Session forking for exploration branches
20. Documentation and examples

## 8. Testing Strategy

**Unit tests** (pytest):
- `test_state.py`: Schema validation, migration, corruption recovery
- `test_hooks.py`: Path blocking, audit logging format
- `test_artifacts.py`: HTML generation, D3 inlining

**Integration tests** (manual or recorded):
- Record agent sessions with mock export
- Verify state mutations match expectations
- Verify artifact output structure

**Agent output evaluation**:
- Pattern count: Did agent find 3+ distinct patterns?
- Pattern quality: Are conversation_ids valid?
- Artifact validity: Does HTML render without errors?

## 9. Design Decisions

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| Agentic over deterministic | Higher quality ceiling; emergent patterns | ADR-001 |
| Local state only | User data sovereignty; transparency | ADR-002 |
| Self-contained HTML | Offline forever; no privacy leakage | ADR-003 |
| Built-in tools only | Battle-tested; no maintenance; agent knows them | ADR-001 |
| No custom MCP | Duplicates SDK functionality | ADR-001 |
| Subagents for deep dives | Preserve main context | Best practice |
| D3.js for visualization | Flexible for timelines, clusters, force graphs | User choice |
| Embeddings only when needed | >5000 conversations OR user requests OR grep insufficient | Agentic search first |

## 10. Success Metrics

| Criterion | Measure |
|-----------|---------|
| Non-obvious insights | User feedback: "I didn't know that" |
| Actionable output | Artifacts serve stated goal |
| Interpretable | Agent explains reasoning clearly |
| Collaborative feel | Natural back-and-forth refinement |

## 11. SDK Verification

| Aspect | Design Choice | SDK Support | Notes |
|--------|---------------|-------------|-------|
| Tools | Built-in only | Full | Read, Grep, Glob, Bash, Write, Edit, Task |
| Custom MCP | None | N/A | Per ADR-001: rejected |
| Session resumption | Capture session_id | `resume=session_id` | SDK handles persistence |
| Subagents | AgentDefinition | `agents={}` param | Isolated context, model override |
| Hooks | PreToolUse, PostToolUse | Limited in Python | No SessionStart/End |
| Cost tracking | ResultMessage | `total_cost_usd`, `usage` | Dedupe by message ID |
| Interrupts | Graceful stop | `client.interrupt()` | Requires ClaudeSDKClient |
| File rewind | Checkpoint restore | `rewind_files()` | Needs `enable_file_checkpointing` |

## 12. References

### Official Documentation
- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Python SDK Reference](https://platform.claude.com/docs/en/agent-sdk/python)
- [Custom Tools](https://platform.claude.com/docs/en/agent-sdk/custom-tools)
- [Hooks Guide](https://platform.claude.com/docs/en/agent-sdk/hooks)
- [Session Management](https://platform.claude.com/docs/en/agent-sdk/sessions)
- [Subagents](https://platform.claude.com/docs/en/agent-sdk/subagents)
- [Cost Tracking](https://platform.claude.com/docs/en/agent-sdk/cost-tracking)

### Anthropic Engineering
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Building Agents with Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
