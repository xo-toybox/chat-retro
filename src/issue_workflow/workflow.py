"""Issue workflow orchestration for the agentic pipeline.

Pipeline: draft → triaged → clustered → prioritized → resolved
Human gates: prioritization approval, low-confidence resolution approval
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)

from shared import Issue, IssueCluster, IssueStatus

from .agents import get_issue_agents
from .state_manager import IssueStateManager


@dataclass
class WorkflowResult:
    """Result of a workflow step."""

    success: bool
    message: str
    data: dict = field(default_factory=dict)


class IssueWorkflow:
    """Orchestrates the issue management workflow."""

    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd or Path.cwd()
        self.state_manager = IssueStateManager()
        self._client: ClaudeSDKClient | None = None

    def _build_options(self, system_prompt: str) -> ClaudeAgentOptions:
        """Build SDK options for workflow agents."""
        return ClaudeAgentOptions(
            system_prompt=system_prompt,
            permission_mode="acceptEdits",
            cwd=str(self.cwd),
            agents=get_issue_agents(),
        )

    async def _run_agent(self, agent_name: str, prompt: str) -> str:
        """Run an agent and collect its response."""
        system_prompt = f"You are the {agent_name} agent. Follow your instructions precisely."

        options = self._build_options(system_prompt)
        response_text = ""

        async with ClaudeSDKClient(options) as client:
            await client.query(prompt)

            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text
                            print(block.text)

        return response_text

    # ========================================================================
    # Pipeline Steps
    # ========================================================================

    async def run_triage(self) -> WorkflowResult:
        """Run triage agent on all draft issues."""
        drafts = self.state_manager.get_drafts()

        if not drafts:
            return WorkflowResult(
                success=True,
                message="No draft issues to triage.",
            )

        print(f"\n=== Triaging {len(drafts)} draft issues ===\n")

        drafts_json = json.dumps(
            [d.model_dump(mode="json") for d in drafts],
            indent=2,
            default=str,
        )

        prompt = f"""Triage these draft issues:

{drafts_json}

For each issue:
1. Create sanitized_title and sanitized_description (remove PII, user paths)
2. Search codebase for affected_files
3. Assign appropriate tags
4. Check for duplicates
5. Update status to "triaged"

Output the updated issues as a JSON array."""

        await self._run_agent("issue-triage", prompt)

        state = self.state_manager.load()
        state.last_triage_run = datetime.now()
        self.state_manager.save(state)

        return WorkflowResult(
            success=True,
            message=f"Triaged {len(drafts)} issues.",
            data={"count": len(drafts)},
        )

    async def run_clustering(self) -> WorkflowResult:
        """Run clustering agent on triaged issues."""
        triaged = self.state_manager.get_issues_by_status(IssueStatus.triaged)

        if not triaged:
            return WorkflowResult(
                success=True,
                message="No triaged issues to cluster.",
            )

        print(f"\n=== Clustering {len(triaged)} triaged issues ===\n")

        issues_json = json.dumps(
            [i.model_dump(mode="json") for i in triaged],
            indent=2,
            default=str,
        )

        prompt = f"""Cluster these triaged issues by affected files:

{issues_json}

Group issues that:
1. Touch the same file(s)
2. Have the same error pattern
3. Could be fixed together

Output:
1. Updated issues with cluster_id
2. IssueCluster records with theme and resolution_strategy

Format as JSON: {{"issues": [...], "clusters": [...]}}"""

        await self._run_agent("issue-clustering", prompt)

        state = self.state_manager.load()
        state.last_cluster_run = datetime.now()
        self.state_manager.save(state)

        return WorkflowResult(
            success=True,
            message=f"Clustered {len(triaged)} issues.",
        )

    async def run_prioritization(self) -> WorkflowResult:
        """Run prioritization agent, then human gate."""
        state = self.state_manager.load()
        clustered = [
            i for i in state.issues.values()
            if i.status in (IssueStatus.triaged, IssueStatus.clustered)
        ]

        if not clustered:
            return WorkflowResult(
                success=True,
                message="No issues to prioritize.",
            )

        print(f"\n=== Prioritizing {len(clustered)} issues ===\n")

        issues_json = json.dumps(
            [i.model_dump(mode="json") for i in clustered],
            indent=2,
            default=str,
        )
        clusters_json = json.dumps(
            [c.model_dump(mode="json") for c in state.clusters.values()],
            indent=2,
            default=str,
        )

        prompt = f"""Prioritize these issues and clusters:

Issues:
{issues_json}

Clusters:
{clusters_json}

For each issue:
1. Assess severity and fix_complexity
2. Compute priority_score
3. Update status to "prioritized"

For each cluster:
1. Compute aggregate_priority (max of members)

Output ranked list as JSON, sorted by priority descending."""

        await self._run_agent("issue-prioritization", prompt)

        # Human gate: approve prioritization
        approved = await self._gate_prioritization()
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

    async def run_resolution(self, cluster_id: str) -> WorkflowResult:
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

        cluster_json = cluster.model_dump_json(indent=2)
        issues_json = json.dumps(
            [i.model_dump(mode="json") for i in issues],
            indent=2,
            default=str,
        )

        prompt = f"""Resolve this issue cluster:

Cluster:
{cluster_json}

Member Issues:
{issues_json}

Analyze root cause and assess confidence:
- HIGH confidence: implement fix directly
- LOW confidence: output fix plan for human approval

Output:
- For HIGH: {{"action": "implemented", "commit": "...", "notes": "..."}}
- For LOW: {{"action": "needs_approval", "plan": {{...}}, "questions": [...]}}"""

        response = await self._run_agent("issue-resolution", prompt)

        # Check if human approval needed
        if '"needs_approval"' in response:
            approved = await self._gate_resolution_plan()
            if not approved:
                return WorkflowResult(
                    success=False,
                    message="Resolution plan rejected.",
                )
            prompt += "\n\nHuman approved the plan. Proceed with implementation."
            await self._run_agent("issue-resolution", prompt)

        # Update cluster and issues as resolved
        cluster.status = "resolved"
        for issue in issues:
            issue.status = IssueStatus.resolved
        self.state_manager.save(state)

        return WorkflowResult(
            success=True,
            message=f"Resolved cluster {cluster_id}.",
        )

    # ========================================================================
    # Human Gates
    # ========================================================================

    async def _gate_prioritization(self) -> bool:
        """Human gate: approve priority ranking."""
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
                print(f"{i}. [{cluster.aggregate_severity.value}] {cluster.theme}")
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
                title = issue.sanitized_title or issue.title
                score = issue.priority_score or 0
                print(f"{i}. [{issue.severity.value}] {title[:50]}")
                print(f"   Priority: {score:.2f}")
                print()

        try:
            response = input("\nApprove this ranking? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        return response in ("", "y", "yes")

    async def _gate_resolution_plan(self) -> bool:
        """Human gate: approve low-confidence resolution plan."""
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

    async def approve_cluster(self, cluster_id: str) -> WorkflowResult:
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

    async def process(self) -> WorkflowResult:
        """Run the full pipeline: triage → cluster → prioritize → resolve."""
        print("\n" + "=" * 60)
        print("ISSUE PROCESSING PIPELINE")
        print("=" * 60)

        result = await self.run_triage()
        if not result.success:
            return result
        print(f"\n[1/4] Triage: {result.message}")

        result = await self.run_clustering()
        if not result.success:
            return result
        print(f"\n[2/4] Clustering: {result.message}")

        result = await self.run_prioritization()
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
            result = await self.run_resolution(cluster.id)
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
