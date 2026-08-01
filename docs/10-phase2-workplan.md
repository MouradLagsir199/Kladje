# 10 — Phase 2 Work Plan: Import Quality Across Platforms

Weeks 4–6. Entering with Phase 1 complete: blog import works end to end, review screen variant A is
built, recipes save to the library.

**Goal of this phase:** every source your users will actually paste produces a good recipe, and you know
what it costs. Nothing in Phases 3–6 is worth starting until this is true, because import quality is the
product and everything else is furniture.

## Exit criteria

Hard gates. Don't move to Phase 3 until all four pass.

1. **Fixture corpus of 45 sources** across blog, YouTube, TikTok, Reels and cookbook photos scores ≥ 80%
   "needs no correction on ingredients" and ≥ 70% "needs no correction on steps"
2. **Measured blended cost per import under €0,008.** Expected ~€0,005
3. **p95 import duration under 25 seconds** on a real mobile connection
4. **Every failure mode in the taxonomy has been triggered at least once** and lands on Dutch copy you'd
   be happy for a stranger to read

## Work breakdown

### 2.1 — Apify integration layer (2–3 days)

Build this as a provider module with the same shape as the model provider (ADR-005), so a dead actor is
a config change rather than a refactor.

- Client wrapper: run actor, poll for completion, fetch dataset items, with a hard 45-second ceiling
- **Response normalisation per actor.** Actor output schemas differ and change without notice. Map each
  one into a single internal shape and validate with Pydantic on the way in. Do not let raw Apify JSON
  reach the synthesis layer
- **Per-platform circuit breaker.** Five consecutive failures on TikTok opens the breaker for 10
  minutes and returns `scraper_failed` immediately rather than burning 45 seconds per request. Blog and
  YouTube paths keep working — that isolation is the whole point
- Store the raw response in `source_cache.raw_payload` before any parsing. When a parse goes wrong in
  three weeks, this is the only way to debug it without paying again
- Cost accounting: record the per-run Apify cost on the `imports` row

**First task of the phase, before writing any of the above:** run one TikTok URL, one Reel, and one
YouTube URL through the actors by hand and save the raw JSON to the repo as fixtures. Everything
downstream is designed against what those responses actually contain, not what the docs claim. Check
specifically whether the transcript arrives as flat text or segments, whether the caption is separate
from any on-screen text field, and whether a thumbnail URL is stable or expiring.

### 2.2 — YouTube path (1–2 days)

Second-best source after blogs, and cheap.

- Captions track plus description via the actor
- **Description parsing matters more than you'd think.** Many creators paste the full ingredient list
  there. If the description contains an ingredient-list-shaped block, treat it as higher-confidence
  evidence than the transcript and say so in the prompt
- Shorts collapse to the standard watch URL in normalisation — already handled in Phase 1, but add
  fixtures for it

### 2.3 — TikTok / Reels path (2–3 days)

- Transcript + caption + metadata into the `EvidenceBundle`. No media download, no ffmpeg (ADR-014)
- Thumbnail URL captured for the recipe photo. **Check whether it expires** — if Apify returns a
  short-lived CDN URL, fetch and copy it into `recipe-media` at import time rather than storing the URL
- `silent_video` detection: synthesis returns fewer than 2 ingredients or no steps → route to prefilled
  manual entry with the thumbnail attached and whatever the caption yielded
- Instrument the `silent_video` rate per platform. This is your single most important quality metric this
  phase — if it's above ~25% on TikTok, ADR-014 needs revisiting sooner than planned

### 2.4 — Prompt hardening (3–4 days, spread across the phase)

The largest single lever on quality, and the work that benefits most from iteration against fixtures.

- Full synthesis prompt: Dutch output, informal register, unit enum, ingredient-dependent volume
  conversion, °F→°C, method rewriting, provenance rules, `raw_text` preservation
- **Provenance honesty is the thing to test hardest.** The model will over-claim `explicit`. Write an
  assertion that samples `explicit` ingredients and checks the name actually appears in the evidence
  text; a model marking converted quantities as `explicit` is the failure that quietly destroys the
  trust the dots are supposed to build
