import { useAuth } from "@clerk/clerk-expo";
import { useCallback } from "react";

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

// Thin fetch wrapper that attaches the current Clerk session token. Not the
// generated client docs/05-client.md eventually wants (src/api/) — that comes
// once the API has an OpenAPI schema to generate from. This is the minimum
// needed now: every request authenticated, one place it happens.
export function useApiClient() {
  const { getToken } = useAuth();

  return useCallback(
    async (path: string, init: RequestInit = {}): Promise<Response> => {
      if (!API_BASE_URL) {
        throw new Error("EXPO_PUBLIC_API_BASE_URL is not set — check app/.env");
      }

      const token = await getToken();
      const headers = new Headers(init.headers);
      headers.set("Content-Type", "application/json");
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }

      return fetch(`${API_BASE_URL}${path}`, { ...init, headers });
    },
    [getToken],
  );
}
