"""Subagent definitions for specialized analysis tasks.

These agents are invoked by the main agent via the Task tool
to perform focused analysis while preserving main context.

Uses Pydantic models to define structured output schemas.
"""

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field


# ============================================================================
# Pydantic models for structured outputs
# ============================================================================


class Topic(BaseModel):
    """A topic extracted from conversations."""

    label: str
    confidence: float = Field(ge=0, le=1)
    description: str | None = None
    keywords: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)
    subtopics: list[str] = Field(default_factory=list)


class TopicCluster(BaseModel):
    """A cluster of related topics."""

    name: str
    topics: list[str]
    relationship: str | None = None


class TopicOutput(BaseModel):
    """Output schema for topic extraction."""

    topics: list[Topic]
    clusters: list[TopicCluster] = Field(default_factory=list)


class OverallSentiment(BaseModel):
    """Overall sentiment assessment."""

    score: float = Field(ge=-1, le=1)
    label: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class SentimentPeriod(BaseModel):
    """Sentiment for a time period."""

    period: str
    score: float
    notable_events: list[str] = Field(default_factory=list)


class SentimentPeak(BaseModel):
    """A peak in sentiment (positive or negative)."""

    type: Literal["positive", "negative"]
    trigger: str
    conversation_id: str | None = None
    intensity: float | None = None


class SentimentOutput(BaseModel):
    """Output schema for sentiment tracking."""

    overall_sentiment: OverallSentiment
    timeline: list[SentimentPeriod] = Field(default_factory=list)
    peaks: list[SentimentPeak] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)


class EffectivePattern(BaseModel):
    """An effective prompting pattern."""

    name: str
    description: str
    examples: list[str] = Field(default_factory=list)
    frequency: int | None = None
    effectiveness: float | None = None


class AntiPattern(BaseModel):
    """A prompting anti-pattern to avoid."""

    name: str
    description: str
    suggestion: str
    examples: list[str] = Field(default_factory=list)
    frequency: int | None = None
    impact: str | None = None


class Habit(BaseModel):
    """A user habit observation."""

    habit: str
    assessment: Literal["beneficial", "neutral", "harmful"]
    frequency: Literal["often", "sometimes", "rarely"] | None = None


class PatternOutput(BaseModel):
    """Output schema for pattern detection."""

    effective_patterns: list[EffectivePattern]
    anti_patterns: list[AntiPattern]
    recommendations: list[str]
    habits: list[Habit] = Field(default_factory=list)


class UsagePatterns(BaseModel):
    """Usage patterns by time."""

    peak_hours: list[int] = Field(default_factory=list)
    peak_days: list[str] = Field(default_factory=list)
    quiet_periods: list[str] = Field(default_factory=list)
    average_daily: float | None = None


class Trend(BaseModel):
    """A usage trend over time."""

    period: str
    direction: Literal["increasing", "decreasing", "stable"]
    magnitude: float | None = None
    notes: str | None = None


class Burst(BaseModel):
    """A burst of activity."""

    start_date: str
    intensity: float
    end_date: str | None = None
    likely_cause: str | None = None


class TopicTimeCorrelation(BaseModel):
    """Correlation between topic and time."""

    topic: str
    pattern: str
    peak_time: str | None = None


class TemporalOutput(BaseModel):
    """Output schema for temporal analysis."""

    usage_patterns: UsagePatterns
    trends: list[Trend] = Field(default_factory=list)
    bursts: list[Burst] = Field(default_factory=list)
    topic_time_correlation: list[TopicTimeCorrelation] = Field(default_factory=list)


# ============================================================================
# Generate JSON Schemas from Pydantic models
# ============================================================================

TOPIC_SCHEMA: dict[str, Any] = TopicOutput.model_json_schema()
SENTIMENT_SCHEMA: dict[str, Any] = SentimentOutput.model_json_schema()
PATTERN_SCHEMA: dict[str, Any] = PatternOutput.model_json_schema()
TEMPORAL_SCHEMA: dict[str, Any] = TemporalOutput.model_json_schema()


# ============================================================================
# Agent definitions
# ============================================================================


@dataclass
class AgentDefinition:
    """Definition for a specialized subagent.

    Mirrors the claude_code_sdk.AgentDefinition interface for use
    with ClaudeCodeOptions(agents={...}).

    Uses output_schema to enforce structured JSON responses.
    """

    description: str
    prompt: str
    tools: list[str]
    model: str = "sonnet"
    output_schema: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for SDK consumption."""
        result = {
            "description": self.description,
            "prompt": self.prompt,
            "tools": self.tools,
            "model": self.model,
        }
        if self.output_schema:
            result["output_schema"] = self.output_schema
        return result


# Topic extraction subagent
TOPIC_EXTRACTOR = AgentDefinition(
    description="Extract and cluster topics from conversation content.",
    prompt="""You are a topic extraction specialist analyzing AI conversation history.

Your task:
1. Read the conversation content thoroughly
2. Identify distinct topics and themes discussed
3. Cluster related topics together
4. Assign confidence scores based on evidence strength

Be thorough but avoid over-extraction. Focus on meaningful, recurring themes.
Your response must conform to the output schema.""",
    tools=["Read", "Grep", "Glob"],
    model="sonnet",
    output_schema=TOPIC_SCHEMA,
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

Focus on patterns, not individual message sentiment.
Your response must conform to the output schema.""",
    tools=["Read", "Grep"],
    model="sonnet",
    output_schema=SENTIMENT_SCHEMA,
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

Be constructive. Focus on patterns with improvement potential.
Your response must conform to the output schema.""",
    tools=["Read", "Grep", "Glob"],
    model="sonnet",
    output_schema=PATTERN_SCHEMA,
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

Use conversation timestamps to identify patterns. Be specific about dates.
Your response must conform to the output schema.""",
    tools=["Read", "Grep"],
    model="haiku",  # Lighter model for metadata analysis
    output_schema=TEMPORAL_SCHEMA,
)


# All available agents
AGENTS = {
    "topic-extractor": TOPIC_EXTRACTOR,
    "sentiment-tracker": SENTIMENT_TRACKER,
    "pattern-detector": PATTERN_DETECTOR,
    "temporal-analyst": TEMPORAL_ANALYST,
}


def get_agents_dict() -> dict[str, dict[str, Any]]:
    """Get agents in format suitable for ClaudeCodeOptions.

    Includes both analysis agents and insight agents.
    """
    from chat_retro.insights import get_insight_agents_dict

    result = {name: agent.to_dict() for name, agent in AGENTS.items()}
    result.update(get_insight_agents_dict())
    return result
