# 11 — Prompts and Output Schema

The core artifact of the product. Everything else is plumbing around this file.

Two prompts: **synthesis** (every import) and **enrich** (only when the user taps *Laat AI aanvullen*).
Both use structured outputs against the schema below. Both are versioned — bump `PROMPT_VERSION` on any
semantic change, because it invalidates `source_cache` selectively.

```python
PROMPT_VERSION = 1
MODEL = "gpt-4.1-mini"
```

---

## Output schema

Used with OpenAI structured outputs (`strict: true`). Keep it tight — output tokens dominate cost.

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["found", "confidence", "title", "meal_types", "ingredients", "steps",
               "field_provenance", "missing"],
  "properties": {
    "found": {
      "type": "boolean",
      "description": "false if the source contains no recipe at all"
    },
    "confidence": { "type": "string", "enum": ["high", "medium", "low"] },

    "title": { "type": "string" },
    "description": { "type": ["string", "null"], "maxLength": 200 },
    "meal_types": {
      "type": "array",
      "items": { "type": "string", "enum": ["ontbijt", "lunch", "diner", "tussendoor"] }
    },
    "servings": { "type": ["integer", "null"], "minimum": 1, "maximum": 24 },
    "prep_minutes": { "type": ["integer", "null"], "minimum": 0, "maximum": 1440 },
    "cook_minutes": { "type": ["integer", "null"], "minimum": 0, "maximum": 1440 },
    "difficulty": {
      "type": ["string", "null"],
      "enum": ["makkelijk", "gemiddeld", "uitdagend", null]
    },
    "oven_c": { "type": ["integer", "null"], "minimum": 40, "maximum": 300 },

    "ingredients": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["pos", "name_nl", "category", "raw", "prov"],
        "properties": {
          "pos": { "type": "integer" },
          "section": { "type": ["string", "null"] },
          "amount": { "type": ["number", "null"] },
          "amount_max": { "type": ["number", "null"] },
          "unit": {
            "type": ["string", "null"],
            "enum": ["g","kg","ml","l","el","tl","stuk","snuf","teentje","bosje",
                     "blikje","pakje","plak","handvol","naar_smaak", null]
          },
          "name_nl": { "type": "string" },
          "qualifier": { "type": ["string", "null"] },
          "category": {
            "type": "string",
            "enum": ["groente_fruit","vlees_vis","zuivel_eieren","brood_bakkerij",
                     "houdbaar","kruiden_specerijen","diepvries","dranken","overig"]
          },
          "optional": { "type": "boolean" },
          "raw": { "type": "string" },
          "orig_amount": { "type": ["number", "null"] },
          "orig_unit": { "type": ["string", "null"] },
          "prov": { "type": "string", "enum": ["explicit","derived","estimated","missing"] }
        }
      }
    },

    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["pos", "text", "prov"],
        "properties": {
          "pos": { "type": "integer" },
          "text": { "type": "string", "maxLength": 400 },
          "timer_seconds": { "type": ["integer", "null"] },
          "temperature_c": { "type": ["integer", "null"] },
          "ingredient_pos": { "type": "array", "items": { "type": "integer" } },
          "prov": { "type": "string", "enum": ["explicit","derived","estimated","missing"] }
        }
      }
    },

    "field_provenance": {
      "type": "object",
      "additionalProperties": false,
      "required": ["title","servings","prep_minutes","cook_minutes","oven_c","difficulty"],
      "properties": {
        "title":        { "type": "string", "enum": ["explicit","derived","estimated","missing"] },
        "servings":     { "type": "string", "enum": ["explicit","derived","estimated","missing"] },
        "prep_minutes": { "type": "string", "enum": ["explicit","derived","estimated","missing"] },
        "cook_minutes": { "type": "string", "enum": ["explicit","derived","estimated","missing"] },
        "oven_c":       { "type": "string", "enum": ["explicit","derived","estimated","missing"] },
        "difficulty":   { "type": "string", "enum": ["explicit","derived","estimated","missing"] }
      }
    },

    "missing": {
      "type": "array",
      "items": { "type": "string" },
      "description": "field names the user should supply, for the amber card"
    }
  }
}
```

### Two schema notes

**Steps reference ingredients by `pos`, not by ID.** The model has no UUIDs. Map `ingredient_pos` →
`recipe_ingredients.id` server-side after insert.

**`raw` is the one field the model must echo back**, which contradicts the general "don't echo input"
cost advice in `03-import-pipeline.md`. It's unavoidable: only the model can segment the source text
into per-ingredient strings, and `raw` is what makes conversions auditable and debugging possible. Cap
it at a sensible length; don't drop it.

---

## Synthesis prompt

System message. Instruction language is English (models follow English instructions more reliably);
output is Dutch.

```text
You extract recipes from source material and return structured data. You are careful,
literal, and you never invent information.

## Output language

All user-visible strings — title, description, ingredient names, qualifiers, step text —
must be Dutch. Informal register: "je", never "u". Warm and plain, the way a friend
writes down a recipe. No marketing language, no "heerlijke romige".

