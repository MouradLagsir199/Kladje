# Receptenapp — Schermspecificatie

Nederlandse markt. Import van recepten uit TikTok / Reels / YouTube / Pinterest / foodblogs, met weekplanning, boodschappenlijst gekoppeld aan supermarktdata, en delen in groepen.

---

## Navigatiestructuur

Tab bar met 5 posities: 4 tabs + 1 centrale actieknop.

```
┌──────────┬──────────┬────────┬──────────┬──────────┐
│  Ontdek  │ Recepten │  (+)   │ Planner  │ Profiel  │
└──────────┴──────────┴────────┴──────────┴──────────┘
```

| Positie | Naam | Icoon | Functie |
|---|---|---|---|
| 1 | Ontdek | kompas | Inspiratie: publiek + groepen |
| 2 | Recepten | boek | Eigen bibliotheek |
| 3 | (+) | plus, gevuld/accentkleur | Import — opent modal over alles heen, geen tab |
| 4 | Planner | kalender | Weekplanning + boodschappenlijst |
| 5 | Profiel | persoon | Groepen, voorkeuren, abonnement |

**Globale schermen** (bereikbaar vanuit meerdere tabs, geen eigen tab): Receptdetail, Kookmodus, Deel-sheet, Zoeken.

---

# TAB 1 — ONTDEK

Doel: inspiratie opdoen en recepten van anderen binnenhalen. Dit is het openingsscherm.

## 1.1 Feed (hoofdscherm)

**Bovenaan**
- Zoekbalk (sticky) — placeholder: "Zoek recept of ingrediënt"
- Rij filterchips, horizontaal scrollbaar: `Alles` `Ontbijt` `Lunch` `Diner` `Tussendoor`
- Daaronder segmented control met 4 subtabs

**Subtabs**

| Subtab | Inhoud |
|---|---|
| Voor jou | Aanbevelingen op basis van dieet, eerdere imports, kooktijd |
| Populair | Meest geïmporteerd/opgeslagen deze week |
| Seizoen | Asperges in april, boerenkool in november, pompoen in oktober — sterk lokaal signaal |
| Groepen | Alleen recepten gedeeld binnen jouw groepen |

**Contentblokken in de feed**
1. Hero-carrousel bovenaan — 3 tot 5 uitgelichte recepten, groot beeld
2. Horizontale rij: "Onder 30 minuten"
3. Horizontale rij: "Nieuw van je groepen" — met avatar van wie het deelde
4. Verticaal raster (2 koloms) — oneindig scrollend

**Receptkaart (het meest hergebruikte component)**
- Foto 4:5, afgeronde hoeken
- Titel, max 2 regels
- Metabalk: ⏱ tijd · 👥 porties · moeilijkheidsdot
- Bronbadge linksboven (TikTok / YouTube / blognaam)
- Hartje rechtsboven → opslaan in bibliotheek
- Optioneel: avatar van groepslid dat het deelde

**States**
- Leeg (nieuwe gebruiker): grote illustratie + "Importeer je eerste recept" → opent (+)
- Laden: skeleton cards, geen spinner
- Offline: banner bovenaan, toon gecachte feed

## 1.2 Categorie-overzicht
Bereikt via een filterchip of "Toon alles". Zelfde raster, titel in de header, filterknop rechtsboven.

## 1.3 Zoeken & filteren
Full-screen overlay.
- Recente zoekopdrachten, suggesties
- Twee zoekmodi: op naam, of **op ingrediënt** ("wat kan ik met prei")
- Filter-sheet: maaltijdtype, max kooktijd (slider), dieet, allergieën uitsluiten, bron, moeilijkheid

---

# TAB 2 — RECEPTEN

Doel: alles wat de gebruiker zelf heeft opgeslagen. Moet volledig offline werken — mensen koken in keukens met slechte wifi.

## 2.1 Bibliotheek (hoofdscherm)

**Subtabs**: `Alles` · `Collecties` · `Onlangs`

- Filterchips: Ontbijt / Lunch / Diner / Tussendoor
- Sorteren: recent toegevoegd, alfabetisch, kooktijd, vaakst gekookt
- Weergaveschakelaar: raster ↔ compacte lijst
- Selectiemodus (lang indrukken): meerdere recepten tegelijk → naar planner, naar collectie, verwijderen

**Leeg**: "Nog geen recepten. Plak een link uit TikTok of Instagram." + knop naar import.

## 2.2 Collecties
Eigen mappen: "Snelle doordeweekse", "Feestdagen", "Vega". Raster van collectiekaarten met stapelvoorbeeld van 3 foto's. Plusknop maakt nieuwe collectie.

## 2.3 Receptdetail — GLOBAAL SCHERM

Het scherm waar mensen de meeste tijd doorbrengen. Scrollend, met sticky actiebalk onderaan.

