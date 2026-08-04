# ATLAS content pack format

A content pack is a folder under `data/content_packs/<pack_id>/`:

```
demo_pack/
  manifest.json
  artworks/
    starry_night.json
    mona_lisa.json
    ...
```

Write short, original educational text. Do not paste long copyrighted
museum copy.

## manifest.json

```json
{
  "pack_id": "demo_pack",
  "name": "ATLAS Demo Pack",
  "version": "0.1.0",
  "description": "…",
  "languages": ["en", "fr"],
  "educational_levels": ["child", "adult_beginner", "expert"],
  "artwork_files": ["artworks/starry_night.json"]
}
```

## Artwork file

Validated against `src/atlas/models/artwork.py` / `content_pack.py`:

```json
{
  "artwork_id": "mona_lisa",
  "title": "Mona Lisa",
  "artist": "Leonardo da Vinci",
  "date": "c. 1503-1519",
  "materials": "Oil on poplar panel",
  "dimensions": "77 cm x 53 cm",
  "culture_origin": "Italian, Renaissance",
  "movement": "High Renaissance",
  "official_description": "…",
  "historical_context": "…",
  "visual_description": "…",
  "themes": ["portrait", "smile"],
  "keywords": ["portrait", "leonardo"],
  "supported_languages": ["en", "fr"],
  "educational_levels": ["child", "adult_beginner", "expert"],
  "sources": [{
    "source_id": "src_ml_demo",
    "title": "…", "url": "…", "publisher": "…",
    "license_note": "…", "last_checked": "2026-06-01"
  }],
  "chunks": [ … ]
}
```

## Chunk fields (every chunk)

| Field | Notes |
|---|---|
| `chunk_id` | unique, stable (e.g. `ml_official_en_adult`) |
| `artwork_id` | must match the artwork |
| `language` | `en` / `fr` / `es` / `it` |
| `educational_level` | `child`, `teen`, `adult_beginner`, `expert`, `visual_impairment`, `simple_language` |
| `chunk_type` | `official_description`, `historical_context`, `visual_description`, `theme`, `fact`, `technique`, `general` |
| `text` | 1–3 sentences, self-contained, spoken-friendly |
| `source_id` | must exist in `sources` |
| `verified` | only `true` chunks are ever retrieved |
| `allowed_for_students` | only `true` chunks are ever retrieved |
| `keywords` | list of lowercase keywords for FTS |

## Authoring guidance

- **Coverage per artwork:** at least `official_description`,
  `visual_description` (important for accessibility), and one
  `historical_context` or `fact`, in **both English and French**.
- Levels are best-effort: if a requested level has no chunks, retrieval
  falls back to `adult_beginner` — so always provide `adult_beginner`.
- `visual_description` chunks double as accessibility descriptions: cover
  shape, colour, composition, atmosphere.
- Keep each chunk answerable aloud in ~10 seconds.

## Ingest and verify

```powershell
python -m atlas.rag.ingest --pack data/content_packs/<pack_id> --mode dev --reset
python -m atlas.rag.evaluator     # guardrail: hit-rate per question category
```

Or from the dashboard: *Re-ingest selected pack* (requires the admin token).
