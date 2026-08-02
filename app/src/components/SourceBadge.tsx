import { StyleSheet, View } from "react-native";

import type { SourcePlatform } from "@/api/types";
import { Text } from "@/components/Text";
import { strings } from "@/strings/nl";
import { radius, type } from "@/theme/tokens";

type Props = {
  platform: SourcePlatform;
  /** `overlay` sits on a photo (white pill); `inline` sits on the canvas (coloured text). */
  variant?: "overlay" | "inline";
  size?: "regular" | "small";
};

const VIDEO: SourcePlatform[] = ["tiktok", "instagram", "youtube"];

/**
 * Where a recipe came from. Always visible on a card, because attribution is not optional —
 * see docs/07-legal-avg.md.
 */
export function SourceBadge({ platform, variant = "overlay", size = "regular" }: Props) {
  const label = strings.platform[platform];

  if (variant === "inline") {
    return (
      <Text variant="caption" tone={VIDEO.includes(platform) ? "sourceVideo" : "sourceWeb"}>
        {label}
      </Text>
    );
  }

  return (
    <View style={[styles.overlay, size === "small" && styles.overlaySmall]}>
      <Text variant="caption" tone="ink" style={styles.label}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    paddingVertical: 5,
    paddingHorizontal: 9,
    borderRadius: 7,
    backgroundColor: "rgba(255,255,255,0.94)",
    alignSelf: "flex-start",
  },
  overlaySmall: { paddingVertical: 4, paddingHorizontal: 8, borderRadius: radius.chip - 3 },
  label: { lineHeight: type.caption.size },
});
