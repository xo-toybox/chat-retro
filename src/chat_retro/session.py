"""Session management for chat-retro."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from claude_code_sdk import (
    AssistantMessage,
    CLINotFoundError,
    ClaudeCodeOptions,
    ClaudeSDKClient,
    ProcessError,
    ResultMessage,
    TextBlock,
)

from .agents import get_agents_dict
from .hooks import HOOK_MATCHERS
from .prompts import SYSTEM_PROMPT
from .usage import UsageReport


# User-friendly error messages
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
    FileNotFoundError: "Export file not found: {path}\nCheck the path and try again.",
}


@dataclass
class Session:
    """Represents an active analysis session."""

    session_id: str | None = None
    export_path: Path | None = None
    usage: UsageReport = field(default_factory=UsageReport)


class SessionManager:
    """Manages chat-retro sessions with Claude Code SDK."""

    SESSIONS_DIR = Path(".chat-retro/sessions")

    def __init__(
        self,
        export_path: Path,
        resume_id: str | None = None,
        cwd: Path | None = None,
    ):
        self.export_path = export_path
        self.resume_id = resume_id
        self.cwd = cwd or Path.cwd()
        self.session = Session(export_path=export_path)
        self._client: ClaudeSDKClient | None = None

    def _build_options(self) -> ClaudeCodeOptions:
        """Build SDK options for this session."""
        return ClaudeCodeOptions(
            system_prompt=SYSTEM_PROMPT,
            permission_mode="acceptEdits",
            cwd=str(self.cwd),
            resume=self.resume_id,
            hooks=HOOK_MATCHERS,
            agents=get_agents_dict(),
        )

    def _save_session_id(self, session_id: str) -> None:
        """Persist session ID for future resumption."""
        self.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        session_file = self.SESSIONS_DIR / "latest.json"
        session_file.write_text(json.dumps({"session_id": session_id}))

    def _load_latest_session_id(self) -> str | None:
        """Load the most recent session ID."""
        session_file = self.SESSIONS_DIR / "latest.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                return data.get("session_id")
            except (json.JSONDecodeError, KeyError):
                return None
        return None

    def _display_message(self, msg: AssistantMessage) -> None:
        """Display an assistant message to the user."""
        for block in msg.content:
            if isinstance(block, TextBlock):
                print(block.text)
            # ToolUseBlock and ToolResultBlock are handled by the SDK

    async def run_interaction_loop(self) -> None:
        """Main interaction loop: user input -> agent response -> repeat."""
        options = self._build_options()

        try:
            async with ClaudeSDKClient(options) as client:
                self._client = client

                # Initial query
                initial_prompt = f"Analyze the conversation export at {self.export_path}"
                self.session.usage.start_turn()
                await client.query(initial_prompt)

                # Process initial response
                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        self._display_message(msg)
                    elif isinstance(msg, ResultMessage):
                        self.session.session_id = msg.session_id
                        self.session.usage.update_from_result(msg)
                        self.session.usage.end_turn()
                        self._save_session_id(msg.session_id)

                # Interactive loop
                while True:
                    try:
                        user_input = input("\nYou: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print()  # Newline after ^C
                        break

                    if not user_input:
                        continue

                    if user_input.lower() in ("exit", "quit", "/quit", "/exit"):
                        print("\nEnding session.")
                        break

                    self.session.usage.start_turn()
                    await client.query(user_input)

                    async for msg in client.receive_response():
                        if isinstance(msg, AssistantMessage):
                            self._display_message(msg)
                        elif isinstance(msg, ResultMessage):
                            self.session.usage.update_from_result(msg)
                            self.session.usage.end_turn()

        except CLINotFoundError as e:
            self.session.usage.record_error(e)
            print(USER_ERRORS[CLINotFoundError], file=sys.stderr)
            raise
        except ProcessError as e:
            self.session.usage.record_error(e)
            print(USER_ERRORS[ProcessError], file=sys.stderr)
            raise
        finally:
            self._client = None
            self._save_metrics()

        # Print final usage
        print(f"\n{self.session.usage.summary()}")

    def _save_metrics(self) -> None:
        """Persist metrics to a JSONL file for later analysis."""
        metrics_file = Path(".chat-retro/metrics.jsonl")
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        with metrics_file.open("a") as f:
            f.write(json.dumps(self.session.usage.detailed_summary()) + "\n")

    async def interrupt(self) -> None:
        """Interrupt current agent execution."""
        if self._client:
            await self._client.interrupt()
