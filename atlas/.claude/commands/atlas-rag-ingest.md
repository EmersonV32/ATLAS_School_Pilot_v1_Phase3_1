Ingest (or re-ingest) an ATLAS content pack:
`python -m atlas.rag.ingest --pack data/content_packs/demo_pack --mode dev --reset`
Replace the pack path if the user names another pack. Afterwards report:
pack_id, artworks, chunks_ingested, vector_count, fts_count, and whether
FTS5 was available. If ingestion fails, validate the pack's manifest.json
against `src/atlas/models/content_pack.py` and report which field is wrong.
