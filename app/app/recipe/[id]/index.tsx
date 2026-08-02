import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import * as Linking from "expo-linking";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useRecipe } from "@/api/recipes";
import type { RecipeDetail } from "@/api/types";
import { Button } from "@/components/Button";
import { ChevronLeftIcon } from "@/components/icons";
import { IngredientRow } from "@/components/IngredientRow";
import { MetaBar, type MetaField } from "@/components/MetaBar";
import { StepCard } from "@/components/StepCard";
import { Text } from "@/components/Text";
import { totalMinutes } from "@/lib/format";
import { strings } from "@/strings/nl";
import { color, radius, space } from "@/theme/tokens";

export default function RecipeDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data: recipe, isPending, isError } = useRecipe(id);

  const [servings, setServings] = useState<number | null>(null);
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  if (isPending) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={color.accent} />
      </View>
    );
  }

  if (isError || !recipe) {
    return (
      <View style={styles.centre}>
        <Text variant="body" tone="muted">
          {strings.detail.loadError}
        </Text>
        <Button label={strings.detail.back} variant="secondary" onPress={() => router.back()} />
      </View>
    );
  }

  // Null until the user touches the stepper, so the recipe's own serving count stays the default.
  const shownServings = servings ?? recipe.servings;
  const scale = shownServings / recipe.servings;

  return (
    <View style={styles.screen}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Hero recipe={recipe} onBack={() => router.back()} topInset={insets.top} />

        <View style={styles.body}>
          <Text variant="display" style={styles.title}>
            {recipe.title}
          </Text>
          <Attribution recipe={recipe} />

          <MetaBar fields={metaFieldsFor(recipe)} />

          <View style={styles.sectionHead}>
            <Text variant="title">{strings.detail.ingredients}</Text>
            <View style={styles.stepper}>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={strings.detail.fewer}
                onPress={() => setServings(Math.max(1, shownServings - 1))}
                style={styles.stepperButton}
              >
                <Text variant="title">−</Text>
              </Pressable>
              <Text variant="bodyBold" style={styles.stepperValue}>
                {strings.detail.servings(shownServings)}
              </Text>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={strings.detail.more}
                onPress={() => setServings(Math.min(20, shownServings + 1))}
                style={styles.stepperButton}
              >
                <Text variant="title">+</Text>
              </Pressable>
            </View>
          </View>

          <View style={styles.ingredients}>
            {recipe.ingredients.map((ingredient) => (
              <IngredientRow
                key={ingredient.id}
                ingredient={ingredient}
                scale={scale}
                checked={!!checked[ingredient.id]}
                onToggle={() =>
                  setChecked((previous) => ({
                    ...previous,
                    [ingredient.id]: !previous[ingredient.id],
                  }))
                }
              />
            ))}
          </View>

          <Text variant="title" style={styles.methodHead}>
            {strings.detail.method}
          </Text>
          <View style={styles.steps}>
            {recipe.steps.map((step, index) => (
              <StepCard key={step.id} step={step} number={index + 1} />
            ))}
          </View>

          {/* Required disclosure: the steps are our words, not the source's. docs/07-legal-avg.md */}
          <Text variant="small" tone="mutedLight" style={styles.footnote}>
            {strings.detail.stepsRewritten}
          </Text>

          <View style={styles.cookStrip}>
            <Text variant="bodyBold">
              {recipe.cooked_count > 0
                ? strings.detail.cookedCount(recipe.cooked_count)
                : strings.detail.neverCooked}
            </Text>
          </View>
        </View>
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: Math.max(insets.bottom, space.lg) }]}>
        <Button
          label={strings.detail.startCooking}
          style={styles.footerPrimary}
          onPress={() => router.push(`/recipe/${recipe.id}/cook`)}
        />
      </View>
    </View>
  );
}

function Hero({
  recipe,
  onBack,
  topInset,
}: {
  recipe: RecipeDetail;
  onBack: () => void;
  topInset: number;
}) {
  return (
    <View style={styles.hero}>
      <Image
        source={recipe.image_url ? { uri: recipe.image_url } : undefined}
        style={StyleSheet.absoluteFill}
        contentFit="cover"
        transition={160}
      />
      <LinearGradient
        colors={["rgba(15,13,12,0.4)", "rgba(15,13,12,0)"]}
        locations={[0, 0.34]}
        style={StyleSheet.absoluteFill}
      />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={strings.detail.back}
        onPress={onBack}
        style={[styles.heroButton, { top: topInset + space.md }]}
      >
        <ChevronLeftIcon color={color.ink} />
      </Pressable>
    </View>
  );
}

function Attribution({ recipe }: { recipe: RecipeDetail }) {
  const platform = strings.platform[recipe.source_platform];
  const line = recipe.source_author
    ? strings.detail.attribution(recipe.source_author, platform)
    : strings.detail.attributionNoAuthor(platform);

  return (
    <View style={styles.attribution}>
      <Text variant="body" tone="muted">
        {line}
      </Text>
      {recipe.source_url && (
        <>
          <Text variant="body" tone="muted">
            {" · "}
          </Text>
          <Pressable
            accessibilityRole="link"
            onPress={() => recipe.source_url && Linking.openURL(recipe.source_url)}
          >
            <Text variant="bodyBold" tone="accent">
              {strings.detail.original}
            </Text>
          </Pressable>
        </>
      )}
    </View>
  );
}

function metaFieldsFor(recipe: RecipeDetail): MetaField[] {
  const total = totalMinutes(recipe);

  return [
    {
      label: strings.meta.total,
      value: total === null ? strings.meta.unknown : strings.meta.minutes(total),
    },
    { label: strings.meta.servings, value: String(recipe.servings) },
    {
      label: strings.meta.difficulty,
      value: recipe.difficulty ? strings.difficulty[recipe.difficulty] : strings.meta.unknown,
    },
    {
      label: strings.meta.kcal,
      value: recipe.kcal_per_serving === null ? strings.meta.unknown : String(recipe.kcal_per_serving),
    },
  ];
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.surface },
  centre: { flex: 1, alignItems: "center", justifyContent: "center", gap: space.lg, padding: space.xxl },
  scroll: { paddingBottom: 120 },

  hero: { height: 290, backgroundColor: color.imageBg },
  heroButton: {
    position: "absolute",
    left: 16,
    width: 36,
    height: 36,
    borderRadius: radius.pill,
    backgroundColor: "rgba(255,255,255,0.9)",
    alignItems: "center",
    justifyContent: "center",
  },

  body: { padding: space.xl },
  title: { fontSize: 24, lineHeight: 29, marginBottom: 8 },
  attribution: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", marginBottom: space.lg },

  sectionHead: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 16,
    marginBottom: space.lg,
  },
  stepper: { flexDirection: "row", alignItems: "center", borderWidth: 1, borderColor: color.line, borderRadius: 11, overflow: "hidden" },
  stepperButton: { width: 36, height: 34, alignItems: "center", justifyContent: "center" },
  stepperValue: { minWidth: 74, textAlign: "center" },

  ingredients: { marginBottom: space.xxl },
  methodHead: { marginBottom: space.lg },
  steps: { gap: 16, marginBottom: space.lg },
  footnote: { marginBottom: space.xxl },
  cookStrip: {
    padding: 15,
    borderRadius: radius.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.line,
  },

  footer: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    paddingTop: 12,
    paddingHorizontal: 16,
    flexDirection: "row",
    gap: 8,
    backgroundColor: color.surface,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: color.lineFaint,
  },
  footerPrimary: { flex: 1 },
});
