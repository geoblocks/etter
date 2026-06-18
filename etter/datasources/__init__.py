"""
Geographic data source layer for resolving location names to geometries.

Provides a Protocol-based interface (GeoDataSource) and concrete implementations:
SwissNames3DSource, SwissBoundaries3DSource, IGNBDCartoSource, PostGISDataSource,
and CompositeDataSource.
"""

from .composite import CompositeDataSource
from .ign_bdcarto import IGNBDCartoSource
from .location_types import LocationTypeName, TypeMap
from .postgis import PostGISDataSource
from .protocol import GeoDataSource
from .swissboundaries3d import SwissBoundaries3DSource
from .swissnames3d import SwissNames3DSource

__all__ = [
    "CompositeDataSource",
    "GeoDataSource",
    "IGNBDCartoSource",
    "LocationTypeName",
    "PostGISDataSource",
    "SwissBoundaries3DSource",
    "SwissNames3DSource",
    "TypeMap",
]
