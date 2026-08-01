# 02 — Data Model

Postgres 16 on Flexible Server. SQLAlchemy 2.0 models, Alembic migrations.

## Two structural decisions first

**Recipes are per-user copies, not shared mutable rows.** When you save a recipe from a group, you get
your own copy with `origin_recipe_id` pointing at the source. This costs storage and duplicates data,
and it buys you an enormous amount: no multi-tenant edit conflicts, no permission checks on every
field, no "someone changed the recipe I planned for Thursday". For a consumer app with small groups
this is the right trade.

**Deduplication happens at the parse layer, not the recipe layer.** A `source_cache` row keyed by
normalised source URL stores the raw AI parse result. Three users importing the same viral TikTok
produce three recipe rows but only one paid pipeline run. This is where your margin comes from — see
`06-monetisation.md`.

## Enums

Fixed enums, per D4. Store the machine value; the Dutch label lives in the client.

```sql
CREATE TYPE unit AS ENUM (
  'g','kg','ml','l','el','tl','stuk','snuf','teentje','bosje',
  'blikje','pakje','plak','handvol','naar_smaak'
);

CREATE TYPE shelf_category AS ENUM (
  'groente_fruit','vlees_vis','zuivel_eieren','brood_bakkerij',
  'houdbaar','kruiden_specerijen','diepvries','dranken','overig'
);

CREATE TYPE provenance AS ENUM ('explicit','derived','estimated','missing');
-- explicit  = green  : literally said or shown in the source
-- derived   = yellow : converted or inferred from something explicit
-- estimated = yellow : filled in by the model with no source support
-- missing   = red    : absent, user must supply

CREATE TYPE meal_type AS ENUM ('ontbijt','lunch','diner','tussendoor');

CREATE TYPE source_platform AS ENUM (
  'tiktok','instagram','youtube','pinterest','web','photo_ocr','manual'
);

CREATE TYPE import_status AS ENUM (
  'queued','fetching','synthesizing',
  'ready_for_review','saved','failed','cancelled'
);

CREATE TYPE plan_tier AS ENUM ('free','premium');
CREATE TYPE group_role AS ENUM ('owner','member');
CREATE TYPE difficulty AS ENUM ('makkelijk','gemiddeld','uitdagend');
```

`naar_smaak` in the unit enum matters more than it looks: "peper en zout naar smaak" is in half of all
recipes and needs somewhere to go that isn't a fake number.

## Core tables

### users

```sql
CREATE TABLE users (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clerk_user_id     TEXT UNIQUE NOT NULL,
  email             TEXT,
  email_verified    BOOLEAN NOT NULL DEFAULT FALSE,
  display_name      TEXT,
  avatar_url        TEXT,
  household_size    SMALLINT NOT NULL DEFAULT 2,
  locale            TEXT NOT NULL DEFAULT 'nl-NL',
  tier              plan_tier NOT NULL DEFAULT 'free',
  trial_started_at  TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at        TIMESTAMPTZ
);
CREATE INDEX ON users (email) WHERE deleted_at IS NULL;
```

`email` is nullable on purpose — Apple Private Relay users may not give you a usable one, and D12
accepts that. `deleted_at` supports the AVG deletion flow (`07-legal-avg.md`).

### user_preferences

Split from `users` because it's written from a different screen and read on every recipe render.

