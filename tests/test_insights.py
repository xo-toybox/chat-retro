"""Tests for insight generators."""

import pytest

from chat_retro.insights import (
    INSIGHT_AGENTS,
    PROMPT_IMPROVEMENT_SCHEMA,
    PROMPT_IMPROVER,
    REPETITION_DETECTOR,
    REPETITION_SCHEMA,
    USAGE_OPTIMIZATION_SCHEMA,
    USAGE_OPTIMIZER,
    ContextRecommendation,
    InsightAgentDefinition,
    PromptExample,
    PromptImprovement,
    PromptImprovementOutput,
    QueryTemplate,
    RepetitiveQuery,
    RepetitionOutput,
    TimeRecommendation,
    UsageOptimizationOutput,
    UsageRecommendation,
    get_insight_agents_dict,
)


class TestPydanticModels:
    """Test Pydantic models for insights."""

    def test_prompt_example_creation(self) -> None:
        example = PromptExample(
            before="Write code",
            after="Write a Python function that validates email addresses",
            improvement_type="specificity",
            explanation="Added language and specific task",
        )
        assert example.before == "Write code"
        assert example.after.startswith("Write a Python")

    def test_prompt_improvement_creation(self) -> None:
        improvement = PromptImprovement(
            category="Clarity",
            suggestion="Be more specific about expected output format",
            priority="high",
        )
        assert improvement.category == "Clarity"
        assert improvement.priority == "high"

    def test_prompt_improvement_output(self) -> None:
        output = PromptImprovementOutput(
            improvements=[
                PromptImprovement(
                    category="Clarity",
                    suggestion="Add output format specifications",
                )
            ],
            summary="Focus on specificity",
            quick_wins=["Add format requests", "Include constraints"],
        )
        assert len(output.improvements) == 1
        assert len(output.quick_wins) == 2

    def test_repetitive_query_creation(self) -> None:
        query = RepetitiveQuery(
            pattern="Explain X concept",
            frequency=5,
            examples=["Explain REST", "Explain OOP"],
        )
        assert query.frequency == 5
        assert len(query.examples) == 2

    def test_query_template_creation(self) -> None:
        template = QueryTemplate(
            name="Code Review",
            template="Review this {language} code for {concern}: {code}",
            variables=["language", "concern", "code"],
            use_case="Requesting code reviews",
        )
        assert len(template.variables) == 3
        assert "{language}" in template.template

    def test_repetition_output(self) -> None:
        output = RepetitionOutput(
            repetitive_queries=[
                RepetitiveQuery(pattern="How to X", frequency=3, examples=[])
            ],
            suggested_templates=[
                QueryTemplate(
                    name="Learning",
                    template="Explain {topic}",
                    variables=["topic"],
                    use_case="Learning new concepts",
                )
            ],
            consolidation_opportunities=["Combine API questions"],
        )
        assert len(output.repetitive_queries) == 1
        assert len(output.suggested_templates) == 1

    def test_usage_recommendation_creation(self) -> None:
        rec = UsageRecommendation(
            recommendation="Start complex tasks in the morning",
            rationale="Higher success rate observed",
            based_on="Analysis of 50 conversations",
            actionable_steps=["Schedule complex work before 10am"],
        )
        assert "morning" in rec.recommendation
        assert len(rec.actionable_steps) == 1

    def test_time_recommendation_creation(self) -> None:
        rec = TimeRecommendation(
            optimal_times=["9am-11am", "2pm-4pm"],
            avoid_times=["late night"],
            reasoning="Higher engagement during these periods",
        )
        assert len(rec.optimal_times) == 2

    def test_context_recommendation_creation(self) -> None:
        rec = ContextRecommendation(
            topic="Code debugging",
            best_approach="Provide full error message and context",
            context_tips=["Include stack trace", "Mention recent changes"],
        )
        assert rec.topic == "Code debugging"
        assert len(rec.context_tips) == 2

    def test_usage_optimization_output(self) -> None:
        output = UsageOptimizationOutput(
            recommendations=[
                UsageRecommendation(
                    recommendation="Use morning hours",
                    rationale="Better focus",
                    based_on="Usage patterns",
                )
            ],
            time_recommendations=TimeRecommendation(
                optimal_times=["morning"],
                avoid_times=["night"],
                reasoning="Pattern analysis",
            ),
            summary_bullets=["Work in mornings", "Provide context"],
        )
        assert len(output.recommendations) == 1
        assert output.time_recommendations is not None
        assert len(output.summary_bullets) == 2


