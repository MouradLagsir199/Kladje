# 04 — API

FastAPI, REST, JSON. Base path `/v1`. All times ISO 8601 UTC.

## Auth

Clerk issues the JWT; the API verifies it against Clerk's JWKS (cached, refreshed on `kid` miss).
Every request carries `Authorization: Bearer <token>`.

On first authenticated request for an unknown `clerk_user_id`, the API creates the `users` row
just-in-time. Don't rely on Clerk webhooks for user creation — they arrive out of order relative to
the first API call and you'll spend a day debugging a race that JIT creation avoids entirely. Use the
webhook only for deletion and email changes.

Middleware resolves `clerk_user_id` → `users.id` and attaches it to the request. **Every query filters
on that id.** There is no shared data in this app except `source_cache`.

## Error contract

```json
{
  "error": {
    "code": "quota_exceeded",
    "message": "Je hebt je 10 imports van deze maand gebruikt.",
    "details": { "resets_at": "2026-09-01T00:00:00Z", "tier": "free" }
  }
}
```

`code` is a stable machine string the client switches on. `message` is Dutch and displayable as-is —
the API owns user-facing error copy so you can fix wording without a store release.

Status codes: 400 validation, 401 no/bad token, 403 entitlement, 404, 409 conflict/duplicate,
422 semantic, 429 rate limit, 5xx.

## Endpoints

### Session and profile

```
GET    /v1/me                          → user, preferences, tier, quota snapshot
PATCH  /v1/me                          → display_name, household_size
PATCH  /v1/me/preferences              → diets, allergens, defaults, notifications
DELETE /v1/me                          → AVG erasure (see 07-legal-avg.md)
POST   /v1/me/devices                  → register Expo push token
GET    /v1/me/quota                    → { used, limit, resets_at, tier }
```

`GET /v1/me` is the app's boot call. Return everything the client needs to render the first screen in
one round trip: user, preferences, tier, quota, pending-import count, group count.

### Import

```
POST   /v1/imports                     → create; body { url } or { manual: true }
                                         headers: Idempotency-Key
                                         409 if duplicate source_url_norm for this user
GET    /v1/imports/{id}                → status + draft (polling fallback)
GET    /v1/imports/{id}/events         → SSE progress stream
PATCH  /v1/imports/{id}/draft          → partial update of the draft during review
POST   /v1/imports/{id}/enrich         → the "Laat AI aanvullen" second model call
POST   /v1/imports/{id}/save           → materialise draft into recipes; body { plan_entry? }
DELETE /v1/imports/{id}                → discard draft
GET    /v1/imports/pending             → drafts awaiting review
```

`POST /v1/imports/photo` (cookbook OCR) is deferred to v2 along with the rest of that feature — see the
update to ADR-014 in `09-decisions-adr.md`.

`POST /v1/imports` returns `202` immediately with the import id and initial status. It does **not**
block for 30 seconds — the client opens the SSE stream. Even though D10 keeps the import in the
foreground, running it in a background task within the same process and streaming events is what makes
the progress screen possible.

`POST /v1/imports/{id}/save` accepting an optional `plan_entry` implements your spec's "Opslaan en
inplannen" in one round trip.

### Recipes

```
GET    /v1/recipes                     → ?q, meal_type, max_minutes, collection_id,
                                          sort=recent|alpha|time|cooked, cursor, limit
GET    /v1/recipes/{id}                → full recipe with ingredients + steps
POST   /v1/recipes                     → manual creation
PATCH  /v1/recipes/{id}                → metadata, notes
PUT    /v1/recipes/{id}/ingredients    → full replace, ordered
PUT    /v1/recipes/{id}/steps          → full replace, ordered
DELETE /v1/recipes/{id}                → soft delete
POST   /v1/recipes/{id}/duplicate      → own copy
POST   /v1/recipes/{id}/cook-logs      → { cooked_at, photo?, rating?, note?, share_group_id? }
GET    /v1/recipes/{id}/scale?servings=6 → recomputed ingredient amounts
```

`PUT` rather than `PATCH` for ingredients and steps: they're ordered collections that the review
screen edits as a whole, and full replace avoids a whole class of position-reconciliation bugs.

`/scale` as a server endpoint is optional — the client can do the arithmetic. Put it on the server
anyway, because the sensible-rounding rules ("1–2 eieren") are the same rules the import pipeline uses
and you want exactly one implementation of them.

Search uses `pg_trgm` plus the Dutch `tsvector` index. Ingredient search ("wat kan ik met prei") is a
join on `recipe_ingredients.name_nl` — a separate query path, exposed as `?ingredient=prei`.

