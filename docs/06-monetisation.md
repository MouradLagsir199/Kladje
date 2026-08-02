# 06 — Monetisation, Quota and Unit Economics

## The tiers

| | Free | Premium |
|---|---|---|
| Price | €0 | €2,99 / month |
| Imports | 10 per rolling 30 days | 100 per billing month |
| Everything else | Unlimited | Unlimited |

Library size, planner, shopping list, groups, cook mode: **unlimited on both tiers.** The only metered
resource is the only expensive one. This is the right model — it's honest, it's easy to explain in one
sentence, and it never punishes someone for using the app you want them using.

## Read this before anything else: the economics

Three corrections to an earlier version of this document, one of which is against you.

**VAT comes off before commission.** €2,99 is the price the user sees, VAT included. Dutch VAT at 21%
means €2,47 ex-VAT, and the store commission applies to that:

| | Commission | Net to you |
|---|---|---|
| Standard rate | 30% | **€1,73** |
| Small Business Program | 15% | **€2,10** |

Enrol in the **App Store Small Business Program** and Google Play's equivalent reduced rate before
launch. Below $1M annual revenue it takes commission from 30% to 15%, worth €0,37 per subscriber per
month for the cost of filling in a form.

**Apify supplies the transcript, and there is no OCR in the link-import path.** Two whole stages gone —
transcription and frame OCR — leaving one model call per import. See `03-import-pipeline.md`; the headline
is **~€0,005 per import** on GPT-4.1 mini, down from the €0,012–0,015 this document previously assumed.

**So the paid tier is comfortable, not tight:**

| Scenario | 100 imports cost | Net at 30% | Net at 15% |
|---|---|---|---|
| Realistic subscriber (10–15 imports/mo, mixed sources) | €0,05–0,08 | €1,73 | €2,10 |
| Heavy user, 100 imports, all TikTok, no cache hits | ~€0,50 | €1,73 | €2,10 |
| Same, if you switched to a frontier-tier model | €3,00–5,00 | **loss** | **loss** |

Margin at the cap is ~65% on the standard rate and ~71% on the small-business rate. Margin for a
typical subscriber is above 95%. The 100-import cap is doing exactly the job it should: bounding a tail
that would otherwise be unbounded, at a level well inside your net revenue.

**Free tier costs you about €0,05 per user per month** at 10 imports. That is cheap enough that the
permanent free tier is unambiguously worth it — free users stay in your groups feature, and invite links
are the only organic growth mechanism in the plan.

**The one thing that breaks this** is model tier drift. A casual switch to a frontier model makes the
paid tier lose money at the cap. Pin the model name in config, record it in `source_cache`, and keep the
daily-spend alert from `01-architecture.md` as a hard circuit breaker. See ADR-011.

**Fixed costs now dominate variable costs by an order of magnitude.** At 250 subscribers you'd spend
maybe €15/month on imports against ~€130 of infrastructure. That reframes where to spend attention:
per-import optimisation past this point is not worth your time, and break-even is set almost entirely by
your Azure and Apify bills. Break-even sits at roughly **50 subscribers** on the standard rate, or **41**
on the small-business rate.

## Quota accounting

Derived by counting rows, never a stored counter (see `02-datamodel.md`).

### Free tier — rolling 30 days

```sql
SELECT count(*) FROM imports
WHERE user_id = $1
  AND counted_against_quota
  AND created_at > now() - INTERVAL '30 days';
```

A rolling window rather than a calendar month. Reason: a calendar month means someone who signs up on
the 28th gets 10 imports for three days, feels cheated, and churns before ever reaching the aha-moment.
Rolling is fairer and it's the same one-line query.

The client needs to show a reset date, so surface `resets_at` = the timestamp of the oldest counted
import in the window, plus 30 days. That's the moment one import frees up.

### Premium — per billing period

Counted within `subscriptions.period_start` → `period_end` as reported by RevenueCat, so the user's
allowance resets exactly when they're charged. Anything else generates support mail.

### What counts

| Event | Counts? | Reasoning |
|---|---|---|
| Successful import, saved | **Yes** | |
| Successful import, abandoned at review | **Yes** | You paid for the pipeline run |
| `low_confidence` partial draft | **Yes** | User got a usable draft |
| Cache hit | **Yes** | You delivered the value; cost is your win, not theirs |
| Duplicate of a recipe the user already has | **No** | No pipeline run, no new value |
| Any `failed` status | **No** | Never charge for your own failure |
| `cancelled` by user during progress | **No** | Even though you may have partially paid |
| Manual entry | **No** | Costs nothing, and you *want* this behaviour |
| Editing an existing recipe | **No** | |
| *Laat AI aanvullen* on an existing import | **No** | Second call on an already-counted import |

