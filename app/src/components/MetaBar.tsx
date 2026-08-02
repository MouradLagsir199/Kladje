import { StyleSheet, View } from "react-native";

import { Text } from "@/components/Text";
import { color } from "@/theme/tokens";

export type MetaField = {
  label: string;
  value: string;
};

/** The bordered strip under a recipe title: mono uppercase label over the value, four across. */
export function MetaBar({ fields }: { fields: MetaField[] }) {
  return (
    <View style={styles.bar}>
      {fields.map((field) => (
        <View key={field.label} style={styles.field}>
          <Text variant="micro" tone="mutedLight">
            {field.label}
          </Text>
          <Text variant="bodyBold" tone="ink">
            {field.value}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    gap: 16,
    alignItems: "center",
    paddingVertical: 13,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderColor: color.lineFaint,
  },
  field: { gap: 3 },
});
