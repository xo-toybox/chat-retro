# Chat Retrospective

Explore your AI conversation history with an agentic approach. The agent proposes patterns, you guide focus, output emerges from collaboration.

## Usage

```bash
uv sync
uv run chat-retro ./conversations.json
uv run chat-retro ./conversations.json --resume SESSION_ID
```

## How It Works

Uses Claude Agent SDK with built-in tools (Read, Grep, Glob, Bash, Write, Edit). Agent explores raw JSON exports directly with no preprocessing. State persists locally in `state.json`. Generated artifacts are self-contained HTML with inlined D3.js.

## Structure

```
src/chat_retro/
├── __main__.py   # CLI entry point
├── session.py    # Claude SDK wrapper, interaction loop
├── state.py      # Pydantic models for state.json
├── prompts.py    # System prompts
├── artifacts.py  # HTML bundler with D3.js
├── hooks.py      # Audit logging
└── usage.py      # Token tracking
```

Runtime files: `state.json`, `.chat-retro/`, `outputs/`
