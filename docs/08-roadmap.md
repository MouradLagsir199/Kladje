# 08 — Roadmap

> **Superseded on 2026-08-03 as a sequencing document.** The Phase 0–7 breakdown below is no longer
> what we are building against — `docs/13-build-tasks.md` is, and it puts a working MVP first
> (Phase M), then the rest of the prototype (N), then hardening (H).
>
> The week-by-week phasing here was wrong in one specific way: it treated caching, circuit breakers,
> quota and telemetry as phase-ordered work rather than as things you add once something exists to
> protect. It also put every screen behind a fully hardened pipeline, which meant the UI stayed
> unproven for months.
>
> Kept because the *reasoning* below is still right — especially the sequencing principle in the
> next paragraph, which the MVP ordering follows more faithfully than the phases ever did — along
> with the effort estimates and the target numbers.

Assumption: one developer, working with Claude Code, part-time-to-full-time. Durations are calendar
estimates for a solo build, not ideal-world engineering days.

The sequencing principle: **prove the import works before building anything to put imports into.** The
riskiest, most differentiating and most likely-to-disappoint part of this product is recipe extraction
quality. Every week spent on the planner before you know whether TikTok imports are good is a week of
risk deferred.

## Phase 0 — Skeleton (week 1)

Goal: a request travels from a phone to Postgres and back.

- Bicep for `kladje-dev`: App Service B1, Postgres Flexible Server B1ms, ACR, Key Vault, `recipe-media`
  container
- FastAPI skeleton in Docker, `/healthz`, deployed via GitHub Actions
- Alembic wired, `users` + `user_preferences` migrated
- Clerk dev instance, Google + Apple configured, JWT verification middleware, JIT user creation
- Expo app with a custom dev client, Clerk sign-in, one authenticated screen showing `GET /v1/me`

**Done when:** you sign in with Apple on a real device and see your own user row.

Do not skip the custom dev client here. Discovering the Expo Go limitation in week 6 is a bad week.

## Phase 1 — Import spine, cheapest source (weeks 2–3)

Goal: paste a blog URL, get a reviewable Dutch recipe.

- URL normalisation with tests for every platform's canonical form
- JSON-LD / microdata / WP Recipe Maker parser
- `EvidenceBundle` abstraction
- Synthesis call with structured output, full prompt including provenance rules and the rewrite
  requirement
- Validation and normalisation layer, unit and category enforcement, sensible rounding
- `imports`, `import_events`, `source_cache` tables; SSE progress endpoint
- Client: paste screen, progress screen, review screen, save
- `recipes`, `recipe_ingredients`, `recipe_steps`; recipe detail screen

**Done when:** you import ten real Dutch and English food blogs and the review screen needs no
corrections on at least seven.

This phase is the whole product in miniature. If the review screen doesn't feel good here, no amount of
planner polish will save it.

## Phase 2 — Import quality across platforms (weeks 4–6)

- YouTube: captions + description
- Apify integration, per-platform circuit breakers
- TikTok / Reels via Apify: transcript + metadata
- **No frame OCR, no ffmpeg, no media download** — the container never touches a video file
- `silent_video` failure routed to prefilled manual entry with the thumbnail attached
- Full failure taxonomy with distinct Dutch copy
- *Laat AI aanvullen* as a separate call
- Fixture corpus of 30–50 evidence bundles + the eval script
- Cost telemetry per import, per stage, per platform

**Done when:** the fixture corpus scores acceptably, and your measured blended cost per import is under
€0,008. Expected is ~€0,005 on GPT-4.1 mini. If you're materially above that, the cause is almost
certainly output tokens — tighten the JSON schema before moving on.

## Phase 3 — Library and share extension (weeks 7–8)

- Library with search (Dutch `tsvector` + trigram), ingredient search, filters, sort, grid/list toggle
- Collections
- Multi-select actions
- Cook mode with wall-clock timers and keep-awake
- Cook log with photo upload to blob via SAS
- Serving scaling with shared rounding logic
- **iOS Share Extension + Android intent filter**, with URL held across auth and paywall detours
- Persisted query cache + `expo-image` disk cache

