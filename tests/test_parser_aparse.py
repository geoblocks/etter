"""Tests for the async GeoFilterParser.aparse method."""

import pytest

from etter.exceptions import ParsingError
from etter.parser import GeoFilterParser
from tests.test_parser_streaming import MockLLM

pytestmark = pytest.mark.anyio


async def test_aparse_returns_geo_query():
    parser = GeoFilterParser(llm=MockLLM(return_valid=True))

    result = await parser.aparse("near Lake Geneva")

    assert result.reference_location.name == "Lake Geneva"
    assert result.spatial_relation.relation == "near"
    assert result.spatial_relation.category == "buffer"
    assert result.original_query == "near Lake Geneva"


async def test_aparse_overwrites_original_query():
    """aparse should set original_query to the caller's string even if the LLM returned a different one."""
    parser = GeoFilterParser(llm=MockLLM(return_valid=True))

    result = await parser.aparse("something else entirely")

    assert result.original_query == "something else entirely"


async def test_aparse_raises_parsing_error_on_invalid_response():
    parser = GeoFilterParser(llm=MockLLM(return_valid=False))

    with pytest.raises(ParsingError):
        await parser.aparse("near Lake Geneva")
