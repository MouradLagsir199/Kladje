import { useLocalSearchParams, useRouter } from "expo-router";
import { StyleSheet, View } from "react-native";

import { useRecipe } from "@/api/recipes";
import { Button } from "@/components/Button";
import { Text } from "@/components/Text";
import { strings } from "@/strings/nl";
import { color, radius, space } from "@/theme/tokens";

export default function ImportDoneScreen() {
  const { recipeId } = useLocalSearchParams<{ id: string; recipeId?: string }>();
  const router = useRouter();
  const { data: recipe } = useRecipe(recipeId);

  return (
    <View style={styles.screen}>
      <View style={styles.card}>
        <View style={styles.tag}>
          <Text variant="caption" tone="successInk">
            {strings.importFlow.done.tag}
          </Text>
        </View>

        <Text variant="display" style={styles.title}>
          {recipe?.title ?? ""}
        </Text>
        <Text variant="body" tone="muted" style={styles.body}>
          {strings.importFlow.done.body}
        </Text>

        <Button
          label={strings.importFlow.done.viewRecipe}
          fullWidth
          disabled={!recipeId}
          onPress={() => recipeId && router.replace(`/recipe/${recipeId}`)}
        />
        <Button
          label={strings.importFlow.done.importAnother}
          variant="secondary"
          fullWidth
          style={styles.secondary}
          onPress={() => router.replace("/import")}
        />
        {/* Dismissing lands back on whatever was underneath the modal, which is where the user
            was before they pasted a link. */}
        <Button
          label={strings.importFlow.close}
          variant="secondary"
          fullWidth
          style={styles.secondary}
          onPress={() => router.dismissAll()}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: color.surface,
    alignItems: "center",
    justifyContent: "center",
    padding: space.xl,
  },
  card: { alignSelf: "stretch", alignItems: "center" },
  tag: {
    paddingVertical: 5,
    paddingHorizontal: 11,
    borderRadius: radius.pill,
    backgroundColor: color.successWash,
    marginBottom: space.lg,
  },
  title: { fontSize: 22, lineHeight: 27, textAlign: "center", marginBottom: 8 },
  body: { textAlign: "center", marginBottom: space.xl },
  secondary: { marginTop: 8 },
});
