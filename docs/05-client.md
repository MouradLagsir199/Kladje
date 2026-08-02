# 05 — Client

Expo / React Native, iOS + Android, single codebase. Custom dev client from day one.

## Stack

| Concern | Choice | Why |
|---|---|---|
| Framework | Expo SDK (latest stable), React Native, TypeScript | D8 |
| Build | EAS Build + EAS Submit + EAS Update | OTA updates are your most valuable ops tool |
| Navigation | Expo Router (file-based) | Typed routes, deep links come free, and you need deep links for share handoff and Prakkie |
| Server state | TanStack Query + persisted cache in MMKV | Implements D11's persisted read cache with almost no code |
| Local state | Zustand | Small, no boilerplate; only for cook-mode timers and UI state |
| Storage | MMKV | Fast synchronous KV, right shape for a query cache |
| Auth | Clerk Expo SDK | ADR-006 |
| Payments | RevenueCat SDK | ADR-010 |
| Share intake | `expo-share-intent` config plugin | Native extension + Android intent filter |
| Lists | FlashList | The library grid and shopping list both need to stay smooth at 500 items |
| Images | `expo-image` | Built-in disk caching, which *is* the offline image story |
| Screen wake | `expo-keep-awake` | Cook mode |
| Errors | Sentry | |

Deliberately **not** included: Redux, a component library, a sync engine, i18n. The app is Dutch-only
at launch — hardcode the strings in a single `nl.ts` module so extracting them later is mechanical, but
don't install an i18n framework for one locale.

## Project layout

```
app/                          # Expo Router
  (onboarding)/               # household, diet, demo-import
  (tabs)/
    ontdek/index.tsx
    recepten/index.tsx        # + collections, pending drafts
    planner/index.tsx         # week + boodschappen subtabs
    profiel/index.tsx         # groups, settings, subscription
  import/                     # modal stack over everything
    index.tsx                 # source picker / paste
    [id]/progress.tsx
    [id]/review.tsx
    [id]/done.tsx
  recipe/[id]/index.tsx       # global screen
  recipe/[id]/cook.tsx        # global screen, full-screen
  group/[id]/index.tsx
  invite/[code].tsx           # unauthenticated preview
src/
  api/                        # generated client + query hooks
  components/                 # component library, see below
  lib/                        # units, scaling, provenance, deeplinks
  strings/nl.ts
  theme/
```

## Component library

Building these first, before screens, is what keeps a 30-screen app consistent when one person builds
it over months. The prototype already establishes the visual language — extract from it.

- **RecipeCard** — three variants: hero, grid (2-col), compact row
- **MetaBar** — time · servings · difficulty, always same order and icons
- **SourceBadge** — platform mark + creator name. Appears on every card and every detail header
- **ProvenanceDot** — green/yellow/red, with an accessible label. Used in review *and* detail
- **IngredientRow** — amount + unit + name, optional original unit beneath, optional checkbox
- **StepCard** — number, text, embedded timer chip
- **PlanSlot** — empty (dotted plus) and filled (mini card) states
- **ShoppingRow** — name, amount, checkbox, source-recipe caption
- **EmptyState** — illustration + text + primary action. A distinct one per main screen
- **QuotaPill** — "3 van je 10 imports" — appears in the import entry and profile

`ProvenanceDot` deserves special attention: it must never be colour-only. Green/yellow/red is invisible
to a meaningful share of users. Pair each with a shape or short label.

## Share handoff

The critical native path, per D9.

1. User taps Share in TikTok, picks your app
2. Share extension (iOS) / intent filter (Android) receives the URL
3. It writes to the shared App Group container and opens the main app via deep link
4. App reads the pending URL, checks auth, and routes:
   - Not signed in → auth screen, URL held, resume after sign-in
   - Quota exhausted → paywall, URL held, resume if they subscribe
   - Otherwise → `POST /v1/imports` and straight to `import/[id]/progress`

The extension does **no** network calls, no auth, no import. It captures and hands off. iOS share
extensions run in a separate process with tight memory limits and no access to your app's Clerk
session; anything more ambitious than capture-and-hand-off will bite you.

Holding the URL across an auth or paywall detour is the part people get wrong. A user whose first-ever
action is sharing a TikTok must land on that recipe after signing up, not on an empty home screen.

