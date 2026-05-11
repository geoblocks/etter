"""
Few-shot examples for LLM prompt to demonstrate query parsing.

These examples cover:
- Simple containment queries
- Buffer queries (positive and negative)
- Directional queries
- Multilingual support (English, German, French)
- Activity queries (demonstrating scope - activities are ignored)
"""

from dataclasses import dataclass

from .models import (
    BufferConfig,
    ConfidenceScore,
    GeoQuery,
    ReferenceLocation,
    SpatialRelation,
)


@dataclass
class ExampleQuery:
    """
    A single example query with expected output.

    Attributes:
        input: Natural language query
        output: Expected GeoQuery structure
        language: Language code (en, de, fr, it)
        description: What this example demonstrates
        exclude_none: Whether to omit None fields in JSON output (default True)
    """

    input: str
    output: GeoQuery
    language: str
    description: str
    exclude_none: bool = True


# Define examples covering key scenarios
EXAMPLES: list[ExampleQuery] = [
    # Simple containment (English)
    ExampleQuery(
        input="restaurants in Geneva",
        language="en",
        description="Simple containment - subject ignored, only geographic filter extracted",
        output=GeoQuery(
            query_type="simple",
            spatial_relation=SpatialRelation(relation="in", category="containment", explicit_distance=None),
            reference_location=ReferenceLocation(
                name="Geneva",
                type="city",
                type_confidence=0.95,
            ),
            buffer_config=None,
            confidence_breakdown=ConfidenceScore(
                overall=0.95,
                location_confidence=0.95,
                relation_confidence=0.95,
                reasoning=None,
            ),
        ),
    ),
    # Buffer query with LLM-inferred distance (English)
    ExampleQuery(
        input="hotels within 5km of Lausanne",
        language="en",
        description="Proximity buffer with explicit distance",
        output=GeoQuery(
            query_type="simple",
            spatial_relation=SpatialRelation(relation="near", category="buffer", explicit_distance=5000),
            reference_location=ReferenceLocation(
                name="Lausanne",
                type="city",
                type_confidence=0.95,
            ),
            buffer_config=BufferConfig(distance_m=5000, buffer_from="center", ring_only=False, inferred=False),
            confidence_breakdown=ConfidenceScore(
                overall=0.95,
                location_confidence=0.95,
                relation_confidence=0.95,
                reasoning=None,
            ),
        ),
    ),
    ExampleQuery(
        input="near Lausanne",
        language="en",
        description="Proximity to a city polygon → buffer from boundary, not center",
        output=GeoQuery(
            query_type="simple",
            spatial_relation=SpatialRelation(relation="near", category="buffer", explicit_distance=None),
            reference_location=ReferenceLocation(
                name="Lausanne",
                type="city",
                type_confidence=0.95,
            ),
            buffer_config=BufferConfig(distance_m=5000, buffer_from="boundary", ring_only=False, inferred=True),
            confidence_breakdown=ConfidenceScore(
                overall=0.90,
                location_confidence=0.95,
                relation_confidence=0.90,
                reasoning="'near Lausanne' → city is a polygon feature → near with buffer from boundary, default 5km",
            ),
        ),
    ),
    # Directional (English)
    ExampleQuery(
        input="hiking north of Bern",
        language="en",
        description="Directional sector query - activity ignored, only geographic filter extracted",
        output=GeoQuery(
            query_type="simple",
            spatial_relation=SpatialRelation(relation="north_of", category="directional", explicit_distance=None),
            reference_location=ReferenceLocation(
                name="Bern",
                type="city",
                type_confidence=0.95,
            ),
            buffer_config=BufferConfig(distance_m=10000, buffer_from="center", ring_only=False, inferred=True),
            confidence_breakdown=ConfidenceScore(
                overall=0.95,
                location_confidence=0.95,
                relation_confidence=0.95,
                reasoning=None,
            ),
        ),
    ),
    # Time-based distance - walking (English)
    ExampleQuery(
        input="30 minutes walking from the station",
        language="en",
        description="Time-based distance - 30 minutes walk ≈ 2500m at 5km/h",
        output=GeoQuery(
            query_type="simple",
            spatial_relation=SpatialRelation(relation="near", category="buffer", explicit_distance=2500),
            reference_location=ReferenceLocation(
                name="station",
                type="train_station",
                type_confidence=0.85,
            ),
            buffer_config=BufferConfig(distance_m=2500, buffer_from="center", ring_only=False, inferred=False),
            confidence_breakdown=ConfidenceScore(
                overall=0.85,
                location_confidence=0.80,
                relation_confidence=0.90,
                reasoning="'30 minutes walking' converted to 2500m buffer (5km/h walking speed)",
            ),
        ),
    ),
    # Complex query with multiple features (English)
    ExampleQuery(
        input="in the heart of a small village",
        language="en",
        description="Complex inference - central area with negative buffer (erosion)",
        output=GeoQuery(
            query_type="simple",
            spatial_relation=SpatialRelation(relation="in_the_heart_of", category="buffer", explicit_distance=None),
            reference_location=ReferenceLocation(
                name="village",
                type="city",
                type_confidence=0.70,
            ),
            buffer_config=BufferConfig(distance_m=-500, buffer_from="boundary", ring_only=False, inferred=True),
            confidence_breakdown=ConfidenceScore(
                overall=0.80,
                location_confidence=0.70,
                relation_confidence=0.90,
                reasoning="'Heart of a small village' → small area erosion -500m",
            ),
        ),
    ),
    # Right bank of a river (French)
    ExampleQuery(
        input="rive droite du Rhône",
        language="fr",
        description="Right bank of a river - one-sided buffer on the right side relative to flow direction",
        output=GeoQuery(
            query_type="simple",
            spatial_relation=SpatialRelation(relation="right_bank", category="buffer", explicit_distance=None),
            reference_location=ReferenceLocation(
                name="Rhône",
                type="river",
                type_confidence=0.95,
            ),
            buffer_config=BufferConfig(
                distance_m=500, buffer_from="boundary", ring_only=False, side="right", inferred=True
            ),
            confidence_breakdown=ConfidenceScore(
                overall=0.95,
                location_confidence=0.95,
                relation_confidence=0.95,
                reasoning="'rive droite' clearly indicates the right bank of the river",
            ),
        ),
    ),
    # No named location — attribute-only query (English)
    ExampleQuery(
        input="vineyards below 600 m",
        language="en",
        description="No named location — attribute-only query, reference_location must be null",
        exclude_none=False,
        output=GeoQuery(
            query_type="simple",
            spatial_relation=SpatialRelation(relation="in", category="containment", explicit_distance=None),
            reference_location=None,
            buffer_config=None,
            confidence_breakdown=ConfidenceScore(
                overall=0.95,
                location_confidence=0.0,
                relation_confidence=0.95,
                reasoning="No named geographic location in query — only an attribute threshold (elevation < 600m)",
            ),
        ),
    ),
    # Clipping relation (English) — one example is sufficient; the LLM generalises to
    # southern_part_of / eastern_part_of / western_part_of by analogy with the relation names.
    ExampleQuery(
        input="ski resorts in the northern part of the Mittelland",
        language="en",
        description="Clipping — clip reference geometry to its northern bbox half",
        output=GeoQuery(
            query_type="simple",
            spatial_relation=SpatialRelation(relation="northern_part_of", category="clipping", explicit_distance=None),
            reference_location=ReferenceLocation(name="Mittelland", type="region", type_confidence=0.92),
            buffer_config=None,
            confidence_breakdown=ConfidenceScore(
                overall=0.92,
                location_confidence=0.92,
                relation_confidence=0.95,
                reasoning="'in the northern part of the Mittelland' → clip to northern bbox half",
            ),
        ),
    ),
    # Bordering relation (English)
    ExampleQuery(
        input="cities bordering Germany",
        language="en",
        description="Bordering relation — ring buffer just outside Germany's boundary for land-border adjacency",
        output=GeoQuery(
            query_type="simple",
            spatial_relation=SpatialRelation(relation="bordering", category="buffer", explicit_distance=None),
            reference_location=ReferenceLocation(
                name="Germany",
                type="country",
                type_confidence=0.98,
            ),
            buffer_config=BufferConfig(distance_m=2000, buffer_from="boundary", ring_only=True, inferred=True),
            confidence_breakdown=ConfidenceScore(
                overall=0.95,
                location_confidence=0.98,
                relation_confidence=0.95,
                reasoning="'bordering Germany' → ring buffer just outside Germany's land border",
            ),
        ),
    ),
    # Multilingual and complex (French)
    ExampleQuery(
        input="near Lake Geneva",
        language="en",
        description="Proximity to a lake feature → use on_shores_of (ring buffer around boundary)",
        output=GeoQuery(
            query_type="simple",
            spatial_relation=SpatialRelation(relation="on_shores_of", category="buffer", explicit_distance=None),
            reference_location=ReferenceLocation(
                name="Lake Geneva",
                type="lake",
                type_confidence=0.95,
            ),
            buffer_config=BufferConfig(distance_m=1000, buffer_from="boundary", ring_only=True, inferred=True),
            confidence_breakdown=ConfidenceScore(
                overall=0.90,
                location_confidence=0.95,
                relation_confidence=0.90,
                reasoning="'near Lake Geneva' → lake is an AREA feature → on_shores_of with ring buffer",
            ),
        ),
    ),
]


def format_examples_for_prompt() -> str:
    """
    Format examples as text for inclusion in LLM prompt.

    Returns:
        Formatted string with all examples
    """
    examples_text = []

    for ex in EXAMPLES:
        examples_text.append(f"Q: {ex.input}")
        examples_text.append(
            f"A: {ex.output.model_dump_json(exclude_none=ex.exclude_none, exclude={'original_query'})}"
        )
        examples_text.append("")

    return "\n".join(examples_text)


def get_examples_by_language(language: str) -> list[ExampleQuery]:
    """
    Get examples filtered by language.

    Args:
        language: Language code (en, de, fr, it)

    Returns:
        List of examples in the specified language
    """
    return [ex for ex in EXAMPLES if ex.language == language]


def get_examples_by_category(category: str) -> list[ExampleQuery]:
    """
    Get examples filtered by spatial relation category.

    Args:
        category: Relation category (containment, buffer, directional)

    Returns:
        List of examples using that category
    """
    return [ex for ex in EXAMPLES if ex.output.spatial_relation.category == category]
