"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price, …)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re
from fractions import Fraction

import config
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

# Words that carry no meaning in a request.
FILLER_WORDS = {"a", "an", "the", "for", "in", "with", "and"}

# Garment words people type, mapped to the category values used in the data.
CATEGORY_MAP = {"tee": "tops", "shirt": "tops", "jacket": "outerwear", "sneakers": "shoes"}

TITLE_POINTS = 2      # a description word found in the listing's title
OTHER_POINTS = 1      # a word found in tags, colors, category, condition or description
EXACT_BONUS = 0.5     # a whole multi-word value, or a word equal to a single-word value


def _words(text) -> list[str]:
    """Lowercase words and numbers; punctuation and hyphens split words."""
    return re.findall(r"[a-z0-9]+", str(text).lower())


def _forms(word: str) -> set[str]:
    """The word plus its singular guesses: one trailing "s" (over 3 letters) or "es" (over 4)."""
    forms = {word}
    if word.endswith("s") and len(word) > 3:
        forms.add(word[:-1])
    if word.endswith("es") and len(word) > 4:
        forms.add(word[:-2])
    return forms


def _same(a: str, b: str) -> bool:
    """True when two words match, allowing a plural ending on either side."""
    return bool(_forms(a) & _forms(b))


def _items(value) -> list[str]:
    """None gives [], a list gives its items, a string is split on commas and the word "or"."""
    if value is None:
        return []
    parts = value if isinstance(value, list) else re.split(r",|\bor\b", value, flags=re.IGNORECASE)
    return [str(p).strip() for p in parts if str(p).strip()]


def _size_pieces(size: str) -> set[str]:
    """"US 8.5" gives {"us", "8.5"}; "S/M" gives {"s", "m"}; "XL (oversized)" gives {"xl", "oversized"}."""
    return {piece for piece in re.split(r"[\s/()]+", size.lower()) if piece}


def _has_phrase(phrase: list[str], words: list[str]) -> bool:
    """True when the phrase's words appear next to each other, in order, in `words`."""
    n = len(phrase)
    return any(all(_same(a, b) for a, b in zip(phrase, words[i:i + n]))
               for i in range(len(words) - n + 1))


def _score(listing: dict, terms: list[tuple[list[str], bool]]) -> tuple[float, Fraction]:
    """
    Points for one listing, and how many of the request's terms it covers.

    Each term is (its words, whether they came from `description`). A one-word
    term earns its single best source. A phrase term, when the listing has the
    whole phrase, earns its words' points plus EXACT_BONUS instead.
    """
    values = [v.lower() for v in listing["style_tags"] + listing["colors"]]
    value_words = [w for v in values for w in _words(v)]
    single_values = [v for v in values if len(_words(v)) == 1]
    title = _words(listing["title"])
    text = _words(listing["description"])

    def category_hit(word):
        return _same(word, listing["category"]) or any(
            _same(word, garment) and category == listing["category"]
            for garment, category in CATEGORY_MAP.items()
        )

    def points(word, from_description, exact_bonus=True):
        best = 0
        if any(_same(word, v) for v in value_words) or category_hit(word) or _same(word, listing["condition"]):
            best = OTHER_POINTS
        if from_description:
            if any(_same(word, t) for t in title):
                best = TITLE_POINTS
            elif any(_same(word, d) for d in text):
                best = max(best, OTHER_POINTS)
        if exact_bonus and any(_same(word, v) for v in single_values):
            best += EXACT_BONUS
        return best

    def found(word):
        return (any(_same(word, w) for w in value_words + title + text)
                or category_hit(word) or _same(word, listing["condition"]))

    score, covered = 0.0, Fraction(0)
    for words, from_description in terms:
        if len(words) == 1:
            score += points(words[0], from_description)
            covered += int(found(words[0]))
            continue
        whole = (any(len(_words(v)) == len(words) and _has_phrase(words, _words(v)) for v in values)
                 or _has_phrase(words, title) or _has_phrase(words, text))
        word_points = sum(points(w, from_description) for w in words)
        if whole:
            phrase_points = sum(points(w, from_description, exact_bonus=False) for w in words) + EXACT_BONUS
            score += max(phrase_points, word_points)
            covered += 1
        else:
            score += word_points
            covered += Fraction(sum(found(w) for w in words), len(words))
    return score, covered


def search_listings(
    description: str,
    size: str | list[str] | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    style_tags: str | list[str] | None = None,
    colors: str | list[str] | None = None,
    category: str | list[str] | None = None,
    condition: str | list[str] | None = None,
) -> list[dict]:
    """
    Search the listings for the best matches to a request. Full spec: README,
    Tool Inventory.

    Hard limits first: price between min_price and max_price (both inclusive),
    and size (a listing passes if every piece of one requested size is among
    the pieces of its size, so "8" matches "US 8" but not "US 8.5"). What is
    left is scored word by word (tag, color, category, condition: 1; a
    description word in the title: 2, in the description: 1; +0.5 for an exact
    value), a whole multi-word tag or color earns its words' points + 0.5, and
    a listing is kept only if it scores above 0 and covers more than half of
    the request's terms. Matching ignores case and a plural "s"/"es".

    Args:
        description: the request's remaining words, e.g. "track jacket".
                     Garment words stay here; the category map handles them.
        size:        one or more sizes, e.g. "S or M" or ["US 8"].
        max_price:   highest price in dollars, inclusive.
        min_price:   lowest price in dollars, inclusive.
        style_tags:  the user's style words, e.g. "vintage, graphic tee".
        colors:      the user's color words, e.g. "dark blue".
        category:    category names (tops, bottoms, outerwear, shoes, accessories).
        condition:   excellent, good or fair.
        A string is split on commas and "or"; None means the input is not used.

    Returns:
        At most config.SEARCH_RESULT_LIMIT listing dicts, unchanged from the
        data, highest score first, then cheapest, then earliest in the file.
        **An empty list when nothing passes — never None, never an exception.**
        The planning loop branches on this.

    Test it from a terminal:
        python -c "from tools import search_listings; print([(x['id'], x['title'], x['price']) for x in search_listings('graphic tee', max_price=30)])"
    """
    # The request as terms: (words, came from description?). A multi-word style
    # tag or color, such as "dark blue", is one phrase term.
    terms = [([w], True) for w in _words(description) if w not in FILLER_WORDS]
    for value, phrases_allowed in ((style_tags, True), (colors, True), (category, False), (condition, False)):
        for item in _items(value):
            words = [w for w in _words(item) if w not in FILLER_WORDS]
            if len(words) > 1 and phrases_allowed:
                terms.append((words, False))
            else:
                terms.extend(([w], False) for w in words)
    if not terms:
        return []

    sizes = _items(size)
    kept = []
    for position, listing in enumerate(load_listings()):
        if min_price is not None and listing["price"] < min_price:
            continue
        if max_price is not None and listing["price"] > max_price:
            continue
        if sizes and not any(_size_pieces(s) <= _size_pieces(listing["size"]) for s in sizes):
            continue
        score, covered = _score(listing, terms)
        if score > 0 and covered / len(terms) > Fraction(1, 2):
            kept.append((-score, listing["price"], position, listing))

    kept.sort(key=lambda entry: entry[:3])
    return [listing for *_, listing in kept[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    # TODO: replace this with your implementation
    return ""


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    # TODO: replace this with your implementation
    return ""