## Import progress screen

Opens an `EventSource` against the SSE endpoint. Renders your spec's checklist with the video thumbnail
behind it. Falls back to 2-second polling if the stream errors.

Three things it must handle:

- **Skipped stages** — a blog import skips the Apify fetch and must look like progress, not a stall
- **Cancel** — abandons the import, marks it `cancelled`, no quota charge
- **Backgrounding** — the user will switch apps. On return, re-open the stream or poll; never restart
  the import

## Review screen — prototype variant A

The most important screen in the product, and the one to over-invest in. Build **variant A only**
("Lijst — inline correctie"). Variants B and C from the prototype are dropped (D16).

Layout, top to bottom, matching the prototype:

- **Amber missing-fields card** — count and list of red fields ("Twee dingen ontbreken · Oventemperatuur
  · aantal personen") with a single dark *Laat AI aanvullen* button
- **Photo + title row** — thumbnail on the left (tap to replace from gallery or camera; no frame
  picker), title as an editable input on the right
- **Three metadata fields** — porties, tijd, oven — each with a `ProvenanceDot` above the label and a
  small *geschat* caption underneath when the value came from AI fill
- **Ingredients** — section header with "sleep om te ordenen", then draggable rows. Each row splits
  amount / unit / name into separate inputs so the structured data stays structured, with the original
  unit in small type beneath any converted quantity
- **Steps** — numbered, editable
- **Sticky footer** — `Opslaan` primary, `Opslaan en inplannen` secondary

Behaviour:

- Every edit PATCHes the draft, debounced. Never hold the only copy in component state
- AI fill flips red dots to amber and adds the *geschat* caption — the transition must be visible, since
  that visibility is the whole point
- No jump-to-source anywhere (D15)

Because there's no jump-to-source, **the provenance dots are now the entire trust mechanism.** Give them
more design attention than the prototype does: never colour alone, a legend or tap-for-explanation on
first use, and dots on the recipe detail screen too, not just here.

## Cook mode

- Full screen, dark, `expo-keep-awake` active
- One step per horizontal page
- Type large enough to read at 60 cm with dirty hands — think 22–28pt body, not 16
- This step's ingredients repeated at the top
- Timers float above the pager and keep running across swipes. They must survive backgrounding: store
  the wall-clock end time, not a countdown, and recompute on resume
- Exit → "Gekookt!" sheet: photo, rating, share to group

Timers-as-end-timestamps rather than tick counters is the single implementation detail that makes cook
mode feel reliable instead of broken.

## Offline behaviour (D11)

Not a sync engine. Three concrete mechanisms:

1. **Persisted query cache** in MMKV with a long `gcTime`. Recipe detail and cook mode read from cache
   and render fully offline if previously visited
2. **`expo-image` disk cache** for all recipe photos
3. **Optimistic checkbox mutations** for ingredient ticks and shopping-list items, queued in MMKV,
   flushed on reconnect, idempotent server-side via `client_id`

Everything else — import, planning, group actions — requires connectivity and says so with a clear
offline banner rather than failing silently.

Worth prefetching the current week's planned recipes and this week's shopping list on app foreground.
That's a handful of requests and it means the two things people need in a kitchen and a supermarket are
always warm.

## Accessibility

Not optional, and cheap if done from the start:

- Dynamic type support — cook mode especially, where users are already straining
- Provenance never signalled by colour alone
- Minimum 44×44pt touch targets; shopping-list checkboxes get tapped with one hand holding a basket
- `accessibilityLabel` on every icon-only button, in Dutch
- Test with VoiceOver once per major screen. Once is enough to catch 90% of it

## Analytics

Small, deliberate event set. Resist the urge to log everything.

`import_started` (platform) · `import_completed` (platform, duration, cache_hit) · `import_failed`
(error_code) · `import_saved` · `enrich_used` · `recipe_cooked` · `plan_week_copied` ·
`shopping_list_generated` · `prakkie_export` · `paywall_shown` · `subscribed` · `group_created` ·
`group_recipe_saved`

The funnel that matters: `import_started → import_completed → import_saved`. Drop-off between the
second and third is a review-screen quality problem, and it's the number that tells you whether the
product works.
