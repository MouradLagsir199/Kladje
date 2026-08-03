# status.html — the build-status page

`docs/status.html` is the source of the shared build-status page:

<https://claude.ai/code/artifact/f9fbbf88-b8cd-4cff-9228-1328cc94a422>

It lives in the repo so it cannot be lost. Publishing it is a separate step from committing it —
editing this file changes nothing until it is republished **to that same URL**. A publish without
the URL mints a new one, and then there are two pages disagreeing about the state of the project.

## What it is for

It answers "where is this?" for someone who has not read `13-build-tasks.md`. So it leads with
whether the product does its job — the four legs of the MVP loop — rather than a task count, which
measures effort rather than progress.

Two things to keep true when editing:

- **Never mark a leg "works" on the strength of a passing test.** Every one of those claims is
  backed by a real run against a real URL. A green unit test is not the same statement.
- **Keep "Needs from you" honest, including when it is empty.** Inventing an ask to fill the box
  trains the reader to skip it.

## Styling

Colours and type come from `14-design-tokens.md`, same as `app/src/theme/tokens.ts`. The three
status colours are deliberately the app's own provenance colours — green for stated, amber for
in-flight, red for blocked — so the page and the product mean the same thing by the same hue.

The page is self-contained: a strict CSP blocks external CSS, fonts and scripts, which is why the
type stack is system faces rather than Schibsted Grotesk.
