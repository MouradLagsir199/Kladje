import { useQuery } from "@tanstack/react-query";

import { useApiClient } from "@/api/client";
import type { MeResponse } from "@/api/types";

/** The boot call. Everything the first screen needs, in one round trip — see docs/04-api.md. */
export function useMe() {
  const api = useApiClient();

  return useQuery({
    queryKey: ["me"],
    queryFn: async (): Promise<MeResponse> => {
      const response = await api("/v1/me");
      if (!response.ok) {
        throw new Error(`GET /v1/me failed met status ${response.status}`);
      }
      return response.json();
    },
  });
}
