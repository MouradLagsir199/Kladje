import { Pressable, StyleSheet, View } from "react-native";

import type { StepOut } from "@/api/types";
import { Text } from "@/components/Text";
import { strings } from "@/strings/nl";
import { color, radius, space } from "@/theme/tokens";

type Props = {
  step: StepOut;
  number: number;
  onStartTimer?: (seconds: number) => void;
};

/** "20 min", or "1 u 30" once a step runs past the hour. */
export function timerLabel(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return strings.meta.minutes(minutes);
  const rest = minutes % 60;
  return rest === 0 ? `${minutes / 60} u` : `${Math.floor(minutes / 60)} u ${rest}`;
}

export function StepCard({ step, number, onStartTimer }: Props) {
  const seconds = step.timer_seconds;

  return (
    <View style={styles.row}>
      <View style={styles.number}>
        <Text variant="caption" tone="ink" style={styles.numberText}>
          {number}
        </Text>
      </View>

      <View style={styles.body}>
        <Text variant="bodyLarge" tone="inkSoft">
          {step.text}
        </Text>
        {/* A chip, not a button, until there is a timer to start. `onStartTimer` turns it into
            one — see M21, where the timer has to survive backgrounding. */}
        {seconds !== null && seconds > 0 && (
          <Pressable
            accessibilityRole={onStartTimer ? "button" : "text"}
            disabled={!onStartTimer}
            onPress={() => onStartTimer?.(seconds)}
            style={styles.timer}
          >
            <Text variant="bodyBold" tone="accent" style={styles.timerText}>
              {strings.detail.timer(timerLabel(seconds))}
            </Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: 13 },
  number: {
    width: 25,
    height: 25,
    borderRadius: radius.pill,
    backgroundColor: color.surfaceSunk,
    alignItems: "center",
    justifyContent: "center",
  },
  numberText: { lineHeight: 12 },
  body: { flex: 1 },
  timer: {
    marginTop: space.md,
    alignSelf: "flex-start",
    paddingVertical: 7,
    paddingHorizontal: 12,
    borderRadius: radius.chip,
    backgroundColor: color.accentWash,
  },
  timerText: { lineHeight: 12.5 },
});
