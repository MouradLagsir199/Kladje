# 07 — AVG, Copyright and Store Review

Not legal advice — I'm not a lawyer, and for the copyright and platform-terms questions in particular
you should get a Dutch IT lawyer to look at your terms and privacy statement before launch. What
follows is the engineering and process work you can do regardless, plus the specific issues worth
paying someone to answer.

## AVG / GDPR

### What personal data the app holds

| Data | Basis | Notes |
|---|---|---|
| Email, name, avatar (via Google/Apple) | Contract | May be an Apple Private Relay address |
| Household size, diets, **allergies** | Contract | Allergies are health data — Article 9 special category |
| Recipes, notes, cook logs, photos | Contract | User-generated |
| Planner and shopping lists | Contract | Reveals household habits |
| Group membership | Contract | Social graph |
| Push tokens | Consent | |
| Analytics events | Legitimate interest | Keep them non-identifying where you can |

**Allergy data is the one that raises the bar.** Article 9 special-category data needs explicit consent,
not just contract necessity. In practice: a clear checkbox during onboarding explaining that you store
allergies to warn them about recipes, separate from the general terms acceptance, and a working way to
delete it. Don't bury it.

### Sub-processors

Every one needs a data processing agreement in place before launch. Most are click-through in the
vendor's dashboard, so this is an afternoon, not a project.

| Processor | Data | Region | DPA |
|---|---|---|---|
| Microsoft Azure | Everything | West Europe | Microsoft Products and Services DPA |
| Clerk | Auth identifiers, email | Configure EU where the plan allows | Clerk DPA |
| Apify | Source URLs | US | Apify DPA |
| OpenAI | Transcripts, captions, prompts | US by default — **see below** | OpenAI DPA + zero-retention |
| RevenueCat | Purchase identifiers | US | RevenueCat DPA |
| Sentry | Error payloads, device info | EU region available — **use it** | Sentry DPA |
| Expo / EAS | Push tokens | US | Expo DPA |

Two concrete actions worth doing on day one because retrofitting them is painful:

- **Ask OpenAI for zero data retention and EU data residency on your API account.** Both are available
  on request for API usage. Zero retention means prompts aren't stored, which materially simplifies your
  privacy statement and is the honest answer to "where does my TikTok go".
- **Set Sentry's region to EU.** It's a dropdown at project creation and irreversible afterwards.

Note that the original spec flagged Azure OpenAI in an EU region as the AVG-cleaner choice, and it is.
ADR-005 keeps you on OpenAI direct as you asked, behind a provider interface — so if a DPIA or a
customer pushes back, switching is a config change rather than a rewrite. That optionality is the whole
reason for the interface.

### Rights implementation

- **Access / portability**: `GET /v1/me/export` producing a JSON bundle of recipes, plans, lists, notes
  and cook logs, plus blob URLs. Build it in v1 — it's a day's work and it's also your best
  "your data is yours" marketing line
- **Erasure**: `DELETE /v1/me` → hard-delete rows, delete blobs, delete the Clerk user, send RevenueCat a
  deletion request, and delete the user's `imports`. Keep `source_cache` — it's keyed on a public URL and
  holds no personal data, which is precisely why the cache is designed that way
- **Rectification**: covered by ordinary editing
- Complete within 30 days; automate it so it's instant

### Retention

| Data | Retention |
|---|---|
| Account + content | Until deletion; auto-delete after 24 months inactive, with warning emails first |
| `imports` rows | 12 months, then purge draft JSONB and keep the counted flag |
| `source_cache` | 180 days |
| Analytics | 14 months |
| Logs / App Insights | 30–90 days |

### Privacy statement

Must name the sub-processors above, state that content from links you submit is sent to a transcription
and language model provider, and cover the allergy consent. The original spec's instinct to put a
"welke data gaat naar transcriptie- en modelproviders" toggle in settings is good — make it a clear
disclosure screen even if there's nothing to toggle.

