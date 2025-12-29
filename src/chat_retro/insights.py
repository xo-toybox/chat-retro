"""Insight generators for actionable recommendations.

These agents analyze patterns and generate specific, actionable suggestions
for improving AI conversation effectiveness.
"""

from enum import StrEnum

from claude_agent_sdk import AgentDefinition


class InsightKey(StrEnum):
    """Available insight agent identifiers."""

    PROMPT_IMPROVER = "prompt-improver"
    REPETITION_DETECTOR = "repetition-detector"
    USAGE_OPTIMIZER = "usage-optimizer"


INSIGHT_AGENTS: dict[InsightKey, AgentDefinition] = {
    InsightKey.PROMPT_IMPROVER: AgentDefinition(
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

Be specific. Use real examples from the conversations. Don't be generic.""",
        tools=["Read", "Grep", "Glob"],
        model="sonnet",
    ),
    InsightKey.REPETITION_DETECTOR: AgentDefinition(
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

Templates should be practical and immediately usable.""",
        tools=["Read", "Grep", "Glob"],
        model="sonnet",
    ),
    InsightKey.USAGE_OPTIMIZER: AgentDefinition(
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

Be specific to this user's actual usage data. Avoid generic advice.""",
        tools=["Read", "Grep", "Glob"],
        model="sonnet",
    ),
}


def get_insight_agents() -> dict[str, AgentDefinition]:
    """Get insight agents for ClaudeAgentOptions."""
    return {k: v for k, v in INSIGHT_AGENTS.items()}
