"""Shared issue types for chat-retro and issue-workflow."""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class IssueStatus(str, Enum):
    """Issue lifecycle status."""

    draft = "draft"
    triaged = "triaged"
    clustered = "clustered"
    prioritized = "prioritized"
    in_progress = "in_progress"
    resolved = "resolved"
    wont_fix = "wont_fix"
    deferred = "deferred"


class IssueSeverity(str, Enum):
    """Issue severity level."""

    critical = "critical"  # Crashes, data loss
    high = "high"  # Major functionality broken
    medium = "medium"  # Minor bugs, UX issues
    low = "low"  # Cosmetic, nice-to-have


class Issue(BaseModel):
    """Issue with lifecycle tracking."""

    model_config = {"use_enum_values": True}

    id: str = Field(default_factory=lambda: uuid4().hex[:12])

    # Content (draft = raw, public = sanitized)
    title: str
    description: str
    sanitized_title: str | None = None
    sanitized_description: str | None = None

    # Classification
    category: str = "bug"
    tags: list[str] = Field(default_factory=list)
    affected_files: list[str] = Field(default_factory=list)

    # Lifecycle
    status: IssueStatus = IssueStatus.draft
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    # Clustering
    cluster_id: str | None = None
    similarity_score: float | None = None

    # Ranking (severity=None means triage agent will assign)
    severity: IssueSeverity | None = None
    frequency: int = 1
    fix_complexity: str | None = None  # trivial, small, medium, large
    priority_score: float | None = None

    # Resolution
    resolution_notes: str | None = None
    resolved_by: str | None = None  # PR/commit reference

    # Context (may contain sensitive data - never in public view)
    context: dict = Field(default_factory=dict)


class IssueCluster(BaseModel):
    """Group of related issues for batch resolution."""

    model_config = {"use_enum_values": True}

    id: str = Field(default_factory=lambda: f"cluster-{uuid4().hex[:8]}")

    # Content
    theme: str  # Agent-generated cluster description
    issue_ids: list[str] = Field(default_factory=list)

    # Classification
    affected_files: list[str] = Field(default_factory=list)
    primary_category: str = "bug"

    # Ranking
    aggregate_severity: IssueSeverity = IssueSeverity.medium
    aggregate_priority: float = 0.0

    # Resolution
    resolution_strategy: str | None = None  # single_pr, multiple_prs
    status: str = "pending"  # pending, approved, in_progress, resolved


class IssueState(BaseModel):
    """Persistent issue management state."""

    schema_version: int = 1

    issues: dict[str, Issue] = Field(default_factory=dict)
    clusters: dict[str, IssueCluster] = Field(default_factory=dict)

    # Processing metadata
    last_triage_run: datetime | None = None
    last_cluster_run: datetime | None = None
    last_prioritize_run: datetime | None = None

    # Configuration
    cluster_threshold: float = 0.7
