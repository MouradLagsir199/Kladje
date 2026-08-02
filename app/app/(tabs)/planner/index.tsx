import { ScrollView, StyleSheet, View } from "react-native";

import { EmptyState } from "@/components/EmptyState";
import { StickyHeader } from "@/components/StickyHeader";
import { Text } from "@/components/Text";
import { strings } from "@/strings/nl";
import { color, space } from "@/theme/tokens";

export default function PlannerScreen() {
  return (
    <View style={styles.screen}>
      <StickyHeader style={styles.header}>
        <Text variant="display">{strings.planner.title}</Text>
      </StickyHeader>

      <ScrollView contentContainerStyle={styles.content}>
        <EmptyState title={strings.planner.soon.title} body={strings.planner.soon.body} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.surface },
  header: { paddingHorizontal: space.xl, paddingBottom: 12 },
  content: { paddingBottom: 40 },
});
