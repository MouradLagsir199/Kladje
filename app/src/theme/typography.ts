import { Platform, type TextStyle } from "react-native";

import { fontFamily } from "./fonts";
import { type as typeScale } from "./tokens";

export type TypeVariant = keyof typeof typeScale;

// The prototype asks for `ui-monospace, Menlo` on micro labels. React Native has no generic
// monospace alias, so each platform gets the face it actually ships.
const monoFamily = Platform.select({ ios: "Menlo", default: "monospace" });

interface TypeSpec {
  size: number;
  weight: keyof typeof fontFamily;
  lineHeight: number;
  tracking?: number;
  mono?: boolean;
  uppercase?: boolean;
}

/**
 * A token name turned into a React Native text style.
 *
 * Two conversions happen here and nowhere else. `lineHeight` in the tokens is a CSS-style
 * multiplier; RN wants absolute pixels. `tracking` is an em value the way the prototype's CSS
 * writes it; RN's `letterSpacing` is in pixels, so it scales with the font size.
 */
export function textStyle(variant: TypeVariant): TextStyle {
  const spec = typeScale[variant] as TypeSpec;

  return {
    fontFamily: spec.mono ? monoFamily : fontFamily[spec.weight],
    fontSize: spec.size,
    lineHeight: Math.round(spec.size * spec.lineHeight * 10) / 10,
    ...(spec.tracking ? { letterSpacing: spec.tracking * spec.size } : {}),
    ...(spec.uppercase ? { textTransform: "uppercase" as const } : {}),
  };
}
