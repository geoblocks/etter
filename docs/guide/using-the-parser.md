# Using the Parser

This page covers the ways to call [`GeoFilterParser`](../api/etter.html#GeoFilterParser) beyond a single `parse`, and how to tune its behavior.

## Choosing an LLM

`GeoFilterParser` accepts any LangChain chat model that supports tool calling: it requests structured output with `with_structured_output(GeoQuery, method="function_calling")`. Two settings are worth passing when you create the model:

```python
llm = init_chat_model(model="gpt-4o", temperature=0, max_retries=3)
```

- `temperature=0` makes the same query parse the same way each time.
- `max_retries` retries transient provider failures (timeouts, rate limits) before etter sees them; a call that still fails is raised as [`LLMInvocationError`](./error-handling#llminvocationerror).

## Confidence and Strict Mode

By default etter warns on low confidence. Use `strict_mode=True` to raise instead:

```python
# Lenient: emits LowConfidenceWarning below threshold
parser = GeoFilterParser(
    llm=llm, confidence_threshold=0.6, strict_mode=False
)

# Strict: raises LowConfidenceError below threshold
parser = GeoFilterParser(
    llm=llm, confidence_threshold=0.8, strict_mode=True
)
```

See [Error Handling](./error-handling#lowconfidenceerror-lowconfidencewarning) for how to catch each one, and [`GeoQuery`](../api/etter.html#GeoQuery) for a full description of all output fields.

## Matching Your Datasource's Types

Pass your datasource to the parser so the prompt lists the concrete types it contains:

```python
parser = GeoFilterParser(llm=llm, datasource=source)
```

The LLM then picks `reference_location.type` from types your datasource actually has. This matters because [`search` filters by type](./datasources#type-system): a type the datasource doesn't know returns no results. The parser only calls `source.get_available_types()`; it never searches the datasource itself.

## Async Parsing

Inside an event loop (e.g. a FastAPI handler), use the async counterpart `aparse` so the LLM call does not block other requests:

```python
geo_query = await parser.aparse("north of Lausanne")
```

`aparse` returns the same `GeoQuery` as `parse`; it differs only in that it awaits `ainvoke` on the underlying LLM. See [`aparse`](../api/etter.html#GeoFilterParser.aparse).

## Streaming

For responsive UIs, use `parse_stream` to receive reasoning events in real time:

```python
from etter import GeoFilterError

try:
    async for event in parser.parse_stream("5km north of Lausanne"):
        if event["type"] == "reasoning":
            # e.g. "Analyzing spatial relationship and location"
            print(event["content"])
        elif event["type"] == "data-response":
            geo_query = event["content"]  # raw dict (GeoQuery fields)
        elif event["type"] == "error":
            print(event["content"])  # human-readable message for the UI
except GeoFilterError:
    ...  # the typed exception is raised right after the "error" event
```

The stream opens with a `start` event and ends with `finish` on success. An `error` event is informational: the generator then raises the same exception `parse` would (e.g. `LLMInvocationError`, `NoReferenceLocationError`), so handle failures with `try`/`except` as shown in [Error Handling](./error-handling). See [`parse_stream`](../api/etter.html#GeoFilterParser.parse_stream) for all event types.

The `data-response` content is a plain dict so it can be serialized straight to the client (e.g. as server-sent events). To work with it as a model, validate it back:

```python
from etter import GeoQuery

geo_query = GeoQuery.model_validate(event["content"])
```

## Batching

`parse_batch` parses several queries and returns the results in input order. `max_concurrency` sets how many run in parallel (threads); it defaults to 1:

```python
results = parser.parse_batch(
    ["restaurants in Geneva", "hikes north of Lausanne"],
    max_concurrency=4,
)
```

`aparse_batch` is the async twin, built on `aparse`. Both raise on the first failing query, with the same exceptions as `parse`. Before raising `max_concurrency`, stay within your provider's rate limit and configure retries on the LLM (e.g. `max_retries`): a rate-limited call surfaces as `LLMInvocationError` (see [Error Handling](./error-handling#llminvocationerror)). To collect failures instead of stopping at the first one, build a [LangChain chain](./langchain#building-a-langchain-chain) and use `batch(..., return_exceptions=True)`.

## Custom Spatial Relations

Pass a `SpatialRelationConfig` with your own relations registered to extend the 21 built-ins:

```python
parser = GeoFilterParser(llm=llm, spatial_config=config)
```

See [Registering Custom Relations](./spatial-relations#registering-custom-relations) for how to build the config.

## Additional Instructions

Pass `additional_instructions` to inject caller-specific rules into the prompt without forking the default system prompt. The text is added as a system message after the main prompt and before the few-shot examples.

Typical uses: region-specific endonyms, domain aliases, or organization-specific place names.

```python
parser = GeoFilterParser(
    llm=llm,
    additional_instructions=(
        "This application serves Swiss users. "
        "'Lac Léman' and 'Lake Geneva' refer to the same body of water. "
        "Prefer the French endonym when the query is in French."
    ),
)
```

## Few-Shot Examples

The prompt includes about a dozen worked examples: each relation category, explicit and default distances, and queries with no named location that must be rejected. They are mostly in English; the LLM handles other languages on its own. Pass `include_examples=False` to leave them out:

```python
parser = GeoFilterParser(llm=llm, include_examples=False)
```

This shortens the prompt, and so the token cost of each call, but gives the LLM less guidance; keep the examples unless you have measured that your model parses your queries correctly without them.
