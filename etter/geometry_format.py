"""
Utilities for converting GeoJSON geometry dicts to alternative output formats (WKT, WKB).
"""

from shapely.geometry import shape

from .models import Feature, GeoJsonGeometry, GeometryFormat


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
    geom = shape(geometry)
    if fmt == "wkt":
        return geom.wkt
    return geom.wkb_hex


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