### Collections

```
GET    /v1/collections
POST   /v1/collections
PATCH  /v1/collections/{id}
DELETE /v1/collections/{id}
PUT    /v1/collections/{id}/recipes    → { recipe_ids: [...] }
```

### Planner

```
GET    /v1/plan?week_start=2026-08-03  → entries for the ISO week
POST   /v1/plan/entries                → { date, slot, recipe_id?, custom_label?, servings? }
PATCH  /v1/plan/entries/{id}           → move slot/date, change servings, mark leftover
DELETE /v1/plan/entries/{id}
POST   /v1/plan/copy                   → { from_week_start, to_week_start }
```

`POST /v1/plan/copy` is the "kopieer vorige week" button. Your spec predicts it'll be the most-used
control in the planner and I agree — households rotate the same fifteen dishes. It's four lines of SQL
and it's a headline feature.

### Shopping list

```
POST   /v1/shopping-lists              → generate/regenerate for { week_start }
GET    /v1/shopping-lists/{id}
PATCH  /v1/shopping-lists/{id}/items/{item_id}  → { is_checked } — idempotent on client_id
POST   /v1/shopping-lists/{id}/items   → manual item
DELETE /v1/shopping-lists/{id}/items/{item_id}
GET    /v1/shopping-lists/{id}/export/prakkie → structured payload for the deeplink
GET    /v1/pantry
PUT    /v1/pantry                      → { names: [...] }
```

Regeneration must **preserve check state** for items whose `(name_nl, unit)` still exists. Wiping
someone's ticked-off list because they added a Thursday dinner is an unforgivable bug and an easy one
to write.

`/export/prakkie` returns the D2 contract and nothing else:

```json
{
  "week_start": "2026-08-03",
  "items": [
    { "name_nl": "olijfolie", "amount": 30, "unit": "ml", "category": "houdbaar" },
    { "name_nl": "kipfilet", "amount": 500, "unit": "g", "category": "vlees_vis" }
  ]
}
```

Keep this endpoint stable and versioned separately in your head from the rest of the API — it's a
contract with another product, and the whole point of D1 is that Prakkie takes it from here.

### Groups

```
GET    /v1/groups
POST   /v1/groups                      → { name, emoji, color }
GET    /v1/groups/{id}                 → detail + members
PATCH  /v1/groups/{id}
DELETE /v1/groups/{id}                 → owner only
POST   /v1/groups/{id}/leave
GET    /v1/groups/{id}/recipes         → shared recipes, cursor paginated
POST   /v1/groups/{id}/recipes         → { recipe_id } share
DELETE /v1/groups/{id}/recipes/{rid}   → unshare, sharer or owner
POST   /v1/groups/{id}/recipes/{rid}/save → copy into own library
POST   /v1/groups/{id}/recipes/{rid}/reactions → { emoji?, comment? }
GET    /v1/invites/{code}              → public preview, no auth required
POST   /v1/invites/{code}/accept       → join
```

`GET /v1/invites/{code}` being unauthenticated implements your spec's "geen accountvereiste om de
preview te zien". Return group name, member count, and 3 recipe thumbnails. Nothing personal.

### Discover

```
GET    /v1/discover/curated            → editorially curated row
GET    /v1/discover/groups             → recent shares across the user's groups
GET    /v1/discover/seasonal           → current-month seasonal tag
```

Per D14 there is no global user feed. `curated` reads from a small admin-managed table (or frankly a
JSON file in blob storage for the first months — you are the editor, and a table you write to via
`psql` is not worse than an admin UI you don't have time to build).

Seasonal is a static month → tags map: asperges in April, boerenkool in November, pompoen in October.
Hardcode it. It's a strong local signal and it costs nothing.

### Health

```
GET /healthz    → liveness, no DB
GET /readyz     → DB connectivity + Clerk JWKS reachable
```

## Pagination

Cursor-based on `(created_at, id)`, never offset. Offset pagination breaks visibly when the user
imports a recipe while scrolling their library.

## Rate limits

Per user, enforced in the API with a Postgres-backed counter (Redis is a resource you don't need yet):

- Imports: 5/min, 30/hour
- Writes: 120/min
- Reads: 600/min

Return `429` with `Retry-After`.

## Versioning

`/v1` in the path. Because you ship OTA JS updates via EAS, most clients will be current within days —
but App Store review delays and users who disable updates mean you must assume an old client is always
in the wild. Never remove a field from a response; add and deprecate.
