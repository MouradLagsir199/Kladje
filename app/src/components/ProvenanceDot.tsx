import { StyleSheet, View } from "react-native";

import type { Provenance } from "@/api/types";
import { strings } from "@/strings/nl";
import { color, dot } from "@/theme/tokens";

const toneFor: Record<Provenance, keyof typeof color> = {
  explicit: "provExplicit",
  // An estimate is a guess the user asked for; a derived value is a conversion we did ourselves.
  // Different meanings, same amber — the "geschat" caption next to the value is what separates
  // them, because three shades of warning is more precision than anyone can read off a 8px dot.
  derived: "provDerived",
  estimated: "provDerived",
  missing: "provMissing",
};

type Props = {
  provenance: Provenance;
  /** Set when the dot already sits next to a "geschat" caption or another textual cue. */
  labelled?: boolean;
};

/**
 * The trust mechanism, and the one place these three colours may be used.
 *
 * 8px rather than the prototype's 5px: below that it is under the perceptual threshold at phone
 * size. Colour is never the only signal — either a caption sits next to it, or the dot carries an
 * accessibility label of its own.
 */
export function ProvenanceDot({ provenance, labelled = false }: Props) {
  return (
    <View
      accessibilityRole={labelled ? "none" : "image"}
      accessibilityLabel={labelled ? undefined : strings.provenance[provenance]}
      style={[styles.dot, { backgroundColor: color[toneFor[provenance]] }]}
    />
  );
}

const styles = StyleSheet.create({
  dot: {
    width: dot.size,
    height: dot.size,
    borderRadius: dot.size / 2,
    flexShrink: 0,
  },
});
