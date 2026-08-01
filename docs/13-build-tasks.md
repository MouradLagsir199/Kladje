# 13 — Build Tasks

Atomic, dependency-ordered tasks. Each has an ID, acceptance criteria, and a verification command.

**Rules for the agent:**
- Work in ID order unless a task says otherwise
- A task is done only when its acceptance criteria hold *and* the verify command runs green
- Tasks marked 🔑 need a credential or a human action — stop and ask, naming exactly what you need
- Tasks marked 📱 need a physical device — stop and ask the user to test
- Commit after each task: `feat(scope): description` referencing the task ID
- **Before building any screen, open `docs/prototype/Receptenapp.dc.html` and find it.** Tokens give you
  the values; the prototype gives you the layout

Legend: **[P]** parallelisable with the previous task · **[B]** blocks a lot downstream

---

## Phase 0 — Skeleton

| ID | Task | Acceptance | Verify |
|---|---|---|---|
| 0.1 | Repo init: `api/`, `app/`, `docs/`, `infra/`, `scripts/`. Copy `CLAUDE.md` to root, plan into `docs/` | Structure exists, `.gitignore` covers `.env`, `node_modules`, `__pycache__`, `*.p8`, `secrets/` | `git status` clean |
| 0.2 | **[B]** FastAPI skeleton with `uv`, Ruff, mypy, pytest. `/healthz` and `/readyz` | App boots, `/healthz` returns 200 | `uv run pytest -q && uv run uvicorn receptenapp.main:app` |
| 0.3 | `core/config.py` — Pydantic Settings reading every var in `docs/12-manual-setup.md`. `.env.example` mirrors it exactly | Missing required var fails at startup with a clear message | `uv run python -c "from receptenapp.core.config import settings; print(settings.environment)"` |
| 0.4 | `core/errors.py` + one exception handler producing the error contract in `docs/04-api.md` | Every error response has `error.code`, `error.message`, optional `error.details` | `uv run pytest tests/test_errors.py` |
| 0.5 | Dockerfile (multi-stage, non-root, no ffmpeg) + `.dockerignore` | Image builds, container serves `/healthz` | `docker build -t api . && docker run -p 8000:8000 api` |
| 0.6 | 🔑 Bicep: App Service B1, Postgres B1ms, ACR, Key Vault, `recipe-media` container, managed identity | `az deployment group create` succeeds against `kladje-dev` | `az webapp show -n receptenapp-api-dev` |
| 0.7 | GitHub Actions: lint → typecheck → test → build → push ACR → deploy slot → swap | Pipeline green on main | Pipeline run |
| 0.8 | **[B]** Alembic wired. Migration 001: enums + `users` + `user_preferences` | `alembic upgrade head` on empty DB succeeds; `downgrade` works | `uv run alembic upgrade head && uv run alembic downgrade -1` |
| 0.9 | 🔑 Clerk JWT middleware: JWKS fetch + cache, verify, resolve `clerk_user_id` → `users.id`, JIT create | Valid token resolves a user; invalid returns 401 with `unauthorized` | `uv run pytest tests/test_auth.py` |
| 0.10 | `GET /v1/me`, `PATCH /v1/me`, `PATCH /v1/me/preferences` | Returns user + preferences + tier + quota stub in one call | `uv run pytest tests/test_me.py` |
| 0.11 | **[B]** Expo app init, TypeScript strict, Expo Router, EAS config, custom dev client | `npx tsc --noEmit` clean, dev client builds | `cd app && npx tsc --noEmit` |
| 0.12 | `app/src/theme/tokens.ts` from `docs/14-design-tokens.md` + Schibsted Grotesk via `expo-font` | Tokens exported, font renders | Visual |
| 0.12b | **Read `docs/prototype/Receptenapp.dc.html` end to end.** Write `docs/prototype/SCREENS.md`: one entry per screen with its layout, in your own words | Every screen in the prototype has an entry | Human skim |
| 0.13 | 🔑 Clerk Expo SDK, Google + Apple sign-in buttons, token attached to API client | Sign-in returns to app authenticated | 📱 device |
| 0.14 | 📱 First device build, signed in, `GET /v1/me` renders own user row | **Phase 0 gate** | 📱 device |

