# Chat Retrospective

Explore your AI conversation history with an agentic approach. The agent proposes patterns, you guide focus, output emerges from collaboration.

## Usage

```bash
uv sync
uv run chat-retro ./conversations.json
uv run chat-retro ./conversations.json --resume SESSION_ID
```

Supports ChatGPT and Claude export formats.

## Features

### Analysis Subagents
- **Topic Extractor**: Clusters conversation topics with confidence scores
- **Sentiment Tracker**: Tracks emotional tone evolution over time
- **Pattern Detector**: Identifies prompting patterns and anti-patterns
- **Temporal Analyst**: Analyzes time-based usage patterns

### Insight Generators
- **Prompt Improver**: Before/after suggestions for better prompting
- **Repetition Detector**: Finds repetitive queries, suggests templates
- **Usage Optimizer**: Time and context recommendations

### Visualizations
- **Timeline**: D3.js area chart of conversation frequency
- **Heatmap**: 7x24 grid showing usage by hour/weekday
- **Topic Clusters**: Force-directed graph of topic relationships
- **Length Distribution**: Histogram with statistics

### Interactive Artifacts
- Filter panel (date, topic, sentiment)
- Full-text search with highlighting
- Click-to-expand detail view
- Annotations with localStorage persistence

### Feedback Collection
- Quality prompts after analysis
- Pattern rating (1-5 or thumbs)
- Gap detection for missing features
- Issue reporting (GitHub or local)

## How It Works

Uses Claude Agent SDK with built-in tools (Read, Grep, Glob, Bash, Write, Edit). Agent explores raw JSON exports directly with no preprocessing. State persists locally in `state.json`. Generated artifacts are self-contained HTML with inlined D3.js.

## Structure

```
src/chat_retro/
├── __main__.py    # CLI entry point
├── session.py     # Claude SDK wrapper, interaction loop
├── state.py       # Pydantic models for state.json
├── prompts.py     # System prompts
├── agents.py      # Analysis subagent definitions
├── insights.py    # Insight generator agents
├── artifacts.py   # HTML bundler with D3.js
├── interactive.py # JS/CSS for interactive artifacts
├── eval.py        # Feedback collection
├── hooks.py       # Audit logging
├── usage.py       # Token tracking
└── viz_templates/ # D3.js visualization templates
    ├── timeline.py
    ├── heatmap.py
    ├── topic_clusters.py
    └── length_distribution.py
```

Runtime files: `state.json`, `.chat-retro/`, `outputs/`

## Development

```bash
uv sync                    # Install dependencies
uv run pytest              # Run tests (253 passing)
uv run pyright             # Type check
```