## Copyright

The riskiest area of the product, and the original spec's analysis is basically correct.

**Ingredient lists** are largely factual and enjoy thin protection at best. **Method prose written by a
blogger is protected expression.** So:

- **Always rewrite method text.** Enforced in the synthesis prompt, and it's the single most important
  legal control in the app. It's also a quality win — bloggers' prose is padded and your users want the
  steps
- **Never store or display the source's method text verbatim.** `recipe_steps.text` holds only rewritten
  text. `raw_text` on ingredients holds the original ingredient string, which is the low-risk half
- **Always attribute**: creator name, platform, and a working link to the original, on the card and on
  the detail screen. This is what creators actually want, and non-negotiable in the UI
- **Never re-host video.** Play the original in an embed or hand off to the platform's app. You store a
  single frame as a thumbnail, under fair-use-adjacent reasoning, and you honour takedowns
- **Ship a notice-and-takedown route** — an email address in the app and in your terms, and a documented
  process. Being responsive is most of your protection in practice

Get a lawyer to confirm the frame-as-thumbnail position and review your terms. It's the one place I'd
actually spend the money.

## Platform terms of service

Be clear-eyed: **scraping TikTok and Instagram via Apify is against those platforms' terms of service.**
Apify provides the capability; the terms exposure is yours. Realistic assessment:

- Enforcement against small consumer apps is rare and usually takes the form of IP blocks and rate
  limiting rather than legal action
- The practical risk is **operational, not legal**: your import path for a platform breaks with no
  notice, on their schedule
- That risk is why per-platform circuit breakers and a graceful degradation story matter. A TikTok
  outage must not break blog imports

Cleaner alternatives where they exist and are worth using:

- **YouTube**: official Data API for metadata; captions are the grey part but far less exposed
- **Blogs and Pinterest**: entirely legitimate — you're reading published structured data, respecting
  `robots.txt`, identifying your user agent, and rate limiting. Do all three
- **oEmbed** endpoints for embedding TikTok and Instagram posts are officially sanctioned and are the
  right way to show the original

This is a business risk to accept consciously, not one to engineer away. It's also a strong argument
for making the blog/YouTube path excellent — it's the part nobody can turn off.

## App Store and Play review

Assume at least one rejection. Prepare for it rather than being surprised.

**Likely grounds:**

- **Unauthorised third-party content** (Apple 5.2.2 and related). Apps that ingest social media content
  get flagged. Your defence: the user supplies the link, you transform rather than republish, you always
  attribute and link back, you don't re-host video, you have a takedown process
- **Sign in with Apple** required because you offer Google login. Non-negotiable
- **Subscription disclosure**: price, period, auto-renewal terms, restore-purchases button, links to
  terms and privacy — all on the paywall itself
- **Account deletion in-app** is mandatory. It must be reachable in the app, not a link to a web form
- **Privacy manifest and nutrition labels** must be accurate about the third-party SDKs you ship
- **Camera and photo-library permission strings** must be specific and in Dutch — "om een pagina uit je
  kookboek te fotograferen", not a generic string. Vague permission copy draws rejections and lowers
  grant rates

**Prepare before you submit:**

- A reviewer note explaining the import model in three sentences, plus a working demo link to import
- A demo account with pre-seeded content — reviewers will not sign up with Google
- A working test subscription in sandbox
- Your takedown policy in your public terms, linked from the app

Write the reviewer note *before* submitting, not after the first rejection. It genuinely changes
outcomes.

## Age rating and content

12+/Teen is right for a recipe app with user-shared content. Because groups let users share content,
Apple expects some moderation capability: a report button on shared recipes and reactions, and the
ability to remove content. Since D14 keeps you group-only with no public feed, this is small — a report
endpoint and an email to yourself is enough at launch. A global feed would have required real moderation
tooling, which is a good part of why D14 is the right call.
