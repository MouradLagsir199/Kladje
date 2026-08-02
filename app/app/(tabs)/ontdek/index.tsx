import { useRouter } from "expo-router";
import { Pressable, ScrollView, StyleSheet, View } from "react-native";

import { EmptyState } from "@/components/EmptyState";
import { StickyHeader } from "@/components/StickyHeader";
import { Text } from "@/components/Text";
import { strings } from "@/strings/nl";
import { color, radius, space } from "@/theme/tokens";

/**
 * The discovery feed's chrome, with its content still to come.
 *
 * Curated content is Phase N — it needs a curated JSON in blob storage that does not exist yet.
 * The header is real so the shell is right; pretending to have a feed by showing the user their
 * own library would be a different product.
 */
export default function DiscoverScreen() {
  const router = useRouter();

  return (
    <View style={styles.screen}>
      <StickyHeader style={styles.header}>
        <Pressable accessibilityRole="search" style={styles.search} disabled>
          <View style={styles.searchGlyph} />
          <Text variant="bodyLarge" tone="mutedLight" style={styles.searchLabel}>
            {strings.feed.searchPlaceholder}
          </Text>
        </Pressable>
      </StickyHeader>

      <ScrollView contentContainerStyle={styles.content}>
        <EmptyState
          title={strings.feed.soon.title}
          body={strings.feed.soon.body}
          actionLabel={strings.feed.soon.action}
          onAction={() => router.push("/import")}
        />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.surface },
  header: { paddingHorizontal: space.xl, paddingBottom: 10 },
  search: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    paddingVertical: 11,
    paddingHorizontal: space.lg,
    borderRadius: 13,
    backgroundColor: color.surfaceSunk,
  },
  searchGlyph: {
    width: 13,
    height: 13,
    borderRadius: radius.pill,
    borderWidth: 2,
    borderColor: color.mutedLight,
  },
  searchLabel: { lineHeight: 14 },
  content: { paddingBottom: 40 },
});
