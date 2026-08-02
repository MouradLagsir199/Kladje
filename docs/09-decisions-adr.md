# 09 — Architecture Decision Records

Format: decision, reasoning, what it costs, when to revisit.

---

## ADR-001 — No supermarket data in this app

**Decision.** No prices, no product catalogue, no SKUs, no chain assortments, no availability signals.
Ingredient handling is translation and metric normalisation only. Product matching happens in Prakkie at
export time.

**Reasoning.** With prices removed, the entire per-chain product apparatus produced only a shelf-accurate
product name — while requiring a matching layer, a retrieval layer, a nightly pipeline, and a backfill
job every time a chain was added. Availability signalling was worse than useless: absence from a scraped
CSV cannot be distinguished from absence from a shelf, so the feature's most common output would have
been a confidently wrong claim on the screen where the app is trying to earn trust.

**Cost.** Shopping list shows generic ingredient names. No pack-size logic. Shelf grouping comes from the
model rather than from data.

**Revisit.** Only if Prakkie's export contract proves insufficient in practice.

---

## ADR-002 — Recipes are per-user copies

**Decision.** Saving a recipe from a group creates a new row owned by the saver, with
`origin_recipe_id` for lineage. No shared mutable recipe rows.

**Reasoning.** Eliminates multi-tenant edit conflicts, per-field permissions, and the "someone changed
the recipe I planned for Thursday" class of bug. Users expect their copy to be theirs — including their
notes and their scaling.

**Cost.** Storage duplication (trivial), and improvements to an original don't propagate to copies.

**Revisit.** If a collaborative-editing use case appears. Unlikely for household recipe sharing.

---

## ADR-003 — Deduplicate at the parse layer, not the recipe layer

**Decision.** `source_cache` keyed on normalised URL stores the raw evidence and the model output.
Recipes are not shared; parses are.

**Reasoning.** Gets the full cost benefit of caching viral content without any of the shared-ownership
complexity of ADR-002. Also holds no personal data, which means it survives account deletion and stays
outside the AVG erasure path.

**Cost.** A cached parse may be stale relative to a source that changed. Acceptable — recipes don't
change.

---

## ADR-004 — No offline sync engine in v1

**Decision.** Online-only, with a persisted TanStack Query cache, `expo-image` disk caching, and
optimistic local writes for checkboxes only.

**Reasoning.** Full two-way sync for recipes with notes, ticks and cook logs is one of the largest pieces
of work in the original spec, and it is not what makes the product good. The three mechanisms above cover
the two moments that actually need to work without a network — cooking in a kitchen, and ticking items in
a supermarket — for a small fraction of the effort.

**Cost.** Editing a recipe requires connectivity. Planning requires connectivity.

**Revisit.** If telemetry shows meaningful offline-failure rates.

---

## ADR-005 — OpenAI direct, behind a provider interface

**Decision.** Use the OpenAI API with an API key, as specified. But put every model call behind a narrow
internal interface (`transcribe`, `synthesize`) so the provider is a config switch. No `vision_ocr`
method for now — cookbook-photo OCR is deferred to v2, see the update to ADR-014.

**Reasoning.** You asked for OpenAI direct and it has the best model availability and the simplest
integration. But the original spec's own AVG section correctly notes that sending user-submitted content
to a US provider is the app's most significant data-protection exposure, and Azure OpenAI in West Europe
or Sweden Central would resolve it while keeping everything in one cloud. The interface costs an
afternoon and preserves that option. Request zero data retention and EU residency on the OpenAI account
regardless — both are available and both simplify your privacy statement.

**Cost.** A thin abstraction layer.

**Revisit.** On a DPIA finding, a B2B enquiry, or if Azure OpenAI pricing becomes favourable.

---

## ADR-006 — Clerk for authentication

**Decision.** Clerk, with Google and Apple as the only sign-in methods.

**Reasoning.** The realistic options were Entra External ID, Supabase Auth, Clerk, and rolling your own
on `expo-auth-session`.

Entra External ID is the Azure-native answer and keeps everything in one tenant, but its React Native
integration is meaningfully rougher than the alternatives and Apple federation in particular is fiddly
to configure. For a solo developer whose scarcest resource is weeks, that's the wrong place to spend
them — auth is undifferentiated work that must simply function.

Supabase Auth is a strong second choice and has an EU region, but adopting it means running a Supabase
project alongside an Azure Postgres you've already chosen, which is two databases' worth of operational
surface for one feature.

Clerk has the best Expo SDK of the group, Google and Apple work in an afternoon including the native
Apple flow, session and refresh handling is solved, and it's free to 10,000 monthly active users — well
past break-even.

