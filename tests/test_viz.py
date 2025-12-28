"""Tests for visualization templates."""

from __future__ import annotations

import pytest
from datetime import datetime
from chat_retro.viz_templates import TimelineViz, HeatmapViz, TopicClusterViz, LengthDistributionViz
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

        # No external CSS/JS references (url(#id) for SVG gradients is ok)
        assert 'href="http' not in html
        assert 'src="http' not in html
        # Allow internal SVG references like url(#gradientId), block external urls
        import re
        external_urls = re.findall(r'url\(["\']?https?://', html)
        assert not external_urls, f"Found external URLs: {external_urls}"

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


class TestHeatmapViz:
    """Tests for HeatmapViz visualization."""

    def test_prepare_data_empty(self):
        """Empty conversation list returns empty heatmap."""
        result = HeatmapViz.prepare_data([])
        assert result == {"heatmap": []}

    def test_prepare_data_aggregates_by_day_hour(self):
        """Conversations are aggregated by day and hour."""
        # Create timestamps for specific day/hour combinations
        # Use a Monday at 9am (weekday=0 in Python, so Sunday=0 in our format means Monday=1)
        monday_9am = datetime(2024, 1, 8, 9, 30).timestamp()  # Monday
        monday_9am_2 = datetime(2024, 1, 8, 9, 45).timestamp()  # Same slot
        tuesday_14pm = datetime(2024, 1, 9, 14, 0).timestamp()  # Tuesday 2pm

        conversations = [
            {"create_time": monday_9am},
            {"create_time": monday_9am_2},
            {"create_time": tuesday_14pm},
        ]
        result = HeatmapViz.prepare_data(conversations)

        assert "heatmap" in result
        assert len(result["heatmap"]) == 2

        # Check counts
        counts = {(item["day"], item["hour"]): item["count"] for item in result["heatmap"]}
        # Monday = day 1 (0=Sunday)
        assert counts.get((1, 9)) == 2
        # Tuesday = day 2
        assert counts.get((2, 14)) == 1

    def test_prepare_data_handles_sunday(self):
        """Sunday is correctly mapped to day 0."""
        sunday = datetime(2024, 1, 7, 10, 0).timestamp()  # Sunday
        conversations = [{"create_time": sunday}]
        result = HeatmapViz.prepare_data(conversations)

        assert len(result["heatmap"]) == 1
        assert result["heatmap"][0]["day"] == 0  # Sunday

    def test_prepare_data_skips_invalid(self):
        """Invalid timestamps are skipped."""
        conversations = [
            {"create_time": datetime(2024, 1, 8, 9, 0).timestamp()},
            {"create_time": None},
            {"other_field": "value"},
        ]
        result = HeatmapViz.prepare_data(conversations)
        assert len(result["heatmap"]) == 1

    def test_get_js_code_returns_string(self):
        """JS code is returned as string."""
        code = HeatmapViz.get_js_code()
        assert isinstance(code, str)
        assert len(code) > 100

    def test_get_js_code_contains_d3_calls(self):
        """JS code uses D3.js methods."""
        code = HeatmapViz.get_js_code()
        assert "d3.select" in code
        assert "d3.scaleBand" in code
        assert "d3.scaleSequential" in code

    def test_get_js_code_creates_7x24_grid(self):
        """JS code creates 7x24 grid structure."""
        code = HeatmapViz.get_js_code()
        assert "day < 7" in code
        assert "hour < 24" in code

    def test_get_js_code_references_data(self):
        """JS code references DATA.heatmap."""
        code = HeatmapViz.get_js_code()
        assert "DATA.heatmap" in code


