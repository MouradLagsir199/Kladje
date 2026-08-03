import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApiClient } from "@/api/client";
import type { ImportDetail, ImportStatus, RecipeDetail } from "@/api/types";

/** Statuses where the server is still working. Anything else is a final answer. */
const IN_FLIGHT: ImportStatus[] = ["queued", "fetching", "synthesizing"];

export function isInFlight(status: ImportStatus): boolean {
  return IN_FLIGHT.includes(status);
}

export type ApiError = Error & {
  code?: string;
  status?: number;
  details?: Record<string, unknown>;
};

async function unwrap<T>(response: Response): Promise<T> {
  if (response.ok) return (await response.json()) as T;

  // The server sends `{error: {code, message, details}}` for everything — see docs/04-api.md.
  // Keeping the code on the thrown error is what lets a screen pick its own Dutch copy per
  // failure instead of showing one generic message for nine different problems.
  const body = (await response.json().catch(() => null)) as {
    error?: { code?: string; message?: string; details?: Record<string, unknown> };
  } | null;

  const error: ApiError = new Error(body?.error?.message ?? `HTTP ${response.status}`);
  error.code = body?.error?.code;
  error.status = response.status;
  error.details = body?.error?.details;
  throw error;
}

export function useCreateImport() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (url: string) =>
      unwrap<ImportDetail>(
        await api("/v1/imports", { method: "POST", body: JSON.stringify({ url }) }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });
}

/**
 * Poll one import until it stops moving.
 *
 * Polling rather than a socket: the server writes an `import_events` row per stage, so each poll
 * returns real progress. SSE is the Phase H upgrade and changes nothing the screen renders.
 */
export function useImport(id: string | undefined) {
  const api = useApiClient();

  return useQuery({
    queryKey: ["import", id],
    enabled: !!id,
    queryFn: async () => unwrap<ImportDetail>(await api(`/v1/imports/${id}`)),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && isInFlight(status) ? 1500 : false;
    },
  });
}

export function usePatchDraft(id: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (patch: Record<string, unknown>) =>
      unwrap<ImportDetail>(
        await api(`/v1/imports/${id}/draft`, { method: "PATCH", body: JSON.stringify(patch) }),
      ),
    // The server re-validates and may have changed the value we just sent — a serving count it
    // refuses comes back as null. Writing the response into the cache keeps the screen honest
    // about what was actually stored.
    onSuccess: (data) => queryClient.setQueryData(["import", id], data),
  });
}

export function useSaveImport(id: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () =>
      unwrap<RecipeDetail>(await api(`/v1/imports/${id}/save`, { method: "POST" })),
    onSuccess: async (recipe) => {
      queryClient.setQueryData(["recipe", recipe.id], recipe);
      await queryClient.invalidateQueries({ queryKey: ["recipes"] });
    },
  });
}
