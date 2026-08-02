# Screens — read from the prototype

One entry per screen in `docs/prototype/Receptenapp.dc.html`, written after reading the whole file
end to end (task 0.12b). This is a map from prototype markup to the routes in `docs/05-client.md`,
plus the layout/behaviour detail that isn't obvious from a five-second look at the file. It doesn't
replace opening the prototype before building a screen — it tells you which block to open and what
to watch for once you're there.

Values referenced below (colours, sizes, radii) live in `app/src/theme/tokens.ts` (task 0.12).

---

## Onboarding — `app/(onboarding)/`

Four steps, one full-screen white sheet, progress dots (3px, `accent` when passed) at the top. Step
content animates in with `slideUp`. Bottom of the sheet is fixed: a filled `accent` primary button
(label changes per step) and a plain "Overslaan" skip link.

1. **Household size** — 4 tappable rows ("1 persoon" … "5 of meer"), each with a label and a grey
   hint. Selected row gets `accentWash` background and `accent` border.
2. **Diet & allergens** — two labeled chip groups (`radius.pill`, multi-select), one for diet, one
   for allergens to exclude. Same active/inactive chip styling as everywhere else in the app.
3. **Market** — 2×2 grid of cards, each with a colour swatch and a label. This step has no named
   route in `docs/05-client.md`'s tree (only `household`, `diet`, `demo-import` are listed) — it's a
   real fourth onboarding screen in the prototype and needs a route added, e.g. `(onboarding)/market`.
4. **Demo/clipboard** — shows a fake "clipboard" card with a TikTok URL and one line of copy: no tour,
   no explanation, just prove the paste-and-import loop once. This is `demo-import`. Finishing this
   step is what triggers the very first import (`impStep2`, see Import below).

## Feed — `(tabs)/ontdek/index.tsx`

Sticky header (blurred, `rgba(255,255,255,.92)`) containing a fake search-bar button (opens Zoeken,
not an inline input) and a horizontally-scrolling row of meal-type chips. Below that, four
vertically-stacked horizontally-scrolling sections:

- **Hero row** — large (300×200) cards, image with a bottom gradient, source badge top-left, title +
  meta over the gradient. `scroll-snap-type: x mandatory`.
- **"Onder 30 minuten"** — `RecipeCard` compact variant, 146px wide, 4:5 image, heart top-right.
- **"Nieuw van je groepen"** — a different card shape entirely: small square thumbnail + title +
  sharer avatar/initials, row layout not a grid.
- **"Seizoen · augustus"** — 2-column grid, `RecipeCard` grid variant with a difficulty dot in the
  meta row.

Every card here opens Receptdetail. The seasonal section header text is literally hardcoded to the
current month, matching `docs/04-api.md`'s "hardcode the seasonal map, it costs nothing."

## Zoeken (search) — overlay, no dedicated route in `docs/05-client.md`

Full-screen overlay (`pop` animation) over Feed, not a tab. Text input pre-filled/focused, a 2-way
segmented control ("recept" vs "ingrediënt" search mode — this is the "wat kan ik met prei" path from
`docs/04-api.md`), a max-kooktijd range slider, a row of filter chips, then a plain list of results
(56px thumbnail + title + meta, no source badge). Needs a route decision when built — likely a modal
pushed from the Feed header's search button rather than its own tab.

## Bibliotheek (library) — `(tabs)/recepten/index.tsx`

Sticky header with a page title, a 2-way grid/list view toggle (top-right, segmented pill), and a
2 or 3-way tab row (Alles / Collecties / — the prototype wires `lib` and `collections` as the same
screen family). Two sub-views:

- **Collecties tab** — 2-column grid of collection cards. Each card is a 3-photo collage (one large
  left, two stacked right) + name + count. A dashed "Nieuwe collectie" tile is always last.
- **Alles tab** — filter chip row, a count + offline-availability line, a sort-cycle button, then
  either the grid or list view of recipes (`RecipeCard` grid variant, or a denser list row variant
  with a 50px thumbnail).

## Collectie (a single collection) — pushed from Bibliotheek

Header with a back link, collection name + count, and an "Toevoegen" button that opens the
recept-kiezer sheet (see below). Empty state (no recipes yet) is a dedicated illustration + text +
single CTA — matches the `EmptyState` component spec exactly. Populated state is the same 2-column
grid as elsewhere, but each card has an extra "Verwijder uit collectie" text link beneath it.

## Receptdetail — `recipe/[id]/index.tsx` (global screen)

