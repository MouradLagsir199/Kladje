import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { Pressable, StyleSheet, View } from "react-native";

import type { RecipeSummary } from "@/api/types";
import { SourceBadge } from "@/components/SourceBadge";
import { Text } from "@/components/Text";
import { metaLine } from "@/lib/format";
import { color, radius, space } from "@/theme/tokens";

type Variant = "hero" | "compact" | "grid";

type Props = {
  recipe: RecipeSummary;
  variant?: Variant;
  onPress?: () => void;
};

const DIFFICULTY_TONE = {
  makkelijk: "provExplicit",
  gemiddeld: "provDerived",
  uitdagend: "provMissing",
} as const;

export function RecipeCard({ recipe, variant = "grid", onPress }: Props) {
  if (variant === "hero") return <HeroCard recipe={recipe} onPress={onPress} />;
  return <StackedCard recipe={recipe} variant={variant} onPress={onPress} />;
}

/** Feed's snap-scrolling row: a 300×200 photo with the title burned into the gradient. */
function HeroCard({ recipe, onPress }: Omit<Props, "variant">) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.hero}>
      <Photo uri={recipe.image_url} style={StyleSheet.absoluteFill} />
      <LinearGradient
        colors={["rgba(15,13,12,0)", "rgba(15,13,12,0.78)"]}
        locations={[0.38, 1]}
        style={StyleSheet.absoluteFill}
      />
      <View style={styles.heroBadge}>
        <SourceBadge platform={recipe.source_platform} />
      </View>
      <View style={styles.heroText}>
        <Text variant="title" tone="surface" numberOfLines={2} style={styles.heroTitle}>
          {recipe.title}
        </Text>
        <Text variant="caption" tone="surface" style={styles.heroMeta}>
          {metaLine(recipe)}
        </Text>
      </View>
    </Pressable>
  );
}

/** The compact and grid variants differ only in width and a couple of sizes. */
function StackedCard({ recipe, variant, onPress }: Props) {
  const isGrid = variant === "grid";

  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={isGrid ? styles.gridCard : styles.compactCard}
    >
      <View style={[styles.thumb, { borderRadius: isGrid ? radius.card : radius.panel }]}>
        <Photo uri={recipe.image_url} style={StyleSheet.absoluteFill} />
        {isGrid && (
          <View style={styles.gridBadge}>
            <SourceBadge platform={recipe.source_platform} size="small" />
          </View>
        )}
      </View>
      <Text variant={isGrid ? "bodyBold" : "body"} tone="ink" numberOfLines={2} style={styles.title}>
        {recipe.title}
      </Text>
      <View style={styles.metaRow}>
        <Text variant="caption" tone="mutedLight">
          {metaLine(recipe)}
        </Text>
        {isGrid && recipe.difficulty && (
          <View
            style={[styles.difficulty, { backgroundColor: color[DIFFICULTY_TONE[recipe.difficulty]] }]}
          />
        )}
      </View>
    </Pressable>
  );
}

function Photo({ uri, style }: { uri: string | null; style: object }) {
  return (
    <Image
      source={uri ? { uri } : undefined}
      style={[style, { backgroundColor: color.imageBg }]}
      contentFit="cover"
      transition={160}
    />
  );
}

const styles = StyleSheet.create({
  hero: {
    width: 300,
    height: 200,
    borderRadius: 20,
    overflow: "hidden",
    backgroundColor: color.imageBg,
  },
  heroBadge: { position: "absolute", left: space.lg, top: space.lg },
  heroText: { position: "absolute", left: space.lg, right: space.lg, bottom: 13 },
  heroTitle: { marginBottom: 5 },
  heroMeta: { opacity: 0.85 },

  compactCard: { width: 146 },
  // Width comes from the parent grid, which owns the gutter arithmetic.
  gridCard: { width: "100%" },
  thumb: {
    aspectRatio: 4 / 5,
    overflow: "hidden",
    backgroundColor: color.imageBg,
    marginBottom: space.md,
  },
  gridBadge: { position: "absolute", left: 8, top: 8 },
  title: { marginBottom: 5 },
  metaRow: { flexDirection: "row", alignItems: "center", gap: space.sm },
  difficulty: { width: 6, height: 6, borderRadius: 3 },
});
