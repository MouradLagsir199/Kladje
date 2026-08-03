import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useImport, usePatchDraft, useSaveImport } from "@/api/imports";
import type { DraftIngredient, DraftRecipe } from "@/api/types";
import { Button } from "@/components/Button";
import { ProvenanceDot } from "@/components/ProvenanceDot";
import { Text } from "@/components/Text";
import { formatAmount } from "@/lib/format";
import { messageForApiError } from "@/lib/import-errors";
import { useDebounced } from "@/lib/use-debounced";
import { strings } from "@/strings/nl";
import { color, radius, space, type } from "@/theme/tokens";

type Form = {
  /** Which import this form was hydrated from, so a different one resets it. */
  importId: string;
  title: string;
  servings: string;
  ingredients: DraftIngredient[];
};

/** Variant A from the prototype. B and C were dropped by D16 and are not built. */
export default function ImportReviewScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const { data, isPending } = useImport(id);
  const patchDraft = usePatchDraft(id);
  const saveImport = useSaveImport(id);

  const recipe = data?.draft?.recipe;

  /**
   * The form, hydrated from the draft exactly once per import.
   *
   * Deliberately not an effect keyed on the draft: this screen polls, so re-hydrating whenever a
   * response arrives would wipe out whatever the user was mid-way through typing. Setting state
   * during render to reset it when the identity changes is the documented pattern for this, and it
   * does not cascade.
   *
   * The one thing that *does* flow back from the server is a value it refused — see `patch` below.
   */
  const [form, setForm] = useState<Form | null>(null);
  if (recipe && form?.importId !== id) {
    setForm({
      importId: id,
      title: recipe.title,
      servings: recipe.servings === null ? "" : String(recipe.servings),
      ingredients: recipe.ingredients,
    });
  }

  const patch = useDebounced((body: Record<string, unknown>) => {
    const sentServings = "servings" in body ? body.servings : undefined;
    patchDraft.mutate(body, {
      onSuccess: (updated) => {
        // Validation runs on hand-typed values too, so a serving count the server refuses comes
        // back null. Reflecting only that case keeps the field honest without letting a slow
        // response overwrite newer keystrokes.
        if (sentServings != null && updated.draft?.recipe.servings === null) {
          setForm((current) => (current ? { ...current, servings: "" } : current));
        }
      },
    });
  });

  if (isPending || !recipe || !form) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={color.accent} />
      </View>
    );
  }

  const missing = recipe.missing.filter((field) => field in strings.importFlow.review.fieldLabels);

  async function save() {
    patch.flush();
    const saved = await saveImport.mutateAsync();
    router.replace(`/import/${id}/done?recipeId=${saved.id}`);
  }

  return (
    <View style={styles.screen}>
      <View style={[styles.header, { paddingTop: insets.top + space.md }]}>
        <Text variant="heading">{strings.importFlow.review.title}</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {missing.length > 0 && (
          <View style={styles.missingCard}>
            <Text variant="bodyBold" tone="warnInk" style={styles.missingTitle}>
              {missing.length === 1
                ? strings.importFlow.review.missingOne
                : strings.importFlow.review.missingMany(missing.length)}
            </Text>
            <Text variant="small" tone="warnInk">
              {missing.map((field) => strings.importFlow.review.fieldLabels[field]).join(" · ")}
            </Text>
          </View>
        )}

        <View>
          <Text variant="micro" tone="mutedLight" style={styles.fieldLabel}>
            {strings.importFlow.review.titleLabel}
          </Text>
          <TextInput
            value={form.title}
            onChangeText={(next) => {
              setForm({ ...form, title: next });
              patch.call({ title: next });
            }}
            style={[styles.input, styles.titleInput]}
          />
        </View>

        <View style={styles.metaRow}>
          <ScalarField
            label={strings.importFlow.review.fieldLabels.servings}
            value={form.servings}
            provenance={recipe.field_provenance.servings}
            onChange={(next) => {
              setForm({ ...form, servings: next });
              const parsed = Number.parseInt(next, 10);
              patch.call({ servings: Number.isFinite(parsed) ? parsed : null });
            }}
          />
          <ReadOnlyField
            label={strings.importFlow.review.fieldLabels.prep_minutes}
            value={recipe.prep_minutes === null ? "—" : strings.meta.minutes(recipe.prep_minutes)}
            provenance={recipe.field_provenance.prep_minutes}
          />
          <ReadOnlyField
            label={strings.importFlow.review.fieldLabels.cook_minutes}
            value={recipe.cook_minutes === null ? "—" : strings.meta.minutes(recipe.cook_minutes)}
            provenance={recipe.field_provenance.cook_minutes}
          />
        </View>

        <Text variant="title">{strings.importFlow.review.ingredients}</Text>
        <View style={styles.ingredients}>
          {form.ingredients.map((item, index) => (
            <IngredientEditor
              key={`${item.pos}-${index}`}
              item={item}
              onChange={(next) =>
                setForm({
                  ...form,
                  ingredients: form.ingredients.map((row, at) => (at === index ? next : row)),
                })
              }
              // Sent on blur rather than per keystroke: re-validation merges duplicates and
              // renumbers, which must not happen while a field still has focus.
              onCommit={() => patchDraft.mutate({ ingredients: form.ingredients })}
            />
          ))}
        </View>

        <Text variant="title">{strings.importFlow.review.steps}</Text>
        <View style={styles.steps}>
          {recipe.steps.map((step) => (
            <View key={step.pos} style={styles.step}>
              <View style={styles.stepNumber}>
                <Text variant="caption" style={styles.stepNumberText}>
                  {step.pos}
                </Text>
              </View>
              <Text variant="body" tone="inkSoft" style={styles.stepText}>
                {step.text}
              </Text>
            </View>
          ))}
        </View>

        {/* Required disclosure, not a nicety — docs/07-legal-avg.md. */}
        <View style={styles.footnote}>
          <Text variant="small" tone="muted">
            {strings.importFlow.review.rewritten}
          </Text>
        </View>

        {saveImport.isError && (
          <Text variant="body" tone="provMissing">
            {messageForApiError(saveImport.error)}
          </Text>
        )}
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: Math.max(insets.bottom, space.lg) }]}>
        <Button
          label={
            saveImport.isPending
              ? strings.importFlow.review.saving
              : strings.importFlow.review.save
          }
          fullWidth
          disabled={saveImport.isPending}
          onPress={save}
        />
      </View>
    </View>
  );
}

