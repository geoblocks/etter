#!/usr/bin/env python3
"""
Load SwissNames3D and IGN BD-CARTO geodata into a PostGIS database.

Raw dataset type values are stored as-is so that a PostGISDataSource with the
appropriate type_map (OBJEKTART_TYPE_MAP / IGN_BDCARTO_TYPE_MAP) can translate
them at query time.

Schema written to PostGIS:
    id TEXT, name TEXT, type TEXT, geom GEOMETRY(4326)

Usage::

    python scripts/load_data_postgis.py

Environment variables:

    ETTER_DB_URL          SQLAlchemy connection URL (required).
                          e.g. postgresql+psycopg2://user:pass@host:5432/db
    SWISSNAMES3D_PATH     Path to the SwissNames3D data directory or shapefile.
                          Default: data/
    IGN_BDCARTO_PATH      Path to the IGN BD-CARTO directory of .gpkg files.
                          Default: data/bdcarto
    SWISSNAMES3D_TABLE    Target table name for SwissNames3D.
                          Default: swissnames3d
    IGN_BDCARTO_TABLE     Target table name for IGN BD-CARTO.
                          Default: ign_bdcarto
    DB_SCHEMA             PostgreSQL schema for both tables.
                          Default: public
    IF_EXISTS             pandas to_postgis if_exists strategy:
                          "replace" (default) | "append" | "fail"
"""

import os
import sys
from pathlib import Path
from typing import Any, Literal

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text

from etter.datasources.ign_bdcarto import _LAYER_CONFIGS, _NAME_COL, _TYPE_COL, IGNBDCartoSource
from etter.datasources.swissnames3d import SwissNames3DSource

DB_URL = os.environ.get("ETTER_DB_URL")
SWISSNAMES3D_PATH = Path(os.environ.get("SWISSNAMES3D_PATH", "data"))
IGN_BDCARTO_PATH = Path(os.environ.get("IGN_BDCARTO_PATH", "data/bdcarto"))
SWISSNAMES3D_TABLE = os.environ.get("SWISSNAMES3D_TABLE", "swissnames3d")
IGN_BDCARTO_TABLE = os.environ.get("IGN_BDCARTO_TABLE", "ign_bdcarto")
DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")
IF_EXISTS_RAW = os.environ.get("IF_EXISTS", "replace").lower()
if IF_EXISTS_RAW not in ("fail", "replace", "append"):
    print(f"Invalid IF_EXISTS value: {IF_EXISTS_RAW}. Must be 'fail', 'replace', or 'append'.", file=sys.stderr)
    sys.exit(1)
IF_EXISTS: Literal["fail", "replace", "append"] = IF_EXISTS_RAW


def _ensure_postgis(engine: Any) -> None:
    """Enable PostGIS extension (idempotent)."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
    print("PostGIS extension enabled.")


def _write_to_postgis(
    gdf: gpd.GeoDataFrame,
    engine: Any,
    table: str,
    schema: str,
    if_exists: Literal["fail", "replace", "append"],
) -> None:
    """Write a GeoDataFrame to PostGIS and rename geometry column to 'geom'."""
    gdf.to_postgis(table, engine, schema=schema, if_exists=if_exists, index=False)
    with engine.connect() as conn:
        conn.execute(text(f"ALTER TABLE {schema}.{table} RENAME COLUMN geometry TO geom"))  # noqa: S608
        conn.commit()
    print(f"  Written {len(gdf):,} rows to {schema}.{table}")


def load_swissnames3d(engine: Any) -> None:
    """Load SwissNames3D into PostGIS by reusing SwissNames3DSource."""
    print(f"\nLoading SwissNames3D from {SWISSNAMES3D_PATH} …")

    if not SWISSNAMES3D_PATH.exists():
        print(f"  SKIP: path not found ({SWISSNAMES3D_PATH})")
        return

    source = SwissNames3DSource(SWISSNAMES3D_PATH)
    source._ensure_loaded()
    raw = source._gdf
    assert raw is not None

    print(f"  Loaded {len(raw):,} features, reprojecting to EPSG:4326 …")
    raw = raw.to_crs("EPSG:4326")

    name_col = source._detect_name_column()
    type_col = source._detect_type_column()
    id_col = source._detect_id_column()

    ids = raw[id_col].astype(str) if id_col else pd.Series([str(i) for i in range(len(raw))])
    names = raw[name_col].astype(str)
    types = raw[type_col].astype(str) if type_col else pd.Series(["unknown"] * len(raw))

    out = gpd.GeoDataFrame({"id": ids, "name": names, "type": types}, geometry=raw.geometry, crs="EPSG:4326")
    out = gpd.GeoDataFrame(out[out["name"].str.strip() != ""], crs="EPSG:4326")

    _write_to_postgis(out, engine, SWISSNAMES3D_TABLE, DB_SCHEMA, IF_EXISTS)


def load_ign_bdcarto(engine: Any) -> None:
    """Load IGN BD-CARTO into PostGIS by reusing IGNBDCartoSource."""
    print(f"\nLoading IGN BD-CARTO from {IGN_BDCARTO_PATH} …")

    if not IGN_BDCARTO_PATH.exists():
        print(f"  SKIP: path not found ({IGN_BDCARTO_PATH})")
        return

    source = IGNBDCartoSource(IGN_BDCARTO_PATH)
    source._ensure_loaded()
    raw = source._gdf
    assert raw is not None

    print(f"  Loaded {len(raw):,} features …")

    def _raw_type(row: pd.Series) -> str:
        layer = row.get("_layer")
        cfg = _LAYER_CONFIGS.get(layer, {}) if layer else {}
        if cfg.get("type_map"):
            type_col: str = cfg["type_col"]
            val = row.get(type_col)
            return str(val) if pd.notna(val) else "unknown"

        val = row.get(_TYPE_COL)
        return str(val) if pd.notna(val) else "unknown"

    id_col = "cleabs" if "cleabs" in raw.columns else None
    ids = raw[id_col].astype(str) if id_col else pd.Series([str(i) for i in range(len(raw))])

    types = raw.apply(_raw_type, axis=1)

    out = gpd.GeoDataFrame(
        {"id": ids, "name": raw[_NAME_COL].astype(str), "type": types},
        geometry=raw.geometry,
        crs="EPSG:4326",
    )
    out = gpd.GeoDataFrame(out[out["name"].str.strip() != ""], crs="EPSG:4326")

    _write_to_postgis(out, engine, IGN_BDCARTO_TABLE, DB_SCHEMA, IF_EXISTS)


def main() -> None:
    if not DB_URL:
        print("ERROR: ETTER_DB_URL environment variable is required.", file=sys.stderr)
        print(
            "Example: export ETTER_DB_URL=postgresql+psycopg2://user:pass@localhost:5432/geodata",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Connecting to database: {DB_URL.split('@')[-1]}")  # hide credentials in log
    engine = create_engine(DB_URL)

    _ensure_postgis(engine)
    load_swissnames3d(engine)
    load_ign_bdcarto(engine)

    print("\nData loading complete.")


if __name__ == "__main__":
    main()
