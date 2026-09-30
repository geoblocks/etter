# Error Handling

etter raises structured exceptions so you can handle each failure mode precisely.

## Exception Hierarchy

- **[GeoFilterError](../api/etter.html#GeoFilterError)**: base class for every etter error
  - **[ParsingError](#parsingerror)**: the LLM failed to produce valid structured output
    - **[LLMInvocationError](#llminvocationerror)**: the LLM call itself failed (network, rate limit, provider error)
  - **[ValidationError](../api/etter.html#ValidationError)**: the output is well-formed but fails validation
    - **[NoReferenceLocationError](#noreferencelocationerror)**: the query has no named geographic location
    - **[UnknownRelationError](#unknownrelationerror)**: the relation is not in the registered config
  - **[LowConfidenceError](#lowconfidenceerror-lowconfidencewarning)**: confidence below threshold (strict mode only)
- **UserWarning** (Python built-in)
  - **[LowConfidenceWarning](#lowconfidenceerror-lowconfidencewarning)**: confidence below threshold (lenient mode only)

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

### LLMInvocationError

A subclass of `ParsingError` raised when the request to the LLM fails before any output is produced: network errors, timeouts, provider errors and rate limits (HTTP 429). The provider's exception is attached as `original_error`. Catch it separately when you want to retry transport failures without retrying malformed output, for example in a concurrent `parse_batch`:

```python
from etter import LLMInvocationError, ParsingError

try:
    result = parser.parse("some query")
except LLMInvocationError as e:
    # Transient: back off and retry, or configure max_retries on the LLM
    log.warning("LLM call failed", error=e.original_error)
except ParsingError as e:
    # Malformed output: retrying the same prompt rarely helps
    log.error("Bad LLM output", raw=e.raw_response)
```

`raw_response` is always empty on an `LLMInvocationError`.

## NoReferenceLocationError

Raised when the query contains no named geographic location. Two kinds of query end up here:

- Pure attribute queries like "vineyards below 600 m" or "slopes steeper than 30°". These are dataset-level attribute filters that must be handled at the application layer.
- Queries whose only "place" is a generic word, like "hikes around a lake" or "hotels near the station". Only proper nouns count as a reference location; a generic terrain or facility word is not resolvable in a datasource.

```python
from etter import NoReferenceLocationError

try:
    result = parser.parse("vineyards below 600 m")
except NoReferenceLocationError:
    # No named location: apply the attribute filter in your query layer
    ...
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
    for warning in w:
        if issubclass(warning.category, LowConfidenceWarning):
            print(f"Low confidence: {warning.message.confidence}")

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
    LLMInvocationError,
    LowConfidenceError,
    NoReferenceLocationError,
    ParsingError,
    UnknownRelationError,
)


def handle_query(parser: GeoFilterParser, user_query: str) -> dict:
    try:
        result = parser.parse(user_query)
    except NoReferenceLocationError:
        # No named location: handle the attribute filter in the app layer
        return {"error": "Query has no geographic location reference"}
    except LLMInvocationError as e:
        # LLM call failed (network, rate limit, provider error).
        # Must come before ParsingError, its parent class.
        log.warning("LLM call failed", error=e.original_error)
        return {"error": "Service temporarily unavailable"}
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
    return result.model_dump()
```

See [`GeoFilterError`](../api/etter.html#GeoFilterError) and its subclasses in the API reference for the full exception API.
