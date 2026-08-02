import { Pressable, StyleSheet, View } from "react-native";

import type { IngredientOut } from "@/api/types";
import { ProvenanceDot } from "@/components/ProvenanceDot";
import { Text } from "@/components/Text";
import { ingredientLine, originalLine } from "@/lib/format";
import { color, radius } from "@/theme/tokens";

type Props = {
  ingredient: IngredientOut;
  /** Multiplier from the portions stepper. */
  scale?: number;
  checked?: boolean;
  onToggle?: () => void;
};

export function IngredientRow({ ingredient, scale = 1, checked = false, onToggle }: Props) {
  const main = ingredientLine(ingredient, scale);
  const original = originalLine(ingredient);

  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}
      accessibilityLabel={main}
      onPress={onToggle}
      style={[styles.row, checked && styles.rowChecked]}
    >
      <View style={[styles.box, checked && styles.boxChecked]}>
        {checked && (
          <Text variant="caption" tone="surface" style={styles.check}>
            ✓
          </Text>
        )}
      </View>

      <View style={styles.body}>
        <Text variant="bodyLarge" tone="ink" style={checked ? styles.struck : undefined}>
          {main}
        </Text>
        {original && (
          // Only shown when a conversion happened, so the user can always get back to what the
          // source actually said. Pairs with the derived dot to the right.
          <Text variant="small" tone="mutedLight" style={styles.original}>
            {original}
          </Text>
        )}
      </View>

      <ProvenanceDot provenance={ingredient.provenance} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 11,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.surfaceSunk,
  },
  rowChecked: { opacity: 0.45 },
  box: {
    width: 21,
    height: 21,
    borderRadius: radius.check,
    borderWidth: 1.5,
    borderColor: color.line,
    alignItems: "center",
    justifyContent: "center",
  },
  boxChecked: { backgroundColor: color.accent, borderColor: color.accent },
  check: { lineHeight: 11 },
  body: { flex: 1 },
  struck: { textDecorationLine: "line-through" },
  original: { marginTop: 3 },
});
