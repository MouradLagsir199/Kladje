import { StyleSheet, Text, View } from "react-native";

import { fontFamily } from "@/theme/fonts";
import { color, space, type } from "@/theme/tokens";

export default function Home() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Receptenapp</Text>
      <Text style={styles.subtitle}>App-init placeholder — screens komen in latere taken.</Text>
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
});
