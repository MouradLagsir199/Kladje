import { Stack } from "expo-router";

/**
 * The import flow as one nested stack, which is what makes it one modal.
 *
 * Without this layout the four steps are four separate root routes (`import/index`,
 * `import/[id]/progress`, …), so the root's `<Stack.Screen name="import">` matches nothing and the
 * modal presentation silently does not apply — the same mismatch that broke the tab bar.
 *
 * Grouping them also means `router.dismissAll()` on the done screen closes the whole flow and
 * returns to whatever the user was looking at when they pasted the link.
 */
export default function ImportLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      {/* No back gesture once the import is running: the pipeline is already spending money, and
          swiping away mid-import strands a row in `fetching` with nothing polling it. */}
      <Stack.Screen name="[id]/progress" options={{ gestureEnabled: false }} />
      <Stack.Screen name="[id]/review" />
      <Stack.Screen name="[id]/done" options={{ gestureEnabled: false }} />
    </Stack>
  );
}