**Header**
- Foto of videothumbnail, full bleed
- Bij video-import: afspeelknop → originele video in overlay
- Terug, delen, overflow (bewerken, dupliceren, verwijderen)

**Titelblok**
- Titel
- Bronregel: `Van @creator op TikTok` + link naar origineel — altijd tonen
- Metarij: tijd · porties · moeilijkheid · kcal (indien bekend)
- Allergie-waarschuwing als het recept botst met het profiel: rode banner

**Portieschuif**
- Stepper of slider, herberekent alle hoeveelheden live
- Rond netjes af: `1,33 ei` → `1–2 eieren`, niet `1,33`

**Ingrediënten**
- Afvinkbare lijst, blijft bewaard tijdens koken
- Per regel de omgerekende Nederlandse eenheid groot, originele eenheid klein eronder: **250 g bloem** · *(2 cups)*
- Knop: "Alles naar boodschappenlijst"

**Bereiding**
- Genummerde stappen
- Herkende tijden zijn tikbare timers: "laat 20 min sudderen" → ⏱ 20:00
- Herkende temperaturen tonen heteluchtvariant: `200 °C (180 °C hetelucht)`

**Notities**
- Vrij tekstveld: "volgende keer minder zout". Dit is waarom mensen terugkomen naar jouw app in plaats van naar TikTok.

**Kooklog**
- "Gekookt op 12 maart" + optionele foto. Telt mee in "vaakst gekookt".

**Sticky actiebalk onderaan**
`Start koken` (primair) · `Plan in` · `Boodschappen` · `Deel`

## 2.4 Kookmodus — GLOBAAL SCHERM

Volledig scherm, scherm blijft aan, donkere achtergrond.
- Eén stap per scherm, horizontaal swipen
- Extra grote typografie — leesbaar vanaf 60 cm afstand met vieze handen
- Ingrediënten voor déze stap bovenaan herhaald
- Actieve timers zwevend in beeld, blijven lopen bij doorswipen
- Voortgangsbalk, stapteller
- Afsluiten → "Gekookt!" markeren + foto toevoegen + delen met groep

## 2.5 Recept bewerken
Formulier met dezelfde velden als het reviewscherm. Handmatig recept toevoegen loopt via ditzelfde scherm, leeg gestart.

---

# CENTRAAL (+) — IMPORT

Geen tab maar een modal-flow over de hele app heen. Dit is het hart van het product.

**Belangrijk buiten de app**: bouw een iOS Share Extension en Android Intent Filter. Niemand kopieert een link en wisselt van app — ze drukken op delen in TikTok en kiezen jouw app. De flow hieronder start dan direct bij stap 2.

## Stap 1 — Bron kiezen
- Groot plakveld; leest automatisch het klembord: "We zagen een TikTok-link — importeren?"
- Bronlogo's als hint: TikTok, Instagram, YouTube, Pinterest, website
- Alternatieven: `Foto van kookboek` (OCR) · `Handmatig invoeren`
- Bij gratis account: teller "3 van je 10 imports deze maand"

## Stap 2 — Verwerken
Toon echte stappen, geen spinner. Dit duurt 10–30 seconden en voelt zonder feedback eindeloos.

```
✓ Video ophalen
✓ Beschrijving lezen
◐ Audio uitlezen
○ Tekst in beeld herkennen
○ Recept samenstellen
```

Videothumbnail als achtergrond. Annuleerknop. Bij falen: nette foutstaat met "Handmatig invoeren" als uitweg.

**Technisch per bron** (voor context bij het ontwerp — verschillende bronnen leveren verschillende kwaliteit op):

| Bron | Aanpak | Kwaliteit |
|---|---|---|
| Blog / Pinterest | `schema.org/Recipe` JSON-LD uitlezen | Hoog — vaak compleet |
| YouTube | Ondertitels + beschrijving | Hoog |
| TikTok / Reels | Spraakherkenning **plus OCR op videoframes** | Wisselend — veel korte recepten worden nooit uitgesproken, alleen in beeld getoond |

## Stap 3 — Review (het belangrijkste scherm van de app)

Hier win of verlies je vertrouwen. Maak dit het rijkste scherm.

**Bovenaan: ontbrekende velden**
Gele kaart met opsomming: "Oventemperatuur ontbreekt · Aantal personen onbekend". Knop **Laat AI aanvullen**. Aangevulde waarden krijgen daarna zichtbaar het label *geschat* — nooit stilzwijgend een getal invullen.

**Herkomst-indicator per veld**
- 🟢 groen — letterlijk gezegd of in beeld getoond
- 🟡 geel — afgeleid, geconverteerd of door AI aangevuld
- 🔴 rood — ontbreekt