**Cost.** A US-based sub-processor in the auth path, holding email and provider identifiers. EU data
residency requires a paid tier. Vendor lock-in on `clerk_user_id`, mitigated by your own `users.id`
being the primary key everywhere internally.

**Revisit.** If auth data residency becomes a blocker, or above 10,000 MAU where pricing starts to
matter. Migration path: Clerk exports users; you'd re-link on email and force re-authentication.

**Override note.** If keeping everything inside Azure matters more to you than integration speed, Entra
External ID is a defensible choice and nothing else in this plan changes — the API only verifies a JWT
against a JWKS endpoint either way.

---

## ADR-007 — Python 3.12 + FastAPI

**Decision.** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, `uv` for dependency management, Ruff for
lint and format, pytest.

**Reasoning.** You already write Python — the scrapers are Python — and the import pipeline is
fundamentally a data-transformation problem where Python's ecosystem is strongest. Async FastAPI handles
SSE cleanly. Pydantic v2 does double duty as your API schema *and* the validation layer for model
structured output, which is a real saving given how central that validation is. And image handling and HTML
parsing are both more comfortable here than in Node.

The counter-argument is a single TypeScript language across client and server, sharing types. It's real,
but it means giving up your existing fluency in the language where the hard part of this product lives.
Generate a typed API client from the OpenAPI schema FastAPI produces for free, and you get most of the
type-sharing benefit anyway.

**Cost.** Two languages in one project. No shared code between client and server.

**Revisit.** No good reason to.

---

## ADR-008 — Azure App Service for Linux Containers

**Decision.** App Service, always on, no scale-to-zero. Not Container Apps, not Functions.

**Reasoning.** Functions on consumption is the worst fit: cold starts land on the import progress
screen — the single moment where the product either feels magical or broken — and long-running HTTP with
a streaming response is what Functions handles least well.

Container Apps' headline feature is scale-to-zero, which is actively harmful for the same reason. Once
you set a minimum replica of one you pay App Service prices for revisions, KEDA rules, Dapr and ingress
configuration you don't need with one container and one developer.

App Service gives you always-on, deployment slots for zero-downtime swaps, managed identity to Key
Vault, and the smallest possible operational surface.

**Cost.** You pay for idle capacity (~€13/month). No autoscaling sophistication.

**Revisit.** When you move imports to a background queue — Container Apps Jobs are genuinely good at
that, and it's the natural home if you adopt ADR-009.

---

## ADR-009 — Foreground imports in v1, background queue deferred

**Decision.** The import runs while the user watches the progress screen, as an in-process background
task streaming SSE. No queue, no worker, no push notification.

**Reasoning.** Your call (D10), and it's the right one for v1: it's dramatically simpler, and the
progress screen doubles as a trust-building device — showing "audio uitlezen" and "tekst in beeld
herkennen" tells the user the app is doing something hard on their behalf, which makes a 25-second wait
feel like value rather than latency.

**Cost.** The user must keep the app open. Long imports that fail after 30 seconds waste their attention
rather than their notification tray. A container restart mid-import loses the import.

**Revisit.** In v2. Background imports with a push notification are a better experience — the user stays
in TikTok, shares three videos in a row, and gets three recipes to review later. Needs a queue (Azure
Storage Queues are sufficient), a worker, and a pending-drafts inbox in the Recepten tab. That inbox is
worth building in v1 anyway, since abandoned reviews need somewhere to live.

---

## ADR-010 — RevenueCat for subscriptions

**Decision.** RevenueCat in front of App Store and Play IAP.

**Reasoning.** Receipt validation for two stores, one entitlement abstraction, and webhooks for renewals,
grace periods, refunds and cancellations — all of which you would otherwise write twice and get subtly
wrong. Free below $2.5k monthly tracked revenue, which is far past break-even. Store IAP itself is
mandatory, not a choice.

**Cost.** Another sub-processor. 1% of revenue above the free threshold.

---

## ADR-011 — GPT-4.1 mini for synthesis, pinned in config

**Decision.** Synthesis on **GPT-4.1 mini** ($0,40 / $1,60 per 1M tokens) on every path. No transcription
model — Apify supplies transcripts. No vision calls in v1 — cookbook-photo OCR is deferred, see the
update to ADR-014. Pin the model name and `prompt_version` in config, record both in `source_cache`,
alert on cost drift.

