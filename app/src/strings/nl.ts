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
    cancel: "Annuleer",
    close: "Sluiten",

    paste: {
      clipboardTitle: (platform: string) => `We zagen een ${platform}-link op je klembord`,
      clipboardGeneric: "We zagen een link op je klembord",
      importIt: "Importeren",
      orPaste: "Of plak een link",
      supported: "TikTok · Instagram · YouTube · blog",
      placeholder: "https://…",
      start: "Importeren",
      quota: (used: number, limit: number) => `${used} van je ${limit} imports deze maand`,
      quotaGone: "Je imports van deze maand zijn op",
      premium: "Premium",
    },

    progress: {
      title: "Recept lezen…",
      // No promise of a duration: it depends on the platform and the length of the video.
      body: "Dit duurt meestal een halve minuut. Je kunt dit scherm open laten staan.",
      stages: {
        fetch: "Bron ophalen",
        synthesize: "Recept uitlezen",
        validate: "Controleren",
      },
      retry: "Opnieuw proberen",
    },

    review: {
      title: "Kloppen deze gegevens?",
      missingOne: "Eén ding ontbreekt",
      missingMany: (n: number) => `${n} dingen ontbreken`,
      fieldLabels: {
        servings: "Aantal personen",
        oven_c: "Oventemperatuur",
        prep_minutes: "Voorbereidingstijd",
        cook_minutes: "Kooktijd",
        difficulty: "Niveau",
        title: "Titel",
      } as Record<string, string>,
      titleLabel: "Titel",
      ingredients: "Ingrediënten",
      steps: "Stappen",
      estimated: "geschat",
      rewritten:
        "Stappen zijn in eigen woorden herschreven. De bron blijft altijd zichtbaar bij het recept.",
      save: "Opslaan in bibliotheek",
      saving: "Opslaan…",
      qty: "Hoeveelheid",
      unit: "Eenheid",
      name: "Ingrediënt",
    },

    done: {
      tag: "Opgeslagen",
      body: "Je vindt dit recept nu in je bibliotheek.",
      viewRecipe: "Bekijk recept",
      importAnother: "Nog een importeren",
    },

    // One per code in the failure taxonomy — docs/03-import-pipeline.md. A generic message makes
    // the app feel broken; each of these owes the user a different next step.
    errors: {
      unsupported_url: "Deze link kennen we niet. Werkt met TikTok, Instagram, YouTube en blogs.",
      private_or_removed: "Dit bericht bestaat niet meer of is privé.",
      source_blocked: "Deze site staat automatisch importeren niet toe.",
      no_recipe_found: "We konden hier geen recept in vinden.",
      low_confidence: "We konden hier geen volledig recept uit halen.",
      no_transcript: "In deze video wordt niets gezegd dat we konden gebruiken.",
      silent_video: "Hier staat te weinig in om een recept van te maken.",
      scraper_failed: "We konden de bron nu niet ophalen.",
      model_failed: "Het uitlezen ging mis. Probeer het nog eens.",
      quota_exceeded: "Je hebt al je imports van deze maand gebruikt.",
      media_too_large: "Deze bron is te groot om te verwerken.",
      timeout: "Dit duurde te lang. Probeer het nog eens.",
      conflict: "Dit recept staat al in je bibliotheek.",
      unknown: "Er ging iets mis. Probeer het nog eens.",
    } as Record<string, string>,

    // Codes where trying again cannot possibly help, so no retry button is offered.
    noRetry: ["unsupported_url", "source_blocked", "quota_exceeded", "conflict"],

    seeRecipe: "Bekijk het recept",
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
