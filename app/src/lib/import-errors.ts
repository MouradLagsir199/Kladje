import type { ApiError } from "@/api/imports";
import { strings } from "@/strings/nl";

/**
 * Dutch copy for one failure code, and whether retrying could possibly help.
 *
 * The taxonomy is a closed set on purpose (docs/03-import-pipeline.md): every code owes the user
 * distinct copy and a way out. Offering "Opnieuw proberen" on `source_blocked` or `quota_exceeded`
 * is worse than offering nothing — it invites someone to keep tapping a button that cannot work.
 */
export function importErrorMessage(code: string | null | undefined): string {
  return strings.importFlow.errors[code ?? "unknown"] ?? strings.importFlow.errors.unknown;
}

export function isRetryable(code: string | null | undefined): boolean {
  return !strings.importFlow.noRetry.includes(code ?? "unknown");
}

export function messageForApiError(error: unknown): string {
  const code = (error as ApiError | null)?.code;
  return importErrorMessage(code);
}
