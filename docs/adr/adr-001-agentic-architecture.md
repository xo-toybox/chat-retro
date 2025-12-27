# ADR-001: Agentic Architecture

| Status | Date |
|--------|------|
| Accepted | 2025-12-27 |

## Context

This project analyzes personal chat conversation exports (ChatGPT, Claude) to surface meaningful patterns. The original design used a deterministic pipeline with fixed classification rules.

**Constraints changed:**
- Deployment narrowed from wide distribution to personal/local use only
- Claude API approved for personal chat data analysis
- Quality prioritized over cost minimization

## Decision Drivers

1. **Quality ceiling**: Fixed rules can only find patterns the rules anticipate
2. **Pattern diversity**: Real conversation data has emergent patterns that defy prescribed categories
3. **User collaboration**: Analysis benefits from human guidance ("focus on work topics")
4. **Flexibility**: Different users have different data shapes and interests

## Decision

Use Claude Agent SDK for collaborative, emergent analysis instead of a deterministic pipeline.

## Approach

### Interaction Model

1. User provides export file
2. Agent samples, explores, proposes initial patterns
3. User guides: "focus here" / "go deeper" / "what about?"
4. Agent refines analysis and visualization
5. Together they produce a final artifact

### Agentic Search Over Embeddings

A key insight from Claude Code: Anthropic found that giving the agent filesystem tools to explore code naturally delivered significantly better results than RAG-based retrieval. Claude Code uses grep/glob (what they call "agentic search") rather than embeddings.

Best practice from Anthropic: "Begin with agentic search, add semantic only for performance scaling."

For this project:
- Chat data is a single JSON file, not a large codebase
- Direct reading + grep/jq may outperform embedding-based clustering
- Embeddings become an optional tool the agent uses when clustering genuinely helps

### SDK Built-in Tools

Use Claude Agent SDK's built-in tools directly. No custom MCP tools for core functionality.

| Tool | Purpose | Example |
|------|---------|---------|
| **Read** | Load file contents | Read conversations, state |
| **Grep** | Content search (ripgrep) | Find conversations mentioning "python" |
| **Glob** | File pattern matching | Discover export files |
| **Bash** | Shell commands | `jq` queries, data transforms |
| **Write** | Create files | Generate artifacts |
| **Edit** | Modify files | Update state.json |
| **Task** | Launch subagents | Deep-dive on specific topics |

**Why built-in tools, not custom MCP:**
- SDK tools are what Claude Code uses—battle-tested for agentic search
- No tool implementation to maintain
- Agent already knows how to use them effectively
- Aligns with "give the agent a computer" philosophy

**Example data access patterns:**
```bash
# Search conversations
Grep: pattern="python" path="./conversations.json"

# Count conversations  
Bash: jq '.conversations | length' conversations.json

# Extract for sampling
Bash: jq -r '.conversations[].title' conversations.json | head -50
```

### Custom Code (Minimal)

Only these components require custom implementation:

| Component | Purpose | Why Custom |
|-----------|---------|------------|
| CLI wrapper | User interaction loop | SDK provides tools, not UI |
| HTML bundler | Inline D3.js into artifacts | Offline artifact requirement (ADR-003) |
| State schema | Validate state.json | Type safety for pattern data |

### What the Agent Decides

- Pattern categories (emergent, not prescribed)
- Whether embeddings/clustering are useful
- Visualization approach
- Level of detail

### What the User Guides

- Focus areas ("more on technical topics")
- Depth ("go deeper on Q3")
- Output preferences ("I prefer timeline views")

## Consequences

### Positive

- **Higher quality ceiling**: Limited by model capability, not rule design
- **Emergent patterns**: Discovers what's actually in the data
- **Collaborative**: User and agent refine together
- **Adaptable**: Same tool works for different usage patterns
- **Minimal code**: SDK handles tool execution, context management

### Negative

- **Higher cost**: API calls vs local compute
- **Slower iteration**: Agent loop vs instant script
- **Less predictable**: Output varies by run
- **Requires interaction**: Not a batch-and-forget tool
- **SDK dependency**: Tied to Claude Agent SDK behavior and updates

### Neutral

- **Complexity shifted**: From rule design to prompt/agent design

## Alternatives Considered

| Option | Verdict |
|--------|---------|
| Deterministic pipeline | Rejected: quality ceiling too low |
| Hybrid (rules + agent refinement) | Rejected: added complexity without clear benefit |
| Full autonomy (no user interaction) | Rejected: user guidance improves results significantly |
| Custom MCP tools | Rejected: duplicates SDK functionality; more code to maintain |

## References

- [Claude Code: Best practices for agentic coding](https://www.anthropic.com/engineering/claude-code-best-practices) - Anthropic Engineering. Key patterns: read before coding, use subagents for complex problems, make a plan first.
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) - Anthropic Engineering. Multi-session state management via progress files.
- [Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk) - Anthropic Engineering. SDK fundamentals, built-in tools.
- [Archived: Spec v1 Deterministic Pipeline](../archive/spec-v1-deterministic-pipeline.md)