**Done when:** you can share a TikTok from the TikTok app, sign in for the first time, and land on the
resulting recipe.

## Phase 4 — Planner and shopping list (weeks 9–10)

- Week grid, 4 slots, drag between slots, week navigation
- Copy previous week
- Per-day diner counts, leftovers marking
- Shopping list generation with merging on `name_nl`, shelf grouping, pantry exclusion
- Manual items, optimistic checkbox writes with `client_id` idempotency
- Regeneration that preserves check state
- Prakkie export endpoint + deeplink

**Done when:** you plan a real week for yourself, shop from the list in an actual supermarket, and
nothing about it annoys you.

That test is not a joke. You are your own first user and the shopping list is where design flaws become
obvious.

## Phase 5 — Groups and Discover (weeks 11–12)

- Groups CRUD, invite links + QR, unauthenticated invite preview
- Share recipe to group, save-to-own-library as a copy
- Reactions and cooked-with-photo
- Report button on shared content
- Discover: curated row (JSON in blob, you're the editor), group activity, seasonal map
- Push notifications: evening meal reminder, defrost reminder, group activity

## Phase 6 — Monetisation and launch prep (weeks 13–14)

- RevenueCat, products in both stores, entitlement sync, signed webhook
- Quota enforcement, rolling window, `resets_at`
- Paywall with all Apple-required elements
- Onboarding: two questions + live demo import
- Empty states for every main screen
- Account deletion, data export
- Privacy statement, terms, takedown policy, DPAs signed
- App Insights alerts including the daily-spend circuit breaker
- Reviewer notes, demo account, sandbox subscription
- Accessibility pass with VoiceOver

## Phase 7 — Beta and launch (weeks 15–16+)

- TestFlight + Play internal testing, 20–30 real users, ideally households
- Watch the `import_started → import_saved` funnel obsessively
- Prompt iteration against real failures, using the eval corpus
- Fix the top three drop-off causes, then submit

## Deferred to v2

Ordered by how often people will ask:

1. **Shared group week planner** — the strongest retention feature you're not building yet, and the
   original spec is right that for households it beats recipe sharing
2. **Background import with push notification** (ADR-009) — better UX, needs a queue
3. **Manual merge of near-duplicate ingredients** on the shopping list
4. **Real offline sync** — only if telemetry shows it actually hurting
5. **iPad / tablet layout** — the planner genuinely wants a real grid
6. **Curated content admin UI** — only once editing JSON in blob storage becomes annoying
7. **Web app** — for SEO and sharing recipes to non-users
8. **Cookbook photo import (vision OCR)** — cut from v1 on 2026-08-02, cost grounds, not a scope
   judgement. See the update to ADR-014 in `09-decisions-adr.md`

## Cost model over time

| Stage | Users | Fixed | Variable | Monthly |
|---|---|---|---|---|
| Development | 1 | €45 | ~€5 | ~€50 |
| Beta | 30 | €85 | ~€10 | ~€95 |
| Launch | 300 (20 paying) | €85 | ~€8 | ~€93 vs €35 revenue |
| Traction | 3,000 (250 paying) | €130 | ~€20 | ~€150 vs €433 revenue |

Break-even sits at roughly **50 paying subscribers** on the standard commission rate, or **41** on the
Small Business rate — set almost entirely by fixed infrastructure cost, since variable cost is now an
order of magnitude smaller. At a 5–8% free-to-paid conversion rate that means roughly 600–1,000 active
users. That's the number the roadmap is really aiming at, and it's why Phase 5's
groups feature matters — invite links are the only organic growth mechanism in the plan.

## What I'd cut if you fall behind

In this order, without much regret:

1. Discover tab entirely — ship with Recepten as the opening tab. It's the least differentiated surface
   in the app and it costs a fortnight
2. Collections — folders are nice, search is sufficient
3. Reactions and cooked-with-photo in groups — sharing alone is the feature
4. Seasonal row
5. Defrost notifications

What I would **not** cut under any circumstances: the review screen's provenance indicators, cook mode,
copy-previous-week, and the share extension. Those four are the product. Everything else is furniture.
