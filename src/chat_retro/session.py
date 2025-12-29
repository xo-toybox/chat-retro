"""Session management for chat-retro."""


import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    CLINotFoundError,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ProcessError,
    ResultMessage,
    TextBlock,
)
from claude_agent_sdk.types import StreamEvent

from .agents import get_agents
from .hooks import HOOK_MATCHERS
from .prompts import SYSTEM_PROMPT
from .usage import UsageReport


# Configuration
RESPONSE_TIMEOUT_SECONDS = 600  # 10 minutes max for any single response
HEARTBEAT_INTERVAL_SECONDS = 30  # Show progress every 30 seconds of silence


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
    TimeoutError: (
        "Response timed out after {timeout}s.\n"
        "The agent may be processing a very large file.\n"
        "Your progress is saved. Run again to resume."
    ),
}


@dataclass
class Session:
    """Represents an active analysis session."""

    session_id: str | None = None
    export_path: Path | None = None
    usage: UsageReport = field(default_factory=UsageReport)
    exit_requested: bool = False


class SessionManager:
    """Manages chat-retro sessions with Claude Code SDK."""

    RUNTIME_DIR = Path(".chat-retro-runtime")

    def __init__(
        self,
        export_path: Path,
        resume_id: str | None = None,
        cwd: Path | None = None,
        initial_prompt: str | None = None,
    ):
        self.export_path = export_path
        self.resume_id = resume_id
        self.cwd = cwd or Path.cwd()
        self.initial_prompt = initial_prompt
        self.session = Session(export_path=export_path)
        self._client: ClaudeSDKClient | None = None

    def _build_options(self) -> ClaudeAgentOptions:
        """Build SDK options for this session."""
        return ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            permission_mode="acceptEdits",
            cwd=str(self.cwd),
            resume=self.resume_id,
            hooks=HOOK_MATCHERS,
            agents=get_agents(),
            include_partial_messages=True,  # Enable streaming visibility
        )

    async def _receive_with_timeout(
        self,
        client: ClaudeSDKClient,
        timeout: float = RESPONSE_TIMEOUT_SECONDS,
    ):
        """Receive response with timeout and heartbeat progress indicator.

        Yields messages from the client, showing periodic heartbeat when
        no visible output is produced. Times out if no messages received
        within the timeout period.
        """
        start_time = time.monotonic()
        last_heartbeat = start_time
        message_count = 0

        try:
            async with asyncio.timeout(timeout):
                async for msg in client.receive_response():
                    now = time.monotonic()
                    message_count += 1

                    # StreamEvents are partial - show heartbeat for long streams
                    if isinstance(msg, StreamEvent):
                        if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                            elapsed = int(now - start_time)
                            print(
                                f"  [working... {elapsed}s, {message_count} events]",
                                file=sys.stderr,
                            )
                            last_heartbeat = now
                        continue  # Don't yield partial events to caller

                    yield msg

                    if isinstance(msg, ResultMessage):
                        return
        except TimeoutError:
            elapsed = int(time.monotonic() - start_time)
            print(
                f"\n{USER_ERRORS[TimeoutError].format(timeout=timeout)}",
                file=sys.stderr,
            )
            raise

    def _save_session_id(self, session_id: str) -> None:
        """Persist session ID for future resumption."""
        self.RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        session_file = self.RUNTIME_DIR / "resume-session.json"
        session_file.write_text(json.dumps({"session_id": session_id}))

    def _load_latest_session_id(self) -> str | None:
        """Load the most recent session ID."""
        session_file = self.RUNTIME_DIR / "resume-session.json"
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
                prompt = (
                    self.initial_prompt
                    or f"Analyze the conversation export at {self.export_path}"
                )
                self.session.usage.start_turn()
                await client.query(prompt)

                # Process initial response
                async for msg in self._receive_with_timeout(client):
                    if isinstance(msg, AssistantMessage):
                        self._display_message(msg)
                    elif isinstance(msg, ResultMessage):
                        self.session.session_id = msg.session_id
                        self.session.usage.update_from_result(msg)
                        self.session.usage.end_turn()
                        self._save_session_id(msg.session_id)

                # Interactive loop
                while not self.session.exit_requested:
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

                    async for msg in self._receive_with_timeout(client):
                        if isinstance(msg, AssistantMessage):
                            self._display_message(msg)
                        elif isinstance(msg, ResultMessage):
                            self.session.usage.update_from_result(msg)
                            self.session.usage.end_turn()

                    if self.session.exit_requested:
                        break

        except CLINotFoundError as e:
            self.session.usage.record_error(e)
            print(USER_ERRORS[CLINotFoundError], file=sys.stderr)
            raise
        except ProcessError as e:
            self.session.usage.record_error(e)
            print(USER_ERRORS[ProcessError], file=sys.stderr)
            raise
        except TimeoutError as e:
            self.session.usage.record_error(e)
            # Error message already printed in _receive_with_timeout
            raise
        finally:
            self._client = None
            self._save_metrics()

        # Print final usage
        print(f"\n{self.session.usage.summary()}")

    def _save_metrics(self) -> None:
        """Persist metrics to a JSONL file for later analysis."""
        logs_dir = self.RUNTIME_DIR / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        metrics_file = logs_dir / "metrics.jsonl"
        with metrics_file.open("a") as f:
            f.write(json.dumps(self.session.usage.detailed_summary()) + "\n")

    async def interrupt(self) -> None:
        """Interrupt current agent execution and request exit."""
        self.session.exit_requested = True
        if self._client:
            await self._client.interrupt()