```sql
CREATE TABLE user_preferences (
  user_id            UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  diets              TEXT[] NOT NULL DEFAULT '{}',      -- vega, vegan, halal, glutenvrij
  allergens          TEXT[] NOT NULL DEFAULT '{}',      -- noten, lactose, gluten, ...
  default_servings   SMALLINT NOT NULL DEFAULT 2,
  show_original_units BOOLEAN NOT NULL DEFAULT TRUE,
  fan_oven_default   BOOLEAN NOT NULL DEFAULT TRUE,
  notif_cooking      BOOLEAN NOT NULL DEFAULT TRUE,
  notif_defrost      BOOLEAN NOT NULL DEFAULT TRUE,
  notif_group        BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Allergens as a text array rather than a lookup table: you need them for a client-side warning banner,
not for analytics. Keep it simple until it isn't.

### recipes

```sql
CREATE TABLE recipes (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  origin_recipe_id  UUID REFERENCES recipes(id) ON DELETE SET NULL,
  import_id         UUID REFERENCES imports(id) ON DELETE SET NULL,

  title             TEXT NOT NULL,
  description       TEXT,
  image_blob_path   TEXT,
  meal_types        meal_type[] NOT NULL DEFAULT '{}',
  servings          SMALLINT NOT NULL DEFAULT 2,
  prep_minutes      SMALLINT,
  cook_minutes      SMALLINT,
  difficulty        difficulty,
  kcal_per_serving  SMALLINT,

  -- attribution, always shown (see 07-legal-avg.md)
  source_platform   source_platform NOT NULL,
  source_url        TEXT,
  source_url_norm   TEXT,
  source_author     TEXT,
  source_title      TEXT,

  notes             TEXT,          -- user's own "next time less salt"
  is_archived       BOOLEAN NOT NULL DEFAULT FALSE,
  cooked_count      INTEGER NOT NULL DEFAULT 0,
  last_cooked_at    TIMESTAMPTZ,

  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at        TIMESTAMPTZ
);

