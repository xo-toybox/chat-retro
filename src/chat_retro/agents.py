"""Subagent definitions for specialized analysis tasks.

These agents are invoked by the main agent via the Task tool
to perform focused analysis while preserving main context.
"""

from enum import StrEnum

from claude_agent_sdk import AgentDefinition


class AgentKey(StrEnum):
    """Available agent identifiers."""

    TOPIC_EXTRACTOR = "topic-extractor"
    SENTIMENT_TRACKER = "sentiment-tracker"
    PATTERN_DETECTOR = "pattern-detector"
    TEMPORAL_ANALYST = "temporal-analyst"


AGENTS: dict[AgentKey, AgentDefinition] = {
    AgentKey.TOPIC_EXTRACTOR: AgentDefinition(
        description="Extract and cluster topics from conversation content.",
        prompt="""You are a topic extraction specialist analyzing AI conversation history.

Your task:
1. Read the conversation content thoroughly
2. Identify distinct topics and themes discussed
3. Cluster related topics together
4. Assign confidence scores based on evidence strength

Be thorough but avoid over-extraction. Focus on meaningful, recurring themes.""",
        tools=["Read", "Grep", "Glob"],
        model="sonnet",
    ),
    AgentKey.SENTIMENT_TRACKER: AgentDefinition(
        description="Track emotional tone and sentiment evolution across conversations.",
        prompt="""You are a sentiment analyst examining AI conversation history.

Your task:
1. Analyze the emotional tone of user messages over time
2. Identify sentiment shifts and their triggers
3. Note peaks (very positive/negative) and their context
4. Track satisfaction patterns

Focus on patterns, not individual message sentiment.""",
        tools=["Read", "Grep"],
        model="sonnet",
    ),
    AgentKey.PATTERN_DETECTOR: AgentDefinition(
        description="Identify prompting patterns, anti-patterns, and usage habits.",
        prompt="""You are a prompting pattern analyst examining AI conversation history.

Your task:
1. Identify recurring prompting patterns (effective and ineffective)
2. Flag anti-patterns that lead to poor results
3. Note effective techniques the user employs
4. Highlight areas where improvements may be possible

Be observational. Focus on pattern discovery, not prescriptive advice.""",
        tools=["Read", "Grep", "Glob"],
        model="sonnet",
    ),
    AgentKey.TEMPORAL_ANALYST: AgentDefinition(
        description="Analyze time-based usage patterns and trends.",
        prompt="""You are a temporal pattern analyst examining AI conversation history.

Your task:
1. Identify usage patterns by time of day, day of week, month
2. Find burst periods vs quiet periods
3. Correlate time patterns with topics
4. Detect trends and seasonality

Use conversation timestamps to identify patterns. Be specific about dates.""",
        tools=["Read", "Grep"],
        model="haiku",
    ),
}


def get_agents() -> dict[str, AgentDefinition]:
    """Get all agents for ClaudeAgentOptions.

    Includes analysis and insight agents.
    """
    from chat_retro.insights import get_insight_agents

    result: dict[str, AgentDefinition] = {k: v for k, v in AGENTS.items()}
    result.update(get_insight_agents())
    return result
