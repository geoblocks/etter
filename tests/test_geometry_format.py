"""
Tests for geometry output format conversion.
"""

import re

import pytest
import shapely
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry

from etter.geometry_format import convert_feature_geometry, convert_geometry
from etter.models import BufferConfig, SpatialRelation
from etter.spatial import apply_spatial_relation

POINT_GEOM = {"type": "Point", "coordinates": [6.63, 46.52]}
POINT_FEATURE = {
    "type": "Feature",
    "id": "test-1",
    "geometry": POINT_GEOM,
    "bbox": [6.63, 46.52, 6.63, 46.52],
    "properties": {"name": "Lausanne"},
}


class TestConvertGeometry:
    def test_geojson_passthrough(self):
        result = convert_geometry(POINT_GEOM, "geojson")
        assert result is POINT_GEOM

    def test_wkt_point(self):
        result = convert_geometry(POINT_GEOM, "wkt")
        assert isinstance(result, str)
        assert result.startswith("POINT")
        assert "6.63" in result
        assert "46.52" in result

    def test_wkb_point(self):
        result = convert_geometry(POINT_GEOM, "wkb")
        assert isinstance(result, str)
        assert re.fullmatch(r"[0-9a-fA-F]+", result)

    def test_wkb_is_hex_decodable(self):
        result = convert_geometry(POINT_GEOM, "wkb")
        decoded = bytes.fromhex(result)
        assert len(decoded) > 0

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError, match="Unknown geometry format"):
            convert_geometry(POINT_GEOM, "Shapely")  # type: ignore[arg-type]

    def test_shapely_point(self):
        result = convert_geometry(POINT_GEOM, "shapely")
        assert result.equals(shape(POINT_GEOM))

    def test_wkt_polygon(self):
        from shapely.geometry import Polygon

        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        geom = mapping(poly)
        result = convert_geometry(geom, "wkt")
        assert result.startswith("POLYGON")

    def test_wkb_polygon(self):
        from shapely.geometry import Polygon

        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        geom = mapping(poly)
        result = convert_geometry(geom, "wkb")
        assert isinstance(result, str)
        assert re.fullmatch(r"[0-9a-fA-F]+", result)


class TestConvertFeatureGeometry:
    def test_geojson_passthrough_returns_same_object(self):
        result = convert_feature_geometry(POINT_FEATURE, "geojson")
        assert result is POINT_FEATURE

    def test_wkt_replaces_geometry(self):
        result = convert_feature_geometry(POINT_FEATURE, "wkt")
        assert isinstance(result["geometry"], str)
        assert result["geometry"].startswith("POINT")

    def test_wkb_replaces_geometry(self):
        result = convert_feature_geometry(POINT_FEATURE, "wkb")
        assert isinstance(result["geometry"], str)
        assert re.fullmatch(r"[0-9a-fA-F]+", result["geometry"])

    def test_shapely_replaces_geometry(self):
        result = convert_feature_geometry(POINT_FEATURE, "shapely")
        assert isinstance(result["geometry"], BaseGeometry)
        assert result["properties"] == POINT_FEATURE["properties"]
        assert POINT_FEATURE["geometry"] is POINT_GEOM

    def test_other_fields_preserved(self):
        result = convert_feature_geometry(POINT_FEATURE, "wkt")
        assert result["type"] == "Feature"
        assert result["id"] == "test-1"
        assert result["bbox"] == [6.63, 46.52, 6.63, 46.52]
        assert result["properties"]["name"] == "Lausanne"

    def test_original_feature_not_mutated(self):
        original_geometry = POINT_FEATURE["geometry"]
        convert_feature_geometry(POINT_FEATURE, "wkt")
        assert POINT_FEATURE["geometry"] is original_geometry


