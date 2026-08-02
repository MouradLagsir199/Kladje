"""M4 — reading recipes out of real saved pages.

Fixtures in `tests/fixtures/blog/` are unedited pages from live sites. Assertions are deliberately
tolerant about exact counts and wording: these files get refreshed when a site changes, and a test
that pins the number of ingredients would fail for reasons that are not bugs.
"""

import pathlib

import pytest

from receptenapp.db.models import SourcePlatform
from receptenapp.services.blog_extract import (
    extract_from_html,
    parse_iso_duration_minutes,
)
from receptenapp.services.evidence import EvidenceBundle

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "blog"
ALL_FIXTURES = sorted(p.name for p in FIXTURES.glob("*.html"))


def load(name: str) -> EvidenceBundle:
    html = (FIXTURES / name).read_text("utf-8")
    return extract_from_html(
        html, url=f"https://example.test/{name}", url_norm=f"https://example.test/{name}"
    )


def test_fixture_corpus_is_present() -> None:
    assert len(ALL_FIXTURES) >= 6, ALL_FIXTURES


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_every_fixture_yields_a_usable_structured_recipe(name: str) -> None:
    bundle = load(name)
    assert bundle.has_structured_recipe, f"{name}: no structured recipe found"
    structured = bundle.structured or {}
    assert structured.get("name"), f"{name}: no title"
    assert len(structured.get("recipeIngredient", [])) >= 3, f"{name}: too few ingredients"
    assert len(structured.get("recipeInstructions", [])) >= 2, f"{name}: too few steps"


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_structured_hit_skips_page_text(name: str) -> None:
    # Sending both would multiply the prompt for no gain — structured data is strictly better.
    assert load(name).page_text is None


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_steps_are_flat_strings_not_nested_objects(name: str) -> None:
    steps = (load(name).structured or {}).get("recipeInstructions", [])
    assert all(isinstance(s, str) and s.strip() for s in steps)
    # A leaked HowToSection wrapper would show up as a dict repr in the text.
    assert not any(s.startswith("{") or "HowToStep" in s for s in steps)


def test_howtosection_nesting_is_flattened() -> None:
    # leukerecepten wraps every step inside a single "Bereiding" HowToSection.
    steps = (load("leukerecepten_carbonara.html").structured or {}).get("recipeInstructions", [])
    assert len(steps) >= 4, steps
    assert any("spek" in s.lower() for s in steps)


def test_dutch_characters_survive() -> None:
    bundle = load("24kitchen_shoarma.html")
    joined = " ".join((bundle.structured or {}).get("recipeInstructions", []))
    assert "°C" in joined or "graden" in joined.lower()


def test_english_page_is_extracted_as_is_without_translating() -> None:
    # Translation is synthesis's job; the extractor must not silently alter evidence.
    structured = load("budgetbytes_en_drumsticks.html").structured or {}
    ingredients = " ".join(structured["recipeIngredient"]).lower()
    assert "tsp" in ingredients or "lb" in ingredients


def test_wordpress_recipe_maker_page_extracts() -> None:
    structured = load("ohmyfoodness_courgette_quiche.html").structured or {}
    assert "quiche" in (structured.get("name") or "").lower()
    assert len(structured["recipeIngredient"]) >= 5


def test_metadata_is_populated() -> None:
    bundle = load("24kitchen_courgettesoep.html")
    assert bundle.title
    assert bundle.thumbnail_url and bundle.thumbnail_url.startswith("http")
    assert bundle.platform is SourcePlatform.web


def test_normalised_recipe_drops_noise_fields() -> None:
    # Every field kept is tokens paid for; ratings and nutrition help write nothing.
    structured = load("leukerecepten_gazpacho.html").structured or {}
    for noisy in ("aggregateRating", "nutrition", "@id", "@type", "isPartOf", "mainEntityOfPage"):
        assert noisy not in structured


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("PT45M", 45),
        ("PT1H10M", 70),
        ("P0DT0H20M", 20),
        ("P1DT2H", 1560),
        ("PT90S", 1),
        # Zero durations mean "never filled in", not "takes no time".
        ("PT0H0M", None),
        ("PT0M", None),
        ("", None),
        ("nonsense", None),
        (None, None),
        (45, None),
    ],
)
def test_iso_duration_parsing(value: object, expected: int | None) -> None:
    assert parse_iso_duration_minutes(value) == expected


def test_zero_duration_is_dropped_while_a_real_one_survives() -> None:
    # This page states a genuine 25-minute prep but emits PT0H0M for cook and total. Reporting
    # "0 minuten kooktijd" would be a confident lie; the field must simply be absent.
    structured = load("leukerecepten_carbonara.html").structured or {}
    assert structured["prepMinutes"] == 25
    assert "cookMinutes" not in structured
    assert "totalMinutes" not in structured


