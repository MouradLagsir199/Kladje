import {
  SchibstedGrotesk_400Regular,
  SchibstedGrotesk_500Medium,
  SchibstedGrotesk_600SemiBold,
  SchibstedGrotesk_700Bold,
  useFonts,
} from "@expo-google-fonts/schibsted-grotesk";

export function useAppFonts(): [boolean, Error | null] {
  return useFonts({
    SchibstedGrotesk_400Regular,
    SchibstedGrotesk_500Medium,
    SchibstedGrotesk_600SemiBold,
    SchibstedGrotesk_700Bold,
  });
}

// Maps a token's `weight` value to the loaded font family name.
// RN needs a distinct family per weight for custom fonts, not fontWeight + one family.
export const fontFamily = {
  "400": "SchibstedGrotesk_400Regular",
  "500": "SchibstedGrotesk_500Medium",
  "600": "SchibstedGrotesk_600SemiBold",
  "700": "SchibstedGrotesk_700Bold",
} as const;
