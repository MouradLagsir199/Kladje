export const strings = {
  appName: "Kladje",
  signIn: {
    subtitle: "Log in om verder te gaan.",
    apple: "Ga verder met Apple",
    google: "Ga verder met Google",
  },
  home: {
    loadError: "Kon /v1/me niet laden.",
    signedInAs: (name: string, tier: "gratis" | "premium", used: number, limit: number) =>
      `Ingelogd als ${name} · ${tier} · ${used}/${limit} imports gebruikt.`,
    signOut: "Uitloggen",
    unknownUser: "onbekend",
  },
};
