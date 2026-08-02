# CLAUDE.md

Instructions for Claude Code working in this repository. Read this before touching anything.

## What this is

**Kladje** — a Dutch mobile app that imports recipes from social media and blogs, normalises them
to Dutch ingredients and metric units, and provides week planning, a price-free shopping list, and
sharing in small groups.

Full plan in `docs/`. Read `docs/00-scope.md` and `docs/03-import-pipeline.md` before your first task.
`docs/09-decisions-adr.md` explains why things are the way they are — **read the relevant ADR before
proposing a change to an architectural decision.**

## Stack

- **API**: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2. `uv` for deps, Ruff for lint and
  format, pytest for tests
- **Client**: Expo / React Native, TypeScript, Expo Router, TanStack Query, Zustand, MMKV
- **Infra**: Azure App Service (Linux container), PostgreSQL Flexible Server, Blob Storage, Key Vault,
  Bicep. Region West Europe
- **External**: Clerk (auth), Apify (scraping), OpenAI (synthesis), RevenueCat (subscriptions)

## Repository layout

```
api/          FastAPI service
  src/receptenapp/
    api/          routers, one file per resource
    core/         config, security, deps
    db/           models, session
    services/     business logic — NOT in routers
    providers/    apify/, openai/, storage/ — external boundaries
    schemas/      Pydantic request/response models
  migrations/     Alembic
  tests/
app/          Expo client
docs/         The plan. Source of truth for intent
  prototype/    Receptenapp.dc.html — the clickable prototype. VISUAL SOURCE OF TRUTH
infra/        Bicep
scripts/      eval.py, seed.py, dev tooling
```

## Non-negotiables

Violating any of these is a bug even if the code works.

1. **No secrets in the repo.** Ever. Config comes from environment variables; production values come
   from Key Vault via App Service settings. `.env` is gitignored. If you find a secret committed, stop
   and tell the user
2. **Every query filters by the authenticated user's id.** There is no shared data in this app except
   `source_cache`. A query without a user filter is a data leak
3. **`unit` and `category` are enums.** Never accept or emit free text for these. See ADR-013
4. **Method step text is always AI-rewritten**, never copied from the source. Legal requirement, see
   `docs/07-legal-avg.md`
5. **Never invent recipe values.** Missing means null plus `missing` provenance. See `docs/11-prompts.md`
6. **No browser storage APIs in the client** — no localStorage/sessionStorage. Use MMKV
7. **Quota is enforced server-side**, checked before any paid API call
8. **No supermarket data, prices, or product matching anywhere.** That's Prakkie. See ADR-001
9. **No OCR or vision anywhere in v1.** Cookbook-photo import is deferred to v2 — a real cost driver
   with no user base yet to justify it. See the 2026-08-02 update to ADR-014
10. **Model name and prompt version are pinned in config**, never hardcoded at a call site, never
    silently changed. See ADR-011
11. **Match the prototype.** Before building any screen, open `docs/prototype/Receptenapp.dc.html` and
    find that screen. It is inline-styled and readable — the exact paddings, weights, orders and
    wording are in there. Use `docs/14-design-tokens.md` for the values and the prototype for the
    layout. Do not invent a layout for a screen the prototype already has

## Conventions

**Python**
- Line length 100. Ruff for both lint and format; run `ruff check --fix && ruff format` before finishing
- Full type annotations. `mypy --strict` on `services/` and `providers/`
- Async throughout. No sync DB calls in request handlers
- Routers are thin: validate, call a service, return. Business logic lives in `services/`
- External calls go through `providers/`, always behind an interface. Never call `openai` or `apify`
  directly from a service
- Custom exceptions in `core/errors.py`, mapped to the error contract in `docs/04-api.md` by one
  handler. Don't build error responses inline

**TypeScript**
- Strict mode. No `any` — use `unknown` and narrow
- Server state in TanStack Query; local UI state in Zustand. Don't mix
- Components in `src/components/` are presentational. Data fetching lives in screens
- All user-facing strings in `src/strings/nl.ts`. No string literals in JSX

**Database**
- One Alembic migration per change. Autogenerate then **always hand-edit** — autogenerate mishandles
  enums and indexes
- Expand/contract for destructive changes. Never drop or rename a column in the same release as the
  code change that needs it
- Enum values are append-only forever
- Every table has `created_at`. User-generated tables have `updated_at`. Personal data has `deleted_at`

**Git**
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- One logical change per commit
- Never commit generated files, `.env`, or anything under `secrets/`

## Definition of done

A task is not complete until all of these hold:

- [ ] Code written and passes `ruff check` and `ruff format --check`
- [ ] Type checks pass (`mypy` for Python, `tsc --noEmit` for TS)
- [ ] Tests written for new logic and passing
- [ ] Migration created and applied cleanly against a fresh database
- [ ] The verification command from the task definition runs green
- [ ] No new secrets, no hardcoded URLs, no `TODO` without an issue reference
- [ ] `docs/` updated if behaviour diverges from the plan

## Verification commands

Run these; don't assume.

```bash
# API
cd api
uv run ruff check . && uv run ruff format --check .
uv run mypy src/receptenapp/services src/receptenapp/providers
uv run pytest -q
uv run alembic upgrade head          # against a scratch DB
uv run uvicorn receptenapp.main:app --reload   # smoke

# Client
cd app
npx tsc --noEmit
npm run lint
npx expo start                        # smoke

# Prompt changes
uv run python scripts/eval.py --prompt-version N
```

## Testing policy

- **Never call paid APIs in tests or CI.** Apify and OpenAI are always mocked. Fixtures live in
  `api/tests/fixtures/`
- Services get unit tests. Routers get one happy-path and one auth-failure integration test each
- The import pipeline is tested against saved `EvidenceBundle` fixtures, never live sources
- Prompt changes are validated by `scripts/eval.py`, not by pytest — different tool, different cadence
- Tolerant assertions on model output. Assert flour is 110–140 g per cup, not exactly 125

## When to stop and ask

Stop and ask the user rather than deciding, when:

- A task needs a credential, an account, or a dashboard action (see `docs/12-manual-setup.md`)
- You'd contradict an ADR. Cite the ADR number and make the case; don't just do it
- A schema change would be destructive to existing data
- Apify's actual response shape differs from what the docs assume
- A third-party API returns something the plan didn't anticipate
- The task is ambiguous in a way that would cost more than an hour to redo

Do **not** stop to ask about: naming, file layout within the conventions above, which library to use for
something uncontroversial, or whether to write a test. Decide and move.

## Things that look sensible and are not

Written down because each of these is a decision someone will otherwise re-litigate:

- **Don't add a queue or background worker.** Imports run in-process in the foreground. ADR-009
- **Don't add Redis.** Rate limiting and caching use Postgres. One less thing to run
- **Don't add a sync engine.** v1 is online-only with a persisted read cache. ADR-004
- **Don't add pgvector.** Nothing to embed — there's no catalogue. ADR-001
- **Don't scale-to-zero the API.** Cold start lands on the import progress screen. ADR-008
- **Don't upgrade the model to "improve quality"** without running the eval and checking the cost
  table. ADR-011
- **Don't make the media container public.** Cook-log photos are personal data
- **Don't build an admin UI** for curated content. A JSON file in blob storage is fine for now

## Language

Code, comments, commit messages, docs: English. Everything a user sees: Dutch, informal, "je" not "u".