---

## Phase 1 — Import spine (blog)

| ID | Task | Acceptance | Verify |
|---|---|---|---|
| 1.1 | **[B]** URL normaliser: strip tracking params, resolve shorteners, canonical forms per platform | Fixture table of 25 URL pairs all pass | `pytest tests/test_url_norm.py` |
| 1.2 | Migration 002: `recipes`, `recipe_ingredients`, `recipe_steps`, `collections`, `collection_recipes`, `cook_logs` | Upgrade + downgrade clean | `alembic upgrade head` |
| 1.3 | Migration 003: `imports`, `import_events`, `source_cache` incl. the partial quota index | Index exists | `\d+ imports` in psql |
| 1.4 | **[B]** `EvidenceBundle` dataclass + Pydantic models per `docs/03-import-pipeline.md` | Serialises round-trip | `pytest tests/test_evidence.py` |
| 1.5 | JSON-LD / microdata / WP Recipe Maker extractor | 10 saved Dutch + English blog HTML fixtures parse to an EvidenceBundle | `pytest tests/test_jsonld.py` |
| 1.6 | 🔑 **[B]** OpenAI provider behind an interface (ADR-005). Synthesis call with structured output using the exact schema in `docs/11-prompts.md` | Returns schema-valid output on a fixture; provider swappable | `pytest tests/test_openai_provider.py` (mocked) |
| 1.7 | Synthesis prompt from `docs/11-prompts.md` verbatim, incl. few-shot. `PROMPT_VERSION=1` pinned in config | Prompt loaded from a versioned module, not inline | `pytest tests/test_prompt_version.py` |
| 1.8 | **[B]** Validation layer: enum enforcement, clamps, fan-oven computation, sensible rounding, dedupe, min-viability | All rules in §2.5 of `docs/10-phase2-workplan.md` covered by tests | `pytest tests/test_validation.py` |
| 1.9 | `source_cache` read-before-spend + write-after-parse, keyed on `url_norm` + `prompt_version` | Second identical import makes zero paid calls | `pytest tests/test_cache.py` |
| 1.10 | Import service: orchestrate normalise → cache → fetch → synthesise → validate → draft | Draft lands in `imports.draft`, nothing in `recipes` yet | `pytest tests/test_import_service.py` |
| 1.11 | `POST /v1/imports` (202 + Idempotency-Key), `GET /v1/imports/{id}`, `DELETE` | Double-tap with same key creates one import | `pytest tests/test_import_api.py` |
| 1.12 | SSE `GET /v1/imports/{id}/events` from `import_events`, with polling fallback documented | Stream emits fetch/synthesize, closes on terminal state | `curl -N` against a running import |
| 1.13 | `PATCH /v1/imports/{id}/draft`, `POST /save`, `POST /enrich` | Save materialises recipe + ingredients + steps, maps `ingredient_pos` → UUIDs | `pytest tests/test_import_save.py` |
| 1.14 | Client: import modal step 1 (paste + clipboard read) | Clipboard containing a URL offers to import | 📱 |
| 1.15 | Client: progress screen with SSE, skipped stages, cancel | Skipped stages show as skipped, not stalled | 📱 |
| 1.16 | **[B]** Client: review screen **variant A only** per `docs/05-client.md` | Matches prototype variant A; every edit PATCHes debounced | 📱 |
| 1.17 | Component library: RecipeCard ×3, MetaBar, SourceBadge, ProvenanceDot (8px, not colour-alone), IngredientRow, StepCard, EmptyState | Rendered in a dev gallery screen | Visual |
| 1.18 | `GET /v1/recipes`, `GET /v1/recipes/{id}` + client recipe detail screen | Detail renders ingredients, steps, provenance dots, source attribution | 📱 |
| 1.19 | **Gate:** import 10 real blogs; ≥7 need no correction | **Phase 1 gate** | Manual review |

---

## Phase 2 — Import quality across platforms

