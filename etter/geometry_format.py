"""
Read geometries given as GeoJSON, WKT, WKB or shapely, and write them as GeoJSON, WKT or WKB.
"""

from typing import TypeAlias

import shapely
from shapely.errors import GEOSException
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry

from .models import Feature, GeoJsonGeometry, GeometryFormat

GeometryInput: TypeAlias = GeoJsonGeometry | BaseGeometry | str | bytes | bytearray | memoryview


def parse_geometry(geometry: GeometryInput) -> BaseGeometry:
    """
    Read a geometry given in any of the supported input formats.

    A string is hex-encoded WKB when it starts with a WKB byte-order marker ("00" or "01"),
    WKT otherwise. Hex is decoded in Python: GEOS's own hex reader is about 15 times slower
    on large outlines.

    Raises:
        ValueError: If a string or bytes value is not a valid WKT or WKB geometry.
    """
    if isinstance(geometry, BaseGeometry):
        return geometry
    try:
        if isinstance(geometry, (bytes, bytearray, memoryview)):
            # Database drivers return binary columns as any of these (psycopg2: memoryview).
            return shapely.from_wkb(bytes(geometry))
        if isinstance(geometry, str):
            if geometry[:2] in ("00", "01"):
                return shapely.from_wkb(bytes.fromhex(geometry))
            return shapely.from_wkt(geometry)
    except (GEOSException, ValueError) as exc:
        raise ValueError(f"Not a valid WKT or WKB geometry: {str(geometry)[:40]!r}") from exc
    return shape(geometry)


def format_geometry(geometry: BaseGeometry, fmt: GeometryFormat) -> GeoJsonGeometry | str:
    """Return a shapely geometry as a GeoJSON dict, a WKT string or a hex-encoded WKB string."""
    if fmt == "geojson":
        return mapping(geometry)
    if fmt == "wkt":
        return geometry.wkt
    # Same uppercase hex as geometry.wkb_hex, encoded in Python: about 10 times faster on large outlines.
    return shapely.to_wkb(geometry).hex().upper()


def convert_geometry(geometry: GeoJsonGeometry, fmt: GeometryFormat) -> GeoJsonGeometry | str:
    """
    Convert a GeoJSON geometry dict to the requested format.

    Args:
        geometry: GeoJSON geometry dict (e.g. {"type": "Point", "coordinates": [...]})
        fmt: Target format — "geojson" returns the dict unchanged, "wkt" returns a WKT string,
             "wkb" returns a hex-encoded WKB string.

    Returns:
        The geometry in the requested format.
    """
    if fmt == "geojson":
        return geometry
    return format_geometry(shape(geometry), fmt)


def convert_feature_geometry(feature: Feature, fmt: GeometryFormat) -> Feature | dict:
    """
    Return a copy of a GeoJSON Feature dict with its geometry converted to the requested format.

    Args:
        feature: GeoJSON Feature dict with a "geometry" key.
        fmt: Target geometry format.

    Returns:
        A new dict identical to the input except the "geometry" value is converted.
        Returns a Feature when fmt is "geojson"; a plain dict otherwise (geometry becomes a string).
    """
    if fmt == "geojson":
        return feature
    return {**feature, "geometry": convert_geometry(feature["geometry"], fmt)}
