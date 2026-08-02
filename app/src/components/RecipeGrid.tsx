import { StyleSheet, View } from "react-native";

import type { RecipeSummary } from "@/api/types";
import { RecipeCard } from "@/components/RecipeCard";

const GUTTER = 7; // half of the prototype's 14px column gap

type Props = {
  recipes: RecipeSummary[];
  onPressRecipe: (id: string) => void;
};

/**
 * The two-column grid used by Bibliotheek, Collectie, Groepdetail and Categorie-overzicht.
 *
 * Negative margin plus per-item padding rather than `gap`: percentage widths and a pixel gap do
 * not add up to 100% on every screen width, and the columns drift apart on narrow phones.
 */
export function RecipeGrid({ recipes, onPressRecipe }: Props) {
  return (
    <View style={styles.grid}>
      {recipes.map((recipe) => (
        <View key={recipe.id} style={styles.item}>
          <RecipeCard recipe={recipe} variant="grid" onPress={() => onPressRecipe(recipe.id)} />
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  grid: { flexDirection: "row", flexWrap: "wrap", marginHorizontal: -GUTTER },
  item: { width: "50%", paddingHorizontal: GUTTER, marginBottom: 18 },
});