def test_page_without_structured_data_falls_back_to_text() -> None:
    html = """
    <html><head><title>Oma's snert</title>
    <meta property="og:image" content="https://example.test/snert.jpg">
    </head><body><nav>menu</nav>
    <article><h1>Snert</h1>
    <p>Week de spliterwten een nacht. Kook ze met prei en selderij.</p></article>
    <footer>copyright</footer></body></html>
    """
    bundle = extract_from_html(
        html, url="https://example.test/s", url_norm="https://example.test/s"
    )
    assert bundle.structured is None
    assert bundle.page_text and "spliterwten" in bundle.page_text
    # Furniture is stripped so the model is not charged for a nav bar.
    assert "menu" not in bundle.page_text
    assert bundle.title == "Oma's snert"
    assert bundle.thumbnail_url == "https://example.test/snert.jpg"


def test_messy_blog_without_structured_data_keeps_recipe_and_drops_other_recipes() -> None:
    """The realistic no-JSON-LD case: a personal blog with the usual clutter around the recipe.

    The danger is not missing the recipe — the model is good at finding one in prose. It is handing
    the model a *second* recipe from the comments or the sidebar and letting it pick the wrong one.
    """
    html = """
    <html><head><title>Snert van oma</title></head><body>
      <nav><a href="/">Home</a><a href="/recepten">Recepten</a></nav>
      <div class="cookie-banner">Wij gebruiken cookies</div>
      <article>
        <h1>Snert van oma</h1>
        <p>Elke winter maakte mijn oma dit. Ze woonde in Friesland en het vroor altijd.</p>
        <h2>Ingredienten</h2>
        <ul><li>500 g spliterwten</li><li>1 winterpeen</li><li>2 preien</li>
            <li>1 rookworst</li><li>200 g speklappen</li></ul>
        <h2>Bereiding</h2>
        <ol><li>Week de spliterwten een nacht in koud water.</li>
            <li>Kook ze in 2 liter water met de speklappen, ongeveer een uur.</li>
            <li>Voeg de winterpeen en prei toe en laat nog 30 minuten koken.</li></ol>
      </article>
      <aside class="related-recipes"><h3>Ook lekker</h3>
        <p>Bruine bonensoep met chorizo en tomaat</p></aside>
      <section id="comments"><h3>Reacties</h3>
        <p>Marieke: ik maak het altijd met 300 g kikkererwten en kurkuma!</p></section>
      <footer>© 2026 Ons Blog</footer>
    </body></html>
    """
    bundle = extract_from_html(html, url="https://x.test/snert", url_norm="https://x.test/snert")
    assert bundle.structured is None
    text = bundle.page_text or ""

    # The actual recipe survives.
    assert "spliterwten" in text
    assert "rookworst" in text
    assert "Week de spliterwten" in text

    # Competing recipes and furniture do not.
    assert "chorizo" not in text, "related-recipes sidebar leaked in"
    assert "kikkererwten" not in text, "a commenter's own recipe leaked in"
    assert "cookies" not in text
    assert "© 2026" not in text


def test_text_fallback_makes_no_assumption_about_page_structure() -> None:
    # No <article>, no <main>, no recognisable class names — just a div soup, which is most of the
    # long tail of blogs. It must still yield the recipe text.
    html = """
    <html><body><div><div><div>
      <span>Bloemkoolsoep</span>
      <div>1 bloemkool, 1 ui, 500 ml bouillon, 100 ml room</div>
      <div>Snijd de bloemkool. Fruit de ui. Kook alles 20 minuten en pureer.</div>
    </div></div></div></body></html>
    """
    bundle = extract_from_html(html, url="https://x.test/b", url_norm="https://x.test/b")
    text = bundle.page_text or ""
    assert "bloemkool" in text.lower()
    assert "pureer" in text
    assert bundle.is_too_thin_to_synthesise() is False


def test_malformed_json_ld_block_does_not_hide_a_valid_one() -> None:
    html = """
    <html><body>
    <script type="application/ld+json">{ this is not json </script>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@graph":[
      {"@type":"WebPage","name":"page"},
      {"@type":"Recipe","name":"Soep","recipeIngredient":["1 prei","2 aardappels","zout"],
       "recipeInstructions":[{"@type":"HowToStep","text":"Snijd de prei."},
                             {"@type":"HowToStep","text":"Kook alles gaar."}]}]}
    </script></body></html>
    """
    bundle = extract_from_html(html, url="https://x.test/a", url_norm="https://x.test/a")
    assert (bundle.structured or {}).get("name") == "Soep"


def test_empty_page_does_not_raise() -> None:
    bundle = extract_from_html("", url="https://x.test/a", url_norm="https://x.test/a")
    assert bundle.structured is None
    assert bundle.is_too_thin_to_synthesise() is True
