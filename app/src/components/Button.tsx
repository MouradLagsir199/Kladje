import { Pressable, type PressableProps, StyleSheet, type ViewStyle } from "react-native";

import { Text } from "@/components/Text";
import { color, radius, space, type } from "@/theme/tokens";

type Variant = "primary" | "secondary";
type Size = "large" | "small";

type Props = Omit<PressableProps, "style"> & {
  label: string;
  variant?: Variant;
  size?: Size;
  fullWidth?: boolean;
  style?: ViewStyle;
};

export function Button({
  label,
  variant = "primary",
  size = "large",
  fullWidth = false,
  disabled = false,
  style,
  ...rest
}: Props) {
  const isPrimary = variant === "primary";

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!disabled }}
      disabled={disabled}
      style={({ pressed }) => [
        styles.base,
        size === "large" ? styles.large : styles.small,
        isPrimary ? styles.primary : styles.secondary,
        pressed && (isPrimary ? styles.primaryPressed : styles.secondaryPressed),
        disabled && styles.disabled,
        fullWidth && styles.fullWidth,
        style,
      ]}
      {...rest}
    >
      <Text
        variant={size === "large" ? "bodyLarge" : "bodyBold"}
        tone={disabled ? "mutedLight" : isPrimary ? "surface" : "ink"}
        // The body tokens carry a line height meant for running text. The prototype sets `/1` on
        // every button, and a single centred label needs that or the button grows past its padding.
        style={{ lineHeight: (size === "large" ? type.bodyLarge : type.bodyBold).size }}
        numberOfLines={1}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.panel,
  },
  large: { paddingVertical: 15, paddingHorizontal: space.lg },
  small: { paddingVertical: space.md, paddingHorizontal: 13, borderRadius: 11 },
  primary: { backgroundColor: color.accent },
  primaryPressed: { backgroundColor: color.accentPress },
  secondary: { borderWidth: 1.5, borderColor: color.line, backgroundColor: color.surface },
  secondaryPressed: { backgroundColor: color.surfaceSunk },
  disabled: { backgroundColor: color.surfaceSunk, borderColor: color.line },
  fullWidth: { alignSelf: "stretch" },
});
