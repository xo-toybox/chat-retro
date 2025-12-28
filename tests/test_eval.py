"""Tests for evaluation and feedback collection."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from chat_retro.eval import (
    GAP_CATEGORIES,
    QUALITY_QUESTIONS,
    FeedbackManager,
    FeedbackSummary,
    GapReport,
    PatternRating,
    QualityResponse,
    SessionFeedback,
    format_feedback_summary,
    get_gap_categories,
    get_quality_questions,
)
from shared import IssueReporter


class TestPatternRating:
    """Test PatternRating model."""

    def test_creation(self) -> None:
        rating = PatternRating(pattern_id="pattern-1", rating=4)
        assert rating.pattern_id == "pattern-1"
        assert rating.rating == 4
        assert rating.comment is None

    def test_with_comment(self) -> None:
        rating = PatternRating(
            pattern_id="pattern-1",
            rating=5,
            comment="Very useful!",
        )
        assert rating.comment == "Very useful!"

    def test_rating_bounds(self) -> None:
        # Valid ratings
        PatternRating(pattern_id="p", rating=1)
        PatternRating(pattern_id="p", rating=5)

        # Invalid ratings
        with pytest.raises(ValueError):
            PatternRating(pattern_id="p", rating=0)
        with pytest.raises(ValueError):
            PatternRating(pattern_id="p", rating=6)

    def test_has_timestamp(self) -> None:
        rating = PatternRating(pattern_id="p", rating=3)
        assert rating.timestamp is not None


class TestQualityResponse:
    """Test QualityResponse model."""

    def test_creation(self) -> None:
        response = QualityResponse(
            question_id="q1",
            question_text="How useful?",
            response="Very useful",
        )
        assert response.question_id == "q1"
        assert response.response == "Very useful"
        assert response.rating is None

    def test_with_rating(self) -> None:
        response = QualityResponse(
            question_id="q1",
            question_text="Rate accuracy",
            response="Good",
            rating=4,
        )
        assert response.rating == 4


class TestGapReport:
    """Test GapReport model."""

    def test_creation(self) -> None:
        gap = GapReport(description="Missing topic X")
        assert gap.description == "Missing topic X"
        assert gap.category == "general"
        assert gap.priority == "medium"

    def test_with_category_and_priority(self) -> None:
        gap = GapReport(
            description="No sentiment for morning chats",
            category="sentiment_analysis",
            priority="high",
        )
        assert gap.category == "sentiment_analysis"
        assert gap.priority == "high"


class TestSessionFeedback:
    """Test SessionFeedback model."""

    def test_creation(self) -> None:
        session = SessionFeedback(session_id="sess-123")
        assert session.session_id == "sess-123"
        assert session.ratings == []
        assert session.quality_responses == []
        assert session.gaps == []

    def test_with_data(self) -> None:
        session = SessionFeedback(
            session_id="sess-123",
            ratings=[PatternRating(pattern_id="p1", rating=4)],
            gaps=[GapReport(description="Missing X")],
        )
        assert len(session.ratings) == 1
        assert len(session.gaps) == 1


class TestFeedbackSummary:
    """Test FeedbackSummary model."""

    def test_default_values(self) -> None:
        summary = FeedbackSummary()
        assert summary.total_ratings == 0
        assert summary.average_rating is None
        assert summary.total_gaps_reported == 0

    def test_with_data(self) -> None:
        summary = FeedbackSummary(
            total_ratings=10,
            average_rating=3.5,
            ratings_by_score={1: 1, 2: 2, 3: 2, 4: 3, 5: 2},
        )
        assert summary.total_ratings == 10
        assert summary.average_rating == 3.5


class TestFeedbackManager:
    """Test FeedbackManager class."""

    def test_start_session(self, tmp_path: Path) -> None:
        manager = FeedbackManager(feedback_dir=tmp_path / "feedback")
        manager.start_session("test-session")
        assert manager.current_session is not None
        assert manager.current_session.session_id == "test-session"

    def test_rate_pattern(self, tmp_path: Path) -> None:
        manager = FeedbackManager(feedback_dir=tmp_path / "feedback")
        manager.start_session("test-session")

        rating = manager.rate_pattern("pattern-1", 4, "Good insight")
        assert rating.rating == 4
        assert rating.comment == "Good insight"
        assert len(manager.current_session.ratings) == 1

    def test_rate_pattern_no_session(self, tmp_path: Path) -> None:
        manager = FeedbackManager(feedback_dir=tmp_path / "feedback")
        with pytest.raises(ValueError, match="No active session"):
            manager.rate_pattern("p", 3)

    def test_thumbs_rating(self, tmp_path: Path) -> None:
        manager = FeedbackManager(feedback_dir=tmp_path / "feedback")
        manager.start_session("test")

        up = manager.thumbs_rating("p1", thumbs_up=True)
        down = manager.thumbs_rating("p2", thumbs_up=False)

        assert up.rating == 5
        assert down.rating == 1

    def test_answer_quality_question(self, tmp_path: Path) -> None:
        manager = FeedbackManager(feedback_dir=tmp_path / "feedback")
        manager.start_session("test")

        response = manager.answer_quality_question(
            "q1",
            "How useful?",
            "Very useful",
            rating=5,
        )
        assert response.response == "Very useful"
        assert len(manager.current_session.quality_responses) == 1

    def test_report_gap(self, tmp_path: Path) -> None:
        manager = FeedbackManager(feedback_dir=tmp_path / "feedback")
        manager.start_session("test")

        gap = manager.report_gap(
            "Missing sentiment for code reviews",
            category="sentiment_analysis",
            priority="high",
        )
        assert gap.category == "sentiment_analysis"
        assert len(manager.current_session.gaps) == 1

    def test_save_and_load_session(self, tmp_path: Path) -> None:
        manager = FeedbackManager(feedback_dir=tmp_path / "feedback")
        manager.start_session("test-save")
        manager.rate_pattern("p1", 4)
        manager.report_gap("Missing X")

        filepath = manager.save_session()
        assert filepath.exists()

        # Load and verify
        sessions = manager.load_all_feedback()
        assert len(sessions) == 1
        assert sessions[0].session_id == "test-save"
        assert len(sessions[0].ratings) == 1

    def test_aggregate_feedback(self, tmp_path: Path) -> None:
        manager = FeedbackManager(feedback_dir=tmp_path / "feedback")

        # Create multiple sessions
        manager.start_session("session-1")
        manager.rate_pattern("p1", 5)
        manager.rate_pattern("p2", 3)
        manager.report_gap("Gap 1", category="topic_detection")
        manager.save_session()

        manager.start_session("session-2")
        manager.rate_pattern("p1", 4)
        manager.report_gap("Gap 2", category="topic_detection")
        manager.report_gap("Gap 3", category="visualization")
        manager.save_session()

        summary = manager.aggregate_feedback()
        assert summary.total_ratings == 3
        assert summary.average_rating == 4.0  # (5+3+4)/3
        assert summary.total_gaps_reported == 3
        assert summary.gaps_by_category["topic_detection"] == 2
        assert summary.gaps_by_category["visualization"] == 1

    def test_get_low_rated_patterns(self, tmp_path: Path) -> None:
        manager = FeedbackManager(feedback_dir=tmp_path / "feedback")

        manager.start_session("s1")
        manager.rate_pattern("good-pattern", 5)
        manager.rate_pattern("bad-pattern", 1)
        manager.rate_pattern("bad-pattern", 2)
        manager.save_session()

        low_rated = manager.get_low_rated_patterns(threshold=2.5)
        assert len(low_rated) == 1
        assert low_rated[0][0] == "bad-pattern"
        assert low_rated[0][1] == 1.5  # avg of 1 and 2


class TestIssueReporter:
    """Test IssueReporter class."""

    def test_create_github_issue_url(self) -> None:
        reporter = IssueReporter(repo_url="https://github.com/test/repo")
        url = reporter.create_github_issue_url(
            title="Bug report",
            body="Description here",
            labels=["bug", "feedback"],
        )
        assert "https://github.com/test/repo/issues/new" in url
        assert "title=Bug+report" in url
        assert "labels=bug%2Cfeedback" in url

    def test_save_draft_issue(self, tmp_path: Path) -> None:
        reporter = IssueReporter(drafts_dir=tmp_path / "drafts")
        filepath = reporter.save_draft_issue(
            title="Test issue",
            description="Something is wrong",
            category="bug",
            context={"session": "123"},
        )

        assert filepath.exists()
        issue = json.loads(filepath.read_text())
        assert issue["title"] == "Test issue"
        assert issue["status"] == "draft"
        assert issue["context"]["session"] == "123"

    def test_get_pending_drafts(self, tmp_path: Path) -> None:
        reporter = IssueReporter(drafts_dir=tmp_path / "drafts")
        reporter.save_draft_issue("Issue 1", "Desc 1")
        reporter.save_draft_issue("Issue 2", "Desc 2")

        pending = reporter.get_pending_drafts()
        assert len(pending) == 2


class TestQualityQuestions:
    """Test quality question utilities."""

    def test_get_quality_questions(self) -> None:
        questions = get_quality_questions()
        assert len(questions) > 0
        assert all("id" in q for q in questions)
        assert all("text" in q for q in questions)
        assert all("type" in q for q in questions)

    def test_question_types(self) -> None:
        questions = get_quality_questions()
        types = {q["type"] for q in questions}
        assert "rating" in types
        assert "text" in types


class TestGapCategories:
    """Test gap category utilities."""

    def test_get_gap_categories(self) -> None:
        categories = get_gap_categories()
        assert len(categories) > 0
        assert "topic_detection" in categories
        assert "sentiment_analysis" in categories
        assert "other" in categories


class TestFormatFeedbackSummary:
    """Test feedback summary formatting."""

    def test_format_empty_summary(self) -> None:
        summary = FeedbackSummary()
        text = format_feedback_summary(summary)
        assert "Total ratings: 0" in text

    def test_format_with_ratings(self) -> None:
        summary = FeedbackSummary(
            total_ratings=10,
            average_rating=4.2,
            ratings_by_score={1: 0, 2: 1, 3: 2, 4: 3, 5: 4},
        )
        text = format_feedback_summary(summary)
        assert "Average rating: 4.2/5.0" in text
        assert "Rating distribution:" in text

    def test_format_with_gaps(self) -> None:
        summary = FeedbackSummary(
            total_gaps_reported=5,
            gaps_by_category={"topic_detection": 3, "other": 2},
        )
        text = format_feedback_summary(summary)
        assert "Gaps reported: 5" in text
        assert "topic_detection: 3" in text
