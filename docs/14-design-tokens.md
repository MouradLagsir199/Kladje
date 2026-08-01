# 14 — Design Tokens

Extracted from `docs/prototype/Receptenapp.dc.html`. This is the visual language already designed — the
build should match it, not reinvent it.

**This file covers values, not layout.** For the composition of any given screen — what sits where, in
what order, with what padding — open the prototype and read it. It's a single inline-styled HTML file,
so every screen is legible as markup. Treat it as the visual source of truth and this file as the
palette you implement it with.

## Colour

```ts
export const color = {
  // Surfaces
  canvas:      '#eceae6',  // app background, warm off-white
  surface:     '#ffffff',  // cards, sheets, inputs
  surfaceAlt:  '#f8f8f6',  // subtle raised / selected rows
  surfaceSunk: '#f4f4f2',  // input wells, inactive segments
  imageBg:     '#e5e3de',  // image placeholder before load

  // Ink
  ink:         '#17171a',  // primary text, also primary button fill
  inkSoft:     '#3a3a3f',  // secondary heading
  muted:       '#6e6e73',  // body secondary
  mutedLight:  '#9a9aa0',  // labels, captions, meta
  disabled:    '#c9c9cd',

  // Lines
  line:        '#e9e9ec',  // default border
  lineWarm:    '#e2e0da',  // border on canvas-coloured surfaces
  lineSoft:    '#ececea',  // dividers, inactive progress

  // Accent — the tomato red
  accent:      '#e8442c',
  accentPress: '#a8331f',
  accentWash:  '#fdece8',  // selected chip / active state background

  // Provenance — the trust mechanism, use nowhere else
  provExplicit:'#2f9e5f',  // green
  provDerived: '#e0a012',  // amber — also 'estimated'
  provMissing: '#d94b3b',  // red

  // Semantic washes
  successWash: '#eef7f1',
  successInk:  '#2f7f52',
  warnWash:    '#fdf6e3',  // the missing-fields card
  warnBorder:  '#f0e0b0',
  warnInk:     '#7a5a10',

  // Source badges
  sourceVideo: '#8a5fc4',  // TikTok / Reels
  sourceWeb:   '#3a6ea5',  // blog / Pinterest

  // Cook mode
  cookBg:      '#16130f',  // near-black, warm
} as const;
```

**Accent is for action, never for status.** The tomato red and the provenance red are deliberately
different values (`#e8442c` vs `#d94b3b`); don't collapse them.

## Type

Single family: **Schibsted Grotesk** (400, 500, 600, 700), loaded via `expo-font`. Monospace only for
uppercase micro-labels — `ui-monospace, Menlo`.

```ts
export const type = {
  display:   { size: 26, weight: '700', lineHeight: 1.15, tracking: -0.02 },
  title:     { size: 17, weight: '700', lineHeight: 1.2 },
  heading:   { size: 16, weight: '700', lineHeight: 1.2 },
  bodyLarge: { size: 15, weight: '400', lineHeight: 1.45 },
  body:      { size: 13.5, weight: '400', lineHeight: 1.5 },
  bodyBold:  { size: 13.5, weight: '600', lineHeight: 1.3 },
  small:     { size: 12.5, weight: '400', lineHeight: 1.45 },
  caption:   { size: 11.5, weight: '500', lineHeight: 1.3 },
  micro:     { size: 10.5, weight: '500', lineHeight: 1, mono: true,
               uppercase: true, tracking: 0.1 },
  tiny:      { size: 9.5,  weight: '500', lineHeight: 1, mono: true },  // "geschat"

  // Cook mode only — readable at 60cm with dirty hands
  cookStep:  { size: 24, weight: '600', lineHeight: 1.35 },
  cookMeta:  { size: 15, weight: '500', lineHeight: 1.3 },
} as const;
```

The prototype's scale is dense because it's a design mockup at 1×. **Respect Dynamic Type in the real
app** — these are the defaults, not fixed values. Cook mode especially must scale up.

## Spacing and shape

```ts
export const space = { xs: 4, sm: 6, md: 9, lg: 14, xl: 20, xxl: 28 } as const;

export const radius = {
  pill:  999,   // chips, filter buttons, avatars — the most-used shape
  card:  15,    // recipe cards, sheets
  panel: 14,    // grouped panels, the missing-fields card
  tile:  13,    // thumbnails
  row:   12,    // list rows, ingredient rows
  input: 10,
  chip:  9,
  dot:   999,
} as const;

export const dot = { size: 5 } as const;  // provenance dot diameter in the prototype
```

**5px is too small for the provenance dot in production.** It works in a mockup viewed at desktop size;
on a phone it's below the perceptual threshold for a colour-blind user and near it for everyone else.
Use 8px, pair with a shape or letter, and never rely on colour alone. This is the one place I'd
deliberately diverge from the prototype.

## Motion

```ts
export const motion = {
  pop:     { from: { scale: 0.94, opacity: 0 }, to: { scale: 1, opacity: 1 }, duration: 180 },
  slideUp: { from: { translateY: 16, opacity: 0 }, to: { translateY: 0, opacity: 1 }, duration: 220 },
  spin:    { duration: 1400, easing: 'linear', loop: true },  // import progress
} as const;
```

Keep it restrained. The only place motion earns attention is the import progress screen, where it
signals work happening.

## Component notes from the prototype

- **Recipe card**: 4:5 image, `radius.card`, source badge top-left, heart top-right, title max 2 lines,
  meta row beneath in `caption`
- **Filter chips**: `radius.pill`, 7×13 padding, `accentWash` background and `accent` text when active,
  `surface` with `line` border when not
- **Missing-fields card**: `warnWash` background, `warnBorder` 1px, `warnInk` text, `radius.panel`,
  primary button filled `ink` not `accent` — the action is neutral, the card is already the alarm
- **Metadata field**: dot + mono uppercase label above, boxed value, `tiny` mono `geschat` caption in
  `provDerived` beneath when estimated
- **Progress step**: ring in `provExplicit` when done with a ✓, `accent` with spin when active,
  `#dcdce0` when pending. Weight goes 600 for done/active, 400 for pending
- **Tab bar**: 4 tabs plus a filled `accent` centre button that opens the import modal — not a tab

## Implementation

Put these in `app/src/theme/tokens.ts` and consume them everywhere. No hex literals in components. If a
value isn't in the tokens file, either add it there or you're about to make an inconsistent screen.
