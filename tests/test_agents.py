"""Tests for subagent definitions."""

import pytest
from claude_agent_sdk import AgentDefinition

from chat_retro.agents import (
    AGENTS,
    TOPIC_EXTRACTOR,
    SENTIMENT_TRACKER,
    PATTERN_DETECTOR,
    TEMPORAL_ANALYST,
    get_agents,
)


class TestAgentDefinition:
    """Tests for SDK AgentDefinition usage."""

    def test_agents_use_sdk_class(self):
        """All agents use the SDK's AgentDefinition."""
        for name, agent in AGENTS.items():
            assert isinstance(agent, AgentDefinition), f"{name} should be AgentDefinition"

    def test_agent_has_required_fields(self):
        """Agents have required description and prompt."""
        for name, agent in AGENTS.items():
            assert agent.description, f"{name} missing description"
            assert agent.prompt, f"{name} missing prompt"


class TestTopicExtractor:
    """Tests for topic-extractor agent."""

    def test_has_required_fields(self):
        """Topic extractor has all required fields."""
        assert TOPIC_EXTRACTOR.description
        assert TOPIC_EXTRACTOR.prompt
        assert TOPIC_EXTRACTOR.tools
        assert TOPIC_EXTRACTOR.model

    def test_description_mentions_topics(self):
        """Description explains the agent's purpose."""
        assert "topic" in TOPIC_EXTRACTOR.description.lower()

    def test_has_file_reading_tools(self):
        """Topic extractor can read files."""
        assert "Read" in TOPIC_EXTRACTOR.tools
        assert "Grep" in TOPIC_EXTRACTOR.tools

    def test_uses_capable_model(self):
        """Uses a capable model for complex analysis."""
        assert TOPIC_EXTRACTOR.model in ("sonnet", "opus")


class TestSentimentTracker:
    """Tests for sentiment-tracker agent."""

    def test_has_required_fields(self):
        """Sentiment tracker has all required fields."""
        assert SENTIMENT_TRACKER.description
        assert SENTIMENT_TRACKER.prompt
        assert SENTIMENT_TRACKER.tools
        assert SENTIMENT_TRACKER.model

    def test_description_mentions_sentiment(self):
        """Description explains sentiment analysis."""
        desc_lower = SENTIMENT_TRACKER.description.lower()
        assert "sentiment" in desc_lower or "emotion" in desc_lower


class TestPatternDetector:
    """Tests for pattern-detector agent."""

    def test_has_required_fields(self):
        """Pattern detector has all required fields."""
        assert PATTERN_DETECTOR.description
        assert PATTERN_DETECTOR.prompt
        assert PATTERN_DETECTOR.tools
        assert PATTERN_DETECTOR.model

    def test_description_mentions_patterns(self):
        """Description explains pattern detection."""
        assert "pattern" in PATTERN_DETECTOR.description.lower()


class TestTemporalAnalyst:
    """Tests for temporal-analyst agent."""

    def test_has_required_fields(self):
        """Temporal analyst has all required fields."""
        assert TEMPORAL_ANALYST.description
        assert TEMPORAL_ANALYST.prompt
        assert TEMPORAL_ANALYST.tools
        assert TEMPORAL_ANALYST.model

    def test_description_mentions_time(self):
        """Description explains temporal analysis."""
        desc_lower = TEMPORAL_ANALYST.description.lower()
        assert "time" in desc_lower or "temporal" in desc_lower

    def test_uses_efficient_model(self):
        """Uses lighter model for metadata analysis."""
        assert TEMPORAL_ANALYST.model == "haiku"


class TestAgentsRegistry:
    """Tests for AGENTS registry."""

    def test_all_agents_registered(self):
        """All expected agents are in registry."""
        expected = ["topic-extractor", "sentiment-tracker", "pattern-detector", "temporal-analyst"]
        for name in expected:
            assert name in AGENTS, f"Missing agent: {name}"

    def test_agent_count(self):
        """Registry has expected number of agents."""
        assert len(AGENTS) == 4


class TestGetAgents:
    """Tests for get_agents function."""

    def test_returns_dict(self):
        """Returns a dictionary."""
        result = get_agents()
        assert isinstance(result, dict)

    def test_contains_all_agents(self):
        """Contains all registered agents."""
        result = get_agents()
        # Analysis agents
        assert "topic-extractor" in result
        assert "sentiment-tracker" in result
        assert "pattern-detector" in result
        assert "temporal-analyst" in result
        # Insight agents
        assert "prompt-improver" in result
        assert "repetition-detector" in result
        assert "usage-optimizer" in result

    def test_all_are_agent_definitions(self):
        """All values are AgentDefinition instances."""
        result = get_agents()
        for name, agent in result.items():
            assert isinstance(agent, AgentDefinition), f"{name} should be AgentDefinition"


class TestAgentIntegration:
    """Integration tests for agents with session."""

    def test_agents_importable_from_session(self):
        """Agents can be imported where session uses them."""
        from chat_retro.session import SessionManager
        from chat_retro.agents import get_agents
        # If this doesn't raise, imports work
        assert get_agents() is not None
