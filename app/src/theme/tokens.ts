// Extracted from docs/14-design-tokens.md, which is extracted from
// docs/prototype/Receptenapp.dc.html. Values only — see the prototype for layout.
// No hex literals in components: if a value isn't here, add it here first.

export const color = {
  // Surfaces
  canvas: "#eceae6",
  surface: "#ffffff",
  surfaceAlt: "#f8f8f6",
  surfaceSunk: "#f4f4f2",
  imageBg: "#e5e3de",

  // Ink
  ink: "#17171a",
  inkSoft: "#3a3a3f",
  muted: "#6e6e73",
  mutedLight: "#9a9aa0",
  disabled: "#c9c9cd",

  // Lines
  line: "#e9e9ec",
  lineWarm: "#e2e0da",
  lineSoft: "#ececea",
  // Hairline under sticky headers and above the tab bar. Lighter than `line` on purpose:
  // it sits under blurred chrome, where `line` reads as a hard edge.
  lineFaint: "#efeff1",

  // Accent — the tomato red
  accent: "#e8442c",
  accentPress: "#a8331f",
  accentWash: "#fdece8",

  // Provenance — the trust mechanism, use nowhere else
  provExplicit: "#2f9e5f",
  provDerived: "#e0a012",
  provMissing: "#d94b3b",

  // Semantic washes
  successWash: "#eef7f1",
  successInk: "#2f7f52",
  warnWash: "#fdf6e3",
  warnBorder: "#f0e0b0",
  warnInk: "#7a5a10",

  // The allergy card on Receptdetail. Red, not amber — an allergen warning comes from the user's
  // own profile, not from how sure we are about a value, so it must not read as a provenance state.
  dangerWash: "#fdeeeb",
  dangerBorder: "#f6cfc7",

  // Import progress, step not started yet.
  pending: "#dcdce0",

  // Source badges
  sourceVideo: "#8a5fc4",
  sourceWeb: "#3a6ea5",

  // Cook mode
  cookBg: "#16130f",
} as const;

export const type = {
  display: { size: 26, weight: "700", lineHeight: 1.15, tracking: -0.02 },
  title: { size: 17, weight: "700", lineHeight: 1.2 },
  heading: { size: 16, weight: "700", lineHeight: 1.2 },
  bodyLarge: { size: 15, weight: "400", lineHeight: 1.45 },
  body: { size: 13.5, weight: "400", lineHeight: 1.5 },
  bodyBold: { size: 13.5, weight: "600", lineHeight: 1.3 },
  small: { size: 12.5, weight: "400", lineHeight: 1.45 },
  caption: { size: 11.5, weight: "500", lineHeight: 1.3 },
  micro: {
    size: 10.5,
    weight: "500",
    lineHeight: 1,
    mono: true,
    uppercase: true,
    tracking: 0.1,
  },
  tiny: { size: 9.5, weight: "500", lineHeight: 1, mono: true }, // "geschat"

  // Tab bar only. Same size as `micro` but proportional and sentence case — `micro` is the mono
  // uppercase treatment for data labels, and a navigation label is not data.
  tabLabel: { size: 10.5, weight: "600", lineHeight: 1 },

  // Cook mode only — readable at 60cm with dirty hands
  cookStep: { size: 24, weight: "600", lineHeight: 1.35 },
  cookMeta: { size: 15, weight: "500", lineHeight: 1.3 },
} as const;

export const space = { xs: 4, sm: 6, md: 9, lg: 14, xl: 20, xxl: 28 } as const;

export const radius = {
  pill: 999, // chips, filter buttons, avatars — the most-used shape
  card: 15, // recipe cards, sheets
  panel: 14, // grouped panels, the missing-fields card
  tile: 13, // thumbnails
  row: 12, // list rows, ingredient rows
  input: 10,
  chip: 9,
  check: 6, // ingredient and shopping checkboxes
  dot: 999,
} as const;

// 8px in production, not the prototype's 5px — see docs/14-design-tokens.md.
// Below the perceptual threshold for a colour-blind user at phone size;
// always pair with a shape or letter, never colour alone.
export const dot = { size: 8 } as const;

export const motion = {
  pop: { from: { scale: 0.94, opacity: 0 }, to: { scale: 1, opacity: 1 }, duration: 180 },
  slideUp: { from: { translateY: 16, opacity: 0 }, to: { translateY: 0, opacity: 1 }, duration: 220 },
  spin: { duration: 1400, easing: "linear", loop: true }, // import progress
} as const;
