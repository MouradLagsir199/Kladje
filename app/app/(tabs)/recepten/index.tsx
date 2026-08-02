import { useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, View } from "react-native";

import { useRecipes } from "@/api/recipes";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { RecipeGrid } from "@/components/RecipeGrid";
import { StickyHeader } from "@/components/StickyHeader";
import { Text } from "@/components/Text";
import { strings } from "@/strings/nl";
import { color, space } from "@/theme/tokens";

export default function LibraryScreen() {
  const router = useRouter();
  const { data, isPending, isError, refetch } = useRecipes();
  const [refreshing, setRefreshing] = useState(false);

  const recipes = data?.items ?? [];

  async function onRefresh() {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }

  return (
    <View style={styles.screen}>
      <StickyHeader style={styles.header}>
        <Text variant="display">{strings.library.title}</Text>
      </StickyHeader>

      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {isPending && <ActivityIndicator style={styles.spinner} color={color.accent} />}

        {isError && (
          <EmptyState
            title={strings.library.loadError}
            body={strings.library.empty.body}
            actionLabel={strings.library.retry}
            onAction={() => refetch()}
          />
        )}

        {!isPending && !isError && recipes.length === 0 && (
          <EmptyState
            title={strings.library.empty.title}
            body={strings.library.empty.body}
            actionLabel={strings.library.empty.action}
            onAction={() => router.push("/import")}
          />
        )}

        {recipes.length > 0 && (
          <>
            <Text variant="small" tone="mutedLight" style={styles.count}>
              {strings.library.count(recipes.length)}
            </Text>
            <RecipeGrid recipes={recipes} onPressRecipe={(id) => router.push(`/recipe/${id}`)} />
            <Button
              label={strings.library.empty.action}
              variant="secondary"
              fullWidth
              style={styles.importButton}
              onPress={() => router.push("/import")}
            />
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.surface },
  header: { paddingHorizontal: space.xl, paddingBottom: 12 },
  content: { paddingHorizontal: space.xl, paddingTop: space.lg, paddingBottom: 40 },
  spinner: { marginTop: 60 },
  count: { marginBottom: space.lg },
  importButton: { marginTop: space.lg },
});
