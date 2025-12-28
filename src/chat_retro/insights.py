"""Insight generators for actionable recommendations.

These agents analyze patterns and generate specific, actionable suggestions
for improving AI conversation effectiveness.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from chat_retro.agents import AgentDefinition


# ============================================================================
# Pydantic models for insight outputs
# ============================================================================


class PromptExample(BaseModel):
    """A before/after prompt improvement example."""

    before: str
    after: str
    improvement_type: str
    explanation: str


class PromptImprovement(BaseModel):
    """A specific prompt improvement suggestion."""

    category: str
    suggestion: str
    examples: list[PromptExample] = Field(default_factory=list)
    priority: Literal["high", "medium", "low"] = "medium"
    impact: str | None = None


class PromptImprovementOutput(BaseModel):
    """Output schema for prompt improvement insights."""

    improvements: list[PromptImprovement]
    summary: str
    quick_wins: list[str] = Field(default_factory=list)


class RepetitiveQuery(BaseModel):
    """A group of repetitive queries."""

    pattern: str
    frequency: int
    examples: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)


class QueryTemplate(BaseModel):
    """A suggested template for common queries."""

    name: str
    template: str
    variables: list[str] = Field(default_factory=list)
    use_case: str


class RepetitionOutput(BaseModel):
    """Output schema for repetition detection."""

    repetitive_queries: list[RepetitiveQuery]
    suggested_templates: list[QueryTemplate]
    consolidation_opportunities: list[str] = Field(default_factory=list)
    time_saved_estimate: str | None = None


class UsageRecommendation(BaseModel):
    """A specific usage optimization recommendation."""

    recommendation: str
    rationale: str
    based_on: str
    actionable_steps: list[str] = Field(default_factory=list)


class TimeRecommendation(BaseModel):
    """Time-based recommendation."""

    optimal_times: list[str] = Field(default_factory=list)
    avoid_times: list[str] = Field(default_factory=list)
    reasoning: str


class ContextRecommendation(BaseModel):
    """Context-based recommendation."""

    topic: str
    best_approach: str
    context_tips: list[str] = Field(default_factory=list)


class UsageOptimizationOutput(BaseModel):
    """Output schema for usage optimization insights."""

    recommendations: list[UsageRecommendation]
    time_recommendations: TimeRecommendation | None = None
    context_recommendations: list[ContextRecommendation] = Field(default_factory=list)
    summary_bullets: list[str] = Field(default_factory=list)


# ============================================================================
# Generate JSON Schemas from Pydantic models
# ============================================================================

PROMPT_IMPROVEMENT_SCHEMA: dict[str, Any] = PromptImprovementOutput.model_json_schema()
REPETITION_SCHEMA: dict[str, Any] = RepetitionOutput.model_json_schema()
USAGE_OPTIMIZATION_SCHEMA: dict[str, Any] = UsageOptimizationOutput.model_json_schema()


# ============================================================================
# Agent definitions for insights
# ============================================================================


# Prompt improvement insight agent
PROMPT_IMPROVER = AgentDefinition(
    description="Generate concrete prompt improvement suggestions with before/after examples.",
    prompt="""You are a prompt engineering coach analyzing AI conversation history.

Your task:
1. Review the user's prompting patterns in the conversations
2. Identify specific opportunities for improvement
3. Create concrete before/after examples based on ACTUAL prompts from the data
4. Prioritize suggestions by potential impact

Focus on:
- Clarity and specificity improvements
- Context-setting techniques
- Instruction structuring
- Constraint specification
- Output format requests

Be specific. Use real examples from the conversations. Don't be generic.
Your response must conform to the output schema.""",
    tools=["Read", "Grep", "Glob"],
    model="sonnet",
    output_schema=PROMPT_IMPROVEMENT_SCHEMA,
)


# Repetition detection insight agent
REPETITION_DETECTOR = AgentDefinition(
    description="Identify repetitive queries and suggest templates for common patterns.",
    prompt="""You are a workflow efficiency analyst examining AI conversation history.

Your task:
1. Find repetitive or similar queries the user makes frequently
2. Group similar queries into patterns
3. Suggest reusable templates with variables
4. Identify opportunities to consolidate repeated work

Look for:
- Similar questions asked multiple times
- Recurring task patterns
- Common request structures
- Repeated context-setting

Templates should be practical and immediately usable.
Your response must conform to the output schema.""",
    tools=["Read", "Grep", "Glob"],
    model="sonnet",
    output_schema=REPETITION_SCHEMA,
)


# Usage optimization insight agent
USAGE_OPTIMIZER = AgentDefinition(
    description="Generate time and context recommendations for optimal AI usage.",
    prompt="""You are a productivity analyst examining AI conversation history.

Your task:
1. Analyze when the user gets best results (time, context, approach)
2. Identify patterns in successful vs less successful interactions
3. Generate actionable recommendations specific to this user's data

Consider:
- Time patterns and their correlation with conversation quality
- Topic-specific approaches that work well
- Context-setting patterns that lead to better outcomes
- Session length and depth patterns

Be specific to this user's actual usage data. Avoid generic advice.
Your response must conform to the output schema.""",
    tools=["Read", "Grep", "Glob"],
    model="sonnet",
    output_schema=USAGE_OPTIMIZATION_SCHEMA,
)


# All insight agents
INSIGHT_AGENTS = {
    "prompt-improver": PROMPT_IMPROVER,
    "repetition-detector": REPETITION_DETECTOR,
    "usage-optimizer": USAGE_OPTIMIZER,
}


def get_insight_agents_dict() -> dict[str, dict[str, Any]]:
    """Get insight agents in format suitable for ClaudeCodeOptions."""
    return {name: agent.to_dict() for name, agent in INSIGHT_AGENTS.items()}
