export type PlanTier = "free" | "premium";

export type UserOut = {
  id: string;
  email: string | null;
  email_verified: boolean;
  display_name: string | null;
  avatar_url: string | null;
  household_size: number;
  locale: string;
  tier: PlanTier;
  created_at: string;
};

export type PreferencesOut = {
  diets: string[];
  allergens: string[];
  default_servings: number;
  show_original_units: boolean;
  fan_oven_default: boolean;
  notif_cooking: boolean;
  notif_defrost: boolean;
  notif_group: boolean;
  updated_at: string;
};

export type QuotaOut = {
  used: number;
  limit: number;
  resets_at: string | null;
  tier: PlanTier;
};

export type MeResponse = {
  user: UserOut;
  preferences: PreferencesOut;
  quota: QuotaOut;
};

// --- Recipes -------------------------------------------------------------------------------
// Mirrors the enums in api/src/receptenapp/db/models.py. These are append-only on the server, so
// widening one here is safe; removing a member is not.

export type Provenance = "explicit" | "derived" | "estimated" | "missing";

export type Unit =
  | "g"
  | "kg"
  | "ml"
  | "l"
  | "el"
  | "tl"
  | "stuk"
  | "snuf"
  | "teentje"
  | "bosje"
  | "blikje"
  | "pakje"
  | "plak"
  | "handvol"
  | "naar_smaak";

export type ShelfCategory =
  | "groente_fruit"
  | "vlees_vis"
  | "zuivel_eieren"
  | "brood_bakkerij"
  | "houdbaar"
  | "kruiden_specerijen"
  | "diepvries"
  | "dranken"
  | "overig";

export type MealType = "ontbijt" | "lunch" | "diner" | "tussendoor";

export type SourcePlatform =
  | "tiktok"
  | "instagram"
  | "youtube"
  | "pinterest"
  | "web"
  | "photo_ocr"
  | "manual";

export type Difficulty = "makkelijk" | "gemiddeld" | "uitdagend";

export type IngredientOut = {
  id: string;
  position: number;
  section: string | null;
  amount: number | null;
  amount_max: number | null;
  unit: Unit | null;
  name_nl: string;
  qualifier: string | null;
  category: ShelfCategory;
  optional: boolean;
  raw_text: string;
  original_amount: number | null;
  original_unit: string | null;
  provenance: Provenance;
};

export type StepOut = {
  id: string;
  position: number;
  text: string;
  timer_seconds: number | null;
  temperature_c: number | null;
  temperature_fan_c: number | null;
  ingredient_ids: string[];
  provenance: Provenance;
};

/** What `GET /v1/recipes` returns per row — no ingredients or steps. */
export type RecipeSummary = {
  id: string;
  title: string;
  image_url: string | null;
  meal_types: MealType[];
  servings: number;
  prep_minutes: number | null;
  cook_minutes: number | null;
  difficulty: Difficulty | null;
  source_platform: SourcePlatform;
  source_author: string | null;
  cooked_count: number;
  created_at: string;
};

/** What `GET /v1/recipes/{id}` returns. */
export type RecipeDetail = RecipeSummary & {
  description: string | null;
  kcal_per_serving: number | null;
  source_url: string | null;
  source_title: string | null;
  notes: string | null;
  last_cooked_at: string | null;
  ingredients: IngredientOut[];
  steps: StepOut[];
};
