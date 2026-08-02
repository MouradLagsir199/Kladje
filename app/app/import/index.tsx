import { useRouter } from "expo-router";
import { ScrollView, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Text } from "@/components/Text";
import { strings } from "@/strings/nl";
import { color, space } from "@/theme/tokens";

/**
 * Import step 1. The extraction pipeline behind this screen already works end to end against real
 * TikTok, Instagram, YouTube and blog URLs (`api/scripts/try_import.py`); what it still lacks is
 * `POST /v1/imports` to call and the synthesis step that turns evidence into a recipe (M8–M13).
 */
export default function ImportScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  return (
    <View style={styles.screen}>
      <View style={[styles.header, { paddingTop: insets.top + space.md }]}>
        <Text variant="title">{strings.importFlow.title}</Text>
        <Button label={strings.importFlow.close} variant="secondary" size="small" onPress={() => router.back()} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <EmptyState title={strings.importFlow.soon.title} body={strings.importFlow.soon.body} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.surface },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: space.xl,
    paddingBottom: space.lg,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.lineFaint,
  },
  content: { paddingBottom: 40 },
});
