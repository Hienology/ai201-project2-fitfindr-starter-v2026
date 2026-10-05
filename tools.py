"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price, …)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are built to the specs in the README's Tool Inventory.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re
from fractions import Fraction

import config
from generate import ModelUnavailable, generate
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
    return all_matches(description, size, max_price, min_price, style_tags,
                       colors, category, condition)[: config.SEARCH_RESULT_LIMIT]


def all_matches(
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
    Every listing search_listings would accept, in the same order, with no
    limit on how many. search_listings returns the first SEARCH_RESULT_LIMIT of
    these; the empty-search message uses the full list to find fixes.
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
    return [listing for *_, listing in kept]


# ── Helpers shared by the two model tools ─────────────────────────────────────

def _short_title(item: dict) -> str:
    """The title before the dash: "Y2K Baby Tee — Butterfly Print" gives "Y2K Baby Tee"."""
    return item["title"].split(" — ")[0]


def _price(item: dict) -> str:
    """Whole dollars: 38.0 gives "$38" (a plain f-string would print "$38.0")."""
    return f"${item['price']:g}"


def _item_details(item: dict) -> str:
    """The item as prompt lines. Brand appears only when the listing has one."""
    lines = [
        f"Item: {item['title']}",
        f"Category: {item['category']}",
        f"Colors: {', '.join(item['colors'])}",
        f"Style tags: {', '.join(item['style_tags'])}",
        f"Condition: {item['condition']}",
        f"Price: {_price(item)}",
    ]
    if item["brand"] is not None:
        lines.append(f"Brand: {item['brand']}")
    return "\n".join(lines)


def _generate_with_retry(prompt: str, system: str) -> str:
    """
    One retry when the model can't be reached. If the retry also fails, or
    generate() raises anything else (still rate limited, call budget used up),
    the error passes through to the caller.
    """
    try:
        return generate(prompt, system=system)
    except ModelUnavailable:
        return generate(prompt, system=system)


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

OUTFIT_RULES = """You suggest outfits for an item someone found second-hand.
Rules:
1. Suggest one or two outfits. Each outfit is one or two sentences.
2. Every outfit uses the new item plus pieces from the wardrobe list, and only those.
3. Name each wardrobe piece exactly as it is written in the list, word for word.
4. Refer to the new item by its name.
5. Do not mention a brand unless one is given.
6. Write plain text: no headings, no bullet points, no markdown."""

GENERAL_ADVICE_RULES = """You give styling advice for an item someone found second-hand.
The person has no saved wardrobe.
Rules:
1. Write two to four sentences of general advice: the kinds of pieces, colors and occasions that suit the item.
2. Refer to the item by its name.
3. Do not mention a brand unless one is given.
4. Write plain text: no headings, no bullet points, no markdown."""


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Suggest one or two outfits for the found item, built from the user's
    wardrobe. Full spec: README, Tool Inventory.

    With wardrobe items, the model must use the new item plus wardrobe pieces
    named word for word as written (capital letters may differ). With an empty
    wardrobe, it gives two to four sentences of general styling advice instead.

    Args:
        new_item: a listing dict as returned by search_listings.
        wardrobe: {"items": [...]}, each item with id, name, category, colors,
                  style_tags and notes. "items" may be empty.

    Returns:
        A non-empty string of plain text. If the model replies with nothing,
        a fixed fallback: "Style the <title before the dash> with simple
        basics in <first color> or neutral tones." If the model can't be
        reached, one retry, then the error passes through.

    Test it from a terminal:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[1], get_example_wardrobe()))"
    """
    if wardrobe["items"]:
        pieces = "\n".join(
            f"- {piece['name']} ({piece['category']}; {', '.join(piece['colors'])})"
            for piece in wardrobe["items"]
        )
        prompt = f"{_item_details(new_item)}\n\nWardrobe:\n{pieces}"
        text = _generate_with_retry(prompt, OUTFIT_RULES)
    else:
        text = _generate_with_retry(_item_details(new_item), GENERAL_ADVICE_RULES)

    if not text.strip():
        return f"Style the {_short_title(new_item)} with simple basics in {new_item['colors'][0]} or neutral tones."
    return text


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

FIT_CARD_RULES = """You write a short caption someone would post about a second-hand find.
Rules:
1. Write two to four sentences that read like a social media post, not a product description.
2. Mention the item exactly once, using the name given. The item word given below may appear only inside that name: do not use it anywhere else, not even inside a style tag; drop it from any tag that contains it.
3. Write the price exactly once, exactly as given (for example $38).
4. Name the platform exactly once, exactly as given.
5. Describe the vibe specifically, using the outfit and the item's style tags.
6. Do not mention any brand unless one is given.
7. Plain text only: no hashtags, no emoji, no markdown."""


def _brands_in_data() -> list[str]:
    """Every brand name that appears in the listings."""
    return sorted({listing["brand"] for listing in load_listings() if listing["brand"]})


def _names_other_brand(caption: str, item: dict) -> bool:
    """True when the caption names a brand from the data other than the item's own."""
    text = caption.lower().replace("’", "'")
    return any(
        re.search(rf"(?<![a-z]){re.escape(brand.lower())}(?![a-z])", text)
        for brand in _brands_in_data()
        if brand != item["brand"]
    )


def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a caption someone would post about the find. Full spec: README,
    Tool Inventory.

    The model is told to write two to four sentences that read like a post,
    mention the item, its price (as whole dollars, e.g. "$38") and its platform
    exactly once each, describe the vibe from the outfit and the style tags,
    and name no brand unless the listing has one.

    Args:
        outfit:   the outfit text suggest_outfit() returned.
        new_item: the same listing dict that went into suggest_outfit().

    Returns:
        A caption string. If `outfit` is empty or only whitespace, returns
        "Can't write a fit card: there is no outfit suggestion to describe."
        without calling the model. If the model replies with nothing, or its
        caption names a brand from the data other than the item's own, returns
        the fallback "Thrifted the <title before the dash> for $<price> on
        <platform>. Simple basics, easy outfit." If the model can't be reached,
        one retry, then the error passes through.

    Identical captions on repeated runs usually mean the response cache is on
    (config.CACHE_ENABLED); set AI201_CACHE=0 to get fresh answers.

    Test it from a terminal:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('Pair it with baggy straight-leg jeans and chunky white sneakers.', load_listings()[1]))"
    """
    if not outfit.strip():
        return "Can't write a fit card: there is no outfit suggestion to describe."

    fallback = (f"Thrifted the {_short_title(new_item)} for {_price(new_item)} on "
                f"{new_item['platform']}. Simple basics, easy outfit.")
    prompt = (
        f"{_item_details(new_item)}\n"
        f"Platform: {new_item['platform']}\n\n"
        f"Name to use for the item: {_short_title(new_item)}\n"
        f"Item word (only inside the name): {_short_title(new_item).split()[-1].lower()}\n"
        f"Price to write: {_price(new_item)}\n\n"
        f"Outfit:\n{outfit}"
    )
    caption = _generate_with_retry(prompt, FIT_CARD_RULES)
    if not caption.strip() or _names_other_brand(caption, new_item):
        return fallback
    return caption
