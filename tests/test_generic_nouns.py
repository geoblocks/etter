"""Tests that generic terrain words are not extracted as a reference location (requires LLM)."""

import pytest

from etter.exceptions import NoReferenceLocationError


@pytest.mark.parametrize(
    "query",
    [
        "hikes around a lake",
        "Wanderungen am See",
        "hotels near the station",
    ],
)
def test_generic_noun_is_not_a_reference_location(parser, query):
    with pytest.raises(NoReferenceLocationError):
        parser.parse(query)


@pytest.mark.parametrize("query", ["hikes near Lake Geneva", "hotels near Zürich main station"])
def test_named_place_still_extracted(parser, query):
    result = parser.parse(query)
    assert result.reference_location is not None