- **Never invent** servings, oven temperature, or cook time — leave `missing`
- Separate `enrich` prompt for *Laat AI aanvullen*, returning only the previously-missing fields, all
  marked `estimated`
- Tighten the JSON schema aggressively. Output tokens dominate cost, so every field you don't need is
  money and latency. Don't echo `raw_text` back if you already hold it
- Version the prompt; bump `prompt_version` on every semantic change

### 2.5 — Validation layer (1–2 days)

Deterministic, after the model, before the user. Cheap insurance against a small model's bad day.

- Unit and category enum enforcement with repair-or-reject
- Clamps: servings 1–24, times 0–1440 min, temperature 40–300 °C
- Compute `temperature_fan_c` yourself; don't trust the model with arithmetic
- Sensible rounding: `1.33 ei` → `amount 1, amount_max 2`. Never show a fractional egg
- Deduplicate identical `name_nl` + `unit`, summing amounts
- Minimum viability: ≥ 2 ingredients and ≥ 1 step, else `low_confidence`
- Allergen cross-check against `user_preferences.allergens`

### 2.6 — Failure taxonomy and copy (1–2 days)

Every code in the `03-import-pipeline.md` table gets distinct Dutch copy and a working exit. Write these
as a set, in one sitting, in one file — written piecemeal they drift into inconsistent voice.

The two that matter most, because they'll be the most common:

- `silent_video` → prefilled manual entry. Frame it as a handoff, not an error: "We konden er geen recept
  uit halen — vul het samen met ons aan" with the fields already partly filled
- `low_confidence` → the draft opens normally with the missing-fields card already expanded

**Trigger every single one deliberately** before this phase closes. A failure path you've never seen is
a failure path that's broken.

### 2.7 — Fixture corpus and eval script (2 days)

The investment that makes every later prompt change safe.

- 45 saved `EvidenceBundle` fixtures committed to the repo: ~15 blog, ~8 YouTube, ~12 TikTok, ~5 Reels,
  ~5 cookbook photos, including deliberately awful ones — a silent video, a recipe in cups, a Reel that's
  80% storytelling, a cookbook page shot at an angle with a shadow across it
- Golden outputs with **tolerant** assertions: flour between 110 and 140 g per cup, not exactly 125.
  Brittle assertions get switched off, and a test you've switched off is worse than no test
- `scripts/eval.py` scoring a prompt version across the corpus: fields extracted, enum violations,
  provenance-honesty spot check, mean output tokens, estimated cost. One command, one table of numbers
- **No paid API calls in CI.** Fixtures only

### 2.8 — Cookbook photo import (2 days) — v1

The only use of vision in the product. Small, because the expensive parts already exist: the review
screen, the validation layer, the draft/save flow. You're adding an entry point and one model call.

**Client (1 day)**
- "Foto van kookboek" option in the import modal's step 1, alongside paste and manual entry
- `expo-image-picker` for camera and gallery, 1–3 images to cover a page turn
- Native permission strings: `NSCameraUsageDescription` and `NSPhotoLibraryUsageDescription` on iOS,
  `CAMERA` and media permissions on Android. Write these in Dutch and make them specific — "om een
  pagina uit je kookboek te fotograferen", not a generic string. Vague permission copy is a
  rejection risk and it also visibly lowers grant rates
- Client-side downscale to ~1,500px long edge before upload. Cookbook type is far larger than video
  overlay text, so you can afford less compression than frames would need — but a 12MP original is
  pointless bytes over a mobile connection
- On-screen guidance before the shutter: flatten the page, avoid shadow, get all of the recipe in frame.
  One line, not a tutorial
- Progress screen reuses the existing SSE flow with two stages (`fetch` becomes `upload`)

**Server (1 day)**
- `POST /v1/imports/photo`, multipart, max 3 files, max 8MB each, JPEG/PNG/HEIC only
- Upload to `recipe-media` under a temp prefix, run the vision call, then **delete the page photos**.
  You have no reason to retain a photograph of someone's cookbook, and not retaining it is the simplest
  possible answer in your privacy statement
- Vision + synthesis in one call on GPT-4.1 mini, returning the same JSON schema as every other path
- Provenance is `explicit` for legible text and `missing` for anything unclear. **There is no transcript
  to cross-reference, so the model must not infer** — say so explicitly in the prompt. This path is
  where over-claiming is most tempting and least detectable
