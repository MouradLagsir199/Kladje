import { Tabs } from "expo-router";

import { TabBar } from "@/components/TabBar";
import { strings } from "@/strings/nl";

// The tab bar is fully custom (the import button in the middle is not a tab), so the navigator
// only supplies routing. Types come from the navigator itself rather than @react-navigation —
// Expo Router SDK 56+ no longer supports importing from those packages directly.
type TabBarRenderer = NonNullable<React.ComponentProps<typeof Tabs>["tabBar"]>;

const renderTabBar: TabBarRenderer = ({ state, navigation }) => (
  <TabBar
    active={state.routes[state.index].name}
    onSelect={(name) => {
      const target = state.routes.find((route) => route.name === name);
      if (!target) return;
      navigation.emit({ type: "tabPress", target: target.key, canPreventDefault: true });
      navigation.navigate(name);
    }}
  />
);

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{ headerShown: false }} tabBar={renderTabBar}>
      <Tabs.Screen name="ontdek" options={{ title: strings.tabs.ontdek }} />
      <Tabs.Screen name="recepten" options={{ title: strings.tabs.recepten }} />
      <Tabs.Screen name="planner" options={{ title: strings.tabs.planner }} />
      <Tabs.Screen name="profiel" options={{ title: strings.tabs.profiel }} />
    </Tabs>
  );
}
