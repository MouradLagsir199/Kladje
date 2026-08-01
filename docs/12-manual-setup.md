# 12 — Manual Setup

Everything an agent cannot do for you. **Work through this in one sitting before starting the build.**
Each step names what it yields and where that value goes, so the agent knows what to expect and never
has to stop and ask.

The goal is a single uninterrupted human session up front, in exchange for long agent runs afterwards.

---

## Before you start

Have ready: your Apple ID, a Google account, a credit card, and about three hours. The Apple Developer
enrolment can take 24–48 hours to approve, so **do step 6 first** and come back to it.

---

## 1. Rotate the exposed Google secret

The web OAuth client secret in `client_secret_670984534617-5jtjlgp8hsvluqsuhhaa51adr0lkki2t...json`
has been shared outside secure storage. Before anything else:

1. Google Cloud Console → APIs & Services → Credentials
2. Open the web client `670984534617-5jtjlgp8...`
3. Add a new client secret, then delete the old one

**Yields:** a fresh client secret. Goes into Clerk in step 3. Never into the repo.

---

## 2. Google Cloud project and consent screen

Both existing clients sit under `project_id: prakkie`. The OAuth consent screen shows the project's app
name and logo, so a Receptenapp user would see Prakkie branding in the Google dialog.

**Do:** create a separate GCP project, `receptenapp`.

1. New project → `receptenapp`
2. APIs & Services → OAuth consent screen → External
3. App name `Receptenapp`, support email, logo, app domain, privacy policy URL, terms URL
   (the URLs must resolve before you submit for verification — a simple static page is enough)
4. Scopes: `email`, `profile`, `openid`. Nothing more — extra scopes trigger verification review
5. Credentials → Create OAuth client ID → **Web application**
6. Authorised redirect URI: the one Clerk gives you in step 3. Come back for this

**Yields:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`. Both go into Clerk, not into your app config.

The existing `installed` (desktop) client is not usable for mobile — ignore it. You only need
platform-specific iOS/Android clients if you ever drop Clerk for `expo-auth-session`.

---

## 3. Clerk

1. Create account, create application `Receptenapp`. **Two instances**: Development and Production
2. Enable Google: paste the client ID and secret from step 2, copy Clerk's redirect URI back into
   Google
3. Enable Apple: needs step 6 complete. Clerk asks for Services ID, Team ID, Key ID and a `.p8` private
   key — all generated in the Apple Developer portal
4. Sessions → set token lifetime. 7-day sessions with refresh is reasonable for a consumer app
5. Copy the JWKS URL and the publishable/secret keys for both instances

**Yields:**
- `CLERK_PUBLISHABLE_KEY` → Expo client, `app.config.ts` (public, safe)
- `CLERK_SECRET_KEY` → API, Key Vault
- `CLERK_JWKS_URL` → API config
- `CLERK_WEBHOOK_SECRET` → API, Key Vault (configure the webhook after the API is deployed)

---

## 4. Azure resources

You have `az` authenticated and `kladje-dev` exists. The agent can run the Bicep, but these are yours:

1. Confirm the subscription and quota allow a new Postgres Flexible Server in West Europe
2. Create resource group `kladje-prod`
3. **Choose and record the Postgres admin password** — put it straight into Key Vault, never in a file
4. Register the resource providers if the subscription is new: `Microsoft.DBforPostgreSQL`,
   `Microsoft.App`, `Microsoft.KeyVault`
5. After first deploy: add your own IP to the Postgres firewall so you can connect with `psql`

**Yields:** `DATABASE_URL`, `AZURE_STORAGE_ACCOUNT`, `KEYVAULT_NAME`, `ACR_NAME`.

---

## 5. OpenAI

1. Create an API key on a project scoped to this app — not your personal default project
2. **Request zero data retention** for the API account. Available on request; it materially simplifies
   your privacy statement and is the honest answer to "where does my TikTok go"
3. **Ask about EU data residency** while you're there. Note the 10% uplift applies only to models
   released on or after 5 March 2026, so GPT-4.1 mini avoids it (ADR-011)
4. Set a monthly spend limit. This is a real circuit breaker, not a formality
5. Set up billing alerts at 50% and 80%

**Yields:** `OPENAI_API_KEY` → Key Vault.

---

## 6. Apple Developer — do this first, it takes days

1. Enrol in the Apple Developer Program (€99/year). Approval can take 24–48 hours
2. Certificates, Identifiers & Profiles:
   - App ID with bundle identifier `nl.receptenapp.app` (or your choice — **record it, it's permanent**)
   - Enable capabilities: Sign in with Apple, App Groups, Push Notifications
   - **App Group** `group.nl.receptenapp.share` — this is how the share extension hands the URL to the
     app. Without it the core interaction doesn't work
   - Services ID for Sign in with Apple, plus a private key (`.p8`) → these go to Clerk in step 3
3. App Store Connect: create the app record, fill in metadata
4. **Enrol in the App Store Small Business Program.** Takes commission from 30% to 15%. This is worth
   €0,37 per subscriber per month for the cost of a form (see `docs/06-monetisation.md`)
5. Create the subscription product: `nl.receptenapp.premium.monthly`, €2,99/month, one group, one tier
6. Agreements, Tax and Banking must be complete or you cannot test purchases at all

**Yields:** bundle ID, App Group ID, Team ID, Apple `.p8` key + Key ID + Services ID, subscription
product ID.

---

## 7. Google Play

1. Play Console developer account (one-off $25)
2. Create the app, package name `nl.receptenapp.app` — **must match iOS bundle ID conventions and is
   permanent**
3. Enrol in the reduced service fee programme (15%)
4. Create the subscription product with the same ID as iOS: `nl.receptenapp.premium.monthly`
5. Set up a service account for EAS Submit, download the JSON key

**Yields:** package name, Play service account JSON → EAS secrets.

---

## 8. RevenueCat

1. Create project, add both iOS and Android apps
2. iOS: needs the App Store Connect shared secret and an in-app purchase key
3. Android: needs the Play service account JSON
4. Create entitlement `premium`, attach both store products to it
5. Configure the webhook to `https://<your-api>/v1/webhooks/revenuecat` — after the API is deployed
6. Copy the webhook signing secret

