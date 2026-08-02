import { ActivityIndicator, StyleSheet, View } from "react-native";

import { color } from "@/theme/tokens";

export default function SSOCallback() {
  return (
    <View style={styles.container}>
      <ActivityIndicator color={color.ink} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: color.canvas,
  },
});
