"""CLI entry point for chat-retro."""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from pathlib import Path

from .session import SessionManager
from .state import StateManager

# Runtime directories
RUNTIME_DIRS = [
    Path(".chat-retro"),
    Path(".chat-retro/sessions"),
    Path("outputs"),
]


def ensure_runtime_dirs() -> None:
    """Create runtime directories if they don't exist."""
    for dir_path in RUNTIME_DIRS:
        dir_path.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="chat-retro",
        description="Analyze your AI conversation history with an agentic approach.",
    )
    parser.add_argument(
        "export_path",
        type=Path,
        help="Path to conversation export file (e.g., conversations.json)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        metavar="SESSION_ID",
        help="Resume a previous session by ID",
    )
    return parser.parse_args()


async def run_async(args: argparse.Namespace) -> int:
    """Run the async session."""
    export_path = args.export_path

    # Ensure runtime directories exist
    ensure_runtime_dirs()

    # Validate export file exists
    if not export_path.exists():
        print(f"Error: Export file not found: {export_path}", file=sys.stderr)
        return 1

    # Load or initialize state
    state_manager = StateManager()
    state = state_manager.load()
    if state is None:
        print("No existing state found. Starting fresh analysis.")
    else:
        print(f"Loaded state with {len(state.patterns)} existing patterns.")

    # Create session manager
    session_manager = SessionManager(
        export_path=export_path,
        resume_id=args.resume,
    )

    # Set up interrupt handler
    loop = asyncio.get_running_loop()

    def handle_interrupt() -> None:
        print("\n\nInterrupting... (press Ctrl+C again to force quit)")
        asyncio.create_task(session_manager.interrupt())

    try:
        loop.add_signal_handler(signal.SIGINT, handle_interrupt)
    except NotImplementedError:
        # Windows doesn't support add_signal_handler
        pass

    # Run session
    try:
        await session_manager.run_interaction_loop()
    except KeyboardInterrupt:
        print("\nSession ended by user.")

    return 0


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        return asyncio.run(run_async(args))
    except KeyboardInterrupt:
        print("\nSession ended.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