function ScalarField({
  label,
  value,
  provenance,
  onChange,
}: {
  label: string;
  value: string;
  provenance: DraftRecipe["field_provenance"][string] | undefined;
  onChange: (next: string) => void;
}) {
  return (
    <View style={styles.field}>
      <FieldLabel label={label} provenance={provenance} />
      <TextInput
        value={value}
        onChangeText={onChange}
        keyboardType="number-pad"
        placeholder="—"
        placeholderTextColor={color.mutedLight}
        style={[styles.input, styles.smallInput]}
      />
      {provenance === "estimated" && (
        <Text variant="tiny" tone="provDerived" style={styles.estimated}>
          {strings.importFlow.review.estimated}
        </Text>
      )}
    </View>
  );
}

function ReadOnlyField({
  label,
  value,
  provenance,
}: {
  label: string;
  value: string;
  provenance: DraftRecipe["field_provenance"][string] | undefined;
}) {
  return (
    <View style={styles.field}>
      <FieldLabel label={label} provenance={provenance} />
      <View style={[styles.input, styles.smallInput, styles.readOnly]}>
        <Text variant="bodyBold">{value}</Text>
      </View>
    </View>
  );
}

function FieldLabel({
  label,
  provenance,
}: {
  label: string;
  provenance: DraftRecipe["field_provenance"][string] | undefined;
}) {
  return (
    <View style={styles.fieldHead}>
      {provenance && <ProvenanceDot provenance={provenance} />}
      <Text variant="micro" tone="mutedLight">
        {label}
      </Text>
    </View>
  );
}

