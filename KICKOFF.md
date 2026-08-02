# KICKOFF — paste this into Claude Code to start the build

Put `CLAUDE.md` at the repo root and this whole folder in `docs/`. Then start a session and paste
everything below the line.

---

You are building **Receptenapp**, a Dutch recipe app, from a complete written plan. I am a solo
developer. Your job is to build it with as few interruptions to me as possible, while stopping cleanly
whenever you genuinely need something only I can provide.

## Start here

1. Read `CLAUDE.md` at the repo root. It contains the conventions, the ten non-negotiables, the
   definition of done, and a list of decisions you should not re-litigate.
2. Read `docs/README.md`, then `docs/00-scope.md`, then `docs/13-build-tasks.md`.
3. Skim the rest of `docs/` so you know what's in each file. Read `docs/03-import-pipeline.md` and
   `docs/11-prompts.md` in full before starting Phase 1 — the import pipeline is the product.
4. Do **not** start coding until you have done the above and given me the plan check below.

## Before you write any code — give me a plan check

Reply with:

- A one-paragraph statement of what you understand the product to be
- The first 5 tasks you'll do, by ID
- **A single consolidated list of every credential, account, ID, and human action you will need before
  you hit your first blocker**, in the order you'll need them. Take this from `docs/12-manual-setup.md`
  and from reading the task list. Tell me which ones I need to have ready *now* versus later
- Anything in the plan that is ambiguous, contradictory, or that you think is wrong

Then stop and wait for me.

## How to work after that

- Work through `docs/13-build-tasks.md` in ID order.
- For each task: implement it, satisfy its acceptance criteria, run its verify command, then commit
  with `feat(scope): description (task N.N)`.
- Run the verify command. Don't tell me something works because it looks right.
- After each task, give me one line: task ID, what you did, verify result. Nothing longer unless
  something went wrong.
- At the end of each phase, stop at the **gate** task and report against the gate criteria before
  continuing.

## When to stop and ask me

Stop and ask — clearly, naming exactly what you need and where you'll put it — when:

- You need a credential, API key, account, dashboard action, or store configuration. Tasks marked 🔑 in
  the task list. **Ask for it in the exact env-var name from `docs/12-manual-setup.md`**, tell me where
  to get it, and tell me whether it goes in `.env`, Key Vault, or a third-party dashboard
- A task is marked 📱 and needs a physical device. Tell me precisely what to test and what a pass looks
  like
- You'd contradict an ADR in `docs/09-decisions-adr.md`. Cite the ADR number and make your case
- Apify's real response shape differs from what the plan assumes
- A migration would be destructive to existing data
- The plan is ambiguous in a way that would cost more than an hour to redo

Batch credential requests where you can. If tasks 0.6, 0.9 and 1.6 all need keys, ask for all three at
once when you reach 0.6 rather than stopping three times.

## When not to stop

Decide and move on: naming, file layout within the conventions, which library to use for something
uncontroversial, whether to write a test, how to phrase Dutch UI copy. Don't ask permission to do the
task you were given.

## Hard rules

These come from `CLAUDE.md`. The ones you're most likely to violate by accident:

1. **No secrets in the repo.** Config from env vars, production values from Key Vault. If I paste a key
   into chat, put it in `.env` (gitignored) and tell me to rotate it if it was ever exposed
2. **Every query filters by the authenticated user's id.** No exceptions except `source_cache`
3. **Never invent recipe values.** Missing means null plus `missing` provenance. Read the provenance
   rules in `docs/11-prompts.md` and treat them as the most important spec in the project
4. **Method steps are always AI-rewritten**, never copied from the source. Legal requirement
5. **No supermarket data, prices, or product matching.** That's a different app
6. **No OCR or vision anywhere in v1.** Cookbook-photo import is deferred to v2 on cost grounds — see
   the update to ADR-014
7. **Model name and prompt version are pinned in config.** Don't upgrade the model to "improve quality"
   without running `scripts/eval.py` and checking the cost table
8. **Never call paid APIs in tests or CI.** Fixtures only
9. Don't add Redis, a queue, a sync engine, or pgvector. Each is explicitly rejected in an ADR

## Two things that decide whether this product is good

Everything else is furniture, so give these disproportionate care:

**The provenance system.** Every extracted field carries green / amber / red honesty about where it came
from. There is no jump-to-source feature, so these dots are the *entire* trust mechanism. A model that
marks a converted quantity as `explicit`, or invents a plausible oven temperature, silently destroys the
thing the product is built on. The eval assertions in `docs/11-prompts.md` exist for exactly this.

**The review screen** (prototype variant A). It's where the user decides whether to trust the import.
Build it carefully and don't simplify it.

## The prototype is the visual source of truth

`docs/prototype/Receptenapp.dc.html` is a working clickable prototype of the whole app — every tab,
the import flow, cook mode, the planner. It's a single inline-styled HTML file, so every screen is
readable as markup with its exact paddings, weights, colours and Dutch wording.

`docs/14-design-tokens.md` gives you the values. The prototype gives you the layout. **Before building
any screen, open the prototype and find it.** Don't invent a layout for a screen that already exists.

Two deliberate divergences from the prototype, both explained in the tokens file: the provenance dot
goes from 5px to 8px and must never be colour-alone, and the photo tile's "Kies frame" overlay becomes
tap-to-replace-from-gallery, because frame extraction was cut with ffmpeg (ADR-014).

`docs/prototype/receptenapp-schermspecificatie.md` is the original Dutch screen spec. It predates
several decisions — it still contains supermarket prices, jump-to-source, and audio transcription, all
of which are cut. Where it conflicts with `docs/`, `docs/` wins. Read it for tone and intent, not scope.

## Where I am right now

I have completed: *(tell the agent — e.g. "nothing yet" / "steps 1–5 of docs/12-manual-setup.md" /
"Apple enrolment submitted, waiting")*

Available to you immediately: *(list what you already have — e.g. Azure CLI authenticated,
resource group `kladje-dev`, Apify actor code at `<path>`, Google OAuth client)*

Begin with the plan check.
