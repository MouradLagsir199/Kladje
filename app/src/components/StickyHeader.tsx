import { StyleSheet, View, type ViewProps } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { color, space } from "@/theme/tokens";

/**
 * The blurred-white header every scrolling screen sits under in the prototype.
 *
 * The prototype hardcodes 52px of top padding for the status bar; on a real device that is the
 * safe-area inset, which is not 52 on most phones.
 */
export function StickyHeader({ style, children, ...rest }: ViewProps) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.header, { paddingTop: insets.top + space.sm }, style]} {...rest}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    backgroundColor: color.surface,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.lineFaint,
  },
});
