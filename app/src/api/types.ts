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