Set `counted_against_quota` at the moment the import reaches `ready_for_review`, in the same
transaction. Not at creation — otherwise a scraper outage silently eats free users' allowance and you
get one-star reviews you can't argue with.

### Enforcement

Check quota at `POST /v1/imports`, before any paid call. Return `429`/`403` with `quota_exceeded` and
the paywall payload. Also re-check server-side at the moment of the first paid call, because a
double-tapped share can slip two requests past a naive check — the `Idempotency-Key` handles the
duplicate, but the ordering still needs care.

Never enforce quota only in the client. Obvious, and worth writing down.

## Store mechanics

**In-app purchase is mandatory** for a subscription that unlocks in-app functionality. Both Apple and
Google require it, and attempting to route around it with your own checkout is a rejection. iDEAL via
Mollie or Adyen — which the original spec mentions — is only relevant if you later sell via a website,
and it isn't worth the complexity for a €2,99 subscription.

One nuance worth knowing: EU DMA rules now permit steering users to external purchase options on iOS in
the EU, and Apple's associated fee structure makes this occasionally worthwhile. It is **not** worth it
at €2,99 and at your scale. Revisit above roughly a thousand subscribers.

**RevenueCat** sits in front of both stores (ADR-010). What it does that matters:

- Receipt validation for both platforms without you writing it
- One entitlement concept across iOS and Android
- Webhooks for renewals, cancellations, billing retries, grace periods, refunds
- Free below $2.5k monthly tracked revenue, which is well past your break-even

Flow: client purchases via RevenueCat SDK → RevenueCat validates → webhook to
`POST /v1/webhooks/revenuecat` → API updates `subscriptions` and `users.tier`. The client also refreshes
entitlement on foreground, so a webhook delay never leaves someone locked out of what they just bought.

Signature-verify the webhook against a Key Vault secret. An unauthenticated endpoint that grants
entitlements is exactly the endpoint someone will find.

### Grace and downgrade

- Billing retry / grace period → keep premium active, `in_grace_period = true`. Apple and Google both
  recover a meaningful share of these
- Expired → `tier = free`. Recipes above any count are **never** locked; the user simply returns to 10
  imports per 30 days. Holding a user's own recipes hostage is both hostile and, given they're personal
  data the user created, legally messy
- Refund webhook → immediate downgrade

## Paywall

Shown at three moments, and nowhere else:

1. Import attempt with quota exhausted — the highest-intent moment there is
2. Tapping the subscription card in Profiel
3. At import 8 of 10, as a soft, dismissible notice — not a wall

The screen itself: one line of value ("100 imports per maand"), the price, the two buttons Apple
requires (subscribe, restore purchases), and links to terms and privacy. Apple rejects paywalls missing
restore-purchases or the subscription terms disclosure with tedious reliability.

### On the 30-day framing — confirmed

**The free tier is permanent. The 10-import allowance is what expires**, resetting on a rolling 30-day
window. Not a trial that ends.

This is the right model. A permanent free tier keeps non-paying users inside your groups feature, which
is the only organic growth mechanism in the plan — someone shares an invite link and brings in a whole
household. A trial that expires would cut that off at exactly the moment it starts working. And it
costs you roughly €0,05 per free user per month, which is a rounding error against the referral value.

Implementation reminder from the quota section above: rolling window, and surface `resets_at` as the
timestamp of the oldest counted import plus 30 days, so the user can see when one frees up.

## Instrumentation you cannot skip

Two dashboards, and they're both about survival rather than growth:

**Cost**: OpenAI spend per day, per import, per platform; cache hit rate; `silent_video` failure rate;
cost per active subscriber.
With a hard alert if daily spend exceeds a ceiling you set. That alert is a circuit breaker against a
bug or an abusive client, and without it a runaway loop can spend a month's revenue overnight.

**Conversion**: free users hitting the quota wall, paywall views, conversion rate, month-1 retention of
subscribers. If conversion off the quota wall is under a few percent, the problem is almost never the
price — it's that import quality wasn't good enough for the first ten to feel worth paying for.
