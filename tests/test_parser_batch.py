"""Tests for GeoFilterParser.parse_batch and aparse_batch."""

import asyncio
import threading
import time

import pytest

from etter.models import BufferConfig, ConfidenceScore, GeoQuery, ReferenceLocation, SpatialRelation
from etter.parser import GeoFilterParser

pytestmark = pytest.mark.anyio


def _geo_query(name: str) -> GeoQuery:
    return GeoQuery(
        spatial_relation=SpatialRelation(relation="near", category="buffer"),
        reference_location=ReferenceLocation(name=name),
        buffer_config=BufferConfig(distance_m=5000, buffer_from="center"),
        confidence_breakdown=ConfidenceScore(overall=0.9, location_confidence=0.9, relation_confidence=0.9),
    )


def _query_from(messages) -> str:
    return messages[-1].content.rsplit("Query: ", 1)[1]


class SlowLLM:
    """Echoes the query back as the location name and records peak concurrency."""

    def __init__(self, delay: float = 0.05):
        self.delay = delay
        self.active = 0
        self.peak = 0
        self._lock = threading.Lock()

    def with_structured_output(self, _schema, **_kwargs):
        return self

    def _enter(self):
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)

    def _exit(self):
        with self._lock:
            self.active -= 1

    def invoke(self, messages):
        self._enter()
        time.sleep(self.delay)
        self._exit()
        return _geo_query(_query_from(messages))

    async def ainvoke(self, messages):
        self._enter()
        await asyncio.sleep(self.delay)
        self._exit()
        return _geo_query(_query_from(messages))


QUERIES = [f"near Place{i}" for i in range(6)]


def test_parse_batch_is_sequential_by_default():
    llm = SlowLLM()
    results = GeoFilterParser(llm=llm).parse_batch(QUERIES)

    assert [r.reference_location.name for r in results] == QUERIES
    assert llm.peak == 1


def test_parse_batch_runs_concurrently_and_keeps_order():
    llm = SlowLLM()
    results = GeoFilterParser(llm=llm).parse_batch(QUERIES, max_concurrency=3)

    assert [r.reference_location.name for r in results] == QUERIES
    assert 1 < llm.peak <= 3


async def test_aparse_batch_runs_concurrently_and_keeps_order():
    llm = SlowLLM()
    results = await GeoFilterParser(llm=llm).aparse_batch(QUERIES, max_concurrency=3)

    assert [r.reference_location.name for r in results] == QUERIES
    assert 1 < llm.peak <= 3


@pytest.fixture
def anyio_backend():
    # aparse_batch relies on asyncio primitives, as LangChain's own async API does.
    return "asyncio"
