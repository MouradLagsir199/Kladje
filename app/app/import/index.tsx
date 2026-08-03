import * as Clipboard from "expo-clipboard";
import { useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import type { ApiError } from "@/api/imports";
import { useCreateImport } from "@/api/imports";
import { useMe } from "@/api/me";
import { Button } from "@/components/Button";
import { Text } from "@/components/Text";
import { messageForApiError } from "@/lib/import-errors";
import { detectPlatform } from "@/lib/platform";
import { strings } from "@/strings/nl";
import { color, radius, space, type } from "@/theme/tokens";

export default function ImportScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data: me } = useMe();
  const createImport = useCreateImport();

  const [url, setUrl] = useState("");
  const [clipboardUrl, setClipboardUrl] = useState<string | null>(null);
  const [conflictRecipeId, setConflictRecipeId] = useState<string | null>(null);

  useEffect(() => {
    // Read once on open. The prototype's clipboard card is the fastest path in the whole app —
    // you share a link from TikTok, open Kladje, and the thing you copied is already offered.
    let cancelled = false;
    Clipboard.getStringAsync()
      .then((text) => {
        const candidate = text.trim();
        if (!cancelled && detectPlatform(candidate)) setClipboardUrl(candidate);
      })
      .catch(() => {
        // A denied clipboard read is not an error worth showing; the paste field still works.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const start = useCallback(
    async (candidate: string) => {
      setConflictRecipeId(null);
      try {
        const created = await createImport.mutateAsync(candidate);
        router.replace(`/import/${created.id}/progress`);
      } catch (error) {
        const apiError = error as ApiError;
        // A duplicate is not really a failure — the recipe the user wanted already exists, so the
        // useful response is a way to open it rather than an apology.
        const existing = apiError.details?.recipe_id;
        if (apiError.code === "conflict" && typeof existing === "string") {
          setConflictRecipeId(existing);
        }
      }
    },
    [createImport, router],
  );

  const quota = me?.quota;
  const outOfQuota = quota ? quota.used >= quota.limit : false;
  const pasted = url.trim();
  const canStart = pasted.length > 0 && !createImport.isPending && !outOfQuota;

  return (
    <View style={styles.screen}>
      <View style={[styles.header, { paddingTop: insets.top + space.md }]}>
        <Text variant="heading">{strings.importFlow.title}</Text>
        <Pressable accessibilityRole="button" onPress={() => router.back()}>
          <Text variant="bodyBold" tone="mutedLight">
            {strings.importFlow.cancel}
          </Text>
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {clipboardUrl && (
          <View style={styles.clipboard}>
            <View style={styles.clipboardDot} />
            <View style={styles.clipboardBody}>
              <Text variant="bodyBold" style={styles.clipboardTitle}>
                {clipboardTitleFor(clipboardUrl)}
              </Text>
              <Text variant="small" tone="accentPress" style={styles.clipboardUrl} numberOfLines={2}>
                {clipboardUrl.replace(/^https?:\/\//, "")}
              </Text>
              <Button
                label={strings.importFlow.paste.importIt}
                size="small"
                disabled={createImport.isPending || outOfQuota}
                onPress={() => start(clipboardUrl)}
              />
            </View>
          </View>
        )}

        <View style={styles.pasteZone}>
          <Text variant="bodyBold" style={styles.pasteTitle}>
            {strings.importFlow.paste.orPaste}
          </Text>
          <Text variant="small" tone="mutedLight" style={styles.pasteHint}>
            {strings.importFlow.paste.supported}
          </Text>
          <TextInput
            value={url}
            onChangeText={setUrl}
            placeholder={strings.importFlow.paste.placeholder}
            placeholderTextColor={color.mutedLight}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            returnKeyType="go"
            onSubmitEditing={() => canStart && start(pasted)}
            style={styles.input}
          />
        </View>

        <Button
          label={createImport.isPending ? strings.importFlow.progress.title : strings.importFlow.paste.start}
          fullWidth
          disabled={!canStart}
          onPress={() => start(pasted)}
        />
        {createImport.isPending && <ActivityIndicator style={styles.spinner} color={color.accent} />}

        {createImport.isError && (
          <View style={styles.error}>
            <Text variant="body" tone="provMissing">
              {messageForApiError(createImport.error)}
            </Text>
            {conflictRecipeId && (
              <Pressable
                accessibilityRole="button"
                onPress={() => router.replace(`/recipe/${conflictRecipeId}`)}
              >
                <Text variant="bodyBold" tone="accent" style={styles.errorAction}>
                  {strings.importFlow.seeRecipe}
                </Text>
              </Pressable>
            )}
          </View>
        )}

        {quota && (
          <View style={styles.quota}>
            <Text variant="small" tone="muted">
              {outOfQuota
                ? strings.importFlow.paste.quotaGone
                : strings.importFlow.paste.quota(quota.used, quota.limit)}
            </Text>
            <Text variant="bodyBold" tone="accent">
              {strings.importFlow.paste.premium}
            </Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

function clipboardTitleFor(url: string): string {
  const platform = detectPlatform(url);
  if (!platform || platform === "web") return strings.importFlow.paste.clipboardGeneric;
  return strings.importFlow.paste.clipboardTitle(strings.platform[platform]);
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.surface },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: space.xl,
    paddingBottom: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.lineFaint,
  },
  content: { padding: space.xl, gap: 16 },

  clipboard: {
    flexDirection: "row",
    gap: 12,
    padding: 15,
    borderRadius: radius.card,
    backgroundColor: color.accentWash,
    borderWidth: 1,
    borderColor: "#f8d3ca",
  },
  clipboardDot: {
    width: 7,
    height: 7,
    borderRadius: radius.pill,
    backgroundColor: color.accent,
    marginTop: 6,
  },
  clipboardBody: { flex: 1, alignItems: "flex-start" },
  clipboardTitle: { marginBottom: 6 },
  clipboardUrl: { marginBottom: 11 },

  pasteZone: {
    borderWidth: 1.5,
    borderStyle: "dashed",
    borderColor: "#d8d8d2",
    borderRadius: radius.card,
    padding: 18,
    alignItems: "center",
  },
  pasteTitle: { marginBottom: 6 },
  pasteHint: { marginBottom: 14, textAlign: "center" },
  input: {
    alignSelf: "stretch",
    paddingVertical: 11,
    paddingHorizontal: 13,
    borderRadius: radius.input,
    borderWidth: 1,
    borderColor: color.line,
    backgroundColor: color.surface,
    fontSize: type.bodyLarge.size,
    color: color.ink,
  },

  spinner: { marginTop: 4 },
  error: { gap: 8 },
  errorAction: { marginTop: 2 },

  quota: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 13,
    paddingHorizontal: 15,
    borderRadius: 13,
    backgroundColor: color.surfaceAlt,
  },
});