| ID | Task | Acceptance | Verify |
|---|---|---|---|
| 2.1 | 🔑 **Do first.** Save raw Apify JSON for 1 TikTok, 1 Reel, 1 YouTube into `tests/fixtures/apify/` | Three real payloads committed | Files exist |
| 2.2 | **[B]** Apify provider: run actor, poll, fetch dataset, 45s ceiling. Pydantic validation at the boundary | Malformed response raises at the boundary, not downstream | `pytest tests/test_apify_provider.py` |
| 2.3 | Per-actor response normalisers → EvidenceBundle. Reuse the user's existing actor code where it fits | Three fixtures normalise correctly | `pytest tests/test_apify_normalise.py` |
| 2.4 | Per-platform circuit breaker: 5 consecutive failures → open 10 min, return `scraper_failed` fast | Blog path unaffected while TikTok breaker is open | `pytest tests/test_circuit_breaker.py` |
| 2.5 | YouTube path: captions + description; ingredient-list-shaped description block treated as high-confidence | 8 YouTube fixtures parse well | `pytest tests/test_youtube.py` |
| 2.6 | TikTok/Reels path: transcript + caption + metadata. Thumbnail copied into blob if the URL expires | 12 fixtures parse; thumbnail persisted | `pytest tests/test_tiktok.py` |
| 2.7 | `silent_video` detection → prefilled manual entry with thumbnail + caption remnants | Silent fixture routes to manual entry, not an error screen | `pytest tests/test_silent_video.py` |
| 2.8 | Full failure taxonomy with distinct Dutch copy, written in one file in one sitting | Every code in the `docs/03` table has copy and an exit | `pytest tests/test_error_copy.py` |
| 2.9 | **[B]** Fixture corpus: 45 EvidenceBundles (15 blog, 8 YT, 12 TikTok, 5 Reels, 5 cookbook) incl. deliberately awful ones | Committed, loadable | `pytest tests/test_corpus_loads.py` |
| 2.10 | `scripts/eval.py` with the 9 assertions in `docs/11-prompts.md`. Commit results alongside prompt | One command, one table; provenance-honesty ≥95% | `uv run python scripts/eval.py --prompt-version 1` |
| 2.11 | Prompt hardening loop against the corpus. Bump `PROMPT_VERSION` per semantic change | No regression on provenance honesty or silent invention | `scripts/eval.py` diff vs previous |
| 2.12 | Cookbook photo: `POST /v1/imports/photo` multipart (≤3 files, 8MB, JPEG/PNG/HEIC), vision call, **delete page photos after parsing** | Photo import produces a draft; blob temp prefix empty afterwards | `pytest tests/test_photo_import.py` |
| 2.13 | 🔑 Client: "Foto van kookboek" entry, `expo-image-picker`, Dutch permission strings, client-side downscale to 1500px | Camera + gallery both work, permissions requested with specific copy | 📱 |
| 2.14 | Telemetry: one event per import (platform, cache hit, per-stage ms, tokens, cost, outcome, silent_video, enrich used) | Events visible in App Insights | Query App Insights |
| 2.15 | 🔑 Daily-spend alert + 5xx / import-failure-rate / p95-duration alerts | Alerts fire on a forced test | Azure alert test |
| 2.16 | **Gate:** corpus ≥80% ingredients / ≥70% steps clean, cost <€0,008, p95 <25s, every failure mode triggered once | **Phase 2 gate** | `scripts/eval.py` + telemetry |

---

## Phase 3 — Library and share extension

