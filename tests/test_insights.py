"""Tests for insight agent definitions."""

import pytest
from claude_agent_sdk import AgentDefinition

from chat_retro.insights import (
    INSIGHT_AGENTS,
    PROMPT_IMPROVER,
    REPETITION_DETECTOR,
    USAGE_OPTIMIZER,
    get_insight_agents,
)


class TestInsightAgents:
    """Tests for insight agent definitions."""

    def test_agents_use_sdk_class(self):
        """All insight agents use the SDK's AgentDefinition."""
        for name, agent in INSIGHT_AGENTS.items():
            assert isinstance(agent, AgentDefinition), f"{name} should be AgentDefinition"

    def test_all_agents_registered(self):
        """All expected insight agents are registered."""
        expected = ["prompt-improver", "repetition-detector", "usage-optimizer"]
        for name in expected:
            assert name in INSIGHT_AGENTS, f"Missing agent: {name}"

    def test_agent_count(self):
        """Registry has expected number of agents."""
        assert len(INSIGHT_AGENTS) == 3


class TestPromptImprover:
    """Tests for prompt-improver agent."""

    def test_has_required_fields(self):
        """Agent has all required fields."""
        assert PROMPT_IMPROVER.description
        assert PROMPT_IMPROVER.prompt
        assert PROMPT_IMPROVER.tools
        assert PROMPT_IMPROVER.model

    def test_description_mentions_prompt(self):
        """Description explains the agent's purpose."""
        desc_lower = PROMPT_IMPROVER.description.lower()
        assert "prompt" in desc_lower

    def test_has_file_reading_tools(self):
        """Agent can read files."""
        assert "Read" in PROMPT_IMPROVER.tools
        assert "Grep" in PROMPT_IMPROVER.tools


class TestRepetitionDetector:
    """Tests for repetition-detector agent."""

    def test_has_required_fields(self):
        """Agent has all required fields."""
        assert REPETITION_DETECTOR.description
        assert REPETITION_DETECTOR.prompt
        assert REPETITION_DETECTOR.tools
        assert REPETITION_DETECTOR.model

    def test_description_mentions_repetition(self):
        """Description explains the agent's purpose."""
        desc_lower = REPETITION_DETECTOR.description.lower()
        assert "repetit" in desc_lower or "template" in desc_lower


class TestUsageOptimizer:
    """Tests for usage-optimizer agent."""

    def test_has_required_fields(self):
        """Agent has all required fields."""
        assert USAGE_OPTIMIZER.description
        assert USAGE_OPTIMIZER.prompt
        assert USAGE_OPTIMIZER.tools
        assert USAGE_OPTIMIZER.model

    def test_description_mentions_usage(self):
        """Description explains the agent's purpose."""
        desc_lower = USAGE_OPTIMIZER.description.lower()
        assert "usage" in desc_lower or "recommend" in desc_lower


class TestGetInsightAgents:
    """Tests for get_insight_agents function."""

    def test_returns_dict(self):
        """Returns a dictionary."""
        result = get_insight_agents()
        assert isinstance(result, dict)

    def test_contains_all_agents(self):
        """Contains all insight agents."""
        result = get_insight_agents()
        assert "prompt-improver" in result
        assert "repetition-detector" in result
        assert "usage-optimizer" in result

    def test_all_are_agent_definitions(self):
        """All values are AgentDefinition instances."""
        result = get_insight_agents()
        for name, agent in result.items():
            assert isinstance(agent, AgentDefinition), f"{name} should be AgentDefinition"