**Terug naar de bron**
Tik op een ingrediënt → springt naar het moment in de video waar het genoemd wordt. Dit is de functie die mensen je app laat vertrouwen. Bij blogs: highlight in de brontekst.

**Bewerkbare velden**
Titel · foto (kies frame uit video) · maaltijdtype · porties · bereidingstijd · ingrediënten (sleepbaar, hoeveelheid + eenheid + naam apart) · stappen · notities

**Conversies inline en omkeerbaar**
Toon altijd beide: **250 g** met klein daaronder *(2 cups)*. Gebruikers moeten kunnen controleren.

De conversielogica is meer werk dan hij lijkt:
- Cups → gram is **ingrediëntafhankelijk**: bloem ≈ 125 g, suiker ≈ 200 g, boter ≈ 225 g, rijst ≈ 185 g per cup. Je hebt een dichtheidstabel nodig, geen formule.
- US cup = 237 ml, metrische cup = 250 ml. Australische eetlepel = 20 ml in plaats van 15 ml.
- `1 stick butter` = 113 g · `1 lb` = 454 g · `1 oz` = 28 g
- °F → °C, en gas mark voor Britse recepten
- Heteluchtvariant tonen bij oventemperatuur
- Normaliseer naar Nederlandse maatvoering: el, tl, snufje, teentje, bosje, blikje, pakje

**Auteursrecht**
Een ingrediëntenlijst is in Nederland niet auteursrechtelijk beschermd, maar de beschrijvende bereidingstekst van een blogger wél. Laat het model de stappen dus altijd herschrijven in eigen woorden, en toon standaard de bron met makersnaam en doorklik. Juridisch veiliger én het is wat creators willen.

**Onderaan**: `Opslaan` (primair) · `Opslaan en inplannen`

## Stap 4 — Bevestiging
Compacte kaart met vervolgacties: `Bekijk recept` · `Plan in` · `Deel met groep`. Bij een dubbele import: "Je hebt dit recept al" + verschilweergave.

---

# TAB 3 — PLANNER

## 3.1 Weekplanner

**Subtabs**: `Week` · `Boodschappen`

**Weekgrid**
- 7 dagen, 4 slots per dag (ontbijt / lunch / diner / tussendoor)
- Mobiel: verticaal per dag, dag-koppen sticky. Tablet: echt grid.
- Leeg slot = gestippelde plusknop → sheet met bibliotheek + zoeken + suggesties
- Gevuld slot = mini-kaart met thumbnail, titel, tijd
- Slepen tussen slots
- Weeknavigatie met pijlen; "Vandaag" springt terug

**Functies die het echt bruikbaar maken**
- **Kopieer vorige week** — de meeste huishoudens roteren dezelfde 15 gerechten. Dit wordt je meestgebruikte knop.
- Meerdere recepten in één slot (hoofdgerecht + bijgerecht)
- Aantal eters per dag instelbaar — donderdag eten er twee mee, hoeveelheden schalen mee
- Restjes-markering: kook zaterdag dubbel, plan het als maandaglunch
- Grote knop onderaan: **Maak boodschappenlijst voor deze week**

**Notificaties**
- 's Ochtends: "Vanavond: [gerecht]. Haal nog kip."
- Avond ervoor: ontdooiherinnering bij bevroren ingrediënten

## 3.2 Dagdetail
Tik op een dag → alle maaltijden van die dag, totale kooktijd, aantal eters, knop naar kookmodus.

## 3.3 Boodschappenlijst

Hier gebruik je je supermarktdatabase — dat is je grootste voordeel op de concurrentie.

**Bovenaan**
- Supermarktkiezer (4 grote ketens), onthoudt de voorkeur uit het profiel
- Totaalprijs, en een vergelijkingsknop: "€ 4,20 goedkoper bij [andere keten]"

**De lijst**
- Gegroepeerd **per schap**: groente & fruit, zuivel, vlees, diepvries, houdbaar. Scheelt echt tijd in de winkel.
- Per regel: productfoto, productnaam, hoeveelheid, prijs, checkbox
- Klein onder de productnaam: uit welk recept het komt
- Aanbiedingsbadge als je die data hebt — dit is een enorme trekker in NL
- Automatisch samenvoegen over recepten heen: drie recepten met ui → één regel
- Handmatig item toevoegen (wc-papier hoort er ook in)

**Productkoppeling**
Matching van vrije tekst naar product is het lastige stuk: `2 el olijfolie` moet `AH Olijfolie extra vierge 500 ml` worden.
- Normaliseer eerst het ingrediënt: verwijder bereidingswoorden als "fijngesneden", "vers", "grof gehakt"
- Fuzzy match tegen productnamen
- Leer van correcties per gebruiker
- Toon altijd een alternatievenlijst in een sheet, want de eerste gok is soms mis
- Verpakkingslogica: recept vraagt 200 g, kleinste verpakking is 250 g → toon dat, en "je houdt 50 g over"

