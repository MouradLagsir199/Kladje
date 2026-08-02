import { Pressable, StyleSheet } from "react-native";

import { Text } from "@/components/Text";
import { color, radius, type } from "@/theme/tokens";

type Props = {
  label: string;
  active?: boolean;
  onPress?: () => void;
};

/**
 * Filter and selection chip. `accentWash` + `accent` when active, bordered `surface` when not —
 * one treatment for meal-type filters, diet, allergens and library filters alike.
 */
export function Chip({ label, active = false, onPress }: Props) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={[styles.chip, active ? styles.active : styles.inactive]}
    >
      <Text variant="body" tone={active ? "accent" : "inkSoft"} style={styles.label}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingVertical: 7,
    paddingHorizontal: 13,
    borderRadius: radius.pill,
    borderWidth: 1,
  },
  active: { backgroundColor: color.accentWash, borderColor: color.accent },
  inactive: { backgroundColor: color.surface, borderColor: color.line },
  label: { lineHeight: type.body.size },
});