class TestApplySpatialRelationFormat:
    def test_default_format_is_geojson(self):
        relation = SpatialRelation(relation="in", category="containment")
        result = apply_spatial_relation(POINT_GEOM, relation)
        assert isinstance(result, dict)
        # Containment on a point falls back to a buffer (see test_spatial.py).
        assert result["type"] == "Polygon"

    def test_geojson_explicit(self):
        relation = SpatialRelation(relation="in", category="containment")
        result = apply_spatial_relation(POINT_GEOM, relation, geometry_format="geojson")
        assert isinstance(result, dict)

    def test_wkt_containment(self):
        relation = SpatialRelation(relation="in", category="containment")
        result = apply_spatial_relation(POINT_GEOM, relation, geometry_format="wkt")
        assert isinstance(result, str)
        # Containment on a point falls back to a buffer (see test_spatial.py).
        assert result.startswith("POLYGON")

    def test_wkb_containment(self):
        relation = SpatialRelation(relation="in", category="containment")
        result = apply_spatial_relation(POINT_GEOM, relation, geometry_format="wkb")
        assert isinstance(result, str)
        assert re.fullmatch(r"[0-9a-fA-F]+", result)

    def test_wkt_buffer(self):
        relation = SpatialRelation(relation="near", category="buffer")
        config = BufferConfig(distance_m=5000, buffer_from="center")
        result = apply_spatial_relation(POINT_GEOM, relation, config, geometry_format="wkt")
        assert isinstance(result, str)
        assert result.startswith("POLYGON")

    def test_wkb_buffer(self):
        relation = SpatialRelation(relation="near", category="buffer")
        config = BufferConfig(distance_m=5000, buffer_from="center")
        result = apply_spatial_relation(POINT_GEOM, relation, config, geometry_format="wkb")
        assert isinstance(result, str)
        assert re.fullmatch(r"[0-9a-fA-F]+", result)

    def test_shapely_buffer(self):
        relation = SpatialRelation(relation="near", category="buffer")
        config = BufferConfig(distance_m=5000, buffer_from="center")
        result = apply_spatial_relation(POINT_GEOM, relation, config, geometry_format="shapely")
        assert isinstance(result, BaseGeometry)
        assert mapping(result) == apply_spatial_relation(POINT_GEOM, relation, config)

    def test_shapely_containment_returns_reference(self):
        relation = SpatialRelation(relation="in", category="containment")
        result = apply_spatial_relation(POLYGON.wkb, relation, geometry_format="shapely")
        assert isinstance(result, BaseGeometry)
        assert result.equals_exact(POLYGON, 0)

    def test_wkt_directional(self):
        relation = SpatialRelation(relation="north_of", category="directional")
        config = BufferConfig(distance_m=10000, buffer_from="center")
        result = apply_spatial_relation(POINT_GEOM, relation, config, geometry_format="wkt")
        assert isinstance(result, str)
        assert result.startswith("POLYGON")


POLYGON_GEOM = {"type": "Polygon", "coordinates": [[[6.6, 46.5], [6.7, 46.5], [6.7, 46.55], [6.6, 46.55], [6.6, 46.5]]]}
POLYGON = shape(POLYGON_GEOM)


class TestApplySpatialRelationInput:
    """The reference geometry can be given in any of the output formats, or as a shapely geometry."""

    @pytest.mark.parametrize(
        "geometry",
        [POLYGON, POLYGON.wkt, POLYGON.wkb_hex, POLYGON.wkb, bytearray(POLYGON.wkb), memoryview(POLYGON.wkb)],
        ids=["shapely", "wkt", "wkb-hex", "wkb-bytes", "wkb-bytearray", "wkb-memoryview"],
    )
    @pytest.mark.parametrize(
        ("relation", "config"),
        [
            (SpatialRelation(relation="in", category="containment"), None),
            (SpatialRelation(relation="near", category="buffer"), BufferConfig(distance_m=5000, buffer_from="center")),
            (
                SpatialRelation(relation="north_of", category="directional"),
                BufferConfig(distance_m=10000, buffer_from="center"),
            ),
            (SpatialRelation(relation="northern_part_of", category="clipping"), None),
        ],
        ids=["containment", "buffer", "directional", "clipping"],
    )
    def test_same_result_as_geojson(self, geometry, relation, config):
        expected = shape(apply_spatial_relation(POLYGON_GEOM, relation, config and config.model_copy()))
        result = shape(apply_spatial_relation(geometry, relation, config and config.model_copy()))
        assert result.equals_exact(expected, 1e-9)

    def test_list_of_mixed_formats_is_unioned(self):
        other = shapely.affinity.translate(POLYGON, xoff=0.2)
        relation = SpatialRelation(relation="in", category="containment")
        result = shape(apply_spatial_relation([POLYGON_GEOM, other.wkb], relation))
        assert result.equals(POLYGON.union(other))

    def test_wkb_in_wkb_out_containment(self):
        relation = SpatialRelation(relation="in", category="containment")
        result = apply_spatial_relation(POLYGON.wkb_hex, relation, geometry_format="wkb")
        assert shapely.from_wkb(result).equals_exact(POLYGON, 0)

    def test_unparsable_string_raises(self):
        relation = SpatialRelation(relation="in", category="containment")
        with pytest.raises(ValueError):
            apply_spatial_relation("not a geometry", relation)
