# ADR-006: Issue Workflow CLI Migration

| Status | Date |
|--------|------|
| Accepted | 2025-12-28 |

## Context

The issue workflow (ADR-005) was implemented using `claude_agent_sdk` directly. This incurs API costs per token, which can be expensive for frequent local development use.

**Cost analysis:**
- SDK/API pricing: $3-5/M input, $15-25/M output tokens
- Estimated ~$0.72 per workflow run (4 agents × ~10K tokens)
- Frequent use: ~$200/month in API costs

Meanwhile, Claude Code subscriptions ($20-200/month) provide fixed-cost usage for interactive and CLI workflows.

**Architecture context:**
- `chat_retro` (online product): Core functionality, needs SDK for API features
- `issue_workflow` (offline tool): Developer-facing, runs locally, ideal for subscription pricing

## Decision Drivers

1. **Cost efficiency**: Local development workflows should use subscription, not per-token API
2. **Simplicity**: Reduce dependency complexity for offline tools
3. **Consistency**: Leverage Claude Code CLI patterns (`-p`, subagents, JSON output)
4. **Maintainability**: Single runner implementation instead of SDK abstractions

## Decision

Migrate `issue_workflow` from `claude_agent_sdk` to Claude Code CLI subprocess calls.

**Architecture after migration:**
```
chat_retro (online product)    → Uses SDK (API pricing) [unchanged]
issue_workflow (offline tool)  → Uses CLI runner (subscription pricing) [migrated]
```

## Approach

### CLI Runner Pattern

Replace `ClaudeSDKClient` with subprocess calls to `claude -p`:

```python
class ClaudeCodeRunner:
    def run(self, prompt: str, allowed_tools: list[str] | None = None) -> RunResult:
        cmd = ['claude', '-p', prompt, '--output-format', 'json', '--max-turns', '10']
        if allowed_tools:
            cmd.extend(['--allowedTools', ','.join(allowed_tools)])
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.cwd)
        # ... parse JSON response
```

### Subagent Definitions

Move agent prompts from Python `AgentDefinition` to `.claude/agents/*.md` files:

```
.claude/agents/
├── issue-triage.md
├── issue-clustering.md
├── issue-prioritization.md
└── issue-resolution.md
```

Claude Code automatically loads these when running in the project directory.

### Sync Execution

SDK used async streams; CLI uses sync subprocess. Workflow methods change from `async def` to `def`.

## Consequences

### Positive

- **Cost reduction**: Fixed subscription vs per-token API (~$100-200/month savings)
- **Simpler code**: No SDK abstractions, just subprocess calls
- **CLI consistency**: Same patterns as interactive Claude Code usage
- **Version-controlled agents**: Subagent definitions in `.claude/agents/` tracked in git

### Negative

- **No streaming**: Batch output instead of real-time (accepted tradeoff)
- **CLI dependency**: Requires `claude` binary installed
- **Session isolation**: Each subprocess is a fresh session (no cross-step memory)

### Neutral

- **Testing approach**: Mock subprocess instead of SDK client
- **Human gates**: Unchanged (`input()` prompts still work)

## Alternatives Considered

| Option | Verdict |
|--------|---------|
| Keep SDK for all | Rejected: costly for local development |
| SDK with caching | Rejected: added complexity, still per-token |
| GitHub Actions only | Rejected: Actions use API keys (API pricing) |
| Hybrid SDK/CLI | Rejected: two code paths to maintain |

## References

- [ADR-005: Agentic Issue Workflow](adr-005-agentic-issue-workflow.md) - Original workflow design