**Reasoning.** Verified pricing as of 1 August 2026. The current lineup is GPT-5.5 as flagship with the
GPT-5.4 family below it; GPT-5.4 mini is $0,75 / $4,50 and GPT-5.4 nano $0,20 / $1,25. GPT-4.1 mini is
cheaper than both mini options and this is an extraction-and-translation task from supplied evidence —
the regime where small models sit closest to frontier ones.

Two further reasons to prefer the 4.1 family specifically: OpenAI charges a 10% uplift on regional
processing (data-residency) endpoints for models released on or after 5 March 2026, which covers the
whole 5.4 family but not 4.1 — so if the AVG discussion in `07-legal-avg.md` pushes you to EU
processing, 4.1 avoids the surcharge. And a human reviews every recipe before it's saved, which is
precisely the safety net that makes a cheaper model acceptable here.

**Note: there is no "GPT-4.5 mini."** GPT-4.5 was a research preview retired from the API in 2025 and
never had a mini variant.

**Cost.** Slightly lower parse quality than the best available model. Mitigated by prompting, the
deterministic validation layer, and the review screen.

**Revisit.** If quality telemetry shows parse failures driving churn. The upgrade path is GPT-5.4 mini,
which roughly doubles synthesis cost — affordable at current margins (see `06-monetisation.md`), so this
is a quality decision rather than a financial one. If it ever stops being affordable, raise the price
rather than the cap.

---

## ADR-012 — Group-only sharing, no global feed

**Decision.** Discover shows group activity, one manually curated row, and a seasonal row. No public
feed of all users' recipes.

**Reasoning.** Your original spec reached this conclusion and it's right. A global feed of imported
third-party content means moderation tooling, spam handling, and a much weaker position on the rights
questions in `07-legal-avg.md` — you'd be republishing other people's recipes at scale rather than
helping individuals keep their own. Groups also produce the growth mechanism: invite links bring in
households.

**Cost.** Weaker cold-start experience for a user with no groups. Mitigated by the curated row and by
onboarding's demo import.

**Revisit.** Once there's a reason to moderate — meaning once you have enough users that a feed would
have content worth showing.

---

## ADR-013 — Fixed enums for unit and shelf category

**Decision.** `unit` and `shelf_category` are Postgres enums. `original_unit` on the source side stays
free text.

**Reasoning.** The Prakkie export contract needs a controlled vocabulary or it's unusable, and a
free-text category from a model fragments shelf grouping into dozens of near-duplicate headings. The
asymmetry is the point: sources can say anything, your output cannot.

**Cost.** Occasional forced mapping when a source uses something genuinely unusual. Enum values are
append-only forever.

---

## ADR-014 — No OCR in the link-import path

**Decision.** Vision is used only for the cookbook-photo entry point. Link imports rely entirely on
Apify's transcript, the post caption, and metadata. No frame extraction, no ffmpeg, no media download.

**Reasoning.** Your call, and the operational payoff is larger than the cost saving. Frame OCR would have
dragged in video downloads, ffmpeg in the container, size ceilings, download timeouts, memory limits, and
a scene-detection heuristic to tune — a substantial amount of infrastructure and failure surface for a
minority of imports. Removing it means the API container never handles a media file, which is one of the
biggest simplifications available in this design.

**Cost.** Recipes shown only as on-screen text cannot be imported. Those attempts fail as
`no_recipe_found` or thin `low_confidence` drafts. It also costs the "choose a frame as the photo" control
in the review screen — replaced by Apify's thumbnail plus pick-from-gallery.

**Mitigation.** The failure must land somewhere good: prefilled manual entry, with whatever the caption
yielded and the thumbnail already attached as the photo. That turns a dead end into 30 seconds of typing.

**Revisit.** If telemetry shows silent-video failures are a large share of TikTok attempts. The pipeline
has a single seam where a rescue OCR pass would slot in after a thin synthesis result, so this decision is
cheap to reverse — deliberately so.

**Update, 2026-08-02 — cookbook-photo OCR deferred to v2 entirely.** The original decision above kept one
exception: vision for the cookbook-photo entry point. That exception is now cut too, on cost grounds —
every vision call is a paid OpenAI request, and there is no user base yet to justify spending on an entry
point nobody is using. v1 now has **no vision, no OCR, anywhere**. Tasks 2.12 (`POST /v1/imports/photo`)
and 2.13 (client "Foto van kookboek" entry) are removed from `13-build-tasks.md`; the fixture corpus in
2.9 drops its 5 cookbook fixtures. The `photo_ocr` value stays in the `source_platform` enum
(`02-datamodel.md`) — enum values are append-only forever, and leaving an unused value costs nothing.
**Revisit** once there's real usage data suggesting the demand justifies the per-call cost.
