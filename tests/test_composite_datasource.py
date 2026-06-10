"""
Tests for CompositeDataSource.
"""

import pytest
from geojson import Feature, Point

from etter.datasources.composite import CompositeDataSource


def make_feature(name: str, type: str, fid: str) -> Feature:
    return Feature(
        id=fid,
        geometry=Point((6.0, 46.0)),
        properties={"name": name, "type": type, "confidence": 1.0},
    )


class StubSource:
    """Minimal GeoDataSource stub backed by a fixed list of features."""

    def __init__(self, features: list[Feature], types: list[str] | None = None):
        self._features = features
        self._types = types or []

    def search(self, _name: str, type: str | None = None, max_results: int = 10) -> list[Feature]:  # noqa: ARG002
        return self._features[:max_results]

    def get_by_id(self, feature_id: str) -> Feature | None:
        return next((f for f in self._features if f["id"] == feature_id), None)

    def get_available_types(self) -> list[str]:
        return self._types


class PreloadableStub(StubSource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preloaded = False

    def preload(self) -> None:
        self.preloaded = True


# --- construction ---


def test_requires_at_least_one_source():
    with pytest.raises(ValueError):
        CompositeDataSource()


# --- search ---


def test_search_merges_results_from_all_sources():
    a = make_feature("Rhône", "river", "a1")
    b = make_feature("Rhône", "river", "b1")
    composite = CompositeDataSource(StubSource([a]), StubSource([b]))
    results = composite.search("Rhône")
    assert len(results) == 2
    assert results[0]["id"] == "a1"
    assert results[1]["id"] == "b1"


def test_search_max_results_applied_per_source():
    """Each source is capped independently; all sources are always queried."""
    features_a = [make_feature("Rhône", "river", f"a{i}") for i in range(5)]
    features_b = [make_feature("Rhône", "river", f"b{i}") for i in range(5)]
    composite = CompositeDataSource(StubSource(features_a), StubSource(features_b))
    results = composite.search("Rhône", max_results=3)
    # source A returns 3, source B returns 3 → 6 total
    assert len(results) == 6
    assert results[0]["id"] == "a0"
    assert results[3]["id"] == "b0"


def test_search_second_source_queried_when_first_fills_quota():
    """Regression for the short-circuit bug fixed in this codebase."""
    features_a = [make_feature("Rhône", "river", f"a{i}") for i in range(10)]
    b = make_feature("Rhône", "river", "b0")
    composite = CompositeDataSource(StubSource(features_a), StubSource([b]))
    results = composite.search("Rhône", max_results=10)
    ids = [f["id"] for f in results]
    assert "b0" in ids


def test_search_empty_source_skipped():
    b = make_feature("Geneva", "city", "b1")
    composite = CompositeDataSource(StubSource([]), StubSource([b]))
    results = composite.search("Geneva")
    assert len(results) == 1
    assert results[0]["id"] == "b1"


def test_search_passes_type_and_name_to_sources():
    received = {}

    class CapturingSource:
        def search(self, name, type=None, max_results=10):  # noqa: ARG002
            received["name"] = name
            received["type"] = type
            return []

        def get_by_id(self, _fid):
            return None

        def get_available_types(self):
            return []

    composite = CompositeDataSource(CapturingSource())
    composite.search("Bern", type="city")
    assert received == {"name": "Bern", "type": "city"}


# --- get_by_id ---


def test_get_by_id_returns_first_match():
    a = make_feature("Lausanne", "city", "x1")
    b = make_feature("Lausanne", "city", "x1")  # same id, second source
    composite = CompositeDataSource(StubSource([a]), StubSource([b]))
    result = composite.get_by_id("x1")
    assert result is a


def test_get_by_id_falls_through_to_second_source():
    a = make_feature("Bern", "city", "a1")
    b = make_feature("Zurich", "city", "b1")
    composite = CompositeDataSource(StubSource([a]), StubSource([b]))
    result = composite.get_by_id("b1")
    assert result is b


def test_get_by_id_returns_none_when_not_found():
    composite = CompositeDataSource(StubSource([]))
    assert composite.get_by_id("missing") is None


# --- get_available_types ---


def test_get_available_types_returns_union():
    composite = CompositeDataSource(
        StubSource([], types=["city", "lake"]),
        StubSource([], types=["lake", "river"]),
    )
    assert composite.get_available_types() == ["city", "lake", "river"]


def test_get_available_types_sorted():
    composite = CompositeDataSource(
        StubSource([], types=["river", "city"]),
        StubSource([], types=["lake"]),
    )
    types = composite.get_available_types()
    assert types == sorted(types)


# --- preload ---


def test_preload_calls_preloadable_sources():
    p = PreloadableStub([])
    s = StubSource([])
    composite = CompositeDataSource(p, s)
    composite.preload()
    assert p.preloaded is True


def test_preload_skips_non_preloadable_sources():
    s = StubSource([])
    composite = CompositeDataSource(s)
    composite.preload()  # must not raise