function IngredientEditor({
  item,
  onChange,
  onCommit,
}: {
  item: DraftIngredient;
  onChange: (next: DraftIngredient) => void;
  onCommit: () => void;
}) {
  return (
    <View style={styles.ingredientRow}>
      <ProvenanceDot provenance={item.prov} />
      <TextInput
        value={item.amount === null ? "" : formatAmount(item.amount)}
        onChangeText={(next) => {
          const parsed = Number.parseFloat(next.replace(",", "."));
          onChange({ ...item, amount: Number.isFinite(parsed) ? parsed : null });
        }}
        onBlur={onCommit}
        keyboardType="decimal-pad"
        accessibilityLabel={strings.importFlow.review.qty}
        style={[styles.input, styles.qtyInput]}
      />
      <TextInput
        value={item.unit ?? ""}
        onChangeText={(next) => onChange({ ...item, unit: (next || null) as typeof item.unit })}
        onBlur={onCommit}
        autoCapitalize="none"
        accessibilityLabel={strings.importFlow.review.unit}
        style={[styles.input, styles.unitInput]}
      />
      <View style={styles.nameCell}>
        <TextInput
          value={item.name_nl}
          onChangeText={(next) => onChange({ ...item, name_nl: next })}
          onBlur={onCommit}
          accessibilityLabel={strings.importFlow.review.name}
          style={[styles.input, styles.nameInput]}
        />
        {item.orig_amount !== null && (
          // What the source actually said, so a conversion is never a black box.
          <Text variant="small" tone="mutedLight" style={styles.original}>
            {formatAmount(item.orig_amount)} {item.orig_unit ?? ""}
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.surface },
  centre: { flex: 1, alignItems: "center", justifyContent: "center" },
  header: {
    paddingHorizontal: space.xl,
    paddingBottom: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.lineFaint,
  },
  content: { padding: space.xl, paddingBottom: 120, gap: 16 },

  missingCard: {
    padding: 15,
    borderRadius: radius.panel,
    backgroundColor: color.warnWash,
    borderWidth: 1,
    borderColor: color.warnBorder,
  },
  missingTitle: { marginBottom: 5 },

  fieldLabel: { marginBottom: 6 },
  input: {
    borderRadius: radius.input,
    borderWidth: 1,
    borderColor: color.line,
    backgroundColor: color.surface,
    color: color.ink,
    paddingVertical: 9,
    paddingHorizontal: 11,
    fontSize: type.bodyLarge.size,
  },
  titleInput: { fontSize: 14.5 },

  metaRow: { flexDirection: "row", gap: 8 },
  field: { flex: 1 },
  fieldHead: { flexDirection: "row", alignItems: "center", gap: 5, marginBottom: 5 },
  smallInput: { paddingVertical: 8, paddingHorizontal: 10, fontSize: 13 },
  readOnly: { backgroundColor: color.surfaceAlt, justifyContent: "center" },
  estimated: { marginTop: 4 },

  ingredients: { gap: 6 },
  ingredientRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
    padding: 10,
    borderRadius: radius.row,
    borderWidth: 1,
    borderColor: color.line,
  },
  qtyInput: { width: 56, paddingVertical: 6, paddingHorizontal: 7, fontSize: 13 },
  unitInput: { width: 62, paddingVertical: 6, paddingHorizontal: 7, fontSize: 13 },
  nameCell: { flex: 1, minWidth: 0 },
  nameInput: { borderColor: "transparent", paddingVertical: 6, paddingHorizontal: 7, fontSize: 13.5 },
  original: { paddingLeft: 7, marginTop: 2 },

  steps: { gap: 8 },
  step: {
    flexDirection: "row",
    gap: 11,
    padding: 12,
    borderRadius: radius.row,
    backgroundColor: color.surfaceAlt,
  },
  stepNumber: {
    width: 22,
    height: 22,
    borderRadius: radius.pill,
    backgroundColor: color.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  stepNumberText: { lineHeight: 11 },
  stepText: { flex: 1 },

  footnote: { padding: 12, borderRadius: radius.row, backgroundColor: color.surfaceAlt },

  footer: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    paddingTop: 12,
    paddingHorizontal: 16,
    backgroundColor: color.surface,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: color.lineFaint,
  },
});
