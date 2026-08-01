# 00 — Scope and Decision Log

## The product in one paragraph

People find recipes on TikTok, Reels, YouTube and blogs, and then lose them. Receptenapp lets you
share a video into the app and get back a clean, structured, Dutch-language recipe with metric
quantities, editable before saving. From there: a week planner, a shopping list generated from that
week's plan, and small private groups to share recipes with a household or friends.

The differentiator is **import quality plus trust in the import**. Not the feed, not the planner —
those are table stakes. The review screen is where the product is won.

## In scope for v1

- Import from TikTok, Instagram Reels, YouTube, Pinterest, food blogs, plus manual entry
- **Cookbook photo import** — photograph a page, vision OCR, same review screen (the only use of vision)
- iOS Share Extension and Android Intent Filter as the primary entry point
- AI parsing into structured recipe: title, servings, times, ingredients, steps, meal type
- English → Dutch translation of ingredient names, imperial/US → metric conversion
- Per-field provenance indicators (green / yellow / red) and a "let AI fill the gaps" action
- Review-and-edit screen before save — **prototype variant A ("Lijst — inline correctie") only**
- Personal library with collections, search, filters
- Recipe detail with serving scaling, checkable ingredients, tappable timers, oven fan-assist variant
- Cook mode: one step per screen, large type, screen stays awake
- Notes and cook log per recipe
- Week planner: 7 days × 4 slots, drag between slots, copy previous week, per-day diner count
- Shopping list generated from the week's plan, **no prices**, grouped by shelf category, merged
  across recipes, with a pantry exclusion list and manual items
- Export/deeplink to Prakkie for price comparison
- Groups: create, invite by link/QR, share recipes, react, mark as cooked
- Free tier: 10 imports per rolling 30 days. Paid tier: €2,99/month for 100 imports/month
- Onboarding: household size, diet + allergies, then a live demo import

## Explicitly out of scope

| Not building | Why |
|---|---|
| Supermarket prices, anywhere | Belongs to Prakkie |
| Product catalogue, SKUs, chain assortments | Belongs to Prakkie |
| Ingredient → product matching | Prakkie does this at export time |
| Preferred-supermarket setting | No longer has a function without prices or products |
| Packaging logic ("smallest pack is 250 g") | Requires SKU-level pack sizes; Prakkie's job |
| Blob → Data Factory → Postgres pipeline | Was only justified by price data. Not needed here |
| Nightly scraper dependency | This app has **no batch layer** at all |
| Offline sync engine, two-way sync | v1 is online-only with a persisted read cache |
| Global public feed of all users' recipes | Moderation, spam and rights liability. Groups + curated only |
| Shared group week planner | Deferred to v2; groups share recipes only in v1 |
| Web app | Cannot be an iOS share target, and share-first is the core interaction |
| Frame OCR on social posts | Vision is for cookbook photos only (which *is* in v1) |
| Tap-an-ingredient-to-jump-to-the-source | Cut. Trust rests on provenance dots and the review screen |
| "Kies frame uit video" photo picker | Needs ffmpeg; thumbnail + gallery covers it |
| Review screen variants B (Triage) and C (Bron) | Variant A only — see D16 |

## Decision log

Numbered decisions from the design interview. Each one is settled unless marked otherwise.

**D1 — No supermarket data in this app.** No prices, no products, no chain awareness, no availability
signals. The four supermarket assortments and the whole blob/ADF pipeline belong to Prakkie.

**D2 — Ingredient handling is translate + normalise only.** English name → Dutch name; cups/oz/lb/°F →
grams/ml/°C. Output is a structured row: `amount` + `unit` (fixed enum) + canonical Dutch name +
shelf category. This structure doubles as the Prakkie export contract.

**D3 — The parsing model does translation, conversion and category tagging in one pass.** Apify supplies
the transcript, so there is no transcription step. **No OCR in the link-import path at all** — vision is
used only for the cookbook-photo entry point. No density
lookup table. Cups-to-grams is ingredient-dependent and the model is roughly right; every converted
value therefore renders with the yellow *geschat* provenance dot.

