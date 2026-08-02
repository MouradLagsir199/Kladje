import { StyleSheet, View } from "react-native";

import { Button } from "@/components/Button";
import { Text } from "@/components/Text";
import { color } from "@/theme/tokens";

type Props = {
  title: string;
  body: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function EmptyState({ title, body, actionLabel, onAction }: Props) {
  return (
    <View style={styles.wrap}>
      <View style={styles.glyph} />
      <Text variant="heading" tone="ink" style={styles.title}>
        {title}
      </Text>
      <Text variant="body" tone="muted" style={styles.body}>
        {body}
      </Text>
      {actionLabel && <Button label={actionLabel} onPress={onAction} />}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { paddingVertical: 70, paddingHorizontal: 34, alignItems: "center" },
  glyph: {
    width: 74,
    height: 74,
    borderRadius: 20,
    backgroundColor: color.surfaceSunk,
    marginBottom: 18,
  },
  title: { marginBottom: 7, textAlign: "center" },
  body: { marginBottom: 18, textAlign: "center" },
});
