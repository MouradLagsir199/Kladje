"""Reads a recipe out of a web page — the cheapest and most accurate source we have.

Most recipe sites publish `schema.org/Recipe` in the page because Google rewards it. That data was
written deliberately by the site author, so it beats anything a model could infer from prose, and it
costs nothing to read.

Order of trust, first hit wins: JSON-LD → microdata → WP Recipe Maker → readable page text.

What comes out is *evidence*, not a finished recipe. Synthesis still runs afterwards, because we
still need Dutch, metric units, a category, and method text in our own words. But it runs on a tidy
dict of about a kilobyte instead of half a megabyte of page — which is most of the cost saving.
"""

import json
import re
from typing import Any
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Tag

from receptenapp.db.models import SourcePlatform
from receptenapp.providers.http import PageFetcher
from receptenapp.services.evidence import EvidenceBundle
from receptenapp.services.url_norm import detect_platform, normalise_url, normalise_url_async

# The one input that can be arbitrarily long, so it needs a ceiling. Roughly 6k tokens, which is
# about half a cent on mini-tier — generous enough that a food blog's opening anecdote does not
# push the ingredients out of the window, cheap enough not to care.
MAX_PAGE_TEXT_CHARS = 24_000

_ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$"
)
_WHITESPACE_RE = re.compile(r"[ \t\r\f\v ]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def parse_iso_duration_minutes(value: Any) -> int | None:
    """`PT45M` / `P0DT0H20M` → minutes.

    A zero duration means "the field exists but was never filled in" — several sites emit `PT0H0M`
    by default. Treating that as a real zero would tell the user a dish takes no time to cook, so it
    comes back as None and ends up `missing`.
    """
    if not isinstance(value, str):
        return None
    match = _ISO_DURATION_RE.match(value.strip())
    if not match:
        return None
    parts = {k: int(v) for k, v in match.groupdict(default="0").items()}
    total = parts["days"] * 1440 + parts["hours"] * 60 + parts["minutes"] + parts["seconds"] // 60
    return total or None


def _first_text(value: Any) -> str | None:
    """schema.org lets almost any field be a string, a list, or an object. Flatten to one string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("name", "text", "url", "@value"):
            if key in value:
                return _first_text(value[key])
        return None
    if isinstance(value, list):
        for item in value:
            if text := _first_text(item):
                return text
    return None


def _yield_text(value: Any) -> str | None:
    """`['4', '4 personen']` → the informative one.

    Sites emit both a bare count and a human phrase. The phrase is better evidence for the model,
    so prefer the longest entry rather than the first.
    """
    if isinstance(value, list):
        candidates = [c for c in (_first_text(v) for v in value) if c]
        return max(candidates, key=len) if candidates else None
    return _first_text(value)


def _flatten_instructions(value: Any) -> list[str]:
    """Instruction lists are nested inconsistently; return a flat list of step strings.

    Some sites emit `HowToStep` directly, others wrap them in one or more `HowToSection`
    ("Voor de saus", "Bereiding"). Both are common on the same site.
    """
    steps: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            if text := node.strip():
                steps.append(text)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if "HowToSection" in types or "itemListElement" in node:
                walk(node.get("itemListElement"))
            elif step_text := _first_text(node.get("text") or node.get("name")):
                steps.append(step_text)

    walk(value)
    return steps


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(value, list):
        return [t for t in (_first_text(v) for v in value) if t]
    return []


def _iter_json_ld(soup: BeautifulSoup) -> list[Any]:
    documents: list[Any] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            documents.append(json.loads(raw.strip()))
        except (json.JSONDecodeError, ValueError):
            # A single malformed block must not lose the other blocks on the page.
            continue
    return documents


def _find_recipe_node(documents: list[Any]) -> dict[str, Any] | None:
    """Depth-first search for an object typed `Recipe`.

    Recipe objects are rarely at the top level: `@graph` arrays and `mainEntity` nesting are both
    the norm, and every one of our fixtures uses one or the other.
    """
    stack: list[Any] = list(documents)
    while stack:
        node = stack.pop(0)
        if isinstance(node, dict):
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if "Recipe" in types:
                return node
            stack.extend(v for v in node.values() if isinstance(v, dict | list))
        elif isinstance(node, list):
            stack.extend(node)
    return None


def _normalise_recipe(node: dict[str, Any]) -> dict[str, Any]:
    """Reduce a schema.org Recipe to a small, predictable dict.

    Deliberately lossy. This is what gets sent to the model, so every field dropped here is tokens
    not paid for; aggregateRating, nutrition, video objects and `@id` graph plumbing are noise for
    the task of writing a Dutch recipe.
    """
    normalised: dict[str, Any] = {
        "name": _first_text(node.get("name")),
        "description": _first_text(node.get("description")),
        "author": _first_text(node.get("author")),
        "recipeYield": _yield_text(node.get("recipeYield")),
        "recipeIngredient": _string_list(node.get("recipeIngredient") or node.get("ingredients")),
        "recipeInstructions": _flatten_instructions(node.get("recipeInstructions")),
        "recipeCategory": _first_text(node.get("recipeCategory")),
        "recipeCuisine": _first_text(node.get("recipeCuisine")),
        "keywords": _first_text(node.get("keywords")),
        "prepMinutes": parse_iso_duration_minutes(node.get("prepTime")),
        "cookMinutes": parse_iso_duration_minutes(node.get("cookTime")),
        "totalMinutes": parse_iso_duration_minutes(node.get("totalTime")),
    }
    return {k: v for k, v in normalised.items() if v not in (None, [], "")}


def _from_microdata(soup: BeautifulSoup) -> dict[str, Any] | None:
    # CSS attribute matching rather than find(attrs=...): equivalent here, and correctly typed.
    scope = soup.select_one('[itemtype*="schema.org/Recipe" i]')
    if scope is None:
        return None

    collected: dict[str, Any] = {}
    for prop in scope.select("[itemprop]"):
        name = prop.get("itemprop")
        if not isinstance(name, str):
            continue
        value = prop.get("content") or prop.get("datetime") or prop.get_text(" ", strip=True)
        if not value or not isinstance(value, str):
            continue
        if name in {"recipeIngredient", "ingredients", "recipeInstructions"}:
            collected.setdefault(name, []).append(value)
        else:
            collected.setdefault(name, value)
    return _normalise_recipe(collected) if collected else None


def _from_wprm(soup: BeautifulSoup) -> dict[str, Any] | None:
    """WP Recipe Maker, which dominates Dutch and US food blogs.

    Only reached when a WPRM page somehow lacks JSON-LD — the plugin normally emits both. Kept
    because the class names are stable and it costs almost nothing to support.
    """
    container = soup.find(class_=re.compile(r"\bwprm-recipe-container\b"))
    if not isinstance(container, Tag):
        return None

    def texts(pattern: str) -> list[str]:
        return [
            t.get_text(" ", strip=True)
            for t in container.find_all(class_=re.compile(pattern))
            if t.get_text(strip=True)
        ]

    name_tag = container.find(class_=re.compile(r"\bwprm-recipe-name\b"))
    collected: dict[str, Any] = {
        "name": name_tag.get_text(" ", strip=True) if isinstance(name_tag, Tag) else None,
        "recipeIngredient": texts(r"\bwprm-recipe-ingredient\b"),
        "recipeInstructions": texts(r"\bwprm-recipe-instruction-text\b"),
    }
    return _normalise_recipe(collected) if collected.get("recipeIngredient") else None


def _meta(soup: BeautifulSoup, *names: str) -> str | None:
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if isinstance(tag, Tag):
            content = tag.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return None


def _readable_text(soup: BeautifulSoup) -> str | None:
    """Body text with the furniture stripped. Used whenever a page has no structured data.

    This is the path most personal blogs take, so it matters more than "fallback" suggests. Two
    problems it has to solve, both specific to recipe sites:

    - **Other recipes on the same page.** Sidebars, "related recipes" and comment threads where
      people post their own variations. Feed those to the model and it may confidently return the
      wrong dish. Cheaper to delete them than to ask the model to ignore them
    - **The story before the recipe.** Food blogs open with several hundred words of anecdote, so
      the budget has to be generous enough that the ingredients are not what gets truncated away

    Deliberately makes **no assumption about page structure**. An earlier version preferred
    `<article>`, then `<main>`, then anything with "recipe" in a class name. Every one of those is a
    guess that is wrong on some sites — and the last one happily matches a "related recipes" widget.
    Removing what is definitely noise is reliable; guessing which container holds the recipe is not.
    Finding the recipe inside ordinary text is what the model is good at, so let it.
    """
    for tag in soup.find_all(
        ["script", "style", "noscript", "nav", "header", "footer", "svg", "aside", "form", "iframe"]
    ):
        tag.decompose()
    # Class/id names that reliably mean "not this recipe" across WordPress themes.
    for junk in soup.select(
        '[class*="comment" i], [id*="comment" i], [class*="related" i], [class*="sidebar" i],'
        '[class*="share" i], [class*="newsletter" i], [class*="cookie" i], [class*="advert" i],'
        '[class*="popup" i], [class*="breadcrumb" i]'
    ):
        junk.decompose()

    root = soup.body or soup
    text = root.get_text("\n", strip=True)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text[:MAX_PAGE_TEXT_CHARS] or None


async def fetch_and_extract(url: str, fetcher: PageFetcher) -> EvidenceBundle:
    """URL in, evidence out. The blog half of Stage 1.

    Re-normalises against the URL we *landed* on rather than the one asked for: shorteners and
    marketing redirects mean those differ often, and the destination is the honest cache key.
    """
    normalised = await normalise_url_async(url, fetcher.resolve_redirect)
    page = await fetcher.fetch(normalised)
    final_norm = normalise_url(page.url)
    return extract_from_html(
        page.html,
        url=page.url,
        url_norm=final_norm,
        platform=detect_platform(urlsplit(final_norm).netloc),
    )


def extract_from_html(
    html: str,
    *,
    url: str,
    url_norm: str,
    platform: SourcePlatform = SourcePlatform.web,
) -> EvidenceBundle:
    """Turn a fetched page into an `EvidenceBundle`. Never raises on unusable input."""
    soup = BeautifulSoup(html, "lxml")

    recipe_node = _find_recipe_node(_iter_json_ld(soup))
    structured = _normalise_recipe(recipe_node) if recipe_node else None
    if not structured:
        structured = _from_microdata(soup) or _from_wprm(soup)

    title_tag = soup.find("title")
    title = (
        (structured or {}).get("name")
        or _meta(soup, "og:title", "twitter:title")
        or (title_tag.get_text(strip=True) if isinstance(title_tag, Tag) else None)
    )

    # Only fall back to page text when there is no structured data. Sending both would multiply the
    # prompt for no gain, since structured data is strictly better evidence.
    page_text = None if structured else _readable_text(soup)

    return EvidenceBundle(
        platform=platform,
        url=url,
        url_norm=url_norm,
        author=(structured or {}).get("author") or _meta(soup, "article:author"),
        title=title,
        caption=(structured or {}).get("description")
        or _meta(soup, "og:description", "description"),
        structured=structured,
        transcript=[],
        page_text=page_text,
        thumbnail_url=_meta(soup, "og:image", "twitter:image"),
    )
