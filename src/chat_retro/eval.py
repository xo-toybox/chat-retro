"""Evaluation and feedback collection for chat-retro.

Provides mechanisms for:
- Quality prompts after analysis
- Rating patterns/insights
- Gap detection (expected but missing)
- Feedback aggregation
- Issue reporting
"""

import json
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

from pydantic import BaseModel, Field


# ============================================================================
# Pydantic models for feedback data
# ============================================================================


class PatternRating(BaseModel):
    """Rating for a single pattern or insight."""

    pattern_id: str
    rating: int = Field(ge=1, le=5)
    timestamp: datetime = Field(default_factory=datetime.now)
    comment: str | None = None


class QualityResponse(BaseModel):
    """Response to a quality question."""

    question_id: str
    question_text: str
    response: str
    rating: int | None = Field(default=None, ge=1, le=5)
    timestamp: datetime = Field(default_factory=datetime.now)


class GapReport(BaseModel):
    """Report of an expected but missing feature/insight."""

    description: str
    category: str = "general"
    priority: Literal["low", "medium", "high"] = "medium"
    timestamp: datetime = Field(default_factory=datetime.now)


class FeedbackSummary(BaseModel):
    """Aggregated feedback statistics."""

    total_ratings: int = 0
    average_rating: float | None = None
    ratings_by_score: dict[int, int] = Field(default_factory=dict)
    total_gaps_reported: int = 0
    gaps_by_category: dict[str, int] = Field(default_factory=dict)
    quality_responses: int = 0


class SessionFeedback(BaseModel):
    """All feedback collected in a session."""

    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    ratings: list[PatternRating] = Field(default_factory=list)
    quality_responses: list[QualityResponse] = Field(default_factory=list)
    gaps: list[GapReport] = Field(default_factory=list)


# ============================================================================
# Quality question templates
# ============================================================================

QUALITY_QUESTIONS = [
    {
        "id": "insight_accuracy",
        "text": "How accurate were the insights about your conversation patterns?",
        "type": "rating",
    },
    {
        "id": "insight_actionable",
        "text": "Were the suggestions actionable? Could you apply them?",
        "type": "rating",
    },
    {
        "id": "missing_patterns",
        "text": "Were there any patterns you expected to see but didn't?",
        "type": "text",
    },
    {
        "id": "most_useful",
        "text": "Which insight or pattern was most useful to you?",
        "type": "text",
    },
    {
        "id": "overall_value",
        "text": "Overall, how valuable was this analysis session?",
        "type": "rating",
    },
]

GAP_CATEGORIES = [
    "topic_detection",
    "sentiment_analysis",
    "temporal_patterns",
    "prompt_suggestions",
    "visualization",
    "other",
]


# ============================================================================
# Feedback manager
# ============================================================================


@dataclass
class FeedbackManager:
    """Manages feedback collection and persistence."""

    feedback_dir: Path = field(default_factory=lambda: Path(".chat-retro/feedback"))
    current_session: SessionFeedback | None = None

    def __post_init__(self) -> None:
        self.feedback_dir.mkdir(parents=True, exist_ok=True)

    def start_session(self, session_id: str) -> None:
        """Start a new feedback session."""
        self.current_session = SessionFeedback(session_id=session_id)

    def rate_pattern(
        self,
        pattern_id: str,
        rating: int,
        comment: str | None = None,
    ) -> PatternRating:
        """Rate a pattern (1-5 scale)."""
        if not self.current_session:
            raise ValueError("No active session. Call start_session first.")

        pattern_rating = PatternRating(
            pattern_id=pattern_id,
            rating=rating,
            comment=comment,
        )
        self.current_session.ratings.append(pattern_rating)
        return pattern_rating

    def thumbs_rating(self, pattern_id: str, thumbs_up: bool) -> PatternRating:
        """Rate a pattern with thumbs up/down (converted to 5/1)."""
        rating = 5 if thumbs_up else 1
        return self.rate_pattern(pattern_id, rating)

    def answer_quality_question(
        self,
        question_id: str,
        question_text: str,
        response: str,
        rating: int | None = None,
    ) -> QualityResponse:
        """Record a quality question response."""
        if not self.current_session:
            raise ValueError("No active session. Call start_session first.")

        quality_response = QualityResponse(
            question_id=question_id,
            question_text=question_text,
            response=response,
            rating=rating,
        )
        self.current_session.quality_responses.append(quality_response)
        return quality_response

    def report_gap(
        self,
        description: str,
        category: str = "general",
        priority: Literal["low", "medium", "high"] = "medium",
    ) -> GapReport:
        """Report an expected but missing feature."""
        if not self.current_session:
            raise ValueError("No active session. Call start_session first.")

        gap = GapReport(
            description=description,
            category=category,
            priority=priority,
        )
        self.current_session.gaps.append(gap)
        return gap

    def save_session(self) -> Path:
        """Save current session feedback to file."""
        if not self.current_session:
            raise ValueError("No active session to save.")

        filename = f"feedback_{self.current_session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.feedback_dir / filename
        filepath.write_text(self.current_session.model_dump_json(indent=2))
        return filepath

    def load_all_feedback(self) -> list[SessionFeedback]:
        """Load all saved feedback files."""
        feedback_files = list(self.feedback_dir.glob("feedback_*.json"))
        sessions = []

        for f in feedback_files:
            try:
                data = json.loads(f.read_text())
                sessions.append(SessionFeedback.model_validate(data))
            except (json.JSONDecodeError, ValueError):
                continue

        return sessions

    def aggregate_feedback(self) -> FeedbackSummary:
        """Aggregate feedback across all sessions."""
        sessions = self.load_all_feedback()

        all_ratings: list[int] = []
        ratings_by_score: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        gaps_by_category: dict[str, int] = {}
        quality_count = 0

        for session in sessions:
            for rating in session.ratings:
                all_ratings.append(rating.rating)
                ratings_by_score[rating.rating] = (
                    ratings_by_score.get(rating.rating, 0) + 1
                )

            for gap in session.gaps:
                gaps_by_category[gap.category] = (
                    gaps_by_category.get(gap.category, 0) + 1
                )

            quality_count += len(session.quality_responses)

        avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else None

        return FeedbackSummary(
            total_ratings=len(all_ratings),
            average_rating=round(avg_rating, 2) if avg_rating else None,
            ratings_by_score=ratings_by_score,
            total_gaps_reported=sum(gaps_by_category.values()),
            gaps_by_category=gaps_by_category,
            quality_responses=quality_count,
        )

    def get_low_rated_patterns(
        self, threshold: float = 2.5
    ) -> list[tuple[str, float, int]]:
        """Get patterns with consistently low ratings.

        Returns list of (pattern_id, avg_rating, count).
        """
        sessions = self.load_all_feedback()
        pattern_ratings: dict[str, list[int]] = {}

        for session in sessions:
            for rating in session.ratings:
                if rating.pattern_id not in pattern_ratings:
                    pattern_ratings[rating.pattern_id] = []
                pattern_ratings[rating.pattern_id].append(rating.rating)

        low_rated = []
        for pattern_id, ratings in pattern_ratings.items():
            avg = sum(ratings) / len(ratings)
            if avg <= threshold:
                low_rated.append((pattern_id, round(avg, 2), len(ratings)))

        return sorted(low_rated, key=lambda x: x[1])


