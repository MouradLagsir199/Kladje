import { useQuery } from "@tanstack/react-query";

import { useApiClient } from "@/api/client";
import type { RecipeDetail, RecipeSummary } from "@/api/types";

type RecipeListResponse = {
  items: RecipeSummary[];
  next_cursor: string | null;
};

async function unwrap<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export function useRecipes() {
  const api = useApiClient();

  return useQuery({
    queryKey: ["recipes"],
    queryFn: async () => unwrap<RecipeListResponse>(await api("/v1/recipes")),
  });
}

export function useRecipe(id: string | undefined) {
  const api = useApiClient();

  return useQuery({
    queryKey: ["recipe", id],
    enabled: !!id,
    queryFn: async () => unwrap<RecipeDetail>(await api(`/v1/recipes/${id}`)),
  });
}
