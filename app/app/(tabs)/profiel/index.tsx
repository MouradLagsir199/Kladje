import { useAuth } from "@clerk/clerk-expo";
import { ActivityIndicator, ScrollView, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useMe } from "@/api/me";
import { useRecipes } from "@/api/recipes";
import { Button } from "@/components/Button";
import { Text } from "@/components/Text";
import { strings } from "@/strings/nl";
import { color, radius, space } from "@/theme/tokens";

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();
  const { signOut } = useAuth();
  const { data: me, isPending, isError } = useMe();
  const { data: recipes } = useRecipes();

  const name = me?.user.display_name ?? me?.user.email ?? strings.home.unknownUser;
  const library = recipes?.items ?? [];
  const cooked = library.reduce((total, recipe) => total + recipe.cooked_count, 0);

  return (
    <ScrollView contentContainerStyle={[styles.content, { paddingTop: insets.top + 10 }]}>
      {isPending && <ActivityIndicator color={color.accent} />}
      {isError && (
        <Text variant="body" tone="muted">
          {strings.profile.loadError}
        </Text>
      )}

      {me && (
        <>
          <View style={styles.identity}>
            <View style={styles.avatar}>
              <Text variant="display" tone="surface" style={styles.initials}>
                {initialsOf(name)}
              </Text>
            </View>
            <View style={styles.identityText}>
              <Text variant="display" style={styles.name} numberOfLines={1}>
                {name}
              </Text>
              <Text variant="body" tone="mutedLight">
                {strings.profile.tier[me.user.tier]}
              </Text>
            </View>
          </View>

          <View style={styles.stats}>
            <Stat value={library.length} label={strings.profile.stats.recipes} />
            <Stat value={cooked} label={strings.profile.stats.cooked} />
            <Stat value={me.quota.used} label={strings.profile.stats.imports} />
          </View>

          {me.user.tier === "free" && (
            <View style={styles.upsell}>
              <Text variant="bodyLarge" tone="surface" style={styles.upsellTitle}>
                {strings.profile.upsell.used(me.quota.used, me.quota.limit)}
              </Text>
              <Text variant="small" style={styles.upsellBody}>
                {strings.profile.upsell.benefit}
              </Text>
              <Button label={strings.profile.upsell.action} size="small" disabled />
            </View>
          )}

          <Button
            label={strings.profile.signOut}
            variant="secondary"
            fullWidth
            onPress={() => signOut()}
          />
        </>
      )}
    </ScrollView>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <View style={styles.stat}>
      <Text variant="display" style={styles.statValue}>
        {value}
      </Text>
      <Text variant="caption" tone="mutedLight">
        {label}
      </Text>
    </View>
  );
}

function initialsOf(name: string): string {
  return name
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: space.xl,
    paddingBottom: 40,
    backgroundColor: color.surface,
    flexGrow: 1,
  },
  identity: { flexDirection: "row", alignItems: "center", gap: space.lg, marginBottom: space.xl },
  avatar: {
    width: 62,
    height: 62,
    borderRadius: radius.pill,
    backgroundColor: color.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  initials: { fontSize: 21, lineHeight: 21 },
  identityText: { flex: 1 },
  name: { fontSize: 21, lineHeight: 25, marginBottom: 3 },

  stats: { flexDirection: "row", gap: 8, marginBottom: 18 },
  stat: {
    flex: 1,
    paddingVertical: space.lg,
    paddingHorizontal: 12,
    borderRadius: radius.panel,
    backgroundColor: color.surfaceAlt,
  },
  statValue: { fontSize: 20, lineHeight: 20, marginBottom: 5 },

  upsell: {
    padding: 16,
    borderRadius: 16,
    backgroundColor: color.cookBg,
    marginBottom: 22,
    alignItems: "flex-start",
  },
  upsellTitle: { marginBottom: 6 },
  upsellBody: { color: "rgba(255,255,255,0.6)", marginBottom: 13 },
});
