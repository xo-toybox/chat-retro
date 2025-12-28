"""Tests for subagent definitions."""

import pytest
from chat_retro.agents import (
    AgentDefinition,
    AGENTS,
    TOPIC_EXTRACTOR,
    SENTIMENT_TRACKER,
    PATTERN_DETECTOR,
    TEMPORAL_ANALYST,
    TOPIC_SCHEMA,
    SENTIMENT_SCHEMA,
    PATTERN_SCHEMA,
    TEMPORAL_SCHEMA,
    get_agents_dict,
)


class TestAgentDefinition:
    """Tests for AgentDefinition dataclass."""

    def test_basic_creation(self):
        """AgentDefinition can be created with required fields."""
        agent = AgentDefinition(
            description="Test agent",
            prompt="You are a test agent.",
            tools=["Read"],
        )
        assert agent.description == "Test agent"
        assert agent.prompt == "You are a test agent."
        assert agent.tools == ["Read"]
        assert agent.model == "sonnet"  # default

    def test_custom_model(self):
        """AgentDefinition accepts custom model."""
        agent = AgentDefinition(
            description="Test",
            prompt="Test",
            tools=[],
            model="haiku",
        )
        assert agent.model == "haiku"

    def test_to_dict(self):
        """to_dict returns proper format for SDK."""
        agent = AgentDefinition(
            description="Desc",
            prompt="Prompt",
            tools=["Read", "Grep"],
            model="opus",
        )
        result = agent.to_dict()

        assert result == {
            "description": "Desc",
            "prompt": "Prompt",
            "tools": ["Read", "Grep"],
            "model": "opus",
        }

    def test_to_dict_with_schema(self):
        """to_dict includes output_schema when provided."""
        schema = {"type": "object", "properties": {"foo": {"type": "string"}}}
        agent = AgentDefinition(
            description="Test",
            prompt="Test",
            tools=[],
            output_schema=schema,
        )
        result = agent.to_dict()

        assert "output_schema" in result
        assert result["output_schema"] == schema

    def test_to_dict_without_schema(self):
        """to_dict omits output_schema when None."""
        agent = AgentDefinition(
            description="Test",
            prompt="Test",
            tools=[],
        )
        result = agent.to_dict()

        assert "output_schema" not in result


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
        assert "extract" in TOPIC_EXTRACTOR.description.lower() or "cluster" in TOPIC_EXTRACTOR.description.lower()

    def test_has_output_schema(self):
        """Topic extractor has structured output schema."""
        assert TOPIC_EXTRACTOR.output_schema is not None
        assert TOPIC_EXTRACTOR.output_schema == TOPIC_SCHEMA

    def test_schema_has_required_fields(self):
        """Schema requires topics array."""
        assert "topics" in TOPIC_SCHEMA["required"]
        assert TOPIC_SCHEMA["properties"]["topics"]["type"] == "array"

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
        assert "sentiment" in SENTIMENT_TRACKER.description.lower() or "emotion" in SENTIMENT_TRACKER.description.lower()

    def test_has_output_schema(self):
        """Sentiment tracker has structured output schema."""
        assert SENTIMENT_TRACKER.output_schema is not None
        assert SENTIMENT_TRACKER.output_schema == SENTIMENT_SCHEMA

    def test_schema_has_required_fields(self):
        """Schema requires overall_sentiment."""
        assert "overall_sentiment" in SENTIMENT_SCHEMA["required"]


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

    def test_has_output_schema(self):
        """Pattern detector has structured output schema."""
        assert PATTERN_DETECTOR.output_schema is not None
        assert PATTERN_DETECTOR.output_schema == PATTERN_SCHEMA

    def test_schema_has_required_fields(self):
        """Schema requires patterns and recommendations."""
        assert "effective_patterns" in PATTERN_SCHEMA["required"]
        assert "anti_patterns" in PATTERN_SCHEMA["required"]
        assert "recommendations" in PATTERN_SCHEMA["required"]


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
        assert "time" in TEMPORAL_ANALYST.description.lower() or "temporal" in TEMPORAL_ANALYST.description.lower()

    def test_prompt_analyzes_patterns(self):
        """Prompt asks for time-based patterns."""
        assert "usage patterns" in TEMPORAL_ANALYST.prompt.lower()
        assert "trend" in TEMPORAL_ANALYST.prompt.lower()

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


class TestGetAgentsDict:
    """Tests for get_agents_dict function."""

    def test_returns_dict(self):
        """Returns a dictionary."""
        result = get_agents_dict()
        assert isinstance(result, dict)

    def test_contains_all_agents(self):
        """Contains all registered agents."""
        result = get_agents_dict()
        # Analysis agents
        assert "topic-extractor" in result
        assert "sentiment-tracker" in result
        assert "pattern-detector" in result
        assert "temporal-analyst" in result
        # Insight agents
        assert "prompt-improver" in result
        assert "repetition-detector" in result
        assert "usage-optimizer" in result

    def test_agent_format_is_dict(self):
        """Each agent is converted to dict format."""
        result = get_agents_dict()
        for name, agent in result.items():
            assert isinstance(agent, dict), f"{name} should be dict"
            assert "description" in agent
            assert "prompt" in agent
            assert "tools" in agent
            assert "model" in agent

    def test_compatible_with_sdk(self):
        """Output format matches SDK expectations."""
        result = get_agents_dict()
        # Each agent should have string description, string prompt, list tools, string model
        for name, agent in result.items():
            assert isinstance(agent["description"], str)
            assert isinstance(agent["prompt"], str)
            assert isinstance(agent["tools"], list)
            assert isinstance(agent["model"], str)


class TestAgentIntegration:
    """Integration tests for agents with session."""

    def test_agents_importable_from_session(self):
        """Agents can be imported where session uses them."""
        from chat_retro.session import SessionManager
        from chat_retro.agents import get_agents_dict
        # If this doesn't raise, imports work
        assert get_agents_dict() is not None
