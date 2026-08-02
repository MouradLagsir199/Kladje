// Every user-facing string in the app. Dutch, informal — "je", never "u".
// No string literals in JSX; if a screen needs new copy it gets added here first.

import type { Difficulty, MealType, Provenance, SourcePlatform, Unit } from "@/api/types";

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

  tabs: {
    ontdek: "Ontdek",
    recepten: "Recepten",
    planner: "Planner",
    profiel: "Profiel",
    importeren: "Recept importeren",
  },

  feed: {
    title: "Ontdek",
    searchPlaceholder: "Zoek recept of ingrediënt",
    quick: "Onder 30 minuten",
    fromGroups: "Nieuw van je groepen",
    showAll: "Toon alles",
    season: (month: string) => `Seizoen · ${month}`,
    soon: {
      title: "Ontdekken komt eraan",
      body: "Hier komen recepten om te ontdekken. Importeer zolang je eigen recepten van TikTok, Instagram, YouTube of een blog.",
      action: "Recept importeren",
    },
  },

  planner: {
    title: "Planner",
    week: "Week",
    shopping: "Boodschappen",
    soon: {
      title: "Weekplanner komt eraan",
      body: "Straks plan je hier je week en maak je in één tik een boodschappenlijst.",
    },
  },

  profile: {
    title: "Profiel",
    tier: { free: "Gratis", premium: "Premium" },
    stats: { recipes: "Recepten", cooked: "Gekookt", imports: "Imports" },
    upsell: {
      used: (used: number, limit: number) => `Je gebruikte ${used} van je ${limit} gratis imports.`,
      benefit: "Met Premium importeer je onbeperkt en deel je met je groepen.",
      action: "Bekijk Premium",
    },
    settings: "Instellingen",
    signOut: "Uitloggen",
    loadError: "Kon je profiel niet laden.",
  },

  cook: {
    close: "Sluiten",
    progress: (current: number, total: number) => `Stap ${current} van ${total}`,
    nowNeeded: "Nu nodig",
    previous: "Vorige stap",
    next: "Volgende",
    finish: "Klaar",
    startTimer: (label: string) => `Start timer ${label}`,
    noSteps: "Dit recept heeft nog geen stappen.",
  },

  importFlow: {
    title: "Recept importeren",
    close: "Sluiten",
    soon: {
      title: "Importeren komt eraan",
      body: "De importmotor werkt al: TikTok, Instagram, YouTube en blogs worden uitgelezen. Dit scherm wordt er nu omheen gebouwd.",
    },
  },

  library: {
    title: "Bibliotheek",
    all: "Alles",
    collections: "Collecties",
    count: (n: number) => `${n} ${n === 1 ? "recept" : "recepten"}`,
    empty: {
      title: "Nog geen recepten",
      body: "Importeer je eerste recept van TikTok, Instagram, YouTube of een blog.",
      action: "Recept importeren",
    },
    loadError: "Kon je recepten niet laden.",
    retry: "Opnieuw proberen",
  },

  detail: {
    ingredients: "Ingrediënten",
    method: "Bereiding",
    servings: (n: number) => `${n} pers.`,
    fewer: "Minder porties",
    more: "Meer porties",
    addAllToList: "Alles naar boodschappenlijst",
    notes: "Jouw notities",
    notesPlaceholder: "Volgende keer minder zout…",
    cookedCount: (n: number) => `${n}× gekookt`,
    lastCooked: (date: string) => `Laatst op ${date}`,
    neverCooked: "Nog niet gekookt",
    startCooking: "Start koken",
    plan: "Plan in",
    list: "Lijst",
    back: "Terug",
    // The always-visible attribution line. Required, see docs/07-legal-avg.md.
    attribution: (author: string, platform: string) => `Van ${author} op ${platform}`,
    attributionNoAuthor: (platform: string) => `Van ${platform}`,
    original: "origineel",
    stepsRewritten: "De stappen zijn door AI herschreven op basis van de bron.",
    timer: (label: string) => `Timer ${label}`,
    loadError: "Kon dit recept niet laden.",
  },

  meta: {
    total: "Totaal",
    prep: "Voorbereiden",
    cook: "Koken",
    servings: "Porties",
    difficulty: "Niveau",
    kcal: "Kcal p.p.",
    minutes: (n: number) => `${n} min`,
    unknown: "—",
  },

  provenance: {
    explicit: "Stond in de bron",
    derived: "Omgerekend",
    estimated: "Geschat door AI",
    missing: "Ontbreekt",
  } satisfies Record<Provenance, string>,

  provenanceShort: {
    explicit: "bron",
    derived: "omgerekend",
    estimated: "geschat",
    missing: "ontbreekt",
  } satisfies Record<Provenance, string>,

  platform: {
    tiktok: "TikTok",
    instagram: "Instagram",
    youtube: "YouTube",
    pinterest: "Pinterest",
    web: "Website",
    photo_ocr: "Foto",
    manual: "Zelf ingevoerd",
  } satisfies Record<SourcePlatform, string>,

  mealType: {
    ontbijt: "Ontbijt",
    lunch: "Lunch",
    diner: "Diner",
    tussendoor: "Tussendoor",
  } satisfies Record<MealType, string>,

  difficulty: {
    makkelijk: "Makkelijk",
    gemiddeld: "Gemiddeld",
    uitdagend: "Uitdagend",
  } satisfies Record<Difficulty, string>,

  // Short forms as they appear in an ingredient line. `stuk` and `naar_smaak` deliberately render
  // as nothing and as a trailing phrase respectively — "2 stuk ei" is not Dutch.
  unit: {
    g: "g",
    kg: "kg",
    ml: "ml",
    l: "l",
    el: "el",
    tl: "tl",
    stuk: "",
    snuf: "snuf",
    teentje: "teentje",
    bosje: "bosje",
    blikje: "blikje",
    pakje: "pakje",
    plak: "plak",
    handvol: "handvol",
    naar_smaak: "naar smaak",
  } satisfies Record<Unit, string>,

  optional: "optioneel",
};
