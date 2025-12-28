# Agents Reference

Chat-retro uses specialized subagents for focused analysis tasks.

## Analysis Subagents

Defined in `src/chat_retro/agents.py`.

| Agent | Description | Tools | Model |
|-------|-------------|-------|-------|
| `topic-extractor` | Extract and cluster topics from conversation content | Read, Grep, Glob | sonnet |
| `sentiment-tracker` | Track emotional tone and sentiment evolution | Read, Grep | sonnet |
| `pattern-detector` | Identify prompting patterns and anti-patterns | Read, Grep, Glob | sonnet |
| `temporal-analyst` | Analyze time-based usage patterns | Read, Grep | haiku |

### topic-extractor

Identifies distinct topics and themes, clusters related topics, assigns confidence scores.

### sentiment-tracker

Analyzes emotional tone over time, identifies sentiment shifts and triggers, tracks satisfaction patterns.

### pattern-detector

Finds recurring prompting patterns (effective and ineffective), flags anti-patterns, highlights improvement opportunities.

### temporal-analyst

Identifies usage patterns by time (hour, day, month), correlates time with topics, detects trends.

## Insight Generators

Defined in `src/chat_retro/insights.py`.

| Agent | Description | Tools | Model |
|-------|-------------|-------|-------|
| `prompt-improver` | Generate prompt improvement suggestions with before/after examples | Read, Grep, Glob | sonnet |
| `repetition-detector` | Find repetitive queries, suggest templates | Read, Grep, Glob | sonnet |
| `usage-optimizer` | Time and context recommendations for optimal usage | Read, Grep, Glob | sonnet |

### prompt-improver

Reviews prompting patterns, creates concrete before/after examples from actual data, prioritizes by impact.

### repetition-detector

Finds repetitive queries, groups into patterns, suggests reusable templates with variables.

### usage-optimizer

Analyzes successful vs unsuccessful interactions, generates user-specific recommendations.

## Usage

Agents are invoked by the main agent via the Task tool:

```python
from chat_retro.agents import get_agents

agents = get_agents()  # Returns all analysis + insight agents
```

The main agent selects appropriate subagents based on analysis needs and current state.
