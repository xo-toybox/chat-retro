"""Bootstrap templates for guided analysis."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "template_prompts"


class TemplateKey(StrEnum):
    """Available template identifiers."""

    SELF_PORTRAIT = "self-portrait"
    SELF_PORTRAIT_V2 = "self-portrait-v2"


@dataclass
class Template:
    """A predefined analysis template."""

    id: TemplateKey
    name: str
    description: str
    prompt_file: str  # filename in template_prompts/

    @property
    def prompt(self) -> str:
        """Load prompt from file."""
        return (PROMPTS_DIR / self.prompt_file).read_text()


TEMPLATES: dict[TemplateKey, Template] = {
    TemplateKey.SELF_PORTRAIT: Template(
        id=TemplateKey.SELF_PORTRAIT,
        name="Self-Portrait",
        description="Personal reflection: themes, archetype, dimensions, poem, and surprises",
        prompt_file="self-portrait.md",
    ),
    TemplateKey.SELF_PORTRAIT_V2: Template(
        id=TemplateKey.SELF_PORTRAIT_V2,
        name="Self-Portrait (v2)",
        description="Personal reflection with epistemic guardrails: acknowledges data limitations, separates confidence levels",
        prompt_file="self-portrait-v2.md",
    ),
}


def get_template(template_id: str | TemplateKey) -> Template | None:
    """Get a template by ID."""
    if isinstance(template_id, str):
        try:
            template_id = TemplateKey(template_id)
        except ValueError:
            return None
    return TEMPLATES.get(template_id)


def list_templates() -> list[Template]:
    """List all registered templates."""
    return list(TEMPLATES.values())