class TestHeatmapIntegration:
    """Integration tests for heatmap with ArtifactGenerator."""

    def test_generate_html_with_heatmap(self, tmp_path):
        """Heatmap can be integrated with ArtifactGenerator."""
        generator = ArtifactGenerator(output_dir=tmp_path)

        # Create sample data with varied times
        import random
        random.seed(42)
        conversations = [
            {"create_time": datetime(2024, 1, 1 + i % 28, random.randint(0, 23), random.randint(0, 59)).timestamp()}
            for i in range(100)
        ]
        data = HeatmapViz.prepare_data(conversations)

        path = generator.save_html(
            filename="heatmap-test",
            title="Usage Heatmap",
            data=data,
            visualization_code=HeatmapViz.get_js_code(),
        )

        assert path.exists()
        content = path.read_text()
        assert "Usage Heatmap" in content
        assert '"heatmap"' in content


class TestTopicClusterViz:
    """Tests for TopicClusterViz visualization."""

    def test_prepare_data_empty(self):
        """Empty patterns list returns empty nodes and links."""
        result = TopicClusterViz.prepare_data([])
        assert result == {"nodes": [], "links": []}

    def test_prepare_data_creates_nodes(self):
        """Patterns are converted to nodes with correct structure."""
        patterns = [
            {"label": "Python", "type": "theme", "conversation_ids": ["c1", "c2", "c3"]},
            {"label": "Debugging", "type": "theme", "conversation_ids": ["c1", "c4"]},
            {"label": "API design", "type": "skill", "conversation_ids": ["c5"]},
        ]
        result = TopicClusterViz.prepare_data(patterns)

        assert len(result["nodes"]) == 3

        # Check node structure
        python_node = next(n for n in result["nodes"] if n["id"] == "Python")
        assert python_node["count"] == 3
        assert python_node["type"] == "theme"
        assert "group" in python_node

    def test_prepare_data_groups_by_type(self):
        """Patterns of same type get same group number."""
        patterns = [
            {"label": "A", "type": "theme", "conversation_ids": []},
            {"label": "B", "type": "theme", "conversation_ids": []},
            {"label": "C", "type": "skill", "conversation_ids": []},
        ]
        result = TopicClusterViz.prepare_data(patterns)

        groups = {n["id"]: n["group"] for n in result["nodes"]}
        assert groups["A"] == groups["B"]  # Same type
        assert groups["A"] != groups["C"]  # Different type

    def test_prepare_data_creates_links_from_shared_conversations(self):
        """Patterns sharing conversations are linked."""
        patterns = [
            {"label": "A", "type": "theme", "conversation_ids": ["c1", "c2"]},
            {"label": "B", "type": "theme", "conversation_ids": ["c1"]},  # Shares c1 with A
            {"label": "C", "type": "skill", "conversation_ids": ["c3"]},  # No shared convos
        ]
        result = TopicClusterViz.prepare_data(patterns)

        # Should have one link between A and B
        assert len(result["links"]) == 1
        link = result["links"][0]
        assert set([link["source"], link["target"]]) == {"A", "B"}
        assert link["value"] == 1

    def test_prepare_data_counts_multiple_shared_conversations(self):
        """Link value reflects number of shared conversations."""
        patterns = [
            {"label": "A", "type": "theme", "conversation_ids": ["c1", "c2", "c3"]},
            {"label": "B", "type": "theme", "conversation_ids": ["c1", "c2"]},  # Shares c1, c2
        ]
        result = TopicClusterViz.prepare_data(patterns)

        assert len(result["links"]) == 1
        assert result["links"][0]["value"] == 2  # Two shared conversations

    def test_prepare_data_skips_empty_labels(self):
        """Patterns without labels are skipped."""
        patterns = [
            {"label": "Valid", "type": "theme", "conversation_ids": ["c1"]},
            {"label": "", "type": "theme", "conversation_ids": ["c2"]},
            {"type": "theme", "conversation_ids": ["c3"]},  # No label key
        ]
        result = TopicClusterViz.prepare_data(patterns)
        assert len(result["nodes"]) == 1

    def test_get_js_code_returns_string(self):
        """JS code is returned as string."""
        code = TopicClusterViz.get_js_code()
        assert isinstance(code, str)
        assert len(code) > 100

    def test_get_js_code_contains_force_simulation(self):
        """JS code uses D3 force simulation."""
        code = TopicClusterViz.get_js_code()
        assert "d3.forceSimulation" in code
        assert "d3.forceLink" in code
        assert "d3.forceManyBody" in code

    def test_get_js_code_supports_dragging(self):
        """JS code includes drag behavior."""
        code = TopicClusterViz.get_js_code()
        assert "d3.drag" in code
        assert "dragstarted" in code
        assert "dragged" in code
        assert "dragended" in code

    def test_get_js_code_references_data(self):
        """JS code references DATA.nodes and DATA.links."""
        code = TopicClusterViz.get_js_code()
        assert "DATA.nodes" in code
        assert "DATA.links" in code


