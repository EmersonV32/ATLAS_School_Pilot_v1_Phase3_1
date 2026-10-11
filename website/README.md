# Public ATLAS website

This folder is the static public project site. It is separate from the visitor
and staff dashboard implemented in `atlas/src/atlas/dashboard/`.

- `index.html`: page content and accessible markup.
- `styles.css`: appearance and responsive layout.
- `main.js`: client-side interactions.
- `assets/`: images used by the page; all are required.
- `.nojekyll`: prevents GitHub Pages from transforming the static bundle.

The [Pages workflow](../.github/workflows/pages.yml) publishes this directory
on relevant changes to `main` or an explicit manual run. Only run the manual
workflow from `main`. Do not publish experimental runtime branches.

For local preview, run `python -m http.server 8080 --directory website` from
the repository root and open `http://127.0.0.1:8080/`.
