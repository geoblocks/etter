---
layout: home

hero:
  name: etter
  text: Geographic filter parsing for LLMs
  tagline: Transform natural language location queries into structured geographic filters — multilingual, streaming-ready, LLM-agnostic.
  image:
    src: /etter-logo.png
    alt: etter
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: API Reference
      link: /api/etter.html

features:
  - title: Geographic Filters Only
    details: etter extracts spatial relationships from queries and ignores everything else. Feature and activity identification is your application's job.
  - title: Multilingual
    details: Parse queries in English, French, German, Italian and more. The LLM handles language — you handle the map.
  - title: 15 Spatial Relations
    details: Containment, buffer, ring, one-sided bank, erosion, and 8 directional sectors — all with sensible defaults and full override support.
  - title: Streaming Support
    details: Real-time reasoning events let you build responsive UIs that show progress as the query is being parsed.
  - title: LLM Agnostic
    details: Works with any LangChain-compatible model — OpenAI, Anthropic, local models via Ollama, and more.
  - title: Pydantic Output
    details: Fully typed structured output with confidence scores. Integrates naturally with FastAPI, SQLAlchemy, and the rest of the Python ecosystem.
---
