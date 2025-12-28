"""CLI entry point for issue-workflow tool.

Uses Claude Code CLI for agent execution (subscription pricing).
See ADR-006 for migration rationale.
"""

import argparse
import json
import sys
from pathlib import Path

from shared import IssueReporter, IssueStatus

from .state_manager import RUNTIME_PATHS
from .workflow import IssueWorkflow


def ensure_runtime_dirs() -> None:
    """Create runtime directories if they don't exist."""
    for key in ("base", "drafts", "issues"):
        RUNTIME_PATHS[key].mkdir(parents=True, exist_ok=True)


def main() -> int:
    """Main entry point for issue-workflow CLI."""
    parser = argparse.ArgumentParser(
        prog="issue-workflow",
        description="Agentic issue management pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # process - full pipeline
    process_parser = subparsers.add_parser(
        "process",
        help="Run full pipeline: triage → cluster → prioritize → resolve",
    )
    process_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Auto-approve all human gates (non-interactive mode)",
    )

    # list - show issues
    list_parser = subparsers.add_parser("list", help="List issues")
    list_parser.add_argument(
        "--status",
        choices=[s.value for s in IssueStatus],
        help="Filter by status",
    )

    # clusters - show clusters
    subparsers.add_parser("clusters", help="List issue clusters")

    # approve - approve cluster for resolution
    approve_parser = subparsers.add_parser(
        "approve",
        help="Approve cluster for resolution",
    )
    approve_parser.add_argument("cluster_id", help="Cluster ID to approve")

    # defer - defer an issue
    defer_parser = subparsers.add_parser("defer", help="Defer an issue")
    defer_parser.add_argument("issue_id", help="Issue ID to defer")

    # wontfix - mark issue as won't fix
    wontfix_parser = subparsers.add_parser("wontfix", help="Mark issue as won't fix")
    wontfix_parser.add_argument("issue_id", help="Issue ID to mark")

    # report-bug - interactive bug report creation
    subparsers.add_parser("report-bug", help="Report a bug interactively")

    # drafts - list pending drafts
    subparsers.add_parser("drafts", help="List pending draft issues")

    args = parser.parse_args()

    if args.command == "process":
        workflow = IssueWorkflow(auto_approve=args.yes)
        result = workflow.process()
        print(f"\n{result.message}")
        return 0 if result.success else 1

    workflow = IssueWorkflow()

    if args.command == "list":
        status = IssueStatus(args.status) if args.status else None
        issues = workflow.list_issues(status)

        if not issues:
            print("No issues found.")
            return 0

        print(f"\n{'ID':<14} {'Status':<12} {'Severity':<10} {'Title'}")
        print("-" * 70)
        for issue in issues:
            title = issue.title[:35]
            # Handle both enum and string (due to use_enum_values=True)
            issue_status = str(issue.status.value if hasattr(issue.status, "value") else issue.status)
            issue_severity = str(issue.severity.value if hasattr(issue.severity, "value") else issue.severity) if issue.severity else "unknown"
            print(f"{issue.id:<14} {issue_status:<12} {issue_severity:<10} {title}")
        print(f"\nTotal: {len(issues)} issues")
        return 0

    elif args.command == "clusters":
        clusters = workflow.list_clusters()

        if not clusters:
            print("No clusters found.")
            return 0

        print(f"\n{'ID':<20} {'Status':<12} {'Priority':<10} {'Theme'}")
        print("-" * 80)
        for cluster in clusters:
            theme = cluster.theme[:35] if cluster.theme else "(no theme)"
            print(
                f"{cluster.id:<20} {cluster.status:<12} "
                f"{cluster.aggregate_priority:<10.2f} {theme}"
            )
        print(f"\nTotal: {len(clusters)} clusters")
        return 0

    elif args.command == "approve":
        result = workflow.approve_cluster(args.cluster_id)
        print(result.message)
        return 0 if result.success else 1

    elif args.command == "defer":
        result = workflow.defer_issue(args.issue_id)
        print(result.message)
        return 0 if result.success else 1

    elif args.command == "wontfix":
        result = workflow.wontfix_issue(args.issue_id)
        print(result.message)
        return 0 if result.success else 1

    elif args.command == "report-bug":
        return handle_report_bug()

    elif args.command == "drafts":
        return handle_list_drafts()

    return 1


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

    filepath = reporter.save_draft_issue(title, description, category, context)
    print(f"\nIssue saved to: {filepath}")

    open_github = input("Open GitHub issue? [y/N]: ").strip().lower()
    if open_github == "y":
        url = reporter.open_github_issue(title, description, labels=[category])
        print(f"Opened: {url}")

    return 0


def handle_list_drafts() -> int:
    """List pending draft issues."""
    ensure_runtime_dirs()
    reporter = IssueReporter()
    drafts = reporter.get_pending_drafts()

    if not drafts:
        print("No pending draft issues.")
        print("Tip: Use 'issue-workflow process' to process drafts.")
        return 0

    print(f"\n=== {len(drafts)} Draft Issues ===\n")
    for draft in drafts:
        print(f"[{draft.get('status', 'draft').upper()}] {draft['title']}")
        print(f"  Category: {draft['category']}")
        print(f"  ID: {draft.get('id', 'unknown')}")
        print(f"  File: {draft['file']}")
        print()

    print("Tip: Use 'issue-workflow process' to triage and process drafts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
