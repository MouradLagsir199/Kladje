import { useAuth, useUser } from "@clerk/clerk-expo";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { fontFamily } from "@/theme/fonts";
import { color, radius, space, type } from "@/theme/tokens";

export default function Home() {
  const { signOut } = useAuth();
  const { user } = useUser();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Receptenapp</Text>
      <Text style={styles.subtitle}>
        Ingelogd als {user?.primaryEmailAddress?.emailAddress ?? user?.fullName ?? "onbekend"}.
      </Text>
      <Text style={styles.note}>GET /v1/me komt in de volgende taak (0.14).</Text>

      <Pressable onPress={() => signOut()} style={styles.button}>
        <Text style={styles.buttonText}>Uitloggen</Text>
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
