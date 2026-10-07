"""Tests for how GeoFilterParser reports LLM transport failures."""

import pytest

from etter.exceptions import LLMInvocationError, ParsingError
from etter.parser import GeoFilterParser

pytestmark = pytest.mark.anyio


class FailingLLM:
    def with_structured_output(self, _schema, **_kwargs):
        return self

    def invoke(self, _messages):
        raise RuntimeError("429 rate limit")

    async def ainvoke(self, _messages):
        raise RuntimeError("429 rate limit")


def test_parse_raises_llm_invocation_error_with_cause():
    parser = GeoFilterParser(llm=FailingLLM())

    with pytest.raises(LLMInvocationError) as exc_info:
        parser.parse("near Lake Geneva")

    assert isinstance(exc_info.value, ParsingError)
    assert isinstance(exc_info.value.original_error, RuntimeError)


async def test_aparse_raises_llm_invocation_error():
    parser = GeoFilterParser(llm=FailingLLM())

    with pytest.raises(LLMInvocationError):
        await parser.aparse("near Lake Geneva")


async def test_parse_stream_reports_llm_failure_once():
    parser = GeoFilterParser(llm=FailingLLM())
    events = []

    with pytest.raises(LLMInvocationError):
        async for event in parser.parse_stream("near Lake Geneva"):
            events.append(event)

    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert error_events[0]["content"].startswith("LLM invocation failed")
