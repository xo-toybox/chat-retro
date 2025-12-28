"""Issue workflow orchestration for the agentic pipeline.

Pipeline: draft → triaged → clustered → prioritized → resolved
Human gates: prioritization approval, low-confidence resolution approval

Uses Claude Code CLI instead of SDK for subscription-based pricing.
See ADR-006 for migration rationale.

Agent prompts are loaded from .claude/agents/*.md files at runtime.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from shared import Issue, IssueCluster, IssueSeverity, IssueStatus

from .runner import ClaudeCodeRunner
from .state_manager import IssueStateManager


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Returns (frontmatter_dict, body_markdown).
    Uses regex to avoid adding pyyaml dependency.
    """
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content

    frontmatter_text, body = match.groups()

    # Simple YAML parsing for flat key: value pairs
    frontmatter: dict[str, Any] = {}
    for line in frontmatter_text.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            value = value.strip()
            # Handle comma-separated lists (tools: Read, Grep, Glob)
            if "," in value:
                value = [v.strip() for v in value.split(",")]
            frontmatter[key.strip()] = value

    return frontmatter, body.strip()


@dataclass
class WorkflowResult:
    """Result of a workflow step."""

    success: bool
    message: str
    data: dict = field(default_factory=dict)


class IssueWorkflow:
    """Orchestrates the issue management workflow.

    Uses Claude Code CLI for agent execution (subscription pricing).
    """

    def __init__(self, cwd: Path | None = None, auto_approve: bool = False):
        self.cwd = cwd or Path.cwd()
        self.auto_approve = auto_approve
        self.state_manager = IssueStateManager()
        self._runner = ClaudeCodeRunner(cwd=self.cwd, max_turns=10)

    def _load_agent_config(self, agent_name: str) -> tuple[list[str], str]:
        """Load tools and prompt from .claude/agents/{agent_name}.md.

        Returns:
            (tools_list, system_prompt_markdown)
        """
        path = self.cwd / ".claude" / "agents" / f"{agent_name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Agent config not found: {path}")

        content = path.read_text()
        frontmatter, body = _parse_frontmatter(content)

        tools = frontmatter.get("tools", [])
        if isinstance(tools, str):
            tools = [tools]

        return tools, body

    def _run_agent(
        self,
        agent_name: str,
        task_context: str,
        *,
        approved: bool = False,
    ) -> dict | list | None:
        """Run an agent via Claude Code CLI.

        Args:
            agent_name: Name of the agent (maps to .claude/agents/*.md).
            task_context: Task-specific context (data to process).
            approved: If True, append approval suffix to prompt.

        Returns:
            Parsed agent response (dict or list), or None on failure.
        """
        tools, system_prompt = self._load_agent_config(agent_name)

        prompt = f"{system_prompt}\n\n## Current Task\n\n{task_context}"

        if approved:
            prompt += "\n\nHuman approved the plan. Proceed with implementation."

        result = self._runner.run(prompt, allowed_tools=tools)

        if not result.success:
            print(f"Agent {agent_name} failed: {result.error}")
            return None

        print(result.output)
        return result.parsed_data

    # ========================================================================
    # Pipeline Steps
    # ========================================================================

    def run_triage(self) -> WorkflowResult:
        """Run triage agent on all draft issues."""
        # Import any loose draft files into state first
        imported = self.state_manager.import_all_drafts()
        if imported:
            print(f"Imported {len(imported)} draft files into state.")

        drafts = self.state_manager.get_drafts()

        if not drafts:
            return WorkflowResult(
                success=True,
                message="No draft issues to triage.",
            )

        print(f"\n=== Triaging {len(drafts)} draft issues ===\n")

        task_context = json.dumps(
            [d.model_dump(mode="json") for d in drafts],
            indent=2,
            default=str,
        )

        result = self._run_agent("issue-triage", task_context)

        if result is None:
            return WorkflowResult(
                success=False,
                message="Triage agent failed.",
            )

        # Apply agent output to state
        state = self.state_manager.load()
        triaged_count = 0

        if isinstance(result, list):
            for issue_data in result:
                issue_id = issue_data.get("id")
                if issue_id and issue_id in state.issues:
                    issue = state.issues[issue_id]
                    # Overwrite with sanitized content (preserve raw in context)
                    if "title" in issue_data and issue_data["title"] != issue.title:
                        issue.context["raw_title"] = issue.title
                        issue.title = issue_data["title"]
                    if "description" in issue_data and issue_data["description"] != issue.description:
                        issue.context["raw_description"] = issue.description
                        issue.description = issue_data["description"]
                    if "affected_files" in issue_data:
                        issue.affected_files = issue_data["affected_files"]
                    if "tags" in issue_data:
                        issue.tags = issue_data["tags"]
                    if "severity" in issue_data:
                        issue.severity = IssueSeverity(issue_data["severity"])
                    issue.status = IssueStatus.triaged
                    issue.updated = datetime.now()
                    triaged_count += 1

        state.last_triage_run = datetime.now()
        self.state_manager.save(state)

        return WorkflowResult(
            success=True,
            message=f"Triaged {triaged_count} issues.",
            data={"count": triaged_count},
        )

    def run_clustering(self) -> WorkflowResult:
        """Run clustering agent on triaged issues."""
        triaged = self.state_manager.get_issues_by_status(IssueStatus.triaged)

        if not triaged:
            return WorkflowResult(
                success=True,
                message="No triaged issues to cluster.",
            )

        print(f"\n=== Clustering {len(triaged)} triaged issues ===\n")

        task_context = json.dumps(
            [i.model_dump(mode="json") for i in triaged],
            indent=2,
            default=str,
        )

        result = self._run_agent("issue-clustering", task_context)

        if result is None:
            return WorkflowResult(
                success=False,
                message="Clustering agent failed.",
            )

        # Apply agent output to state
        state = self.state_manager.load()
        cluster_count = 0

        if isinstance(result, dict):
            # Create/update clusters (accept both id/cluster_id and issue_ids/member_issue_ids)
            for cluster_data in result.get("clusters", []):
                cluster_id = (
                    cluster_data.get("id")
                    or cluster_data.get("cluster_id")
                    or f"cluster-{len(state.clusters)}"
                )
                issue_ids = (
                    cluster_data.get("issue_ids")
                    or cluster_data.get("member_issue_ids")
                    or []
                )
                cluster = IssueCluster(
                    id=cluster_id,
                    theme=cluster_data.get("theme", ""),
                    issue_ids=issue_ids,
                    affected_files=cluster_data.get("affected_files", []),
                    resolution_strategy=cluster_data.get("resolution_strategy"),
                )
                state.clusters[cluster.id] = cluster
                cluster_count += 1

            # Update issues with cluster assignments
            for issue_data in result.get("issues", []):
                issue_id = issue_data.get("id")
                if issue_id and issue_id in state.issues:
                    issue = state.issues[issue_id]
                    if "cluster_id" in issue_data:
                        issue.cluster_id = issue_data["cluster_id"]
                    if "similarity_score" in issue_data:
                        issue.similarity_score = issue_data["similarity_score"]
                    issue.status = IssueStatus.clustered
                    issue.updated = datetime.now()

        state.last_cluster_run = datetime.now()
        self.state_manager.save(state)

        return WorkflowResult(
            success=True,
            message=f"Created {cluster_count} clusters from {len(triaged)} issues.",
        )

    def run_prioritization(self) -> WorkflowResult:
        """Run prioritization agent, then human gate."""
        state = self.state_manager.load()
        to_prioritize = [
            i for i in state.issues.values()
            if i.status in (IssueStatus.triaged, IssueStatus.clustered)
        ]

        if not to_prioritize:
            return WorkflowResult(
                success=True,
                message="No issues to prioritize.",
            )

        print(f"\n=== Prioritizing {len(to_prioritize)} issues ===\n")

        task_context = json.dumps(
            {
                "issues": [i.model_dump(mode="json") for i in to_prioritize],
                "clusters": [c.model_dump(mode="json") for c in state.clusters.values()],
            },
            indent=2,
            default=str,
        )

        result = self._run_agent("issue-prioritization", task_context)

        if result is None:
            return WorkflowResult(
                success=False,
                message="Prioritization agent failed.",
            )

        # Apply agent output to state
        if isinstance(result, dict):
            # Update issues with priority scores
            for issue_data in result.get("issues", []):
                issue_id = issue_data.get("id")
                if issue_id and issue_id in state.issues:
                    issue = state.issues[issue_id]
                    if "severity" in issue_data:
                        issue.severity = IssueSeverity(issue_data["severity"])
                    if "fix_complexity" in issue_data:
                        issue.fix_complexity = issue_data["fix_complexity"]
                    if "priority_score" in issue_data:
                        issue.priority_score = issue_data["priority_score"]
                    issue.status = IssueStatus.prioritized
                    issue.updated = datetime.now()

            # Update clusters with aggregate priority (accept both id/cluster_id)
            for cluster_data in result.get("clusters", []):
                cluster_id = cluster_data.get("id") or cluster_data.get("cluster_id")
                if cluster_id and cluster_id in state.clusters:
                    cluster = state.clusters[cluster_id]
                    if "aggregate_priority" in cluster_data:
                        cluster.aggregate_priority = cluster_data["aggregate_priority"]
                    if "aggregate_severity" in cluster_data:
                        cluster.aggregate_severity = IssueSeverity(
                            cluster_data["aggregate_severity"]
                        )

        # Human gate: approve prioritization
        approved = self._gate_prioritization()
        if not approved:
            return WorkflowResult(
                success=False,
                message="Prioritization rejected by user.",
            )

        state.last_prioritize_run = datetime.now()
        self.state_manager.save(state)

        return WorkflowResult(
            success=True,
            message="Prioritization approved.",
        )

    def run_resolution(self, cluster_id: str) -> WorkflowResult:
        """Run resolution agent on an approved cluster."""
        state = self.state_manager.load()

        if cluster_id not in state.clusters:
            return WorkflowResult(
                success=False,
                message=f"Cluster {cluster_id} not found.",
            )

        cluster = state.clusters[cluster_id]
        if cluster.status != "approved":
            return WorkflowResult(
                success=False,
                message=f"Cluster {cluster_id} not approved for resolution.",
            )

        issues = [state.issues[iid] for iid in cluster.issue_ids if iid in state.issues]

        print(f"\n=== Resolving cluster: {cluster.theme} ===\n")
        print(f"Issues: {len(issues)}")
        print(f"Affected files: {', '.join(cluster.affected_files[:5])}")

        task_context = json.dumps(
            {
                "cluster": cluster.model_dump(mode="json"),
                "issues": [i.model_dump(mode="json") for i in issues],
            },
            indent=2,
            default=str,
        )

        result = self._run_agent("issue-resolution", task_context)

        if result is None:
            return WorkflowResult(
                success=False,
                message="Resolution agent failed.",
            )

        # Check if human approval needed
        needs_approval = (
            isinstance(result, dict) and result.get("action") == "needs_approval"
        )

        if needs_approval:
            user_approved = self._gate_resolution_plan()
            if not user_approved:
                return WorkflowResult(
                    success=False,
                    message="Resolution plan rejected.",
                )
            result = self._run_agent("issue-resolution", task_context, approved=True)

        # Apply resolution output to state
        if isinstance(result, dict):
            if "commit" in result:
                for issue in issues:
                    issue.resolved_by = result["commit"]
            if "notes" in result:
                for issue in issues:
                    issue.resolution_notes = result["notes"]

        # Update cluster and issues as resolved
        cluster.status = "resolved"
        for issue in issues:
            issue.status = IssueStatus.resolved
        self.state_manager.save(state)

        return WorkflowResult(
            success=True,
            message=f"Resolved cluster {cluster_id}.",
        )

    def _fast_track_resolve(self, issue: Issue) -> WorkflowResult:
        """Resolve critical issue immediately, skipping cluster/prioritize.

        Creates a singleton cluster and resolves in one state transaction.
        """
        print(f"\n=== FAST-TRACK: {issue.title[:50]} ===")
        print(f"Severity: CRITICAL - bypassing normal queue")

        # Create singleton cluster with auto-approval
        cluster = IssueCluster(
            theme=f"Critical: {issue.title}",
            issue_ids=[issue.id],
            affected_files=issue.affected_files,
            aggregate_severity=IssueSeverity.critical,
            aggregate_priority=10.0,  # Max priority
            status="approved",  # Auto-approve critical issues
        )

        # Single state load - will be saved in run_resolution()
        state = self.state_manager.load()
        state.clusters[cluster.id] = cluster
        issue.cluster_id = cluster.id
        issue.status = IssueStatus.prioritized
        state.issues[issue.id] = issue  # Update issue in state
        self.state_manager.save(state)

        # Resolve - run_resolution() handles its own state management
        return self.run_resolution(cluster.id)

    # ========================================================================
    # Human Gates
    # ========================================================================

    def _gate_prioritization(self) -> bool:
        """Human gate: approve priority ranking."""
        if self.auto_approve:
            print("\n[--yes] Auto-approving prioritization")
            return True

        state = self.state_manager.load()

        print("\n" + "=" * 60)
        print("HUMAN GATE: Priority Review")
        print("=" * 60)

        clusters = sorted(
            state.clusters.values(),
            key=lambda c: c.aggregate_priority,
            reverse=True,
        )[:10]

        if clusters:
            print("\nTop clusters by priority:\n")
            for i, cluster in enumerate(clusters, 1):
                # Handle both enum and string (due to use_enum_values=True)
                sev = cluster.aggregate_severity
                sev_str = str(sev.value if hasattr(sev, "value") else sev)
                print(f"{i}. [{sev_str}] {cluster.theme}")
                print(f"   Priority: {cluster.aggregate_priority:.2f}")
                print(f"   Issues: {len(cluster.issue_ids)}")
                print()
        else:
            issues = sorted(
                state.issues.values(),
                key=lambda i: i.priority_score or 0,
                reverse=True,
            )[:10]

            print("\nTop issues by priority:\n")
            for i, issue in enumerate(issues, 1):
                title = issue.title
                score = issue.priority_score or 0
                # Handle both enum and string (due to use_enum_values=True)
                sev = issue.severity
                severity = str(sev.value if hasattr(sev, "value") else sev) if sev else "unknown"
                print(f"{i}. [{severity}] {title[:50]}")
                print(f"   Priority: {score:.2f}")
                print()

        try:
            response = input("\nApprove this ranking? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        return response in ("", "y", "yes")

    def _gate_resolution_plan(self) -> bool:
        """Human gate: approve low-confidence resolution plan."""
        if self.auto_approve:
            print("\n[--yes] Auto-approving resolution plan")
            return True

        print("\n" + "=" * 60)
        print("HUMAN GATE: Resolution Plan Approval")
        print("=" * 60)
        print("\nThe agent is not confident about the fix approach.")
        print("Review the plan above and decide whether to proceed.\n")

        try:
            response = input("Approve this plan? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        return response in ("y", "yes")

    def approve_cluster(self, cluster_id: str) -> WorkflowResult:
        """Approve a cluster for resolution."""
        state = self.state_manager.load()

        if cluster_id not in state.clusters:
            return WorkflowResult(
                success=False,
                message=f"Cluster {cluster_id} not found.",
            )

        cluster = state.clusters[cluster_id]
        cluster.status = "approved"
        self.state_manager.save(state)

        return WorkflowResult(
            success=True,
            message=f"Cluster {cluster_id} approved for resolution.",
        )

    # ========================================================================
    # Full Pipeline
    # ========================================================================

    def process(self) -> WorkflowResult:
        """Run the full pipeline: triage → cluster → prioritize → resolve.

        Critical issues are fast-tracked after triage, skipping cluster/prioritize.
        """
        print("\n" + "=" * 60)
        print("ISSUE PROCESSING PIPELINE")
        print("=" * 60)

        result = self.run_triage()
        if not result.success:
            return result
        print(f"\n[1/4] Triage: {result.message}")

        # Fast-track critical issues (skip clustering/prioritization)
        state = self.state_manager.load()
        critical_issues = [
            i for i in state.issues.values()
            if i.status == IssueStatus.triaged and i.severity == IssueSeverity.critical
        ]
        if critical_issues:
            print(f"\n=== Fast-tracking {len(critical_issues)} critical issues ===")
            fast_track_failures = []
            for issue in critical_issues:
                ft_result = self._fast_track_resolve(issue)
                if not ft_result.success:
                    fast_track_failures.append((issue.id, ft_result.message))
            if fast_track_failures:
                print(f"\nWarning: {len(fast_track_failures)} fast-track resolutions failed:")
                for issue_id, msg in fast_track_failures:
                    print(f"  - {issue_id}: {msg}")

        result = self.run_clustering()
        if not result.success:
            return result
        print(f"\n[2/4] Clustering: {result.message}")

        result = self.run_prioritization()
        if not result.success:
            return result
        print(f"\n[3/4] Prioritization: {result.message}")

        state = self.state_manager.load()
        approved_clusters = [
            c for c in state.clusters.values()
            if c.status == "approved"
        ]

        if not approved_clusters:
            print("\nNo clusters approved for resolution.")
            print("Approve clusters with: issue-workflow approve <cluster-id>")
            return WorkflowResult(
                success=True,
                message="Pipeline paused. Approve clusters to continue.",
            )

        for cluster in approved_clusters:
            result = self.run_resolution(cluster.id)
            print(f"\n[4/4] Resolution ({cluster.id}): {result.message}")

        return WorkflowResult(
            success=True,
            message="Pipeline complete.",
        )

    # ========================================================================
    # Management Commands
    # ========================================================================

    def list_issues(self, status: IssueStatus | None = None) -> list[Issue]:
        """List issues, optionally filtered by status."""
        state = self.state_manager.load()
        issues = list(state.issues.values())

        if status:
            issues = [i for i in issues if i.status == status]

        return sorted(issues, key=lambda i: i.priority_score or 0, reverse=True)

    def list_clusters(self) -> list[IssueCluster]:
        """List all clusters."""
        state = self.state_manager.load()
        return sorted(
            state.clusters.values(),
            key=lambda c: c.aggregate_priority,
            reverse=True,
        )

    def defer_issue(self, issue_id: str) -> WorkflowResult:
        """Mark issue as deferred."""
        state = self.state_manager.load()
        if issue_id not in state.issues:
            return WorkflowResult(False, f"Issue {issue_id} not found.")

        state.issues[issue_id].status = IssueStatus.deferred
        state.issues[issue_id].updated = datetime.now()
        self.state_manager.save(state)

        return WorkflowResult(True, f"Issue {issue_id} deferred.")

    def wontfix_issue(self, issue_id: str) -> WorkflowResult:
        """Mark issue as won't fix."""
        state = self.state_manager.load()
        if issue_id not in state.issues:
            return WorkflowResult(False, f"Issue {issue_id} not found.")

        state.issues[issue_id].status = IssueStatus.wont_fix
        state.issues[issue_id].updated = datetime.now()
        self.state_manager.save(state)

        return WorkflowResult(True, f"Issue {issue_id} marked as won't fix.")
