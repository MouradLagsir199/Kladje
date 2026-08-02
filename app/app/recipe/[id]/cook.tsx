import { useLocalSearchParams, useRouter } from "expo-router";
import { useKeepAwake } from "expo-keep-awake";
import { StatusBar } from "expo-status-bar";
import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useRecipe } from "@/api/recipes";
import { timerLabel } from "@/components/StepCard";
import { Text } from "@/components/Text";
import { ingredientLine } from "@/lib/format";
import { strings } from "@/strings/nl";
import { color, radius, space } from "@/theme/tokens";

/**
 * Cook mode: near-black, one step per screen, and the display stays on.
 *
 * The scale is deliberately larger than anywhere else in the app — this is read from across a
 * worktop with your hands full, not held at arm's length.
 */
export default function CookScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data: recipe, isPending } = useRecipe(id);
  const [index, setIndex] = useState(0);

  useKeepAwake();

  if (isPending || !recipe) {
    return (
      <View style={styles.screen}>
        <StatusBar style="light" />
        <ActivityIndicator color={color.accent} />
      </View>
    );
  }

  const steps = recipe.steps;
  const step = steps[index];

  if (!step) {
    return (
      <View style={[styles.screen, styles.centre]}>
        <StatusBar style="light" />
        <Text variant="bodyLarge" style={styles.dimText}>
          {strings.cook.noSteps}
        </Text>
        <Pressable accessibilityRole="button" onPress={() => router.back()}>
          <Text variant="bodyBold" style={styles.dimText}>
            {strings.cook.close}
          </Text>
        </Pressable>
      </View>
    );
  }

  const isLast = index === steps.length - 1;
  // Only the ingredients this step actually uses. Denormalised on the step so cook mode never
  // has to work it out — see the `ingredient_ids` column.
  const needed = recipe.ingredients.filter((ingredient) => step.ingredient_ids.includes(ingredient.id));

  return (
    <View style={[styles.screen, { paddingTop: insets.top + space.md, paddingBottom: Math.max(insets.bottom, space.xl) }]}>
      <StatusBar style="light" />

      <View style={styles.topBar}>
        <Pressable accessibilityRole="button" onPress={() => router.back()}>
          <Text variant="bodyBold" style={styles.dimText}>
            {strings.cook.close}
          </Text>
        </Pressable>
        <Text variant="bodyBold" style={styles.dimText}>
          {strings.cook.progress(index + 1, steps.length)}
        </Text>
      </View>

      <View style={styles.bars}>
        {steps.map((each, position) => (
          <View key={each.id} style={[styles.bar, position <= index && styles.barDone]} />
        ))}
      </View>

      {needed.length > 0 && (
        <View style={styles.needed}>
          <Text variant="micro" style={styles.neededLabel}>
            {strings.cook.nowNeeded}
          </Text>
          <View style={styles.pills}>
            {needed.map((ingredient) => (
              <View key={ingredient.id} style={styles.pill}>
                <Text variant="bodyLarge" style={styles.pillText}>
                  {ingredientLine(ingredient)}
                </Text>
              </View>
            ))}
          </View>
        </View>
      )}

      <ScrollView style={styles.stepScroll} contentContainerStyle={styles.stepContent}>
        <Text variant="cookStep" tone="surface">
          {step.text}
        </Text>
        {/* Shows how long the step takes. Actually starting it is M21's wall-clock timer, which
            has to survive backgrounding to be worth anything — a button that forgets is worse. */}
        {step.timer_seconds !== null && step.timer_seconds > 0 && (
          <View style={styles.timer}>
            <Text variant="cookMeta" style={styles.timerText}>
              {strings.detail.timer(timerLabel(step.timer_seconds))}
            </Text>
          </View>
        )}
      </ScrollView>

      <View style={styles.nav}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={strings.cook.previous}
          disabled={index === 0}
          onPress={() => setIndex((current) => Math.max(0, current - 1))}
          style={[styles.navBack, index === 0 && styles.navDisabled]}
        >
          <Text variant="cookMeta" tone="surface">
            ‹
          </Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={() => (isLast ? router.back() : setIndex((current) => current + 1))}
          style={styles.navNext}
        >
          <Text variant="cookMeta" tone="surface">
            {isLast ? strings.cook.finish : strings.cook.next}
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.cookBg, paddingHorizontal: 24 },
  centre: { alignItems: "center", justifyContent: "center", gap: space.xl },
  dimText: { color: "rgba(255,255,255,0.6)" },

  topBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 22 },
  bars: { flexDirection: "row", gap: 5, marginBottom: 30 },
  bar: { flex: 1, height: 3, borderRadius: 2, backgroundColor: "rgba(255,255,255,0.16)" },
  barDone: { backgroundColor: color.accent },

  needed: { marginBottom: 26 },
  // A warm tint of the accent, legible on near-black where the accent itself is not.
  neededLabel: { color: "#e8825f", marginBottom: 12 },
  pills: { flexDirection: "row", flexWrap: "wrap", gap: 7 },
  pill: { paddingVertical: 9, paddingHorizontal: 13, borderRadius: radius.pill, backgroundColor: "rgba(255,255,255,0.09)" },
  pillText: { color: "rgba(255,255,255,0.92)" },

  stepScroll: { flex: 1 },
  stepContent: { paddingBottom: space.xl },
  timer: {
    marginTop: 22,
    alignSelf: "flex-start",
    paddingVertical: 13,
    paddingHorizontal: 20,
    borderRadius: 13,
    backgroundColor: "rgba(232,68,44,0.16)",
    borderWidth: 1,
    borderColor: "rgba(232,68,44,0.45)",
  },
  timerText: { color: "#f2836a" },

  nav: { flexDirection: "row", gap: 10 },
  navBack: {
    paddingVertical: 17,
    paddingHorizontal: 22,
    borderRadius: radius.card,
    backgroundColor: "rgba(255,255,255,0.1)",
    alignItems: "center",
  },
  navDisabled: { opacity: 0.35 },
  navNext: {
    flex: 1,
    paddingVertical: 17,
    borderRadius: radius.card,
    backgroundColor: color.accent,
    alignItems: "center",
  },
});