| ID | Task | Acceptance | Verify |
|---|---|---|---|
| 3.1 | Search: Dutch `tsvector` + `pg_trgm`; `?q=` and `?ingredient=` paths | "prei" finds recipes containing prei | `pytest tests/test_search.py` |
| 3.2 | Recipe list filters, sort, cursor pagination on `(created_at, id)` | No duplicates across pages when a recipe is added mid-scroll | `pytest tests/test_pagination.py` |
| 3.3 | `PUT /recipes/{id}/ingredients`, `PUT /steps`, `PATCH`, `DELETE` (soft), `POST /duplicate` | Full-replace preserves ordering | `pytest tests/test_recipe_crud.py` |
| 3.4 | Collections CRUD + `PUT /collections/{id}/recipes` | | `pytest tests/test_collections.py` |
| 3.5 | `GET /recipes/{id}/scale` with shared rounding logic (same module the pipeline uses) | 1.33 eggs → "1–2 eieren" | `pytest tests/test_scaling.py` |
| 3.6 | Blob SAS issuance + `POST /recipes/{id}/cook-logs` with photo upload | SAS expires; photo retrievable while valid | `pytest tests/test_blob.py` |
| 3.7 | Client: library screen, grid/list toggle, filters, sort, multi-select | | 📱 |
| 3.8 | Client: collections | | 📱 |
| 3.9 | **[B]** Client: cook mode — dark, keep-awake, one step per page, **timers as wall-clock end times** | Timer survives backgrounding for 5 min | 📱 |
| 3.10 | Client: cook log with photo + rating | | 📱 |
| 3.11 | 🔑 **[B]** iOS Share Extension via `expo-share-intent` config plugin + App Group. Captures URL, writes to shared container, opens app. No network, no auth in the extension | Sharing from TikTok opens the app with the URL | 📱 |
| 3.12 | Android intent filter for text/URL share | Same on Android | 📱 |
| 3.13 | **[B]** URL held across auth and paywall detours; resumes to the import after sign-in | First-ever action = share → sign up → lands on that recipe | 📱 |
| 3.14 | Persisted TanStack Query cache in MMKV + `expo-image` disk cache | Airplane mode: previously-viewed recipe and cook mode still render | 📱 |
| 3.15 | **Gate:** share a TikTok from TikTok, sign in fresh, land on the recipe | **Phase 3 gate** | 📱 |

---

## Phase 4 — Planner and shopping list

| ID | Task | Acceptance | Verify |
|---|---|---|---|
| 4.1 | Migration 004: `plan_entries`, `shopping_lists`, `shopping_list_items`, `pantry_items` | | `alembic upgrade head` |
| 4.2 | Planner API: get week, create/patch/delete entries, `POST /plan/copy` | Copy-week duplicates all entries to the target week | `pytest tests/test_planner.py` |
| 4.3 | **[B]** Shopping list generation: expand plan → scale by entry servings → exclude pantry → exclude leftovers → merge on `(name_nl, unit)` → group by category | Three recipes with ui produce one line | `pytest tests/test_shopping_gen.py` |
| 4.4 | **Regeneration preserves check state** for surviving `(name_nl, unit)` pairs | Adding a Thursday dinner does not clear ticked items | `pytest tests/test_shopping_regen.py` |
| 4.5 | Item patch idempotent on `client_id`; manual items; pantry CRUD | Replayed request creates no duplicate | `pytest tests/test_shopping_items.py` |
| 4.6 | `GET /shopping-lists/{id}/export/prakkie` — the D2 contract, nothing more | Payload matches `docs/04-api.md` exactly | `pytest tests/test_prakkie_export.py` |
| 4.7 | Client: week grid, drag between slots, week nav, per-day diner count, leftovers | | 📱 |
| 4.8 | Client: copy-previous-week button, prominent | | 📱 |
| 4.9 | Client: shopping list grouped by shelf, optimistic checkbox writes queued in MMKV, flushed on reconnect | Airplane mode ticking persists and syncs later | 📱 |
| 4.10 | Client: Prakkie deeplink button | | 📱 |
| 4.11 | **Gate:** plan a real week, shop from the list in an actual supermarket | **Phase 4 gate** | Human |

---

## Phase 5 — Groups and Discover

