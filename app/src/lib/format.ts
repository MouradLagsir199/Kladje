import type { IngredientOut, RecipeSummary, Unit } from "@/api/types";
import { strings } from "@/strings/nl";

/**
 * Units that say nothing without a number.
 *
 * "ml groente olie" is not a line anyone would write, but a real TikTok import produced exactly
 * that: the source never said how much oil, so `amount` is null while `unit` survived. The vague
 * units are the opposite — "snuf zout" and "handvol rucola" read perfectly without a number.
 */
const MEASURES_NEEDING_AN_AMOUNT: Unit[] = ["g", "kg", "ml", "l", "el", "tl"];

/** Dutch decimal comma, and no trailing zeroes — "1,5 el", not "1.50 el". */
export function formatAmount(amount: number): string {
  const rounded = Math.round(amount * 100) / 100;
  return (Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(2).replace(/0+$/, "")) //
    .replace(".", ",");
}

export function totalMinutes(recipe: Pick<RecipeSummary, "prep_minutes" | "cook_minutes">) {
  if (recipe.prep_minutes === null && recipe.cook_minutes === null) return null;
  return (recipe.prep_minutes ?? 0) + (recipe.cook_minutes ?? 0);
}

/** The one-line summary under a card: "25 min · 4 pers." */
export function metaLine(recipe: RecipeSummary): string {
  const total = totalMinutes(recipe);
  const parts = [
    total === null ? null : strings.meta.minutes(total),
    strings.detail.servings(recipe.servings),
  ];
  return parts.filter(Boolean).join(" · ");
}

/**
 * An ingredient as one readable line, scaled to the servings the user is looking at.
 *
 * Scaling multiplies the amount and nothing else: a "snuf zout" stays a snuf, and an ingredient
 * with no amount at all keeps its wording. Guessing what half a bosje peterselie is would be
 * inventing a value.
 */
export function ingredientLine(ingredient: IngredientOut, scale = 1): string {
  const unitIsMeaningless =
    ingredient.amount === null &&
    ingredient.unit !== null &&
    MEASURES_NEEDING_AN_AMOUNT.includes(ingredient.unit);
  const unit = ingredient.unit && !unitIsMeaningless ? strings.unit[ingredient.unit] : "";

  const quantity =
    ingredient.amount === null
      ? ""
      : ingredient.amount_max === null
        ? formatAmount(ingredient.amount * scale)
        : `${formatAmount(ingredient.amount * scale)}–${formatAmount(ingredient.amount_max * scale)}`;

  // "naar smaak" reads as a suffix in Dutch, not a unit in front of the name.
  const head =
    ingredient.unit === "naar_smaak"
      ? ingredient.name_nl
      : [quantity, unit, ingredient.name_nl].filter(Boolean).join(" ");

  const tail = [
    ingredient.unit === "naar_smaak" ? unit : null,
    ingredient.qualifier,
    ingredient.optional ? strings.optional : null,
  ].filter(Boolean);

  return tail.length ? `${head}, ${tail.join(", ")}` : head;
}

/** The grey caption under a converted line: what the source actually said. */
export function originalLine(ingredient: IngredientOut): string | null {
  if (ingredient.original_amount === null && !ingredient.original_unit) return null;
  return [
    ingredient.original_amount === null ? null : formatAmount(ingredient.original_amount),
    ingredient.original_unit,
  ]
    .filter(Boolean)
    .join(" ");
}
