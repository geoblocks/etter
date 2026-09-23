# LangChain Integration

etter's prompt and validation are exposed separately from `GeoFilterParser`, so you can plug them into your own LangChain code.

## Composing With Your Own Schema

To extract your own fields from the same query in a single LLM call, nest `GeoQuery` in your output model, reuse etter's prompt, and validate the nested result with `finalize_geo_query`:

```python
from pydantic import BaseModel
from etter import (
    GeoQuery,
    SpatialRelationConfig,
    build_geo_prompt_template,
    finalize_geo_query,
)

class Output(BaseModel):
    geo: GeoQuery
    language: str

config = SpatialRelationConfig()
instructions = "Also return the ISO 639-1 code of the query language."
prompt = build_geo_prompt_template(
    config, additional_instructions=instructions
)

structured_llm = llm.with_structured_output(Output)
result = structured_llm.invoke(prompt.format_messages(query=query))
geo = finalize_geo_query(result.geo, config, query)
```

`finalize_geo_query` runs the same validation and enrichment pipeline as `GeoFilterParser` and accepts the same `confidence_threshold` and `strict_mode` arguments. See [`build_geo_prompt_template`](../api/etter.html#build_geo_prompt_template) and [`finalize_geo_query`](../api/etter.html#finalize_geo_query).

## Building a LangChain Chain

`build_geo_prompt_template` returns a standard `ChatPromptTemplate`, so it composes with any LangChain Runnable. Because the prompt step consumes the input dict, use `RunnablePassthrough.assign` to keep the query around for `finalize_geo_query`:

```python
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from etter import (
    GeoQuery,
    SpatialRelationConfig,
    build_geo_prompt_template,
    finalize_geo_query,
)

config = SpatialRelationConfig()
prompt = build_geo_prompt_template(config)
geo_llm = llm.with_structured_output(GeoQuery)


def finalize(d: dict) -> GeoQuery:
    return finalize_geo_query(d["geo"], config, d["query"])


chain = (
    RunnablePassthrough.assign(geo=prompt | geo_llm)
    | RunnableLambda(finalize)
)

geo = chain.invoke({"query": "Wanderungen rund um Zermatt"})
```

This runs the same prompt and validation as `GeoFilterParser.parse`, and the chain gets every Runnable method for free. One difference: `parse` wraps provider failures in `LLMInvocationError`, while the chain lets the provider's own exception propagate. `batch` runs the queries concurrently and can collect failures instead of raising on the first one:

```python
results = chain.batch(
    [
        {"query": "restaurants in Geneva"},
        {"query": "vineyards below 600 m"},
    ],
    config={"max_concurrency": 4},
    return_exceptions=True,
)
# [GeoQuery(...), NoReferenceLocationError(...)]
```

`ainvoke`, `abatch` and `batch_as_completed` work the same way. If you only need concurrency, [`parse_batch`](./using-the-parser#batching) does the same without building a chain.