class TestTopicClusterIntegration:
    """Integration tests for topic clusters with ArtifactGenerator."""

    def test_generate_html_with_clusters(self, tmp_path):
        """Topic clusters can be integrated with ArtifactGenerator."""
        generator = ArtifactGenerator(output_dir=tmp_path)

        patterns = [
            {"label": "Python", "type": "language", "conversation_ids": ["c1", "c2", "c3", "c4", "c5"]},
            {"label": "JavaScript", "type": "language", "conversation_ids": ["c2", "c6", "c7"]},
            {"label": "Debugging", "type": "activity", "conversation_ids": ["c1", "c2", "c3"]},
            {"label": "Testing", "type": "activity", "conversation_ids": ["c4", "c5"]},
            {"label": "API design", "type": "topic", "conversation_ids": ["c1", "c6"]},
        ]
        data = TopicClusterViz.prepare_data(patterns)

        path = generator.save_html(
            filename="clusters-test",
            title="Topic Clusters",
            data=data,
            visualization_code=TopicClusterViz.get_js_code(),
        )

        assert path.exists()
        content = path.read_text()
        assert "Topic Clusters" in content
        assert '"nodes"' in content
        assert '"links"' in content


class TestLengthDistributionViz:
    """Tests for LengthDistributionViz visualization."""

    def test_prepare_data_empty(self):
        """Empty conversation list returns empty distribution."""
        result = LengthDistributionViz.prepare_data([])
        assert result == {"distribution": [], "stats": {}}

    def test_prepare_data_with_mapping(self):
        """Conversations with mapping dict count messages."""
        conversations = [
            {"mapping": {"m1": {}, "m2": {}, "m3": {}}},  # 3 messages
            {"mapping": {"m1": {}}},  # 1 message
            {"mapping": {"m1": {}, "m2": {}, "m3": {}, "m4": {}, "m5": {}}},  # 5 messages
        ]
        result = LengthDistributionViz.prepare_data(conversations, bin_size=5)

        assert "distribution" in result
        assert "stats" in result
        assert result["stats"]["total"] == 3
        assert result["stats"]["min"] == 1
        assert result["stats"]["max"] == 5

    def test_prepare_data_with_messages_list(self):
        """Conversations with messages list count correctly."""
        conversations = [
            {"messages": [{"role": "user"}, {"role": "assistant"}]},  # 2 messages
            {"messages": [{"role": "user"}]},  # 1 message
        ]
        result = LengthDistributionViz.prepare_data(conversations, bin_size=5)

        assert result["stats"]["total"] == 2
        assert result["stats"]["min"] == 1
        assert result["stats"]["max"] == 2

    def test_prepare_data_bins_correctly(self):
        """Conversations are binned by length."""
        # Create conversations with specific lengths
        conversations = [
            {"mapping": {f"m{i}": {} for i in range(3)}},  # 3 messages -> bin 1-5
            {"mapping": {f"m{i}": {} for i in range(7)}},  # 7 messages -> bin 6-10
            {"mapping": {f"m{i}": {} for i in range(8)}},  # 8 messages -> bin 6-10
            {"mapping": {f"m{i}": {} for i in range(12)}},  # 12 messages -> bin 11-15
        ]
        result = LengthDistributionViz.prepare_data(conversations, bin_size=5)

        # Should have 3 bins
        assert len(result["distribution"]) == 3

        bins = {d["bin"]: d["count"] for d in result["distribution"]}
        assert bins.get("1-5") == 1
        assert bins.get("6-10") == 2
        assert bins.get("11-15") == 1

    def test_prepare_data_calculates_mean(self):
        """Mean is calculated correctly."""
        conversations = [
            {"mapping": {f"m{i}": {} for i in range(10)}},  # 10
            {"mapping": {f"m{i}": {} for i in range(20)}},  # 20
            {"mapping": {f"m{i}": {} for i in range(30)}},  # 30
        ]
        result = LengthDistributionViz.prepare_data(conversations)

        assert result["stats"]["mean"] == 20.0

    def test_prepare_data_calculates_median_odd(self):
        """Median is calculated correctly for odd count."""
        conversations = [
            {"mapping": {f"m{i}": {} for i in range(5)}},
            {"mapping": {f"m{i}": {} for i in range(10)}},
            {"mapping": {f"m{i}": {} for i in range(15)}},
        ]
        result = LengthDistributionViz.prepare_data(conversations)

        assert result["stats"]["median"] == 10

    def test_prepare_data_calculates_median_even(self):
        """Median is calculated correctly for even count."""
        conversations = [
            {"mapping": {f"m{i}": {} for i in range(4)}},
            {"mapping": {f"m{i}": {} for i in range(6)}},
            {"mapping": {f"m{i}": {} for i in range(8)}},
            {"mapping": {f"m{i}": {} for i in range(10)}},
        ]
        result = LengthDistributionViz.prepare_data(conversations)

        # Median of [4, 6, 8, 10] = (6 + 8) / 2 = 7
        assert result["stats"]["median"] == 7

    def test_prepare_data_fallback_length(self):
        """Conversations without mapping or messages default to 1."""
        conversations = [
            {"other_field": "value"},
            {"title": "Some conversation"},
        ]
        result = LengthDistributionViz.prepare_data(conversations)

        assert result["stats"]["total"] == 2
        assert result["stats"]["min"] == 1
        assert result["stats"]["max"] == 1

    def test_get_js_code_returns_string(self):
        """JS code is returned as string."""
        code = LengthDistributionViz.get_js_code()
        assert isinstance(code, str)
        assert len(code) > 100

    def test_get_js_code_contains_d3_calls(self):
        """JS code uses D3.js methods."""
        code = LengthDistributionViz.get_js_code()
        assert "d3.select" in code
        assert "d3.scaleBand" in code
        assert "d3.scaleLinear" in code

    def test_get_js_code_references_data(self):
        """JS code references DATA.distribution and DATA.stats."""
        code = LengthDistributionViz.get_js_code()
        assert "DATA.distribution" in code
        assert "DATA.stats" in code

    def test_get_js_code_handles_empty_data(self):
        """JS code handles empty data gracefully."""
        code = LengthDistributionViz.get_js_code()
        assert "No length data" in code


class TestLengthDistributionIntegration:
    """Integration tests for length distribution with ArtifactGenerator."""

    def test_generate_html_with_distribution(self, tmp_path):
        """Length distribution can be integrated with ArtifactGenerator."""
        generator = ArtifactGenerator(output_dir=tmp_path)

        # Create sample conversations with varied lengths
        conversations = [
            {"mapping": {f"m{i}": {} for i in range(length)}}
            for length in [3, 5, 7, 8, 10, 12, 15, 20, 25, 30]
        ]
        data = LengthDistributionViz.prepare_data(conversations)

        path = generator.save_html(
            filename="length-dist-test",
            title="Conversation Length Distribution",
            data=data,
            visualization_code=LengthDistributionViz.get_js_code(),
        )

        assert path.exists()
        content = path.read_text()
        assert "Conversation Length Distribution" in content
        assert '"distribution"' in content
        assert '"stats"' in content