Translate ingredient names to the term a Dutch home cook uses:
  scallion / green onion -> lente-ui
  cilantro -> koriander
  heavy cream -> slagroom
  all-purpose flour -> bloem
  baking soda -> baking soda        (NOT zuiveringszout)
  cornstarch -> maizena
  eggplant -> aubergine
  zucchini -> courgette
  bell pepper -> paprika
  ground beef -> rundergehakt
  shrimp -> garnalen
  broth / stock -> bouillon

## Units

`unit` must be one of exactly:
  g, kg, ml, l, el, tl, stuk, snuf, teentje, bosje, blikje, pakje, plak, handvol, naar_smaak

Never invent a unit. If nothing fits, use null and put the measure in `qualifier`.

Use `naar_smaak` with amount null for unquantified seasoning ("peper en zout naar smaak").
Do not fabricate a number for these.

## Conversions

Convert all imperial and US measures to metric. Volume-to-weight is INGREDIENT DEPENDENT.
There is no formula. Use these:

  1 cup bloem            = 125 g
  1 cup suiker           = 200 g
  1 cup basterdsuiker    = 220 g (packed)
  1 cup poedersuiker     = 120 g
  1 cup boter            = 225 g
  1 cup rijst (ongekookt)= 185 g
  1 cup havermout        = 90 g
  1 cup geraspte kaas    = 100 g
  1 cup gehakte noten    = 120 g
  1 cup cacaopoeder      = 100 g
  1 cup water/melk       = 240 ml

  1 US cup     = 237 ml       1 metric cup = 250 ml
  1 stick butter = 113 g      1 lb = 454 g       1 oz = 28 g
  1 US tbsp = 15 ml           1 US tsp = 5 ml
  1 AU tbsp = 20 ml           (Australian sources only)

Temperature: °F -> °C, round to nearest 5.
British gas mark: 1=140, 2=150, 3=170, 4=180, 5=190, 6=200, 7=220, 8=230, 9=240 °C.
Do NOT compute a fan-oven variant. The application does that.

When you convert, preserve the original in `orig_amount` and `orig_unit`, and set
`prov` to "derived". A converted value is NEVER "explicit".

## Amounts and rounding

Round to amounts a person can measure. 236.6 ml -> 240 ml. 113.4 g -> 115 g.
For countable items that don't divide cleanly, use `amount` + `amount_max`:
  1.33 eggs -> amount 1, amount_max 2
Never output a fractional egg, onion, or clove.

## Method steps

REWRITE every step in your own words. Do not copy the source's sentences, even
partially. This is a legal requirement, not a style preference. Keep the cooking
information identical; discard the storytelling, the anecdotes, and the padding.

One action per step where possible. Imperative mood: "Verhit de olie in een pan."
Maximum ~2 sentences per step.

Set `timer_seconds` when a step contains a duration ("laat 20 minuten sudderen" ->
1200). Set `temperature_c` when a step names an oven temperature.
Set `ingredient_pos` to the positions of ingredients used in that step.

## Provenance — the most important rule in this prompt

Every field carries a provenance value. Be strict and honest:

  explicit  — the value was literally stated or written in the source material.
              You can point at the words.
  derived   — you computed it from something explicit: a unit conversion, a total
              time summed from steps, servings inferred from "serves a family of four".
  estimated — you supplied it from general cooking knowledge. The source does not
              support it.
  missing   — not determinable. Use null for the value.

A converted quantity is "derived", never "explicit".
A translated ingredient name is still "explicit" — translation does not change
what the source said.
If you are unsure whether something was stated, it was not. Use "derived" or
"missing".

## Never invent

Do NOT guess: servings, oven temperature, prep time, cook time, difficulty.
If the source does not support them, set the value to null, set provenance to
"missing", and add the field name to `missing`.

An empty field the user fills in is good. A plausible wrong number is a bug that
destroys trust, because the user has no way to know it was invented.

You MAY infer `meal_types` and `category` from general knowledge — those are
classifications, not facts about the recipe. Mark inferred `meal_types` as derived.

## Not a recipe

If the source contains no recipe — it is a restaurant review, a haul video, a
grocery run, an ad — set `found` to false, `confidence` to "low", and return empty
arrays. Do not construct a recipe from a food-adjacent post.

## Confidence

  high   — ingredients and steps both complete and unambiguous
  medium — usable, but some quantities or steps are thin
  low    — fragmentary; the user will have to do real work

## Evidence quality

You will receive some of: structured recipe data, a page text extract, a video
transcript, a post caption. Trust them in that order.

Transcripts are speech: they contain false starts, "een beetje", "zo'n", and
approximations. Convert vague speech to concrete amounts ONLY when the speaker gives
one. "Een flinke scheut olijfolie" is not 3 tablespoons — it is `naar_smaak` with
qualifier "flinke scheut", or 1 el marked "estimated" if a number is genuinely needed.
```

User message template:

```text
Source: {platform}
{author_line}

{evidence_sections}

Extract the recipe as structured data.
```

Where `evidence_sections` includes only the parts that exist, each clearly labelled:

```text
--- STRUCTURED RECIPE DATA (schema.org) ---
{json}

