# Expertise artwork source files

These lossless source images are retained so the expertise-card assets can be
rebuilt without relying on a browser cache, clipboard history, or the Jetson.
The optimized WebP files used by the visitor dashboard live under
`src/atlas/dashboard/static/visitor/assets/`.

| File | Artwork | Recovery role |
|---|---|---|
| `mona-lisa.png` | Mona Lisa | Source for `expertise-mona.webp` |
| `great-wave.png` | The Great Wave off Kanagawa | Source for `expertise-wave.webp` |
| `ambassadors.png` | The Ambassadors | Source for `expertise-ambassadors.webp` |

Run `sha256sum -c manifest.sha256` from this directory after restoring the
repository. The original download URLs were not recorded when these files were
provided, so source attribution and reproduction-rights metadata remain a
separate documentation task before public publication.
