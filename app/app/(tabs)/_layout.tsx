import { Tabs } from "expo-router";

import { matchesTab, TabBar } from "@/components/TabBar";

// The tab bar is fully custom (the import button in the middle is not a tab), so the navigator
// only supplies routing. Types come from the navigator itself rather than @react-navigation —
// Expo Router SDK 56+ no longer supports importing from those packages directly.
type TabBarRenderer = NonNullable<React.ComponentProps<typeof Tabs>["tabBar"]>;

// Screens are discovered from the filesystem; there are deliberately no `Tabs.Screen` entries.
// A directory route is named after its path — `ontdek/index`, not `ontdek` — so declaring them by
// the name we *call* them would silently not match, which is exactly the bug this replaced.
const renderTabBar: TabBarRenderer = ({ state, navigation }) => (
  <TabBar
    active={state.routes[state.index]?.name ?? ""}
    onSelect={(tab) => {
      const target = state.routes.find((route) => matchesTab(route.name, tab));
      if (!target) return;
      navigation.emit({ type: "tabPress", target: target.key, canPreventDefault: true });
      navigation.navigate(target.name);
    }}
  />
);

export default function TabsLayout() {
  return <Tabs screenOptions={{ headerShown: false }} tabBar={renderTabBar} />;
}