Not a tab — pushed from anywhere a card is tapped. Layout, top to bottom:

- **290px hero image** with a top gradient, a back button and two action buttons (share, more) floating
  over it, and a centered circular play button — tapping it is presumably how you reach Kookmodus or
  play the original clip inline (prototype doesn't fully specify which)
- **Title, "Van [creator] op [source] · origineel" attribution line** — this is the always-visible
  source link required by no-jump-to-source (D15) and the copyright rewrite requirement
- **Meta row** — 4 columns (time/portions/difficulty/etc.), each a mono uppercase label over a value,
  bordered top and bottom
- **Allergy warning card** (conditional) — red dot + bold warning + explanation, `warnWash`-style but
  in the red/missing palette, not amber — this fires from the user's own allergen preferences, not
  provenance
- **Ingredients** — section header with a portions stepper (−/+ pill) inline. Rows have a checkbox,
  main line (scaled quantity), and an original-unit caption line beneath when converted, plus a small
  provenance dot per row
- **"Alles naar boodschappenlijst"** full-width secondary button
- **Steps** — numbered circle + text, inline "Timer" chip on steps that have one
- **Notes textarea** — free text, borderless, inline in a grey panel
- **Cook-count strip** — "3× gekookt · Laatst op 12 juli"
- **Sticky footer** (blurred) — "Start koken" primary (opens Kookmodus), "Plan in" and "Lijst" secondary

## Kookmodus (cook mode) — `recipe/[id]/cook.tsx` (global, full-screen)

Near-black (`cookBg`) full-screen, not a sheet. Top bar: "Sluiten" + "Stap N van M". Below that a
segmented progress bar (one bar per step, not a single track). "Nu nodig" ingredient pills for the
current step only. The step text itself is large (29px in the prototype; tokens specify 24px — cook
mode explicitly overrides the base scale for 60cm readability). Optional inline "Start timer" pill in
the accent-on-dark treatment. Bottom nav is just two buttons: back-chevron and next (label changes to
whatever finishes the flow on the last step).

## Import — `import/` modal stack

The prototype treats this as one continuous full-screen modal with an internal step machine
(`impStep1`–`impStep4`), not the four separate routes docs/05-client.md implies
(`index.tsx`, `[id]/progress.tsx`, `[id]/review.tsx`, `[id]/done.tsx`) — but the four steps map
directly onto those four routes:

- **Step 1 → `import/index.tsx`** — clipboard-detected URL card (if a supported link is on the
  clipboard) with one big "Importeren" button, a dashed "of plak een link" zone, two secondary
  buttons ("Foto van kookboek" — **cut, ADR-014 update, don't build this**; "Handmatig"), and a quota
  pill at the bottom.
- **Step 2 → `import/[id]/progress.tsx`** — video thumbnail behind a translucent overlay, a checklist
  of stages animating through pending → active (spin) → done (check, `provExplicit` green ring). The
  prototype's stage list still includes "Audio uitlezen" as a separate row from "Tekst in beeld
  herkennen" — per `docs/03-import-pipeline.md` this collapses to effectively two stages now that
  Apify supplies the transcript directly; the progress copy needs updating from the prototype, not
  copied verbatim.
- **Step 3 → `import/[id]/review.tsx`** — the three variants live side by side here, switchable via
  the top-right toggle in the prototype chrome (not part of the real app). **Build variant A only**
  (D16):
  - **Variant A ("Lijst — inline correctie")** — this is the one described in full in
    `docs/05-client.md` and is what actually gets built: amber missing-fields card, photo+title row,
    3 metadata fields with dots, draggable ingredient rows split into qty/unit/name inputs, numbered
    editable steps, a static footnote about steps being rewritten.
  - **Variant B ("Triage")** — one full-screen question per field, answered in sequence (5 of 5
    dots), each with a "Hoor het terug in de video" source-jump link. **Not built** — dropped by D16.
  - **Variant C ("Split met bron")** — sticky video-quote header, ingredient rows that jump to a video
    timestamp when tapped. **Not built** — dropped by D16, and jump-to-source is cut entirely (D15).
- **Step 4 → `import/[id]/done.tsx`** — a single centered confirmation card: thumbnail, green
  "Opgeslagen" tag, title, one line of reassurance text, primary "Bekijk recept" + two secondary
  buttons ("Plan in", "Deel met groep").

## Planner — `(tabs)/planner/index.tsx`, week + boodschappen subtabs

Shared header: title, a week-number stepper (‹ wk N ›), and a 2-tab row (Week / Boodschappen).

- **Week subtab** — a prominent "Kopieer vorige week" banner-button first (D-ranked as the
  single most-used control per `docs/04-api.md`'s planner notes), then one block per day: day name +
  date + an "N eters" pill, then 4 meal slots (Ontbijt/Lunch/Diner/Tussendoor). Filled slots are
  `PlanSlot` filled state (thumbnail + meal-type label + title + optional "restje" tag + time).
  Empty slots are the dotted-plus `PlanSlot` empty state. A full-width "Maak boodschappenlijst"
  button closes the tab.
- **Boodschappen (shopping) subtab** — a summary card (week label, "N van M te gaan", and a shared-with
  avatar stack when a group shares the list), then aisle-grouped sections (mono uppercase aisle name +
  divider line), each with `ShoppingRow`s (checkbox, product name, source-recipe caption, quantity).
  Below the list: an "Item toevoegen" dashed button, a pantry-exclusion note linking to Voorraadkast,
  and — separately boxed, visually distinct with its own dark "P" mark — the Prakkie hand-off card
  (explanation text + one button that becomes a confirmation strip once sent). Keep this box visually
  separate from the app's own accent colour per D1/D2 — it's clearly "another product," not a
  Kladje feature.

## Voorraadkast (pantry) — reached from Boodschappen, no dedicated route named yet

Back link to Boodschappen, title + one line of explanation, then a bordered list of toggle rows
(product name + hint text + a rounded switch). A dashed "Product toevoegen" button at the bottom.
Maps to `PUT /v1/pantry` in `docs/04-api.md`.

## Profiel — `(tabs)/profiel/index.tsx`, groups/settings/subscription

Avatar-initials circle + name + tier label, a 3-stat row (`flex` cards, big number + small label),
then a dark **upsell card** (imports-used copy, benefit line, price button) — this is the paywall
entry point, not a separate screen. Below that: a Groepen section (row per group: colour swatch,
name, member/recipe counts, chevron) with a "Nieuwe groep" action, then a bordered Instellingen list
(label + current value + chevron per row, 7 rows in the mock).

## Groepdetail — `group/[id]/index.tsx` (global screen)

Back-to-Profiel link, group colour swatch + name + "N leden · gedeelde weekplanner aan", two actions
side by side (Uitnodigen / QR-code), then a 3-tab row (prototype wires `groupTabs` generically —
likely Recepten / Planner / Leden). Below: 2-column grid of shared recipes, each card showing the
sharer's avatar-initials + name under the title, no heart icon (favouriting isn't a group-recipe
action here).

## Categorie-overzicht — reached from Ontdek, no dedicated route named yet

Back-to-Ontdek link, a title (category name) + a "Filter" button that opens Zoeken. Straightforward
2-column recipe grid below, same card as everywhere else. This is the "Toon alles" destination from
Feed's horizontal sections.

## Recept-kiezer / Collectie-sheet — shared bottom sheet, not a route

A modal bottom sheet (slides up from `pickerOpen`, dark scrim behind), used both for "add recipes to
a collection" and (per the component's generic naming) likely reused for "share to group." Sticky
header with a title + "Klaar" to dismiss, then a plain checkbox list (thumbnail optional, title +
subtitle). Worth building as one reusable sheet component rather than two, matching how the prototype
already treats it as one thing.

## Persistent chrome (not screens)

- **Tab bar** — 4 destinations (Ontdek, Recepten, Planner, Profiel) plus a **5th, non-tab centre
  button**: a filled `accent` circle that overlaps the bar (`margin-top:-14px`) and opens the Import
  modal directly. It is not a 5th tab and has no active state — don't build it as one.
- **Timer pill** — floats bottom-center (104px up, above the tab bar) whenever a cook-mode timer is
  running, survives navigating away from Kookmodus in the prototype's state model. Matches
  `docs/05-client.md`'s "timers float above the pager and keep running across swipes."

## Gaps worth a decision before building these screens

None of these block Phase 0/1/2 work, but they're real screens in the prototype without a named route
in `docs/05-client.md`'s tree yet: the onboarding **market** step, **Zoeken** (search), and
**Categorie-overzicht**. Reasonable defaults: `(onboarding)/market`, a modal route off `(tabs)/ontdek`
for search, and `(tabs)/ontdek/category/[key]` for the category view — worth confirming when Phase 3
actually gets there rather than deciding unilaterally now.