- No `source_url`. Capture book title and author as free-text fields on the review screen if the user
  offers them, so attribution isn't simply absent
- Counts against quota (it's a paid model call), `source_platform = 'photo_ocr'`
- Cost: ~€0,004 per import, of which ~€0,002 is the image tokens

**Failure modes worth their own copy**
- `photo_unreadable` — blur, shadow, or a page too curved near the spine. Prompt a retake with the
  specific problem named. Don't try to correct curvature in software
- `no_recipe_found` — the photo is of something that isn't a recipe
- Partial reads are the common case: a legible ingredient list with a method half-lost in the gutter.
  That's a `low_confidence` draft, which the review screen already handles

**One legal note that's stronger here than elsewhere.** A cookbook's method prose is more clearly
protected expression than a blog post's — professionally edited, commercially published, and with a
rights holder who has lawyers. The rewrite rule in the synthesis prompt isn't optional on this path, and
there's no source URL to attribute to, which makes the rewrite your only protection rather than one of
two. Worth raising with the lawyer reviewing your terms (`07-legal-avg.md`).

### 2.9 — Cost and quality telemetry (1 day)

One custom event per import carrying: platform, cache hit, per-stage duration, input/output tokens,
estimated cost, outcome, `silent_video` flag, whether AI fill was used.

Then the two dashboards from `01-architecture.md`, and the daily-spend alert. Set the alert threshold
before you have users, not after — it's a circuit breaker against a runaway loop, and the cost of not
having it is a month's revenue overnight.

## Effort reality check

Summing the items: ~18 working days against a 15-day, three-week window. Adding cookbook photo import
pushed this phase over. Three honest options:

1. **Let it be 3.5 weeks.** Recommended. This phase is the product; the planner can wait
2. **Move cookbook photo to Phase 3**, where it sits comfortably alongside the library work and reuses
   the same camera/permission plumbing the cook log needs anyway. It's still v1 either way
3. **Trim the fixture corpus to 30.** Cheapest-looking cut and the one I'd resist — the corpus is what
   makes every later prompt change safe

Don't cut the failure-copy work (2.6) or the telemetry (2.9). Both look skippable and both cost you
much more later.

## Sequencing within the phase

```
Week 4  │ 2.1 Apify layer ──────────┐
        │ (fixtures FIRST, day 1)   │
        │ 2.2 YouTube ──────────────┤
        │                           │
Week 5  │ 2.3 TikTok / Reels ───────┤
        │ 2.7 Fixture corpus ───────┼── 2.4 Prompt hardening runs
        │ 2.5 Validation layer      │   continuously against the
        │                           │   growing corpus
Week 6  │ 2.6 Failure copy ─────────┤
        │ 2.8 Cookbook photo ───────┤
        │ 2.9 Telemetry ────────────┘
        │ Measure. Gate. Decide.
```

Prompt hardening is not a discrete task — it runs the whole phase, and it needs the corpus to exist
early. That's why 2.7 starts in week 5 rather than at the end, and why capturing raw Apify fixtures is
day one.

## Risks specific to this phase

**Apify actor output changes under you.** Likeliest disruption in the whole project. Mitigation is the
normalisation layer plus Pydantic validation at the boundary, so a schema change fails loudly at one
place instead of producing subtly wrong recipes.

**Silent-video rate turns out high.** If more than a quarter of TikTok imports have no usable audio
transcript, TikTok — probably your most-shared platform — has a bad hit rate. Decide the threshold now,
before you have data and a motive to rationalise it. Above 25%, revisit ADR-014; the pipeline has one
seam where a rescue OCR pass slots in.

**Prompt iteration without measurement.** Real risk for a solo developer: you tweak, it feels better,
you ship, and something else regressed. The eval script exists to stop that, and it only works if you
run it on every change. Make it a pre-commit hook if you don't trust yourself.

**Over-fitting to your own taste in recipes.** You'll build the corpus from things you'd cook. Deliberately
include a few sources you find annoying — 12-minute storytelling Reels, American baking blogs in cups,
protein-powder content. Those are what your users will paste.
