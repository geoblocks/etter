"""Shared base for lazily-loaded, in-memory GeoDataFrame-backed geo datasources."""

from importlib.util import find_spec
from typing import TYPE_CHECKING, Any

from geojson import Feature

if TYPE_CHECKING:
    import geopandas as gpd


_FILES_EXTRA_MODULES = ("geopandas", "rapidfuzz")


def _require_files_extra() -> None:
    """Check, without importing them, that the ``[files]`` extra's packages are installed."""
    missing = [name for name in _FILES_EXTRA_MODULES if find_spec(name) is None]
    if missing:
        raise ImportError(
            f"File-backed datasources require {' and '.join(missing)}. "
            'Install the extra with: pip install "etter[files]"'
        )


def _is_missing(val: Any) -> bool:
    """Return True for None and pandas missing values (NaN, NaT, NA)."""
    if val is None:
        return True
    import pandas as pd

    try:
        return bool(pd.isna(val))
    except (TypeError, ValueError):
        return False


def to_serializable(val: Any) -> str | int | float | bool | None:
    """Convert a pandas/numpy value to a JSON-serializable Python primitive.

    Returns None for missing values (NaN, NaT, None) so callers can omit them
    from feature properties.
    """
    if _is_missing(val):
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    if hasattr(val, "item"):
        return val.item()
    return val


def fuzzy_search_index(
    normalized: str,
    token_index: dict[str, set[str]],
    name_index: dict[str, list[int]],
    threshold: float = 75.0,
) -> list[int]:
    """
    Fuzzy search over a token-inverted index.

    Uses token_sort_ratio so that single-token candidates do not score 100%
    against multi-token queries (avoids the subset-match inflation of
    token_set_ratio).

    Args:
        normalized: Already-normalized query string.
        token_index: Maps each token to the set of indexed name keys that contain it.
        name_index: Maps each indexed name key to its list of row indices.
        threshold: Minimum score (0–100) to include a candidate.

    Returns:
        Row indices sorted by descending score.
    """
    from rapidfuzz import fuzz

    candidates: set[str] = set()
    for token in normalized.split():
        candidates |= token_index.get(token, set())

    matches: list[tuple[int, float]] = []
    for name in candidates:
        score = fuzz.token_sort_ratio(normalized, name)
        if score >= threshold:
            for idx in name_index[name]:
                matches.append((idx, score))

    matches.sort(key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in matches]


class GeoDataFrameSource:
    """
    Shared lazy-loading, fuzzy-search, and by-id lookup behavior for datasources backed by
    an in-memory GeoDataFrame with a name/token index (SwissNames3DSource, IGNBDCartoSource,
    SwissBoundaries3DSource).

    Subclasses set ``self._gdf``, ``self._name_index``, ``self._token_index``, and
    ``self._id_col`` in ``__init__``, and implement ``_load_data()`` and ``_row_to_feature()``.
    """

    _gdf: "gpd.GeoDataFrame | None"
    _name_index: dict[str, list[int]]
    _token_index: dict[str, set[str]]
    _id_col: str | None

    def preload(self) -> None:
        """Eagerly load data. Call at startup to avoid first-query latency."""
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        """Load data lazily on first access."""
        if self._gdf is not None:
            return
        self._load_data()

    def _load_data(self) -> None:
        raise NotImplementedError

    def _row_to_feature(self, idx: int) -> Feature:
        raise NotImplementedError

    def _fuzzy_search(self, normalized: str, threshold: float = 75.0) -> list[int]:
        return fuzzy_search_index(normalized, self._token_index, self._name_index, threshold)

    def get_by_id(self, feature_id: str) -> Feature | None:
        """
        Get a specific feature by its unique identifier.

        Args:
            feature_id: Unique identifier (e.g. a UUID, ``cleabs`` string, or row index).

        Returns:
            The matching GeoJSON Feature dict, or None if not found.
        """
        self._ensure_loaded()
        assert self._gdf is not None

        if self._id_col:
            matches = self._gdf[self._gdf[self._id_col].astype(str) == feature_id]
            if not matches.empty:
                return self._row_to_feature(matches.index[0])

        # Fallback: try as row index
        try:
            idx = int(feature_id)
            if 0 <= idx < len(self._gdf):
                return self._row_to_feature(idx)
        except ValueError:
            pass

        return None