class TestSchemaGeneration:
    """Test JSON Schema generation."""

    def test_prompt_improvement_schema_exists(self) -> None:
        assert PROMPT_IMPROVEMENT_SCHEMA is not None
        assert "properties" in PROMPT_IMPROVEMENT_SCHEMA

    def test_prompt_improvement_schema_has_improvements(self) -> None:
        props = PROMPT_IMPROVEMENT_SCHEMA.get("properties", {})
        assert "improvements" in props
        assert "summary" in props

    def test_repetition_schema_exists(self) -> None:
        assert REPETITION_SCHEMA is not None
        assert "properties" in REPETITION_SCHEMA

    def test_repetition_schema_has_templates(self) -> None:
        props = REPETITION_SCHEMA.get("properties", {})
        assert "repetitive_queries" in props
        assert "suggested_templates" in props

    def test_usage_optimization_schema_exists(self) -> None:
        assert USAGE_OPTIMIZATION_SCHEMA is not None
        assert "properties" in USAGE_OPTIMIZATION_SCHEMA

    def test_usage_optimization_schema_has_recommendations(self) -> None:
        props = USAGE_OPTIMIZATION_SCHEMA.get("properties", {})
        assert "recommendations" in props
        assert "summary_bullets" in props


class TestInsightAgentDefinition:
    """Test InsightAgentDefinition dataclass."""

    def test_basic_creation(self) -> None:
        agent = InsightAgentDefinition(
            description="Test agent",
            prompt="Test prompt",
            tools=["Read"],
        )
        assert agent.description == "Test agent"
        assert agent.model == "sonnet"

    def test_to_dict(self) -> None:
        agent = InsightAgentDefinition(
            description="Test",
            prompt="Prompt",
            tools=["Read", "Grep"],
            output_schema={"type": "object"},
        )
        d = agent.to_dict()
        assert d["description"] == "Test"
        assert d["tools"] == ["Read", "Grep"]
        assert "output_schema" in d

    def test_to_dict_without_schema(self) -> None:
        agent = InsightAgentDefinition(
            description="Test",
            prompt="Prompt",
            tools=["Read"],
        )
        d = agent.to_dict()
        assert "output_schema" not in d


class TestPromptImprover:
    """Test prompt improvement agent."""

    def test_has_required_fields(self) -> None:
        assert PROMPT_IMPROVER.description
        assert PROMPT_IMPROVER.prompt
        assert PROMPT_IMPROVER.tools

    def test_description_mentions_prompt(self) -> None:
        assert "prompt" in PROMPT_IMPROVER.description.lower()

    def test_has_output_schema(self) -> None:
        assert PROMPT_IMPROVER.output_schema is not None

    def test_schema_has_improvements(self) -> None:
        props = PROMPT_IMPROVER.output_schema.get("properties", {})
        assert "improvements" in props

    def test_has_file_reading_tools(self) -> None:
        assert "Read" in PROMPT_IMPROVER.tools


class TestRepetitionDetector:
    """Test repetition detection agent."""

    def test_has_required_fields(self) -> None:
        assert REPETITION_DETECTOR.description
        assert REPETITION_DETECTOR.prompt
        assert REPETITION_DETECTOR.tools

    def test_description_mentions_repetitive(self) -> None:
        assert "repetitive" in REPETITION_DETECTOR.description.lower()

    def test_has_output_schema(self) -> None:
        assert REPETITION_DETECTOR.output_schema is not None

    def test_schema_has_queries_and_templates(self) -> None:
        props = REPETITION_DETECTOR.output_schema.get("properties", {})
        assert "repetitive_queries" in props
        assert "suggested_templates" in props


class TestUsageOptimizer:
    """Test usage optimization agent."""

    def test_has_required_fields(self) -> None:
        assert USAGE_OPTIMIZER.description
        assert USAGE_OPTIMIZER.prompt
        assert USAGE_OPTIMIZER.tools

    def test_description_mentions_usage(self) -> None:
        desc_lower = USAGE_OPTIMIZER.description.lower()
        assert "time" in desc_lower or "usage" in desc_lower

    def test_has_output_schema(self) -> None:
        assert USAGE_OPTIMIZER.output_schema is not None

    def test_schema_has_recommendations(self) -> None:
        props = USAGE_OPTIMIZER.output_schema.get("properties", {})
        assert "recommendations" in props


class TestInsightAgentsRegistry:
    """Test agents registry."""

    def test_all_agents_registered(self) -> None:
        assert "prompt-improver" in INSIGHT_AGENTS
        assert "repetition-detector" in INSIGHT_AGENTS
        assert "usage-optimizer" in INSIGHT_AGENTS

    def test_agent_count(self) -> None:
        assert len(INSIGHT_AGENTS) == 3


class TestGetInsightAgentsDict:
    """Test get_insight_agents_dict function."""

    def test_returns_dict(self) -> None:
        result = get_insight_agents_dict()
        assert isinstance(result, dict)

    def test_contains_all_agents(self) -> None:
        result = get_insight_agents_dict()
        assert "prompt-improver" in result
        assert "repetition-detector" in result
        assert "usage-optimizer" in result

    def test_agent_format_is_dict(self) -> None:
        result = get_insight_agents_dict()
        for agent_dict in result.values():
            assert isinstance(agent_dict, dict)
            assert "description" in agent_dict
            assert "prompt" in agent_dict
            assert "tools" in agent_dict
