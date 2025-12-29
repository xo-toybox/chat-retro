"""Tests for insight agent definitions."""

import pytest
from claude_agent_sdk import AgentDefinition

from chat_retro.insights import (
    INSIGHT_AGENTS,
    InsightKey,
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
        agent = INSIGHT_AGENTS[InsightKey.PROMPT_IMPROVER]
        assert agent.description
        assert agent.prompt
        assert agent.tools
        assert agent.model

    def test_description_mentions_prompt(self):
        """Description explains the agent's purpose."""
        agent = INSIGHT_AGENTS[InsightKey.PROMPT_IMPROVER]
        desc_lower = agent.description.lower()
        assert "prompt" in desc_lower

    def test_has_file_reading_tools(self):
        """Agent can read files."""
        agent = INSIGHT_AGENTS[InsightKey.PROMPT_IMPROVER]
        assert "Read" in agent.tools
        assert "Grep" in agent.tools


class TestRepetitionDetector:
    """Tests for repetition-detector agent."""

    def test_has_required_fields(self):
        """Agent has all required fields."""
        agent = INSIGHT_AGENTS[InsightKey.REPETITION_DETECTOR]
        assert agent.description
        assert agent.prompt
        assert agent.tools
        assert agent.model

    def test_description_mentions_repetition(self):
        """Description explains the agent's purpose."""
        agent = INSIGHT_AGENTS[InsightKey.REPETITION_DETECTOR]
        desc_lower = agent.description.lower()
        assert "repetit" in desc_lower or "template" in desc_lower


class TestUsageOptimizer:
    """Tests for usage-optimizer agent."""

    def test_has_required_fields(self):
        """Agent has all required fields."""
        agent = INSIGHT_AGENTS[InsightKey.USAGE_OPTIMIZER]
        assert agent.description
        assert agent.prompt
        assert agent.tools
        assert agent.model

    def test_description_mentions_usage(self):
        """Description explains the agent's purpose."""
        agent = INSIGHT_AGENTS[InsightKey.USAGE_OPTIMIZER]
        desc_lower = agent.description.lower()
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
