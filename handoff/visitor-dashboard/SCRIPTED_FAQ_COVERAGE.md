# Scripted visitor FAQ coverage

The fast path answers these ten common question families before retrieval:

1. What is this / which artwork is this?
2. Who painted, made, or created it?
3. When was it made / how old is it?
4. What does it show / what is happening?
5. How was it made / which technique or materials were used?
6. What does it mean or symbolize?
7. Why is it famous, important, or special?
8. Where is it now / which museum holds it?
9. What detail should I notice?
10. Tell me a fun, interesting, or surprising fact.

Each family includes several local phrasings plus conservative fuzzy matching
for small speech-recognition errors. Explicit artwork titles can resolve an
answer without camera context; a deictic question with no identified work asks
which artwork the visitor means. Unmatched questions continue to hybrid RAG and
Gemini rather than receiving a generic scripted answer.

## Coverage matrix

- Artworks: Girl with a Pearl Earring, The Great Wave off Kanagawa, Liberty
  Leading the People, Mona Lisa, The Starry Night, Sunflowers, and the Golden
  Burial Mask of Tutankhamun.
- Languages: English, French, Spanish, Italian, and Traditional Chinese.
- Profiles: `early_child`, `child`, `teen`, `adult_beginner`, `expert`,
  `visual_impairment`, and `simple_language`.
- Follow-up behavior: non-expert answers end with one short, relevant question;
  the early-child profile uses shorter, child-directed questions; expert answers
  add a concise technical note; visual-description choices add a concrete
  looking detail without replacing the age level.

## Factual sources

The catalogue translates and condenses facts already attributed in the demo
content pack. Source IDs remain aligned with the artwork JSON files:

- Mauritshuis: Girl with a Pearl Earring and its technical research.
- Metropolitan Museum of Art and British Museum: The Great Wave.
- Louvre collections and gallery guide: Liberty Leading the People and Mona Lisa.
- Museum of Modern Art: The Starry Night.
- National Gallery, London: Sunflowers.
- Grand Egyptian Museum and the University of Oxford Griffith Institute:
  Tutankhamun's burial mask.

The exact URLs and chunk-level source assignments remain in
`atlas/data/content_packs/demo_pack/artworks/*.json`. Native-speaker review is
still required before a public museum release; automated tests prove coverage
and routing, not curatorial approval of translated phrasing.