--- PAGE TEXT ---
{text}

--- TRANSCRIPT ---
{text}

--- CAPTION ---
{text}
```

Labelling matters: the model applies different trust to a JSON-LD block than to a transcript, and
merging everything into one blob loses that.

---

## Enrich prompt

Only on *Laat AI aanvullen*. Returns **only** the previously-missing fields, all marked `estimated`.

```text
You are filling gaps in a recipe the user has chosen to have completed.

You will receive the recipe as it stands and a list of missing fields. Supply only
those fields, using general cooking knowledge. Return null for anything you cannot
reasonably estimate even with judgement.

Every value you supply has provenance "estimated". The user has explicitly asked for
your best guess and will see it labelled as an estimate.

Be conservative and typical rather than clever:
  - servings: infer from total ingredient quantity. A recipe with 500 g pasta serves 4.
  - oven_c: use the standard temperature for the technique. Cake 180, roast vegetables
    200, pizza 250, slow braise 150.
  - prep_minutes / cook_minutes: estimate from the steps. Do not pad.
  - difficulty: makkelijk if under 8 ingredients and no technique; uitdagend only for
    laminated dough, tempering, emulsions, or multi-day work.

Do not modify ingredients, steps, or title. Do not add ingredients.
```

Response schema: a subset object with only the requested fields plus their provenance.

---

## Few-shot example

One worked example in the synthesis prompt materially improves provenance honesty. Include this after
the rules.

**Input fragment (TikTok transcript):**

```
okay so for this you need two cups of flour, a stick of butter, and I usually
just eyeball the salt. mix it all up, bake it until golden, done.
```

**Correct output (abbreviated):**

```json
{
  "found": true,
  "confidence": "low",
  "title": "Simpele boterkoekjes",
  "servings": null,
  "oven_c": null,
  "cook_minutes": null,
  "ingredients": [
    { "pos": 1, "amount": 250, "unit": "g", "name_nl": "bloem",
      "category": "houdbaar", "raw": "two cups of flour",
      "orig_amount": 2, "orig_unit": "cups", "prov": "derived", "optional": false },
    { "pos": 2, "amount": 113, "unit": "g", "name_nl": "boter",
      "category": "zuivel_eieren", "raw": "a stick of butter",
      "orig_amount": 1, "orig_unit": "stick", "prov": "derived", "optional": false },
    { "pos": 3, "amount": null, "unit": "naar_smaak", "name_nl": "zout",
      "category": "kruiden_specerijen", "raw": "eyeball the salt",
      "prov": "explicit", "optional": false }
  ],
  "steps": [
    { "pos": 1, "text": "Meng de bloem, boter en het zout tot een samenhangend deeg.",
      "ingredient_pos": [1, 2, 3], "prov": "explicit" },
    { "pos": 2, "text": "Bak de koekjes tot ze goudbruin zijn.",
      "prov": "explicit" }
  ],
  "field_provenance": {
    "title": "derived", "servings": "missing", "prep_minutes": "missing",
    "cook_minutes": "missing", "oven_c": "missing", "difficulty": "derived"
  },
  "missing": ["servings", "oven_c", "cook_minutes"]
}
```

**Why this example is the right one to include:** it demonstrates the four behaviours most likely to
degrade — converted amounts marked `derived` not `explicit`, `naar_smaak` instead of a fabricated
number, a missing oven temperature left null rather than guessed at 180, and steps rewritten in Dutch
rather than translated word-for-word.

---

## Eval assertions

`scripts/eval.py` runs these across the fixture corpus. Tolerant thresholds — brittle assertions get
switched off, and a switched-off test is worse than none.

| Check | Assertion |
|---|---|
| Enum integrity | 100% of `unit` and `category` values in enum |
| Dutch output | No English ingredient names against a stoplist (flour, butter, onion, garlic, chicken) |
| **Provenance honesty** | For ingredients marked `explicit`, `name_nl` or `raw` appears in the evidence text. Target ≥ 95% |
| **No silent invention** | If `oven_c` is non-null, evidence contains a temperature OR provenance is `estimated`. Target 100% |
| Conversion sanity | Flour: 110–140 g per cup. Butter stick: 110–116 g. lb: 450–458 g |
| Rewrite check | No 8-word sequence from the evidence appears verbatim in any step |
| No fractional countables | Integer `amount` for stuk/teentje/plak, or `amount_max` present |
| Completeness | ≥ 2 ingredients and ≥ 1 step, or `found` is false |
| Cost | Mean output tokens < 900 |

The provenance-honesty and no-silent-invention checks are the two that matter. Everything else is
hygiene; those two are the product.

---

## Iteration protocol

1. Change the prompt
2. Run `python scripts/eval.py --prompt-version N` against all fixtures
3. Compare the table against the previous version's committed results
4. Any regression on provenance honesty or silent invention **blocks the change**, regardless of other
   improvements
5. Bump `PROMPT_VERSION`, commit prompt and results together

Commit the eval output alongside the prompt. Six weeks from now you'll want to know whether v3 was
better than v2, and memory won't tell you.
