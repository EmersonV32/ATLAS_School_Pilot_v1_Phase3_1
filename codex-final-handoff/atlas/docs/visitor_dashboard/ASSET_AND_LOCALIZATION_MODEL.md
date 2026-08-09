# Asset and localization model

## Locales

Locale metadata records the locale code, native name, English name, text
direction, validation state, and static message file. Pass 1 prepares English,
French, Spanish, Italian, Arabic, and Traditional Chinese infrastructure.

Only validated locales appear in public mode. Development mode may display
provisional locales with a visible Preview label. Selecting Arabic applies a
document-level RTL direction and mirrored layout flow; it is not treated as
right-aligned English.

## Interests

Interest cards come from a replaceable local JSON manifest. Each entry has:

- stable identifier;
- short label;
- approved local image path;
- artwork title and accessible image description;
- attribution and approval status;
- public/development visibility.

Pass 1 uses locally authored abstract SVG museum textures clearly marked as
placeholders. It does not download art or reuse legacy training images.
Public mode hides entries without an approved image and attribution.

## Branding

CSS custom properties define museum logo slot, ATLAS mark, palette, type
scale, radii, and motion. No network asset is required. Host-museum branding
can replace local placeholders without changing the onboarding logic.

