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

// --- Imports -------------------------------------------------------------------------------

export type ImportStatus =
  | "queued"
  | "fetching"
  | "synthesizing"
  | "ready_for_review"
  | "saved"
  | "failed"
  | "cancelled";

/** One stage transition. The progress screen renders these rather than a timer. */
export type ImportEvent = {
  stage: string;
  state: string;
  detail: string | null;
  at: string;
};

/** The synthesis output as it sits in `imports.draft`, before anything reaches the library. */
export type DraftRecipe = {
  found: boolean;
  confidence: "high" | "medium" | "low";
  title: string;
  description: string | null;
  meal_types: MealType[];
  servings: number | null;
  prep_minutes: number | null;
  cook_minutes: number | null;
  difficulty: Difficulty | null;
  oven_c: number | null;
  ingredients: DraftIngredient[];
  steps: DraftStep[];
  field_provenance: Record<string, Provenance>;
  missing: string[];
};

/** Short keys, because output tokens are the cost driver — see docs/11-prompts.md. */
export type DraftIngredient = {
  pos: number;
  section: string | null;
  amount: number | null;
  amount_max: number | null;
  unit: Unit | null;
  name_nl: string;
  qualifier: string | null;
  category: ShelfCategory;
  optional: boolean;
  raw: string;
  orig_amount: number | null;
  orig_unit: string | null;
  prov: Provenance;
};

export type DraftStep = {
  pos: number;
  text: string;
  timer_seconds: number | null;
  temperature_c: number | null;
  ingredient_pos: number[];
  prov: Provenance;
};

export type ImportDetail = {
  id: string;
  status: ImportStatus;
  platform: SourcePlatform;
  source_url: string | null;
  draft: {
    recipe: DraftRecipe;
    source: {
      platform: SourcePlatform;
      url: string | null;
      url_norm: string | null;
      author: string | null;
      title: string | null;
    };
  } | null;
  recipe_id: string | null;
  error_code: string | null;
  error_detail: string | null;
  duration_ms: number | null;
  created_at: string;
  events: ImportEvent[];
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
  /** Provenance for the recipe's own scalar fields. Null on recipes saved before migration 003. */
  field_provenance: Record<string, Provenance> | null;
  ingredients: IngredientOut[];
  steps: StepOut[];
};
