# 13 — Build Tasks

Atomic, dependency-ordered tasks. Each has an ID, acceptance criteria, and a verification command.

**Rules for the agent:**
- Work in ID order unless a task says otherwise
- A task is done only when its acceptance criteria hold *and* the verify command runs green
- Tasks marked 🔑 need a credential or a human action — stop and ask, naming exactly what you need.
  Check `secrets/` first: the OpenAI key, Apify token, Apple `.p8` and Google client secrets are
  already there
- Tasks marked 📱 need a physical device
- Commit after each task: `feat(scope): description` referencing the task ID
- **Before building any screen, open `docs/prototype/Receptenapp.dc.html` and find it.** Tokens give you
  the values; the prototype gives you the layout

Legend: **[P]** parallelisable with the previous task · **[B]** blocks a lot downstream

---

## How this list is ordered (read once)

**Reordered 2026-08-03 to put a working MVP first.** The previous ordering was
phase-by-phase-by-layer: the whole import pipeline hardened before any screen existed, planner
before groups, monetisation last. It was defensible on paper and wrong in practice — it front-loaded
plumbing that is *known* to work (migrations, caching, circuit breakers) ahead of the two things
that are genuinely uncertain: whether the AI produces recipes good enough to cook from, and whether
the app feels like the prototype. Neither of those gets answered by a correct Alembic file.

So: **Phase M is a vertical slice.** Share a TikTok → get a correct Dutch recipe → it is in your
library → you can cook from it, in the real UI. Everything in M exists to make that one loop real.

Deliberately deferred, and why:

| Deferred | Why it can wait |
|---|---|
| `source_cache` | A cost optimisation. Re-importing during development pays OpenAI twice; that is pennies until there are users |
| Circuit breakers, rate limiting | Protect against load we do not have |
| `scripts/eval.py`, prompt hardening | Needs a real corpus of failures, which needs real imports first |
| Telemetry, alerts | Nothing to observe yet |
| Quota, paywall, RevenueCat | Nothing worth paying for until the loop works |
| Groups, Discover, planner, shopping list | Real product value, but none of it exists without recipes in a library first |

The old ordering is in git history if any of this needs revisiting. **Phase 0 is complete.**

---

## Phase M — MVP: one recipe, end to end

The gate: **share a TikTok from the TikTok app, and end up looking at a correct Dutch recipe in your
own library.** Nothing in this phase is optional to that sentence.

### M-A — Make a recipe exist (server)

