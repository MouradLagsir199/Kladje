import { Text as RNText, type TextProps } from "react-native";

import { color } from "@/theme/tokens";
import { textStyle, type TypeVariant } from "@/theme/typography";

type Props = TextProps & {
  variant?: TypeVariant;
  tone?: keyof typeof color;
};

/**
 * Every piece of text in the app goes through here, so a screen can never quietly invent a font
 * size. `variant` and `tone` are token names — if the design needs a value that isn't one, the
 * value belongs in `theme/tokens.ts` first.
 */
export function Text({ variant = "body", tone = "ink", style, ...rest }: Props) {
  return <RNText style={[textStyle(variant), { color: color[tone] }, style]} {...rest} />;
}
