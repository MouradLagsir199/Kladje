import { useSSO } from "@clerk/clerk-expo";
import { useCallback } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import * as WebBrowser from "expo-web-browser";

import { useWarmUpBrowser } from "@/lib/use-warm-up-browser";
import { fontFamily } from "@/theme/fonts";
import { color, radius, space, type } from "@/theme/tokens";

WebBrowser.maybeCompleteAuthSession();

export default function SignIn() {
  useWarmUpBrowser();
  const { startSSOFlow } = useSSO();

  const onPress = useCallback(
    async (strategy: "oauth_apple" | "oauth_google") => {
      try {
        const { createdSessionId, setActive } = await startSSOFlow({ strategy });
        if (createdSessionId && setActive) {
          await setActive({ session: createdSessionId });
        }
      } catch (err) {
        console.error(`${strategy} sign-in error:`, err);
      }
    },
    [startSSOFlow],
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Receptenapp</Text>
      <Text style={styles.subtitle}>Log in om verder te gaan.</Text>

      <View style={styles.buttons}>
        <Pressable onPress={() => onPress("oauth_apple")} style={styles.buttonPrimary}>
          <Text style={styles.buttonPrimaryText}>Ga verder met Apple</Text>
        </Pressable>
        <Pressable onPress={() => onPress("oauth_google")} style={styles.buttonSecondary}>
          <Text style={styles.buttonSecondaryText}>Ga verder met Google</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: space.xl,
    padding: space.xxl,
    backgroundColor: color.canvas,
  },
  title: {
    fontFamily: fontFamily["700"],
    fontSize: type.display.size,
    lineHeight: type.display.size * type.display.lineHeight,
    color: color.ink,
  },
  subtitle: {
    fontFamily: fontFamily["400"],
    fontSize: type.body.size,
    lineHeight: type.body.size * type.body.lineHeight,
    color: color.muted,
  },
  buttons: {
    width: "100%",
    gap: space.sm,
    marginTop: space.lg,
  },
  buttonPrimary: {
    width: "100%",
    paddingVertical: space.lg,
    borderRadius: radius.panel,
    backgroundColor: color.ink,
    alignItems: "center",
  },
  buttonPrimaryText: {
    fontFamily: fontFamily["600"],
    fontSize: type.bodyLarge.size,
    color: color.surface,
  },
  buttonSecondary: {
    width: "100%",
    paddingVertical: space.lg,
    borderRadius: radius.panel,
    borderWidth: 1.5,
    borderColor: color.line,
    alignItems: "center",
  },
  buttonSecondaryText: {
    fontFamily: fontFamily["600"],
    fontSize: type.bodyLarge.size,
    color: color.ink,
  },
});
