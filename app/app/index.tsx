import { useAuth } from "@clerk/clerk-expo";
import { useQuery } from "@tanstack/react-query";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { useApiClient } from "@/api/client";
import type { MeResponse } from "@/api/types";
import { strings } from "@/strings/nl";
import { fontFamily } from "@/theme/fonts";
import { color, radius, space, type } from "@/theme/tokens";

export default function Home() {
  const { signOut } = useAuth();
  const apiClient = useApiClient();

  const {
    data: me,
    isPending,
    isError,
  } = useQuery({
    queryKey: ["me"],
    queryFn: async (): Promise<MeResponse> => {
      const response = await apiClient("/v1/me");
      if (!response.ok) {
        throw new Error(`GET /v1/me failed met status ${response.status}`);
      }
      return response.json();
    },
  });

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{strings.appName}</Text>

      {isPending && <ActivityIndicator color={color.ink} />}
      {isError && <Text style={styles.subtitle}>{strings.home.loadError}</Text>}
      {me && (
        <Text style={styles.subtitle}>
          {strings.home.signedInAs(
            me.user.display_name ?? me.user.email ?? strings.home.unknownUser,
            me.user.tier === "premium" ? "premium" : "gratis",
            me.quota.used,
            me.quota.limit,
          )}
        </Text>
      )}

      <Pressable onPress={() => signOut()} style={styles.button}>
        <Text style={styles.buttonText}>{strings.home.signOut}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: space.md,
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
    textAlign: "center",
  },
  note: {
    fontFamily: fontFamily["400"],
    fontSize: type.small.size,
    color: color.mutedLight,
    textAlign: "center",
  },
  button: {
    marginTop: space.lg,
    paddingHorizontal: space.xl,
    paddingVertical: space.md,
    borderRadius: radius.panel,
    borderWidth: 1.5,
    borderColor: color.line,
  },
  buttonText: {
    fontFamily: fontFamily["600"],
    fontSize: type.bodyBold.size,
    color: color.ink,
  },
});
