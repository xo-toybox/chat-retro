"""Subagent definitions for specialized analysis tasks.

These agents are invoked by the main agent via the Task tool
to perform focused analysis while preserving main context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentDefinition:
    """Definition for a specialized subagent.

    Mirrors the claude_code_sdk.AgentDefinition interface for use
    with ClaudeCodeOptions(agents={...}).
    """

    description: str
    prompt: str
    tools: list[str]
    model: str = "sonnet"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for SDK consumption."""
        return {
            "description": self.description,
            "prompt": self.prompt,
            "tools": self.tools,
            "model": self.model,
        }


# Topic extraction subagent
TOPIC_EXTRACTOR = AgentDefinition(
    description="Extract and cluster topics from conversation content.",
    prompt="""You are a topic extraction specialist analyzing AI conversation history.

Your task:
1. Read the conversation content thoroughly
2. Identify distinct topics and themes discussed
3. Cluster related topics together
4. Assign confidence scores based on evidence strength

Output format (JSON):
{
    "topics": [
        {
            "label": "Topic Name",
            "description": "Brief description of this topic",
            "keywords": ["keyword1", "keyword2"],
            "conversation_ids": ["conv_id1", "conv_id2"],
            "confidence": 0.85,
            "subtopics": ["subtopic1", "subtopic2"]
        }
    ],
    "clusters": [
        {
            "name": "Cluster Name",
            "topics": ["Topic1", "Topic2"],
            "relationship": "Description of how these topics relate"
        }
    ]
}

Be thorough but avoid over-extraction. Focus on meaningful, recurring themes.""",
    tools=["Read", "Grep", "Glob"],
    model="sonnet",
)


# Sentiment tracking subagent
SENTIMENT_TRACKER = AgentDefinition(
    description="Track emotional tone and sentiment evolution across conversations.",
    prompt="""You are a sentiment analyst examining AI conversation history.

Your task:
1. Analyze the emotional tone of user messages over time
2. Identify sentiment shifts and their triggers
3. Note peaks (very positive/negative) and their context
4. Track satisfaction patterns

Output format (JSON):
{
    "overall_sentiment": {
        "score": 0.6,  // -1.0 to 1.0
        "label": "moderately positive",
        "confidence": 0.8
    },
    "timeline": [
        {
            "period": "2024-01",
            "score": 0.7,
            "notable_events": ["Positive: successful debugging session"]
        }
    ],
    "peaks": [
        {
            "type": "positive" | "negative",
            "conversation_id": "conv_id",
            "trigger": "Description of what caused this peak",
            "intensity": 0.9
        }
    ],
    "patterns": [
        "User tends to be more frustrated during debugging",
        "Positive sentiment correlates with successful code completion"
    ]
}

Focus on patterns, not individual message sentiment.""",
    tools=["Read", "Grep"],
    model="sonnet",
)


# Pattern detection subagent
PATTERN_DETECTOR = AgentDefinition(
    description="Identify prompting patterns, anti-patterns, and usage habits.",
    prompt="""You are a prompting pattern analyst examining AI conversation history.

Your task:
1. Identify recurring prompting patterns (effective and ineffective)
2. Flag anti-patterns that lead to poor results
3. Note effective techniques the user employs
4. Suggest improvements based on observed patterns

Output format (JSON):
{
    "effective_patterns": [
        {
            "name": "Pattern Name",
            "description": "How the user employs this pattern",
            "examples": ["Brief example 1", "Brief example 2"],
            "frequency": 15,
            "effectiveness": 0.9
        }
    ],
    "anti_patterns": [
        {
            "name": "Anti-Pattern Name",
            "description": "What the user does that's ineffective",
            "examples": ["Brief example"],
            "frequency": 5,
            "impact": "Leads to clarification loops",
            "suggestion": "How to improve"
        }
    ],
    "habits": [
        {
            "habit": "Description of observed habit",
            "frequency": "often" | "sometimes" | "rarely",
            "assessment": "beneficial" | "neutral" | "harmful"
        }
    ],
    "recommendations": [
        "Specific, actionable recommendation based on patterns"
    ]
}

Be constructive. Focus on patterns with improvement potential.""",
    tools=["Read", "Grep", "Glob"],
    model="sonnet",
)


# Temporal analysis subagent
TEMPORAL_ANALYST = AgentDefinition(
    description="Analyze time-based usage patterns and trends.",
    prompt="""You are a temporal pattern analyst examining AI conversation history.

Your task:
1. Identify usage patterns by time of day, day of week, month
2. Find burst periods vs quiet periods
3. Correlate time patterns with topics
4. Detect trends and seasonality

Output format (JSON):
{
    "usage_patterns": {
        "peak_hours": [9, 10, 14, 15],
        "peak_days": ["Tuesday", "Wednesday"],
        "quiet_periods": ["Weekends", "Early morning"],
        "average_daily": 3.5
    },
    "trends": [
        {
            "period": "2024-Q1 to 2024-Q2",
            "direction": "increasing" | "decreasing" | "stable",
            "magnitude": 0.25,  // percentage change
            "notes": "Usage increased after starting new project"
        }
    ],
    "bursts": [
        {
            "start_date": "2024-03-15",
            "end_date": "2024-03-18",
            "intensity": 3.5,  // multiplier vs average
            "likely_cause": "Project deadline"
        }
    ],
    "topic_time_correlation": [
        {
            "topic": "Debugging",
            "peak_time": "afternoon",
            "pattern": "More debugging queries later in the day"
        }
    ]
}

Use conversation timestamps to identify patterns. Be specific about dates.""",
    tools=["Read", "Grep"],
    model="haiku",  # Lighter model for metadata analysis
)


# All available agents
AGENTS = {
    "topic-extractor": TOPIC_EXTRACTOR,
    "sentiment-tracker": SENTIMENT_TRACKER,
    "pattern-detector": PATTERN_DETECTOR,
    "temporal-analyst": TEMPORAL_ANALYST,
}


def get_agents_dict() -> dict[str, dict[str, Any]]:
    """Get agents in format suitable for ClaudeCodeOptions."""
    return {name: agent.to_dict() for name, agent in AGENTS.items()}