CREATE INDEX ON recipes (user_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX ON recipes (user_id, source_url_norm);          -- duplicate-import detection
CREATE INDEX ON recipes USING GIN (to_tsvector('dutch', title || ' ' || coalesce(description,'')));
```

Note `to_tsvector('dutch', ...)` — Postgres ships a Dutch stemmer, use it. And `source_url_norm` is
what powers your spec's "Je hebt dit recept al" screen.

### recipe_ingredients

The most important table in the schema. This is also the Prakkie export contract (D2).

```sql
CREATE TABLE recipe_ingredients (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipe_id         UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  position          SMALLINT NOT NULL,
  section           TEXT,                -- "Voor de saus", optional grouping

  amount            NUMERIC(10,2),       -- NULL for naar_smaak
  amount_max        NUMERIC(10,2),       -- for ranges: "1-2 eieren"
  unit              unit,
  name_nl           TEXT NOT NULL,       -- canonical Dutch name, merge key
  qualifier         TEXT,                -- "fijngesneden", "op kamertemperatuur"
  category          shelf_category NOT NULL DEFAULT 'overig',
  optional          BOOLEAN NOT NULL DEFAULT FALSE,

  -- provenance and reversibility
  raw_text          TEXT NOT NULL,       -- exactly as it appeared in the source
  original_amount   NUMERIC(10,2),       -- "2" from "2 cups"
  original_unit     TEXT,                -- "cups" — free text, source-side only
  provenance        provenance NOT NULL DEFAULT 'explicit',

  UNIQUE (recipe_id, position)
);
CREATE INDEX ON recipe_ingredients (recipe_id);
CREATE INDEX ON recipe_ingredients (name_nl);
```

Three fields here carry disproportionate weight:

- **`raw_text`** is what makes conversions reversible and auditable. Never discard the original string.
  It's also your only debugging tool when a parse goes wrong three weeks later.
- **`original_unit` is free text while `unit` is an enum.** That asymmetry is deliberate: the source
  can say anything, your output cannot.
- **`provenance`** is what the review screen renders as a coloured dot. It is the trust mechanism in the
  product now that there's no jump-to-source — so the honesty of this field matters more than any other.

### recipe_steps

```sql
CREATE TABLE recipe_steps (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipe_id         UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  position          SMALLINT NOT NULL,
  text              TEXT NOT NULL,          -- always AI-rewritten, never copied verbatim
  timer_seconds     INTEGER,                -- detected "20 min sudderen"
  temperature_c     SMALLINT,
  temperature_fan_c SMALLINT,               -- computed, conventionally 20 °C lower
  ingredient_ids    UUID[] NOT NULL DEFAULT '{}',  -- for cook mode's per-step ingredient list
  provenance        provenance NOT NULL DEFAULT 'explicit',
  UNIQUE (recipe_id, position)
);
```

`ingredient_ids` denormalises the step↔ingredient link into an array rather than a join table. Cook
mode reads it on every screen and never writes it; an array is the right shape.

### collections

```sql
CREATE TABLE collections (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  emoji      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE collection_recipes (
  collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
  recipe_id     UUID REFERENCES recipes(id) ON DELETE CASCADE,
  added_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (collection_id, recipe_id)
);
```

### cook_logs

```sql
CREATE TABLE cook_logs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipe_id       UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  cooked_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  photo_blob_path TEXT,
  rating          SMALLINT CHECK (rating BETWEEN 1 AND 5),
  note            TEXT,
  shared_group_id UUID REFERENCES groups(id) ON DELETE SET NULL
);
CREATE INDEX ON cook_logs (recipe_id, cooked_at DESC);
```

## Import tables

### source_cache

The cost-control table. Read this before every paid pipeline run.

```sql
CREATE TABLE source_cache (
  url_norm        TEXT PRIMARY KEY,
  platform        source_platform NOT NULL,
  raw_payload     JSONB NOT NULL,     -- Apify response, transcript, page HTML extract
  parsed_recipe   JSONB NOT NULL,     -- the model's structured output
  model           TEXT NOT NULL,
  prompt_version  SMALLINT NOT NULL,
  cost_eur_cents  NUMERIC(8,4),
  hit_count       INTEGER NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at      TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '180 days'
);
CREATE INDEX ON source_cache (expires_at);
```

`prompt_version` is what lets you invalidate selectively when you improve the prompt, instead of
throwing away every cached parse. Bump it, and cache entries below the current version are treated as
misses for new imports while existing recipes stay untouched.

### imports

```sql
CREATE TABLE imports (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status            import_status NOT NULL DEFAULT 'queued',
  platform          source_platform NOT NULL,
  source_url        TEXT,
  source_url_norm   TEXT,

  draft             JSONB,             -- editable review payload before save
  recipe_id         UUID REFERENCES recipes(id) ON DELETE SET NULL,

  cache_hit         BOOLEAN NOT NULL DEFAULT FALSE,
  counted_against_quota BOOLEAN NOT NULL DEFAULT FALSE,
  cost_eur_cents    NUMERIC(8,4),
  duration_ms       INTEGER,
  error_code        TEXT,
  error_detail      TEXT,

  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at      TIMESTAMPTZ
);
CREATE INDEX ON imports (user_id, created_at DESC);
CREATE INDEX ON imports (user_id, counted_against_quota, created_at)
  WHERE counted_against_quota;
```

That last partial index is the one your quota check hits on every single import. Get it right.

### import_events

Powers the five-step progress screen and gives you per-stage timing telemetry for free.

```sql
CREATE TABLE import_events (
  id         BIGSERIAL PRIMARY KEY,
  import_id  UUID NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
  stage      TEXT NOT NULL,       -- fetch, synthesize
  state      TEXT NOT NULL,       -- started, done, failed, skipped
  detail     TEXT,
  at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON import_events (import_id, id);
```

## Planner and shopping

### plan_entries

```sql
CREATE TABLE plan_entries (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date          DATE NOT NULL,
  slot          meal_type NOT NULL,
  position      SMALLINT NOT NULL DEFAULT 0,   -- multiple dishes per slot
  recipe_id     UUID REFERENCES recipes(id) ON DELETE CASCADE,
  custom_label  TEXT,                          -- "afhalen", "restjes"
  servings      SMALLINT,                      -- overrides recipe servings
  is_leftover_of UUID REFERENCES plan_entries(id) ON DELETE SET NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON plan_entries (user_id, date);
CREATE UNIQUE INDEX ON plan_entries (user_id, date, slot, position);
```

`is_leftover_of` implements the cook-double-on-Saturday-eat-it-Monday feature, and importantly means
leftovers are **excluded from the shopping list** — they're already bought.

### shopping_lists and items

```sql
CREATE TABLE shopping_lists (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  week_start    DATE NOT NULL,
  generated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, week_start)
);

CREATE TABLE shopping_list_items (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  list_id       UUID NOT NULL REFERENCES shopping_lists(id) ON DELETE CASCADE,
  name_nl       TEXT NOT NULL,        -- merge key, per D5
  amount        NUMERIC(10,2),
  unit          unit,
  category      shelf_category NOT NULL DEFAULT 'overig',
  is_checked    BOOLEAN NOT NULL DEFAULT FALSE,
  checked_at    TIMESTAMPTZ,
  checked_by    UUID REFERENCES users(id) ON DELETE SET NULL,
  is_manual     BOOLEAN NOT NULL DEFAULT FALSE,
  source_recipe_ids UUID[] NOT NULL DEFAULT '{}',  -- "uit: Pasta pesto, Curry"
  client_id     TEXT,                  -- idempotency key for optimistic local writes
  UNIQUE (list_id, name_nl, unit)
);
CREATE INDEX ON shopping_list_items (list_id, category);
```

`client_id` is what makes D11's optimistic checkbox writes safe: the client generates it, retries are
idempotent, and a flaky supermarket connection can't produce duplicate rows.

Merging rule: group plan entries for the week → expand each recipe's ingredients scaled to the
entry's servings → exclude pantry items → group by `(name_nl, unit)` → sum `amount`. Mixed units for
the same name (200 g bloem + 1 pakje bloem) stay separate lines. Don't be clever here.

### pantry_items

```sql
CREATE TABLE pantry_items (
  user_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name_nl  TEXT NOT NULL,
  PRIMARY KEY (user_id, name_nl)
);
```

Seed it on onboarding with zout, peper, olijfolie, bloem, suiker, azijn. This is a one-line feature
that visibly improves every shopping list, so it's worth doing in v1.

## Groups

```sql
CREATE TABLE groups (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  description TEXT,
  emoji       TEXT,
  color       TEXT,
  created_by  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  invite_code TEXT UNIQUE NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE group_members (
  group_id  UUID REFERENCES groups(id) ON DELETE CASCADE,
  user_id   UUID REFERENCES users(id) ON DELETE CASCADE,
  role      group_role NOT NULL DEFAULT 'member',
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (group_id, user_id)
);

CREATE TABLE group_recipes (
  group_id   UUID REFERENCES groups(id) ON DELETE CASCADE,
  recipe_id  UUID REFERENCES recipes(id) ON DELETE CASCADE,
  shared_by  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  shared_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (group_id, recipe_id)
);
CREATE INDEX ON group_recipes (group_id, shared_at DESC);

CREATE TABLE group_reactions (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id   UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  recipe_id  UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  emoji      TEXT,
  comment    TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Shared recipes stay owned by the sharer. Another member saving it creates their own copy with
`origin_recipe_id` set. If the sharer deletes theirs, the copies survive — which is what users expect
and what the cascade above gives you.

## Subscription and quota

```sql
CREATE TABLE subscriptions (
  user_id            UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  rc_app_user_id     TEXT UNIQUE,
  store              TEXT,                    -- app_store, play_store
  product_id         TEXT,
  entitlement_active BOOLEAN NOT NULL DEFAULT FALSE,
  period_start       TIMESTAMPTZ,
  period_end         TIMESTAMPTZ,
  in_grace_period    BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Quota is **derived, not stored as a counter.** Counting rows in `imports` where
`counted_against_quota` is true within the current window is cheap with the partial index above, and
it can never drift out of sync the way a denormalised counter does. Full accounting rules in
`06-monetisation.md`.

## Devices

```sql
CREATE TABLE devices (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expo_push_token TEXT UNIQUE NOT NULL,
  platform    TEXT NOT NULL,
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Needed for the morning "vanavond eet je X" and defrost reminders, and for background imports if you
adopt ADR-009 in v2.

## Migration conventions

- Alembic, one migration per PR, autogenerate then **always hand-edit** — autogenerate gets enums and
  indexes wrong.
- Expand/contract for anything destructive: add nullable column → backfill → start writing → make
  non-null in a later release. Never in one step, because an OTA JS update and an API deploy are not
  atomic with each other.
- Adding an enum value is safe and non-blocking in PG 12+. Removing one is not — treat enum values as
  append-only forever.
- Every table gets `created_at`. Anything user-generated gets `updated_at`. Anything personal gets
  `deleted_at` rather than a hard delete, except on an AVG erasure request.
