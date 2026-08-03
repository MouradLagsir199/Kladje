import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect } from "react";
import { ActivityIndicator, Pressable, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useImport } from "@/api/imports";
import type { ImportDetail } from "@/api/types";
import { Button } from "@/components/Button";
import { Text } from "@/components/Text";
import { importErrorMessage, isRetryable } from "@/lib/import-errors";
import { strings } from "@/strings/nl";
import { color, radius, space } from "@/theme/tokens";

/** The pipeline's stages, in the order the server runs them. */
const STAGES = [
  { key: "fetch", label: strings.importFlow.progress.stages.fetch },
  { key: "synthesize", label: strings.importFlow.progress.stages.synthesize },
  { key: "validate", label: strings.importFlow.progress.stages.validate },
] as const;

type StageState = "pending" | "active" | "done" | "failed";

export default function ImportProgressScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data, isError } = useImport(id);

  useEffect(() => {
    if (data?.status === "ready_for_review") {
      router.replace(`/import/${id}/review`);
    }
    if (data?.status === "saved" && data.recipe_id) {
      // Reachable by coming back to a finished import; there is nothing left to review.
      router.replace(`/recipe/${data.recipe_id}`);
    }
  }, [data?.status, data?.recipe_id, id, router]);

  const failed = data?.status === "failed";

  return (
    <View style={[styles.screen, { paddingTop: insets.top + 34 }]}>
      <Text variant="display" style={styles.title}>
        {failed ? importErrorMessage(data?.error_code) : strings.importFlow.progress.title}
      </Text>

      {!failed && (
        <Text variant="body" tone="muted" style={styles.body}>
          {strings.importFlow.progress.body}
        </Text>
      )}

      {!failed && (
        <View style={styles.stages}>
          {STAGES.map((stage) => (
            <StageRow key={stage.key} label={stage.label} state={stateOf(stage.key, data)} />
          ))}
        </View>
      )}

      {failed && (
        <View style={styles.actions}>
          {isRetryable(data?.error_code) && (
            <Button
              label={strings.importFlow.progress.retry}
              onPress={() => router.replace("/import")}
            />
          )}
          <Pressable accessibilityRole="button" onPress={() => router.back()}>
            <Text variant="bodyBold" tone="muted">
              {strings.importFlow.close}
            </Text>
          </Pressable>
        </View>
      )}

      {isError && (
        <Text variant="body" tone="provMissing">
          {strings.importFlow.errors.unknown}
        </Text>
      )}
    </View>
  );
}

/**
 * A stage's state, read from the event rows the server wrote.
 *
 * Deliberately not a timer. The prototype animates five stages over a fixed duration, which looks
 * identical whether the import is working or hung — and this pipeline has three stages, not five,
 * now that Apify supplies the transcript directly.
 */
function stateOf(stage: string, data: ImportDetail | undefined): StageState {
  if (!data) return "pending";
  const events = data.events.filter((event) => event.stage === stage);
  if (events.some((event) => event.state === "failed")) return "failed";
  if (events.some((event) => event.state === "done")) return "done";
  if (events.some((event) => event.state === "started")) return "active";
  return "pending";
}

function StageRow({ label, state }: { label: string; state: StageState }) {
  return (
    <View style={[styles.stage, state !== "pending" && styles.stageLit]}>
      <View style={[styles.ring, RING[state]]}>
        {state === "done" && (
          <Text variant="tiny" tone="surface" style={styles.check}>
            ✓
          </Text>
        )}
        {state === "active" && <ActivityIndicator size="small" color={color.accent} />}
      </View>
      <Text variant="bodyLarge" tone={state === "pending" ? "mutedLight" : "ink"}>
        {label}
      </Text>
    </View>
  );
}

const RING: Record<StageState, { borderColor: string; backgroundColor: string }> = {
  pending: { borderColor: color.pending, backgroundColor: "transparent" },
  active: { borderColor: color.accent, backgroundColor: "transparent" },
  done: { borderColor: color.provExplicit, backgroundColor: color.provExplicit },
  failed: { borderColor: color.provMissing, backgroundColor: color.provMissing },
};

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.surface, paddingHorizontal: 24, paddingBottom: 30 },
  title: { fontSize: 21, lineHeight: 26, marginBottom: 6 },
  body: { marginBottom: 26 },
  stages: { gap: 2 },
  stage: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 13,
    paddingHorizontal: 15,
    borderRadius: radius.row,
  },
  stageLit: { backgroundColor: color.surfaceAlt },
  ring: {
    width: 22,
    height: 22,
    borderRadius: radius.pill,
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
  },
  check: { lineHeight: 10 },
  actions: { gap: space.lg, alignItems: "flex-start", marginTop: space.lg },
});