| ID | Task | Acceptance | Verify |
|---|---|---|---|
| ~~M1~~ | ~~Apply migration 002.~~ **Done 2026-08-03.** Verified upgrade → downgrade → upgrade on a scratch DB, then applied to `receptenapp_dev` | Round-trip clean; enums survive the downgrade (they belong to 001) | `uv run alembic upgrade head` |
| ~~M2~~ | ~~Migration 003: `imports`, `import_events`, the deferred `recipes.import_id` FK, and `recipes.field_provenance`.~~ **Done 2026-08-03.** Round-tripped down and back up against the real database | Upgrade + downgrade clean | `uv run alembic upgrade head` |
| ~~M3~~ | **[B]** ~~`EvidenceBundle`, the one structure every source collapses into.~~ **Done 2026-08-03** | Round-trips through Pydantic | `pytest tests/test_evidence.py` |
| ~~M4~~ | ~~Blog extractor: JSON-LD → microdata → WP Recipe Maker, in that order of trust.~~ **Done 2026-08-03**, plus M4b (fetches a live URL) and a plain page-text fallback, because blog markup is not consistent | 6 saved Dutch/English blog fixtures produce an EvidenceBundle | `pytest tests/test_blog_extract.py` |
| ~~M5~~ | **[B]** ~~Apify provider behind an interface.~~ **Done 2026-08-03.** Uses `run-sync-get-dataset-items`; validation at the boundary | Malformed response raises at the boundary, not three layers down | `pytest tests/test_apify_normalise.py` |
| ~~M6~~ | 🔑 ~~Save one raw Apify payload each for TikTok, Reel and YouTube.~~ **Done 2026-08-03** — normalisers are written against real shapes, never guessed ones | Three real payloads committed | Files exist |
| ~~M7~~ | ~~Per-actor normalisers → EvidenceBundle.~~ **Done 2026-08-03.** 6 of 8 real URLs produce evidence; the two allrecipes links are `source_blocked` by the publisher and stay that way — see docs/03 | The three fixtures normalise correctly | `pytest tests/test_apify_normalise.py` |
| ~~M8~~ | **[B]** ~~OpenAI provider behind an interface (ADR-005), model and `PROMPT_VERSION` pinned in config.~~ **Done 2026-08-03.** Raw httpx to match the Apify provider; no `openai` dependency | Schema-valid output on a fixture; provider swappable | `pytest tests/test_openai_provider.py` |
| ~~M9~~ | ~~Synthesis prompt v1, verbatim from `docs/11-prompts.md` including the few-shot.~~ **Done 2026-08-03.** Loaded by version from `services/prompts/`; an unknown version raises rather than falling back | Prompt loaded from a versioned module, not inline | `pytest tests/test_prompt_version.py` |
| M9b | *Laat AI aanvullen* as a **separate second call**, run only when the user asks. Fills only the missing fields, marks every one `estimated` | Default import spends nothing on guessing; user-consented guesses are attributable | `pytest tests/test_enrich.py` |
| ~~M10~~ | **[B]** ~~Validation: clamps, rounding, dedupe, min-viability.~~ **Done 2026-08-03.** Closes both gaps the real TikTok exposed: `servings: 18` is dropped rather than clamped, and a measure with no amount loses its unit. Also merges duplicate ingredients, marking the sum `derived` | Rules in §2.5 covered | `pytest tests/test_validation.py` |
| ~~M11~~ | ~~Import service: route → fetch → synthesise → validate → draft.~~ **Done 2026-08-03.** Foreground, in-process, no queue (ADR-009). Quota enforced *before* the first paid call; `counted_against_quota` set only on reaching `ready_for_review`, so a failed import is not charged | Draft lands in `imports.draft`, nothing in `recipes` yet | `pytest tests/test_import_flow.py` |
| ~~M12~~ | ~~`POST /v1/imports`, `GET /v1/imports/{id}`, `PATCH .../draft`, `POST .../save`.~~ **Done 2026-08-03.** 202 + polling rather than SSE (that is H2). Save is idempotent; a duplicate URL is 409 before anything is spent | Save produces a complete recipe owned by the caller | `pytest tests/test_import_flow.py` |
| ~~M13~~ | ~~`GET /v1/recipes`, `GET /v1/recipes/{id}`.~~ **Done 2026-08-03** | Detail returns ingredients, steps, provenance, attribution | `pytest tests/test_recipes_api.py` |
| ~~M14~~ | ~~**Server gate:** one script imports a real TikTok and a real blog end to end and prints the recipe.~~ **Done 2026-08-03.** A leukerecepten page and a spoken-English TikTok both came back as correct Dutch, with `1 lb` → `454 g` marked `derived`. `--save-for` writes into a library | Both produce something you would cook | `uv run python scripts/try_import.py <url> --synthesise` |

### M-B — Make it look like the prototype (client)

| ID | Task | Acceptance | Verify |
|---|---|---|---|
| ~~M15~~ | **[B]** ~~Component library from the prototype.~~ **Done 2026-08-03.** No dev gallery screen — the real screens are the check | Matches the prototype | Visual |
| ~~M16~~ | ~~Tab shell matching the prototype's bottom bar.~~ **Done 2026-08-03.** The centre import button is not a tab and has no active state | Tabs navigate, correct icons and Dutch labels | 📱 |
| ~~M17~~ | ~~Import flow: paste + clipboard detection, progress, review variant A.~~ **Done 2026-08-03.** Progress renders real `import_events` rows, not a timer. Ingredient edits PATCH on blur, scalars debounced. No *Laat AI aanvullen* button until M9b exists | Every review edit PATCHes debounced | 📱 |
| ~~M18~~ | ~~Library screen + recipe detail.~~ **Done 2026-08-03** | Detail renders ingredients, steps, provenance dots, source attribution | 📱 |
| M19 | Onboarding (household size, diet + allergens with explicit Article 9 consent) + profile screen. Profile exists; onboarding does not | Allergy consent is separate from terms acceptance | 📱 |
| M20 | Android share intent for text/URL, and the URL survives sign-in | Share from TikTok → app opens → recipe imports | 📱 |
| M21 | Cook mode — **mostly done 2026-08-03**: dark, keep-awake, one step per page, per-step ingredient pills. **Outstanding: the timer.** The chip shows a step's duration but starts nothing, because a timer that forgets across backgrounding is worse than none | Timer survives backgrounding for 5 min | 📱 |
| M22 | **MVP GATE:** share a TikTok from TikTok on a fresh install, sign in, land on the recipe, cook from it | 📱 | Human |

---

## Phase N — the rest of the prototype

Everything the prototype shows that the MVP loop does not need.

