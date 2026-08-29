Run the ATLAS retrieval evaluation guardrail:
`python -m atlas.rag.evaluator` (uses the built-in demo-pack eval cases:
factual, visual, interpretive, French, refusal, injection, accessibility).
Requires the demo pack to be ingested first (see /atlas-rag-ingest).
Report hit-rate@k and MRR per category and overall. Flag any category whose
hit rate dropped below 0.5 — that usually means a chunk/metadata regression.
