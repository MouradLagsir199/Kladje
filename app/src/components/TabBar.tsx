import { useRouter } from "expo-router";
import { Pressable, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { BooksIcon, CalendarIcon, CompassIcon, PersonIcon } from "@/components/icons";
import { Text } from "@/components/Text";
import { strings } from "@/strings/nl";
import { color, radius, space } from "@/theme/tokens";

type IconComponent = (props: { color: string; size?: number }) => React.ReactElement;

const TABS: { name: string; label: string; Icon: IconComponent }[] = [
  { name: "ontdek", label: strings.tabs.ontdek, Icon: CompassIcon },
  { name: "recepten", label: strings.tabs.recepten, Icon: BooksIcon },
  { name: "planner", label: strings.tabs.planner, Icon: CalendarIcon },
  { name: "profiel", label: strings.tabs.profiel, Icon: PersonIcon },
];

type Props = {
  /** Route name of the focused tab, e.g. "recepten". */
  active: string;
  onSelect: (name: string) => void;
};

/**
 * Four tabs with the import button wedged in the middle.
 *
 * The centre button is not a fifth tab and never shows an active state — it opens the import
 * modal over whatever you were doing and returns you there. Building it as a tab would give it a
 * selected state it can never legitimately be in.
 */
export function TabBar({ active, onSelect }: Props) {
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const half = TABS.length / 2;

  return (
    <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, space.md) }]}>
      {TABS.slice(0, half).map((tab) => (
        <TabButton key={tab.name} tab={tab} active={active === tab.name} onSelect={onSelect} />
      ))}

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={strings.tabs.importeren}
        onPress={() => router.push("/import")}
        style={({ pressed }) => [styles.importButton, pressed && styles.importPressed]}
      >
        <View style={styles.plusHorizontal} />
        <View style={styles.plusVertical} />
      </Pressable>

      {TABS.slice(half).map((tab) => (
        <TabButton key={tab.name} tab={tab} active={active === tab.name} onSelect={onSelect} />
      ))}
    </View>
  );
}

function TabButton({
  tab,
  active,
  onSelect,
}: {
  tab: (typeof TABS)[number];
  active: boolean;
  onSelect: (name: string) => void;
}) {
  const tint = active ? color.ink : color.mutedLight;

  return (
    <Pressable
      accessibilityRole="tab"
      accessibilityState={{ selected: active }}
      accessibilityLabel={tab.label}
      onPress={() => onSelect(tab.name)}
      style={styles.tab}
    >
      <tab.Icon color={tint} />
      <Text variant="tabLabel" style={{ color: tint }}>
        {tab.label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingTop: 11,
    paddingHorizontal: 12,
    backgroundColor: color.surface,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: color.lineFaint,
  },
  tab: { flex: 1, alignItems: "center", gap: 5, paddingTop: 2 },
  importButton: {
    width: 54,
    height: 54,
    borderRadius: radius.pill,
    backgroundColor: color.accent,
    alignItems: "center",
    justifyContent: "center",
    marginTop: -14,
    shadowColor: color.accent,
    shadowOpacity: 0.45,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  importPressed: { backgroundColor: color.accentPress },
  plusHorizontal: { position: "absolute", width: 20, height: 2.5, borderRadius: 2, backgroundColor: color.surface },
  plusVertical: { position: "absolute", width: 2.5, height: 20, borderRadius: 2, backgroundColor: color.surface },
});
