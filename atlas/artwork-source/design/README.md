# Retained visitor-design sources

These public PNG assets were moved here during the 2026-10-11 repository
cleanup. Their bytes and SHA-256 hashes were checked before and after the move.
They are design/reference sources, not files served by the current visitor UI.

| File | Retained role | Former location |
|---|---|---|
| `atlas-logo-v2.png` | Lossless ATLAS branding source; the visitor UI serves `atlas-logo-v2.webp` | `src/atlas/dashboard/static/visitor/assets/atlas-logo-v2.png` |
| `expertise-triptych.png` | Historical expertise-card composition/reference | `src/atlas/dashboard/static/visitor/assets/expertise-triptych.png` |

The current expertise cards use the three separate `expertise-*.webp` files.
Their original artwork sources remain in the parent `artwork-source/`
directory and are covered by its existing integrity manifest. The triptych
is retained separately so it cannot be mistaken for an active UI dependency.

Original creator/download attribution was not recorded in these files. This
relocation does not establish publication rights or public-release approval.
Keep this distinction when creating future branding or artwork variants.

## Integrity

```text
7e26bcbce3223b8e1713418411b324326b4387d11de7d3f0eeb38448dbb33362  atlas-logo-v2.png
be860119db0d1659a70bd9e9066bc8d57923912f8c20986a8115efbb67ddc7f3  expertise-triptych.png
```
