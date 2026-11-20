"""
Tests for prompt construction.
"""

import pytest

from etter.parser import GeoFilterParser
from etter.prompts import build_geo_prompt_template
from etter.spatial_config import SpatialRelationConfig


class MockLLM:
    """Minimal mock LLM for prompt-construction tests (no API calls)."""

    def with_structured_output(self, _schema, **kwargs):  # noqa: ARG002
        return self


def test_additional_instructions_in_prompt():
    """additional_instructions appear in the system message before the examples."""
    instructions = "Use French endonyms for Swiss locations."
    mock_llm = MockLLM()
    parser = GeoFilterParser(llm=mock_llm, additional_instructions=instructions)

    system = parser.prompt.format_messages(query="near Lake Geneva")[0].content

    assert instructions in system, "additional_instructions should be in the system message"
    assert system.index(instructions) < system.index("EXAMPLES:"), (
        "additional_instructions should appear before the few-shot examples"
    )


@pytest.mark.parametrize(
    "options",
    [{}, {"additional_instructions": "Use French endonyms."}, {"include_examples": False}],
    ids=["default", "instructions", "no-examples"],
)
def test_single_system_message(options):
    """Some providers reject more than one system message."""
    messages = build_geo_prompt_template(SpatialRelationConfig(), **options).format_messages(query="near Lausanne")
    assert [m.type for m in messages] == ["system", "human"]
    assert messages[1].content.endswith("near Lausanne")


def test_braces_in_additional_instructions_are_kept():
    instructions = 'Answer {"lang": "fr"} for French queries.'
    messages = build_geo_prompt_template(SpatialRelationConfig(), additional_instructions=instructions).format_messages(
        query="q"
    )
    assert instructions in messages[0].content
