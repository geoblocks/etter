# Error Handling

etter raises structured exceptions so you can handle each failure mode precisely.

## Exception Hierarchy

```
GeoFilterError
├── ParsingError          — LLM failed to produce valid structured output
├── ValidationError
│   └── UnknownRelationError  — relation not in registered config
└── LowConfidenceError    — confidence below threshold (strict mode only)

UserWarning
└── LowConfidenceWarning  — confidence below threshold (lenient mode only)
```

All exceptions are importable from the top-level `etter` package.

## ParsingError

Raised when the LLM response cannot be parsed into a valid [`GeoQuery`](../api/etter.html#GeoQuery). The raw LLM output is attached for debugging.

```python
from etter import ParsingError

try:
    result = parser.parse("some query")
except ParsingError as e:
    print(f"Parsing failed: {e}")
    print(f"Raw LLM response: {e.raw_response}")
```

## UnknownRelationError

Raised when the LLM extracts a spatial relation that is not registered in the parser's [`SpatialRelationConfig`](../api/etter.html#SpatialRelationConfig).

```python
from etter import UnknownRelationError

try:
    result = parser.parse("some query")
except UnknownRelationError as e:
    print(f"Unknown relation: {e.relation_name}")
```

This usually means the LLM hallucinated a relation name. You can either expand the config to include it, or catch and handle it here.

## LowConfidenceError / LowConfidenceWarning

When the confidence score falls below `confidence_threshold`:

- **`strict_mode=False`** (default): emits a `LowConfidenceWarning` (`UserWarning`) and returns the result anyway.
- **`strict_mode=True`**: raises `LowConfidenceError`.

```python
import warnings
from etter import LowConfidenceError, LowConfidenceWarning

# Catch the warning (lenient mode)
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    result = parser.parse("some ambiguous query")
    if w and issubclass(w[0].category, LowConfidenceWarning):
        print(f"Low confidence: {w[0].message.confidence}")

# Catch the error (strict mode)
try:
    result = parser.parse("some ambiguous query")
except LowConfidenceError as e:
    print(f"Confidence {e.confidence} below threshold")
    print(f"Reasoning: {e.reasoning}")
```

## Full Example

```python
from etter import (
    GeoFilterParser,
    ParsingError,
    UnknownRelationError,
    LowConfidenceError,
)

try:
    result = parser.parse(user_query)
except ParsingError as e:
    # LLM output was malformed
    log.error("Parse failed", raw=e.raw_response)
    return {"error": "Could not understand query"}
except UnknownRelationError as e:
    # LLM produced a relation we don't know
    log.warning("Unknown relation", relation=e.relation_name)
    return {"error": f"Unsupported spatial relation: {e.relation_name}"}
except LowConfidenceError as e:
    # Only in strict_mode=True
    log.warning("Low confidence", score=e.confidence)
    return {"error": "Query too ambiguous to parse reliably"}
```

See [`exceptions`](../api/etter.html#etter.exceptions) for the full exception API.