| ID | Task | Acceptance | Verify |
|---|---|---|---|
| 5.1 | Migration 005: `groups`, `group_members`, `group_recipes`, `group_reactions`, `devices` | | `alembic upgrade head` |
| 5.2 | Groups CRUD, invite code generation, leave, owner-only delete | Non-member gets 403 on group content | `pytest tests/test_groups.py` |
| 5.3 | `GET /v1/invites/{code}` **unauthenticated** preview: name, member count, 3 thumbnails, nothing personal | No auth required; no emails leaked | `pytest tests/test_invites.py` |
| 5.4 | Share to group; `POST .../save` creates an owned copy with `origin_recipe_id` | Sharer deleting theirs leaves copies intact | `pytest tests/test_group_share.py` |
| 5.5 | Reactions, cooked-with-photo, report endpoint | | `pytest tests/test_reactions.py` |
| 5.6 | Discover: curated row from a JSON blob, group activity, seasonal month→tag map (hardcoded) | Curated content editable without a deploy | `pytest tests/test_discover.py` |
| 5.7 | Client: groups list, create, detail, invite link + QR | | 📱 |
| 5.8 | Client: Discover tab | | 📱 |
| 5.9 | 🔑 Push: device registration, Expo push, evening meal reminder, defrost reminder, group activity | Notification arrives on a real device | 📱 |

---

## Phase 6 — Monetisation and launch prep

| ID | Task | Acceptance | Verify |
|---|---|---|---|
| 6.1 | Migration 006: `subscriptions` | | `alembic upgrade head` |
| 6.2 | **[B]** Quota: derived count on rolling 30 days (free) / billing period (premium). `counted_against_quota` set at `ready_for_review` in the same transaction | Failures and cancels never count; duplicates never count | `pytest tests/test_quota.py` |
| 6.3 | Quota check before any paid call; `GET /v1/me/quota` with `resets_at` | Exhausted quota returns `quota_exceeded` + paywall payload | `pytest tests/test_quota_enforce.py` |
| 6.4 | 🔑 RevenueCat webhook, **signature-verified**, entitlement sync, grace period, refund downgrade | Unsigned request rejected | `pytest tests/test_revenuecat.py` |
| 6.5 | 🔑 Client: RevenueCat SDK, paywall with price, subscribe, **restore purchases**, terms + privacy links | Apple's required elements all present | 📱 |
| 6.6 | Paywall triggers: quota wall, profile card, soft notice at import 8/10 | Soft notice dismissible | 📱 |
| 6.7 | Rate limiting (Postgres-backed): imports 5/min 30/hr, writes 120/min, reads 600/min, `Retry-After` | | `pytest tests/test_rate_limit.py` |
| 6.8 | Onboarding: household size, diet + allergies with **explicit Article 9 consent**, live demo import | Allergy consent separate from terms acceptance | 📱 |
| 6.9 | `GET /v1/me/export` (JSON bundle) and `DELETE /v1/me` (hard delete + blobs + Clerk + RevenueCat; keeps `source_cache`) | Deleted user's rows gone, cache intact | `pytest tests/test_gdpr.py` |
| 6.10 | Empty states for every main screen | | Visual |
| 6.11 | Accessibility pass: Dynamic Type, 44pt targets, Dutch `accessibilityLabel`, VoiceOver on each main screen | Provenance never colour-alone | 📱 VoiceOver |
| 6.12 | 🔑 Legal pages live, DPAs signed, privacy statement lists every sub-processor | URLs resolve | Manual |
| 6.13 | 🔑 Store metadata, screenshots, reviewer notes **written before submission**, demo account seeded, sandbox subscription | Reviewer can import without signing up with Google | Manual |

---

## Phase 7 — Beta and launch

| ID | Task | Acceptance |
|---|---|---|
| 7.1 | TestFlight + Play internal testing, 20–30 users, ideally households |
| 7.2 | Watch `import_started → import_completed → import_saved`. Fix the top 3 drop-off causes |
| 7.3 | Prompt iteration against real failures using the eval corpus |
| 7.4 | 🔑 Submit. Assume one rejection round |

---

## Dependency summary

The tasks that block the most downstream work, in order: **0.2**, **0.8**, **0.11**, **1.4**, **1.6**,
**1.8**, **1.16**, **2.2**, **2.9**, **3.11**, **4.3**, **6.2**.

If any of those is shaky, stop and fix it rather than building on it.