# ============================================================================
# Issue reporter
# ============================================================================


@dataclass
class IssueReporter:
    """Quick path to report issues."""

    repo_url: str = "https://github.com/example/chat-retro"
    local_issues_dir: Path = field(
        default_factory=lambda: Path(".chat-retro/issues")
    )

    def __post_init__(self) -> None:
        self.local_issues_dir.mkdir(parents=True, exist_ok=True)

    def create_github_issue_url(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> str:
        """Generate a GitHub issue URL with pre-filled content."""
        params: dict[str, str] = {
            "title": title,
            "body": body,
        }
        if labels:
            params["labels"] = ",".join(labels)

        return f"{self.repo_url}/issues/new?{urlencode(params)}"

    def open_github_issue(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> str:
        """Open browser to create GitHub issue."""
        url = self.create_github_issue_url(title, body, labels)
        webbrowser.open(url)
        return url

    def save_local_issue(
        self,
        title: str,
        description: str,
        category: str = "bug",
        context: dict | None = None,
    ) -> Path:
        """Save issue locally for offline reporting."""
        import uuid

        issue = {
            "title": title,
            "description": description,
            "category": category,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
            "reported": False,
        }

        # Include UUID to ensure uniqueness even if called rapidly
        unique_id = uuid.uuid4().hex[:8]
        filename = f"issue_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{unique_id}.json"
        filepath = self.local_issues_dir / filename
        filepath.write_text(json.dumps(issue, indent=2))
        return filepath

    def get_pending_issues(self) -> list[dict]:
        """Get locally saved issues that haven't been reported."""
        issues = []
        for f in self.local_issues_dir.glob("issue_*.json"):
            try:
                issue = json.loads(f.read_text())
                if not issue.get("reported", False):
                    issue["file"] = str(f)
                    issues.append(issue)
            except (json.JSONDecodeError, ValueError):
                continue
        return issues

    def mark_issue_reported(self, filepath: str | Path) -> None:
        """Mark a local issue as reported."""
        path = Path(filepath)
        if path.exists():
            issue = json.loads(path.read_text())
            issue["reported"] = True
            path.write_text(json.dumps(issue, indent=2))


# ============================================================================
# CLI integration helpers
# ============================================================================


def get_quality_questions() -> list[dict]:
    """Get quality questions for CLI prompts."""
    return QUALITY_QUESTIONS.copy()


def get_gap_categories() -> list[str]:
    """Get available gap categories."""
    return GAP_CATEGORIES.copy()


def format_feedback_summary(summary: FeedbackSummary) -> str:
    """Format feedback summary as readable string."""
    lines = [
        "=== Feedback Summary ===",
        "",
        f"Total ratings: {summary.total_ratings}",
    ]

    if summary.average_rating is not None:
        lines.append(f"Average rating: {summary.average_rating}/5.0")

    if summary.ratings_by_score:
        lines.append("\nRating distribution:")
        for score in range(5, 0, -1):
            count = summary.ratings_by_score.get(score, 0)
            bar = "█" * count
            lines.append(f"  {score}★: {bar} ({count})")

    if summary.total_gaps_reported > 0:
        lines.append(f"\nGaps reported: {summary.total_gaps_reported}")
        for category, count in sorted(
            summary.gaps_by_category.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            lines.append(f"  - {category}: {count}")

    lines.append(f"\nQuality responses: {summary.quality_responses}")

    return "\n".join(lines)