| ID | Task | Verify |
|---|---|---|
| N1 | Search: Dutch `tsvector` + `pg_trgm`, `?q=` and `?ingredient=` | `pytest tests/test_search.py` |
| N2 | Recipe CRUD: full-replace ingredients/steps, soft delete, duplicate | `pytest tests/test_recipe_crud.py` |
| N3 | Collections API + client | `pytest tests/test_collections.py` |
| N4 | Cursor pagination on `(created_at, id)`, filters, sort, multi-select | `pytest tests/test_pagination.py` |
| N5 | Cook logs with photo + rating, blob SAS issuance | `pytest tests/test_blob.py` |
| N6 | Migration 004 + planner API (week, entries, copy-week) | `pytest tests/test_planner.py` |
| N7 | **[B]** Shopping list generation: expand → scale → exclude pantry → exclude leftovers → merge on `(name_nl, unit)` → group by shelf | `pytest tests/test_shopping_gen.py` |
| N8 | Regeneration preserves check state for surviving `(name_nl, unit)` pairs | `pytest tests/test_shopping_regen.py` |
| N9 | Planner + shopping list screens | 📱 |
| N10 | Prakkie export (`docs/04-api.md` contract, nothing more) + deeplink button | `pytest tests/test_prakkie_export.py` |
| N11 | Migration 005 + groups, invites, share-to-group, reactions | `pytest tests/test_groups.py` |
| N12 | Discover tab: curated JSON blob, group activity, seasonal tags | `pytest tests/test_discover.py` |
| N13 | Groups + Discover screens | 📱 |
| N14 | iOS share extension + App Group | 📱 |
| N15 | Persisted TanStack Query cache in MMKV + `expo-image` disk cache | 📱 airplane mode |

---

## Phase H — hardening and professionalisation

Everything pulled out of the original ordering. None of it is optional before launch; all of it is
premature before the MVP works.

| ID | Task | Verify |
|---|---|---|
| H1 | `source_cache` read-before-spend + write-after-parse, keyed on `url_norm` + `prompt_version` | `pytest tests/test_cache.py` |
| H2 | SSE `GET /v1/imports/{id}/events`, polling fallback documented | `curl -N` |
| H3 | Per-platform circuit breaker: 5 failures → open 10 min | `pytest tests/test_circuit_breaker.py` |
| H4 | Full failure taxonomy with distinct Dutch copy, written in one sitting | `pytest tests/test_error_copy.py` |
| H5 | `silent_video` detection → prefilled manual entry | `pytest tests/test_silent_video.py` |
| H6 | Fixture corpus: 40 EvidenceBundles incl. deliberately awful ones | `pytest tests/test_corpus_loads.py` |
| H7 | `scripts/eval.py` with the 9 assertions in `docs/11-prompts.md` | `uv run python scripts/eval.py --prompt-version 1` |
| H8 | Prompt hardening against the corpus; bump `PROMPT_VERSION` per semantic change | eval diff |
| H9 | **[B]** Quota: derived count, rolling 30 days / billing period, `counted_against_quota` set at `ready_for_review` in the same transaction | `pytest tests/test_quota.py` |
| H10 | Quota enforced before any paid call; `GET /v1/me/quota` | `pytest tests/test_quota_enforce.py` |
| H11 | 🔑 RevenueCat webhook, signature-verified, entitlement sync, grace, refund | `pytest tests/test_revenuecat.py` |
| H12 | 🔑 RevenueCat SDK, paywall, restore purchases, terms + privacy links | 📱 |
| H13 | Paywall triggers: quota wall, profile card, soft notice at 8/10 | 📱 |
| H14 | Rate limiting (Postgres-backed), `Retry-After` | `pytest tests/test_rate_limit.py` |
| H15 | Telemetry: one event per import (platform, per-stage ms, tokens, cost, outcome) | App Insights |
| H16 | 🔑 Daily-spend alert, 5xx / failure-rate / p95 alerts | Azure alert test |
| H17 | `GET /v1/me/export`, `DELETE /v1/me` (hard delete + blobs + Clerk + RevenueCat, keeps `source_cache`) | `pytest tests/test_gdpr.py` |
| H18 | Accessibility: Dynamic Type, 44pt targets, Dutch labels, VoiceOver | 📱 VoiceOver |
| H19 | Empty states for every screen | Visual |
| H20 | 🔑 Legal pages live, DPAs signed, sub-processors listed | Manual |
| H21 | 🔑 Store metadata, screenshots, reviewer notes, demo account, sandbox subscription | Manual |
| H22 | TestFlight + Play internal testing, 20–30 users | — |
| H23 | Watch `import_started → completed → saved`; fix the top 3 drop-offs | — |
| H24 | 🔑 Submit. Assume one rejection round | — |

---

## Dependency summary

Within the MVP, the tasks that block the most: **M3** (EvidenceBundle), **M5** (Apify provider),
**M8** (OpenAI provider), **M10** (validation), **M15** (component library).

If any of those is shaky, stop and fix it rather than building on it.
