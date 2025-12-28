"""CLI entry point for chat-retro."""


import argparse
import asyncio
import json
import signal
import sys
from pathlib import Path

from .eval import IssueReporter
from .session import SessionManager
from .state import StateManager

# Runtime directories
RUNTIME_DIRS = [
    Path(".chat-retro-runtime"),
    Path(".chat-retro-runtime/state"),
    Path(".chat-retro-runtime/logs"),
    Path(".chat-retro-runtime/issues"),
    Path(".chat-retro-runtime/feedback"),
    Path(".chat-retro-runtime/outputs"),
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
        nargs="?",
        help="Path to conversation export file (e.g., conversations.json)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        metavar="SESSION_ID",
        help="Resume a previous session by ID",
    )
    parser.add_argument(
        "--report-bug",
        action="store_true",
        help="Report a bug interactively",
    )
    parser.add_argument(
        "--list-issues",
        action="store_true",
        help="List pending local issues",
    )
    return parser.parse_args()


def handle_report_bug() -> int:
    """Interactive bug report creation."""
    ensure_runtime_dirs()
    reporter = IssueReporter()

    print("=== Bug Report ===\n")

    title = input("Title: ").strip()
    if not title:
        print("Error: Title is required.", file=sys.stderr)
        return 1

    print("Description (end with empty line):")
    lines = []
    while True:
        try:
            line = input()
            if not line:
                break
            lines.append(line)
        except EOFError:
            break
    description = "\n".join(lines)

    category = input("Category [bug/feature/improvement] (default: bug): ").strip()
    if not category:
        category = "bug"

    # Auto-capture context
    context: dict = {}
    state_path = Path(".chat-retro-runtime/state/analysis.json")
    if state_path.exists():
        try:
            state_data = json.loads(state_path.read_text())
            context["schema_version"] = state_data.get("schema_version")
            context["pattern_count"] = len(state_data.get("patterns", []))
        except Exception:
            pass

    corrupt_path = Path(".chat-retro-runtime/state/analysis.json.corrupt")
    if corrupt_path.exists():
        context["has_corrupt_state"] = True

    filepath = reporter.save_local_issue(title, description, category, context)
    print(f"\nIssue saved to: {filepath}")

    open_github = input("Open GitHub issue? [y/N]: ").strip().lower()
    if open_github == "y":
        url = reporter.open_github_issue(title, description, labels=[category])
        print(f"Opened: {url}")

    return 0


def handle_list_issues() -> int:
    """List pending local issues."""
    ensure_runtime_dirs()
    reporter = IssueReporter()
    issues = reporter.get_pending_issues()

    if not issues:
        print("No pending issues.")
        return 0

    print(f"\n=== {len(issues)} Pending Issues ===\n")
    for issue in issues:
        status = "[REPORTED]" if issue.get("reported") else "[PENDING]"
        print(f"{status} {issue['title']}")
        print(f"  Category: {issue['category']}")
        print(f"  Created: {issue['timestamp']}")
        print(f"  File: {issue['file']}")
        print()

    return 0


async def run_async(args: argparse.Namespace) -> int:
    """Run the async session."""
    export_path = args.export_path

    if export_path is None:
        print("Error: export_path is required for analysis.", file=sys.stderr)
        print("Usage: chat-retro <export_path>", file=sys.stderr)
        return 1

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

    # Handle utility commands first
    if args.report_bug:
        return handle_report_bug()

    if args.list_issues:
        return handle_list_issues()

    # Normal analysis mode requires export_path
    try:
        return asyncio.run(run_async(args))
    except KeyboardInterrupt:
        print("\nSession ended.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
