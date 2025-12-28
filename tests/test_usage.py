"""Tests for usage tracking and metrics collection."""

import time
from unittest.mock import MagicMock

import pytest

from chat_retro.usage import ErrorRecord, TurnTiming, UsageReport


class TestTurnTiming:
    """Tests for TurnTiming dataclass."""

    def test_creation(self):
        timing = TurnTiming(
            turn_number=1,
            latency_seconds=2.5,
            timestamp="2024-01-01T12:00:00",
        )
        assert timing.turn_number == 1
        assert timing.latency_seconds == 2.5
        assert timing.timestamp == "2024-01-01T12:00:00"


class TestErrorRecord:
    """Tests for ErrorRecord dataclass."""

    def test_creation(self):
        record = ErrorRecord(
            timestamp="2024-01-01T12:00:00",
            error_type="ValueError",
            message="test error",
            turn=3,
        )
        assert record.error_type == "ValueError"
        assert record.message == "test error"
        assert record.turn == 3


class TestUsageReport:
    """Tests for UsageReport metrics tracking."""

    def test_turn_timing(self):
        """Test latency tracking per turn."""
        report = UsageReport()

        report.start_turn()
        time.sleep(0.01)  # Small delay to ensure measurable latency
        report.end_turn()

        assert len(report.turn_timings) == 1
        assert report.turn_timings[0].turn_number == 1
        assert report.turn_timings[0].latency_seconds >= 0.01

    def test_multiple_turns(self):
        """Test latency tracking across multiple turns."""
        report = UsageReport()

        for _ in range(3):
            report.start_turn()
            report.end_turn()

        assert len(report.turn_timings) == 3
        assert report.turn_timings[0].turn_number == 1
        assert report.turn_timings[1].turn_number == 2
        assert report.turn_timings[2].turn_number == 3

    def test_avg_latency(self):
        """Test average latency calculation."""
        report = UsageReport()
        report.turn_timings = [
            TurnTiming(1, 1.0, ""),
            TurnTiming(2, 2.0, ""),
            TurnTiming(3, 3.0, ""),
        ]
        assert report.avg_latency_seconds == 2.0

    def test_avg_latency_empty(self):
        """Test average latency with no turns."""
        report = UsageReport()
        assert report.avg_latency_seconds == 0.0

    def test_total_latency(self):
        """Test total latency calculation."""
        report = UsageReport()
        report.turn_timings = [
            TurnTiming(1, 1.5, ""),
            TurnTiming(2, 2.5, ""),
        ]
        assert report.total_latency_seconds == 4.0

    def test_record_error(self):
        """Test error recording."""
        report = UsageReport()
        report.turns = 5

        error = ValueError("test error message")
        report.record_error(error)

        assert len(report.errors) == 1
        assert report.errors[0].error_type == "ValueError"
        assert report.errors[0].message == "test error message"
        assert report.errors[0].turn == 5

    def test_summary_includes_latency(self):
        """Test that summary includes latency when turns exist."""
        report = UsageReport()
        report.session_id = "abc12345"
        report.turn_timings = [
            TurnTiming(1, 2.0, ""),
            TurnTiming(2, 4.0, ""),
        ]

        summary = report.summary()
        assert "3.0s avg latency" in summary

    def test_summary_includes_errors(self):
        """Test that summary includes error count."""
        report = UsageReport()
        report.session_id = "abc12345"
        report.errors = [
            ErrorRecord("", "Error1", "msg1", 1),
            ErrorRecord("", "Error2", "msg2", 2),
        ]

        summary = report.summary()
        assert "2 errors" in summary

    def test_detailed_summary_structure(self):
        """Test detailed summary returns correct structure."""
        report = UsageReport()
        report.session_id = "test123"
        report.total_cost_usd = 0.05
        report.input_tokens = 1000
        report.output_tokens = 500
        report.cache_read_tokens = 200
        report.turns = 2
        report.turn_timings = [TurnTiming(1, 1.5, "2024-01-01T12:00:00")]
        report.errors = [ErrorRecord("2024-01-01T12:00:00", "Error", "msg", 1)]

        details = report.detailed_summary()

        assert details["session_id"] == "test123"
        assert details["cost_usd"] == 0.05
        assert details["tokens"]["input"] == 1000
        assert details["tokens"]["output"] == 500
        assert details["tokens"]["cache_read"] == 200
        assert details["tokens"]["total"] == 1500
        assert details["turns"] == 2
        assert len(details["timing"]["per_turn"]) == 1
        assert len(details["errors"]) == 1

    def test_session_duration(self):
        """Test session duration tracking."""
        report = UsageReport()
        time.sleep(0.01)
        assert report.session_duration_seconds >= 0.01

    def test_end_turn_without_start(self):
        """Test that end_turn is safe when start wasn't called."""
        report = UsageReport()
        report.end_turn()  # Should not raise
        assert len(report.turn_timings) == 0
