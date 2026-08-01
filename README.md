# Receptenapp — Technical Plan

Working name: **Receptenapp** (sibling product: **Prakkie**, which owns supermarket prices and product matching).

Dutch-market mobile app that imports recipes from TikTok, Reels, YouTube, Pinterest and food blogs,
normalises them to Dutch ingredients and metric units, and supports week planning, a price-free
shopping list, and sharing in small groups.

## Documents

| File | Contents |
|---|---|
| [00-scope.md](00-scope.md) | What the app is, what it explicitly is not, decision log from the design interview |
| [01-architecture.md](01-architecture.md) | System architecture, Azure resources, environments, deployment |
| [02-datamodel.md](02-datamodel.md) | Postgres schema, enums, migrations, indexing |
| [03-import-pipeline.md](03-import-pipeline.md) | The core feature: fetch → transcribe → OCR → synthesise → review |
| [04-api.md](04-api.md) | REST surface, SSE progress stream, auth, error contract |
| [05-client.md](05-client.md) | Expo app structure, navigation, share extension, caching, screen inventory |
| [06-monetisation.md](06-monetisation.md) | Free/paid tiers, quota accounting, RevenueCat, store rules, unit economics |
| [07-legal-avg.md](07-legal-avg.md) | GDPR/AVG, sub-processors, copyright, platform ToS, App Review strategy |
| [08-roadmap.md](08-roadmap.md) | Phased build plan, milestones, cost model, break-even |
| [09-decisions-adr.md](09-decisions-adr.md) | Architecture decision records, including the ones I decided for you |
| [10-phase2-workplan.md](10-phase2-workplan.md) | Detailed Phase 2 breakdown: import quality across platforms |
| [11-prompts.md](11-prompts.md) | **The actual prompts, output schema, few-shot, eval assertions** |
| [12-manual-setup.md](12-manual-setup.md) | Human-only setup: accounts, credentials, env var contract |
| [13-build-tasks.md](13-build-tasks.md) | ~90 atomic tasks, dependency-ordered, with verify commands |
| [14-design-tokens.md](14-design-tokens.md) | Colour, type, spacing extracted from the prototype |
| [CLAUDE.md](CLAUDE.md) | Agent instructions — goes at repo **root**, not in docs/ |
| [KICKOFF.md](KICKOFF.md) | **The prompt to paste into Claude Code to start the build** |
| [prototype/](prototype/) | The clickable prototype + original Dutch screen spec. Visual source of truth |

## Handing this to an agent

`CLAUDE.md` belongs at the **repository root**; everything else goes in `docs/`. Before starting the
build, work through `12-manual-setup.md` in one sitting — it's the set of things an agent cannot do
(accounts, credentials, signing certificates, store products), and front-loading it buys long
uninterrupted agent runs afterwards.

**To start:** put `CLAUDE.md` at the repo root, this folder in `docs/`, then paste `KICKOFF.md` into
Claude Code. It will read the plan and come back with a consolidated list of every credential it needs
before writing any code.

Not written, and deliberately left to the agent: the Bicep templates (task 0.6) and full per-endpoint
response schemas (the agent generates these from the Pydantic models, and FastAPI publishes the
OpenAPI spec for free).

## Reading order

If you only read two: `00-scope.md` then `03-import-pipeline.md`. The import pipeline is the product;
everything else is scaffolding around it.

## Status of open questions

Three decisions were still open when this plan was written. I made them and documented the reasoning
in `09-decisions-adr.md` — ADR-006 (auth provider), ADR-007 (API language), ADR-008 (compute runtime).
Override any of them; the rest of the plan holds either way.

No open questions remain. Cookbook-photo OCR was the last one and is now **in v1**, built at the end of
Phase 2 — see `10-phase2-workplan.md` §2.9.

## Docs are in English, product is in Dutch

Technical documentation is English so it works cleanly with tooling and libraries. All user-facing
copy, enum labels shown to users, and the existing screen specification stay Dutch, informal register,
never "u".