**D4 — `unit` and `category` are fixed enums.** Never free text. A free-text unit makes the Prakkie
handoff unusable later; a free-text category fragments shelf grouping into forty headings.

**D5 — Shopping list merges on canonical Dutch name.** "ui" and "rode ui" stay separate lines. Manual
merge is a v2 nicety.

**D6 — Shopping list has no prices.** Price comparison is a button that deeplinks to Prakkie.

**D7 — Onboarding is two questions:** household size, diet + allergies. Then a live demo import as
the aha-moment.

**D8 — Client is Expo / React Native**, iOS and Android launching simultaneously.

**D9 — Share extension is a launch requirement.** It captures the URL, writes it to a shared
container, and hands off to the app. It does not perform the import.

**D10 — Import runs in the foreground** with the five-step progress screen. Not a background queue
with push notification. (Revisit in v2 — see ADR-009.)

**D11 — v1 is online-only**, with a persisted read cache so recipe detail and cook mode survive bad
kitchen wifi, and optimistic local state for ingredient and shopping-list checkboxes.

**D12 — Auth methods are Google and Apple only.** No email/password. Account linking on verified
email, with a manual "link another sign-in" flow in profile as the escape hatch for Apple Private
Relay addresses.

**D13 — Postgres is Azure Database for PostgreSQL Flexible Server**, West Europe, B1ms burstable,
public access with firewall rules and enforced SSL.

**D14 — Discover starts group-based plus one manually curated editorial row.** No global user feed.

**D15 — No jump-to-source.** Tapping an ingredient does not open the video at a timestamp, and blogs do
not highlight matched source text. `source_time_ms` is removed from the schema. Trust now rests entirely
on the provenance dots, the visible *geschat* labels, the always-shown original units, and the fact that
nothing is saved without the user reviewing it. This also means Apify transcript timestamps are
irrelevant — one fewer unknown to verify.

**D16 — Review screen is prototype variant A only.** "Lijst — inline correctie": amber missing-fields
card with *Laat AI aanvullen*, photo plus title, three metadata fields each with a provenance dot and a
*geschat* label where applicable, draggable ingredient rows, numbered steps. Variants B (Triage,
one-question-at-a-time) and C (Bron, source-anchored) are dropped. C depended on jump-to-source, so D15
removed it anyway.

## Decisions I made for you

Documented with reasoning in `09-decisions-adr.md`:

- **Auth provider: Clerk** (ADR-006)
- **API language: Python 3.12 + FastAPI** (ADR-007)
- **Compute: Azure App Service for Linux Containers** (ADR-008)
- **Model provider: OpenAI direct, behind a provider interface** (ADR-005)

## Known risks, ranked

1. **Model tier drift is the financial risk, not per-import cost.** €2,99 nets €1,73 after 21% VAT and a
   30% store cut (€2,10 on the Small Business rate). At €0,005 per import on GPT-4.1 mini, 100 imports
   cost €0,60 and the margin is comfortable — but a switch to a frontier model would cost €3–5 and make
   the paid tier lose money at the cap. Pin the model; keep the daily-spend circuit breaker. See
   `06-monetisation.md` and ADR-011.
2. **App Store review on third-party content.** Apps ingesting TikTok/Instagram material get rejected
   under the unauthorised-third-party-content guidelines. Mitigation strategy in `07-legal-avg.md`.
3. **Silent videos are an accepted product limitation.** Transcripts are audio-derived, and a meaningful
   share of short-form recipes are never spoken aloud — only shown as on-screen text. With no frame OCR,
   those imports fail. Mitigation is a prefilled manual-entry fallback, not a rescue pass. Instrument the
   rate; if it's large, that's the signal to revisit.
4. **Platform terms of service.** Apify scraping of TikTok and Instagram sits in a grey area that is
   yours to accept, not mine to wave away.
5. **Solo developer, 30+ screens.** The roadmap in `08-roadmap.md` cuts hard for this reason.