**Voorraadkast**
Aparte lijst met basisproducten die je altijd hebt. Zout, olie, bloem en peper verschijnen dan niet elke week op de lijst. Instelbaar per product.

**Delen**
Lijst delen met huisgenoot, realtime afvinken, met wie wat afvinkte.

---

# TAB 4 — PROFIEL

## 4.1 Profieloverzicht
- Avatar, naam
- Statistiekenrij: recepten · deze maand gekookt · groepen
- Snelkoppelingen naar de subsecties
- Abonnementskaart als de gebruiker gratis is

## 4.2 Groepen

**Groepenlijst**
Kaarten met naam, aantal leden, avatarstapel, aantal gedeelde recepten. Plusknop → nieuwe groep.

**Groep aanmaken**
Naam, omschrijving, kleur/emoji, leden uitnodigen.

**Groepdetail**
- Subtabs: `Recepten` · `Leden` · `Planner`
- Recepten: raster van gedeelde recepten met "gedeeld door [naam]"
- Reacties en "gekookt!"-markering met foto
- Leden: lijst met rol (eigenaar / lid — meer rollen heb je niet nodig om te beginnen)
- **Gedeelde weekplanner**: optioneel per groep. Voor huisgenoten en gezinnen is dit een sterkere reden om samen in de app te zitten dan alleen recepten delen.

**Uitnodigen**
Deelbare link + QR-code. Geen accountvereiste om de preview te zien.

## 4.3 Instellingen

| Groep | Instellingen |
|---|---|
| Voorkeuren | Standaard aantal porties · voorkeurssupermarkt · eenhedenweergave (metrisch / origineel erbij) · hetelucht standaard aan |
| Dieet | Vega, veganistisch, halal, glutenvrij · allergieën → geven waarschuwingen op receptdetail |
| Notificaties | Kookherinnering, ontdooiherinnering, groepsactiviteit |
| Account | E-mail, wachtwoord, verwijderen |
| Abonnement | Gratis vs premium, importtellers |
| Privacy | Welke data naar transcriptie- en modelproviders gaat |
| Over | Voorwaarden, privacyverklaring, feedback |

---

# Onboarding (buiten de tabs)

Drie schermen, niet meer. Vraag alleen wat je meteen gebruikt:

1. Huishoudgrootte → bepaalt standaard portiegrootte
2. Dieetvoorkeuren en allergieën
3. Voorkeurssupermarkt → bepaalt productsuggesties, dus geen "nice to have"

Sluit af met een **live demo-import**: laat de gebruiker een TikTok-link plakken en het zien werken. Dat is je aha-moment, niet een tour.

---

# Componentenbibliotheek

Voor consistentie in het ontwerp — deze componenten komen overal terug:

- **Receptkaart** in 3 varianten: groot (hero), raster (2 koloms), compact (lijstregel)
- **Metabalk**: tijd, porties, moeilijkheid — altijd dezelfde volgorde en iconen
- **Bronbadge**: platformlogo + creatornaam
- **Herkomst-indicator**: 3 kleuren, gebruikt in review én receptdetail
- **Ingrediëntregel**: hoeveelheid + eenheid + naam + optionele originele eenheid + checkbox
- **Stapkaart**: nummer, tekst, ingebedde timer
- **Slotkaart** voor de planner: leeg en gevuld
- **Boodschapsregel**: productfoto, naam, prijs, hoeveelheid, checkbox
- **Lege staat**: illustratie + tekst + primaire actie — voor elk hoofdscherm apart

**Toon**: warm en informeel Nederlands, geen "u". Eten is gezellig, niet klinisch.

---

# Drie dingen om nu al te beslissen

**Kosten per import.** Spraakherkenning plus OCR plus een modelaanroep kost een paar cent per video. Bij een gratis tier loopt dat snel op. Overweeg een limiet van bijvoorbeeld 10 imports per maand gratis, en cache agressief op genormaliseerde URL — als drie gebruikers dezelfde virale video importeren, betaal je één keer.

**AVG.** Je stuurt gebruikersdata naar transcriptie- en modelproviders. Leg vast welke, zorg voor verwerkersovereenkomsten, kies waar mogelijk EU-regio's, en zet het in je privacyverklaring.

**Betalingen.** iDEAL via Mollie of Adyen voor web, maar in-app aankopen moeten via App Store en Play Store. Reken op 15–30% commissie.

**Scope-keuze voor Ontdek**: is het een globale feed van alle gebruikers, of alleen van je groepen? Globaal betekent moderatie, spam en rechtenvragen over andermans content. Start met groep-gebaseerd plus een handmatig geredigeerde uitgelicht-rij.