**Yields:** `REVENUECAT_PUBLIC_SDK_KEY` → client. `REVENUECAT_WEBHOOK_SECRET` → Key Vault.

---

## 9. Apify

You already have actor code, so this is mostly confirming access.

1. Create account, generate an API token
2. **Note the plan.** Free credits run out quickly; Starter is ~$39/month and is a fixed cost in the
   model (see `docs/01-architecture.md`)
3. Record the actor IDs you're using for TikTok, Instagram and YouTube
4. **Run one URL per platform by hand and save the raw JSON** into `api/tests/fixtures/apify/`. This is
   the single most useful thing you can do for the agent — everything downstream gets built against
   real response shapes rather than assumed ones

**Yields:** `APIFY_TOKEN` → Key Vault. Actor IDs → config. Raw fixtures → repo.

---

## 10. Expo / EAS

1. Expo account, create the project, record the project ID
2. `eas credentials` — generate iOS distribution certificate and provisioning profile, and the Android
   keystore. **Back up the Android keystore somewhere safe; losing it means you can never update the
   app again**
3. Configure `eas.json` with development, preview and production profiles
4. Add secrets: `eas secret:create` for the Play service account JSON

**Yields:** `EXPO_PROJECT_ID`, signing credentials held by EAS.

---

## 11. Sentry

1. Create project. **Choose the EU region at creation — it cannot be changed afterwards**
2. Separate projects for API and client

**Yields:** `SENTRY_DSN_API` → Key Vault. `SENTRY_DSN_APP` → client config.

---

## 12. Legal pages

These must exist as reachable URLs before store submission and before Google's consent screen review.

1. Privacy statement naming every sub-processor in `docs/07-legal-avg.md`
2. Terms of service including the notice-and-takedown route and a contact address
3. Host anywhere static — GitHub Pages is fine

**Yields:** two URLs, referenced in the app, both stores, and the Google consent screen.

---

## Environment variable contract

Everything the agent needs, in one place. `api/.env.example` should mirror this exactly.

```bash
# --- Core ---
ENVIRONMENT=dev                        # dev | prod
LOG_LEVEL=INFO
API_BASE_URL=https://receptenapp-api-dev.azurewebsites.net

# --- Database ---
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/receptenapp?ssl=require

# --- Auth (Clerk) ---
CLERK_SECRET_KEY=sk_test_...
CLERK_JWKS_URL=https://<slug>.clerk.accounts.dev/.well-known/jwks.json
CLERK_WEBHOOK_SECRET=whsec_...

# --- OpenAI ---
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4.1-mini              # pinned, see ADR-011
PROMPT_VERSION=1

# --- Apify ---
APIFY_TOKEN=apify_api_...
APIFY_ACTOR_TIKTOK=<actor-id>
APIFY_ACTOR_INSTAGRAM=<actor-id>
APIFY_ACTOR_YOUTUBE=<actor-id>
APIFY_TIMEOUT_SECONDS=45

# --- Storage ---
AZURE_STORAGE_ACCOUNT=dlskladjedevweu
AZURE_STORAGE_CONTAINER=recipe-media

# --- Billing ---
REVENUECAT_WEBHOOK_SECRET=...
FREE_IMPORTS_PER_30D=10
PREMIUM_IMPORTS_PER_PERIOD=100

# --- Limits ---
IMPORT_RATE_PER_MINUTE=5
IMPORT_RATE_PER_HOUR=30
DAILY_SPEND_ALERT_EUR=25

# --- Observability ---
SENTRY_DSN=https://...
APPLICATIONINSIGHTS_CONNECTION_STRING=...
```

Client config (`app/.env`, all public — these ship in the bundle):

```bash
EXPO_PUBLIC_API_BASE_URL=https://receptenapp-api-dev.azurewebsites.net
EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
EXPO_PUBLIC_REVENUECAT_IOS_KEY=appl_...
EXPO_PUBLIC_REVENUECAT_ANDROID_KEY=goog_...
EXPO_PUBLIC_SENTRY_DSN=https://...
```

---

## Things that will still interrupt the agent

Be realistic about these. Front-loading the steps above removes most interruptions, not all.

| Interruption | When | Why unavoidable |
|---|---|---|
| First device build | End of Phase 0 | Physical device, developer mode, trust profile |
| Share extension testing | Phase 3 | Simulator won't tell you if it works. Real phone, real TikTok app |
| Push notification testing | Phase 5 | Requires a real device and a real APNs token |
| Sandbox purchase testing | Phase 6 | Sandbox tester account, real device, manual purchase flow |
| Apify actor output surprises | Phase 2 | Mitigated by saving raw fixtures in step 9 |
| App Store rejection | Phase 7 | Assume one round. Reviewer notes prepared in advance help |
| Prompt quality judgement | Phase 2, ongoing | Someone has to read 40 recipes and say whether they're good. That someone is you |

That last one is worth sitting with. The eval script measures schema conformance and provenance
honesty, but whether a recipe is *good* — whether the steps make sense to cook from — is a human
judgement, and it's the judgement the whole product rests on. Budget real time for it.
