"""Tests for visualization templates."""

from __future__ import annotations

import pytest
from datetime import datetime
from chat_retro.viz_templates import TimelineViz
from chat_retro.artifacts import ArtifactGenerator


class TestTimelineViz:
    """Tests for TimelineViz visualization."""

    def test_prepare_data_empty(self):
        """Empty conversation list returns empty timeline."""
        result = TimelineViz.prepare_data([])
        assert result == {"timeline": []}

    def test_prepare_data_with_timestamps(self):
        """Conversations with Unix timestamps are processed."""
        # Use timestamps that result in same date in local timezone
        # Get today's midnight in local time as reference
        import time
        today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        ts_day1 = today.timestamp()
        ts_day2 = (today.replace(day=today.day + 1) if today.day < 28 else today.replace(month=today.month + 1, day=1)).timestamp()

        conversations = [
            {"create_time": ts_day1},
            {"create_time": ts_day1},  # Same day
            {"create_time": ts_day2},  # Next day
        ]
        result = TimelineViz.prepare_data(conversations)

        assert "timeline" in result
        assert len(result["timeline"]) == 2
        # Counts should be 2 for first day, 1 for second
        counts = [item["count"] for item in result["timeline"]]
        assert sorted(counts) == [1, 2]

    def test_prepare_data_with_iso_strings(self):
        """Conversations with ISO date strings are processed."""
        conversations = [
            {"created_at": "2024-03-15T10:30:00Z"},
            {"created_at": "2024-03-15T14:00:00Z"},
            {"created_at": "2024-03-16T09:00:00Z"},
        ]
        result = TimelineViz.prepare_data(conversations)

        assert len(result["timeline"]) == 2
        counts = {item["date"]: item["count"] for item in result["timeline"]}
        assert counts.get("2024-03-15") == 2
        assert counts.get("2024-03-16") == 1

    def test_prepare_data_sorted_by_date(self):
        """Timeline data is sorted by date."""
        conversations = [
            {"create_time": 1704153600},  # 2024-01-02
            {"create_time": 1704067200},  # 2024-01-01
            {"create_time": 1704240000},  # 2024-01-03
        ]
        result = TimelineViz.prepare_data(conversations)

        dates = [item["date"] for item in result["timeline"]]
        assert dates == sorted(dates)

    def test_prepare_data_skips_invalid(self):
        """Invalid timestamps are skipped."""
        conversations = [
            {"create_time": 1704067200},  # Valid
            {"create_time": None},  # Invalid
            {"other_field": "value"},  # No timestamp
            {"create_time": "not-a-date"},  # Invalid string
        ]
        result = TimelineViz.prepare_data(conversations)

        assert len(result["timeline"]) == 1

    def test_get_js_code_returns_string(self):
        """JS code is returned as string."""
        code = TimelineViz.get_js_code()
        assert isinstance(code, str)
        assert len(code) > 100  # Non-trivial code

    def test_get_js_code_contains_d3_calls(self):
        """JS code uses D3.js methods."""
        code = TimelineViz.get_js_code()
        assert "d3.select" in code
        assert "d3.scaleTime" in code
        assert "d3.axisBottom" in code

    def test_get_js_code_references_data(self):
        """JS code references DATA.timeline."""
        code = TimelineViz.get_js_code()
        assert "DATA.timeline" in code

    def test_get_js_code_handles_empty_data(self):
        """JS code handles empty data gracefully."""
        code = TimelineViz.get_js_code()
        assert "No timeline data" in code


class TestTimelineIntegration:
    """Integration tests for timeline with ArtifactGenerator."""

    def test_generate_html_with_timeline(self):
        """Timeline can be integrated with ArtifactGenerator."""
        generator = ArtifactGenerator()

        data = TimelineViz.prepare_data([
            {"create_time": 1704067200},
            {"create_time": 1704153600},
        ])

        html = generator.generate_html(
            title="Timeline Test",
            data=data,
            visualization_code=TimelineViz.get_js_code(),
        )

        # HTML is valid
        assert "<!DOCTYPE html>" in html
        assert "<title>Timeline Test</title>" in html

        # Data is embedded
        assert '"timeline"' in html
        assert '"date"' in html
        assert '"count"' in html

        # D3.js code is included
        assert "d3.select" in html

    def test_html_is_self_contained(self):
        """Generated HTML has no external dependencies."""
        generator = ArtifactGenerator()

        html = generator.generate_html(
            title="Test",
            data={"timeline": []},
            visualization_code=TimelineViz.get_js_code(),
        )

        # No external CSS/JS references
        assert 'href="http' not in html
        assert 'src="http' not in html
        assert 'url(' not in html or 'url(data:' in html

    def test_html_renders_with_real_data(self, tmp_path):
        """Save and verify HTML artifact with real-ish data."""
        generator = ArtifactGenerator(output_dir=tmp_path)

        # Create sample data
        conversations = [
            {"create_time": 1704067200 + i * 86400}  # One per day
            for i in range(30)
        ]
        data = TimelineViz.prepare_data(conversations)

        path = generator.save_html(
            filename="timeline-test",
            title="30 Day Timeline",
            data=data,
            visualization_code=TimelineViz.get_js_code(),
        )

        # File created
        assert path.exists()
        assert path.suffix == ".html"

        # Content is valid
        content = path.read_text()
        assert len(content) > 10000  # D3.js is large
        assert "30 Day Timeline" in content
