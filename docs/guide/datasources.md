# Datasources

A datasource resolves a location name (e.g. `"Lausanne"`) to a geometry. etter ships with four implementations and a composable aggregator.

All datasources implement the [`GeoDataSource`](../api/etter.html#GeoDataSource) protocol — no inheritance required.

## SwissNames3D

Wraps the [swisstopo SwissNames3D](https://www.swisstopo.admin.ch/en/landscape-model-swissnames3d) dataset (Shapefile/GDB). Covers Switzerland with ~80 geographic feature types.

```python
from etter.datasources import SwissNames3DSource

source = SwissNames3DSource("data/swissnames3d/")
results = source.search("Lausanne", type="settlement", max_results=5)
```

Handles EPSG:2056 → WGS84 reprojection and fuzzy name matching automatically. Data is loaded lazily on first use.

## SwissBoundaries3D

Wraps the [swisstopo swissBOUNDARIES3D](https://www.swisstopo.admin.ch/en/landscape-model-swissboundaries3d) dataset (Shapefile). Covers Swiss administrative boundaries: cantons, municipalities, and districts.

```python
from etter.datasources import SwissBoundaries3DSource

source = SwissBoundaries3DSource("data/swissboundaries3d/")
results = source.search("Bern", type="canton")
```

If given a directory, automatically loads and concatenates all three boundary shapefiles (BEZIRKSGEBIET, HOHEITSGEBIET, KANTONSGEBIET). Handles EPSG:2056 → WGS84 reprojection and drops 3D coordinates. Data is loaded lazily on first use.

## IGN BD-CARTO

Wraps the [IGN BD-CARTO](https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-CARTO) GeoPackage for France. Covers 14 thematic layers (administrative boundaries, hydrography, named places, protected areas, etc.).

```python
from etter.datasources import IGNBDCartoSource

source = IGNBDCartoSource("data/bdcarto/")
results = source.search("Rhône", type="water")
```

Handles Lambert-93 (EPSG:2154) → WGS84 reprojection and French article stripping (`le`, `la`, `l'`, `les`, `de`, `du`, `des`).

## PostGIS

A generic PostGIS datasource that works with any table. The connection is validated at construction time.

```python
from etter.datasources import PostGISDataSource

source = PostGISDataSource(
    connection="postgresql+psycopg2://...",
    table="public.my_geodata",
    type_map={"municipality": ["COMMUNE"], "river": ["COURS_EAU"]},
)
results = source.search("Genève", type="municipality")
```

The `type_map` maps **normalized type names** (as used by etter's type system) to lists of **raw values** in the database's type column — the same direction as `SwissNames3DSource`'s `OBJEKTART_TYPE_MAP`.

Use the `TypeMap` type alias when defining your own map to get editor auto-complete and static validation of keys:

```python
from etter.datasources import PostGISDataSource, TypeMap

my_map: TypeMap = {
    "municipality": ["COMMUNE"],
    "river": ["COURS_EAU"],
}
source = PostGISDataSource(
    connection="postgresql+psycopg2://...",
    table="public.my_geodata",
    type_map=my_map,
)
```

Keys must be valid etter type names (concrete types such as `"lake"` or category names such as `"water"`). An invalid key like `"lac"` is caught by static analysis tools (mypy, pyright) at type-check time rather than silently producing wrong results at runtime.

Install the extra for PostGIS support:

```bash
pip install "etter[postgis]"
```

The search cascade is: exact match → fuzzy (`pg_trgm`) → ILIKE. CRS reprojection is done at query time via `ST_Transform` when the stored SRID differs from 4326.

See [`PostGISDataSource`](../api/etter.html#PostGISDataSource) for the full constructor reference.

## CompositeDataSource

Fan-out across multiple datasources. Every source is queried in order and the results are concatenated. `max_results` is passed to each source individually, so the merged list can contain up to `max_results` features per source:

```python
from etter.datasources import (
    CompositeDataSource,
    IGNBDCartoSource,
    SwissBoundaries3DSource,
    SwissNames3DSource,
)

source = CompositeDataSource(
    SwissNames3DSource("data/swissnames3d/"),
    SwissBoundaries3DSource("data/swissboundaries3d/"),
    IGNBDCartoSource("data/bdcarto/"),
)
results = source.search("Geneva", type="settlement")
```

## Type System

All datasources share a common type hierarchy for fuzzy type matching. Query with a category and it matches all concrete types within it:

| Category | Concrete types (examples) |
|----------|--------------------------|
| `water` | `lake`, `river`, `pond`, `spring`, `glacier` |
| `landforms` | `mountain`, `peak`, `hill`, `pass`, `valley` |
| `mountain` | `mountain`, `peak` |
| `natural` | `cave`, `forest`, `nature_reserve` |
| `island` | `island`, `peninsula` |
| `settlement` | `city`, `town`, `village`, `hamlet` |
| `administrative` | `country`, `canton`, `municipality`, `region` |
| `transport` | `train_station`, `airport`, `road`, `bridge` |
| `building` | `building`, `tower`, `monument`, `fountain` |
| `amenity` | `restaurant`, `hospital`, `school`, `park` |
| `infrastructure` | `power_plant`, `landfill`, `quarry` |
| `other` | `viewpoint`, `field_name`, `historical_site` |

```python
# Matches lake, river, pond, spring, ...
source.search("Morat", type="water")

# Matches only "lake"
source.search("Morat", type="lake")
```

In all bundled datasources `type` is a filter, not a ranking hint: features of other types are dropped, and a name that is neither a category nor a known type only matches features whose type is exactly that string. If the type the LLM inferred turns out wrong, a search can come back empty; retry without `type` to fall back to a name-only search.

See [`location_types.py`](https://github.com/geoblocks/etter/blob/main/etter/datasources/location_types.py) for the complete hierarchy.

### TypeMap

`TypeMap` is a type alias (`dict[LocationTypeName, list[str]]`) that restricts dictionary keys to known etter type names. Use it when defining a `type_map` for `PostGISDataSource` or when building your own datasource map:

```python
from etter.datasources import TypeMap

# Editors auto-complete the keys; static checkers flag unknown keys.
my_map: TypeMap = {
    "lake": ["LAC", "RETENUE"],
    "river": ["COURS_EAU"],
}
```

`LocationTypeName` is the underlying `Literal[...]` type covering all concrete types (e.g. `"lake"`, `"mountain"`) and all category names (e.g. `"water"`, `"landforms"`). Both are importable from `etter.datasources`.

## Implementing a Custom Datasource

Any class with `search`, `get_by_id` and `get_available_types` methods matching the protocol qualifies:

```python
class MyDataSource:
    def get_available_types(self) -> list[str]:
        return ["city", "river", "lake"]

    def search(
        self,
        name: str,
        type: str | None = None,
        max_results: int = 10,
    ) -> list[dict]:
        # Return GeoJSON Feature dicts in WGS84, best match first
        ...

    def get_by_id(self, feature_id: str) -> dict | None:
        # Return a feature by its unique ID
        ...
```

Return features the way the bundled datasources do, so they can be mixed in a `CompositeDataSource`:

- coordinates in WGS84 (EPSG:4326), since `apply_spatial_relation()` expects them;
- a unique `id`, which `get_by_id()` looks up;
- `name`, `type` and `confidence` in `properties`, with `type` taken from the [type hierarchy](#type-system).

`get_available_types()` lists the concrete types your datasource returns; `GeoFilterParser(datasource=...)` passes them to the LLM so it infers types your datasource can match. See [`GeoDataSource`](../api/etter.html#GeoDataSource) for the full protocol definition.
