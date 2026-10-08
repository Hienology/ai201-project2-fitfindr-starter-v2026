"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re
from collections import Counter

import config
import trace
from tools import suggest_outfit, create_fit_card
from mcp_client import call_tool   # search_listings is reached through MCP (mcp_server.py)
# Matching helpers shared with search_listings, so the parse and the search agree.
from tools import CATEGORY_MAP, FILLER_WORDS, _items, _same, _size_pieces, _words, all_matches
from generate import ModelUnavailable
from utils.data_loader import load_listings


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        "received_ids": {},          # the item id the loop handed to each model tool
    }


# ── parsing the query ─────────────────────────────────────────────────────────
# Regular expressions and word lists built from the data; no model call.

_BETWEEN = re.compile(r"between \$(\d+(?:\.\d+)?) and \$(\d+(?:\.\d+)?)")
_UNDER = re.compile(r"under \$(\d+(?:\.\d+)?)")
_OVER = re.compile(r"over \$(\d+(?:\.\d+)?)")
# "size M", "in size 8", "size US 8", "size S or M", "size S, M"
_SIZE = re.compile(r"(?:in )?sizes? ((?:us )?[\w./]+(?:\s*(?:,|\bor\b)\s*(?:us )?[\w./]+)*)")


def _vocabulary() -> dict:
    """Tag, color and condition values from data/listings.json, split by word count."""
    listings = load_listings()
    tags = {t.lower() for listing in listings for t in listing["style_tags"]}
    colors = {c.lower() for listing in listings for c in listing["colors"]}
    longest_first = lambda values: sorted(values, key=lambda v: -len(_words(v)))
    return {
        "multi_tags": longest_first(v for v in tags if len(_words(v)) > 1),
        "multi_colors": longest_first(v for v in colors if len(_words(v)) > 1),
        "tags": {v for v in tags if len(_words(v)) == 1},
        "colors": {v for v in colors if len(_words(v)) == 1},
        "conditions": {listing["condition"] for listing in listings},
    }


def _without_limits(text: str) -> str:
    """The lowercased query with its price and size phrases removed."""
    for pattern in (_BETWEEN, _UNDER, _OVER, _SIZE):
        text = pattern.sub(" ", text)
    return text


def parse_query(query: str) -> dict:
    """
    Turn the user's text into the 8 inputs of search_listings (README,
    Planning Loop): prices and sizes by regular expression; adjacent words that
    form a multi-word tag or color become one item; single tag, color and
    condition words go to their inputs; every other word, including garment
    words and category names, goes to description. category is never filled.
    """
    text = query.lower()
    parsed = {"description": "", "size": None, "max_price": None, "min_price": None,
              "style_tags": None, "colors": None, "category": None, "condition": None}
    if match := _BETWEEN.search(text):
        parsed["min_price"], parsed["max_price"] = float(match[1]), float(match[2])
    if match := _UNDER.search(text):
        parsed["max_price"] = float(match[1])
    if match := _OVER.search(text):
        parsed["min_price"] = float(match[1])
    if match := _SIZE.search(text):
        parsed["size"] = match[1]

    vocab = _vocabulary()
    words = [w for w in _words(_without_limits(text)) if w not in FILLER_WORDS]
    tags, colors, conditions, description = [], [], [], []
    i = 0
    while i < len(words):
        phrase = next((v for v in vocab["multi_tags"] + vocab["multi_colors"]
                       if len(words[i:i + len(_words(v))]) == len(_words(v))
                       and all(_same(a, b) for a, b in zip(_words(v), words[i:]))), None)
        if phrase:
            n = len(_words(phrase))
            (tags if phrase in vocab["multi_tags"] else colors).append(" ".join(words[i:i + n]))
            i += n
            continue
        word = words[i]
        if any(_same(word, garment) for garment in CATEGORY_MAP):
            description.append(word)            # garment words keep their title points
        elif any(_same(word, t) for t in vocab["tags"]):
            tags.append(word)
        elif any(_same(word, c) for c in vocab["colors"]):
            colors.append(word)
        elif any(_same(word, c) for c in vocab["conditions"]):
            conditions.append(word)
        else:
            description.append(word)
        i += 1

    parsed["description"] = " ".join(description)
    parsed["style_tags"] = ", ".join(tags) or None
    parsed["colors"] = ", ".join(colors) or None
    parsed["condition"] = ", ".join(conditions) or None
    return parsed


# ── the empty-search message ──────────────────────────────────────────────────
# The student's wording: "Your issue is at …. One way it can help is by (action)."

NO_WORDS_MESSAGE = ("Your issue is at the words: there is nothing to search for. One way it can "
                    "help is by saying what you are looking for, such as tops, bottoms, outerwear, "
                    "shoes or accessories.")


def _or_list(values: list[str]) -> str:
    return values[0] if len(values) == 1 else ", ".join(values[:-1]) + " or " + values[-1]


def empty_search_message(query: str, parsed: dict) -> str:
    """
    Name every part of the query that blocked the search (price, size, words),
    quote the user's value, and give a fix from the data (criterion 5).

    Each layer is first checked on its own against all listings. If every
    layer is fine on its own, the combination is the problem, so layers are
    dropped one at a time to find the one that blocks.
    """
    listings = load_listings()
    if not any(parsed[k] for k in ("description", "style_tags", "colors", "category", "condition")):
        return NO_WORDS_MESSAGE

    low, high = parsed["min_price"], parsed["max_price"]
    priced = low is not None or high is not None
    in_range = lambda p: (low is None or p >= low) and (high is None or p <= high)
    sizes = _items(parsed["size"])
    no_price, no_size = {"min_price": None, "max_price": None}, {"size": None}

    blocking = []
    if priced and not any(in_range(x["price"]) for x in listings):
        blocking.append("price")
    if sizes and not any(any(_size_pieces(s) <= _size_pieces(x["size"]) for s in sizes) for x in listings):
        blocking.append("size")
    if not all_matches(**{**parsed, **no_price, **no_size}):
        blocking.append("words")
    if not blocking:
        if priced and all_matches(**{**parsed, **no_price}):
            blocking.append("price")
        elif sizes and all_matches(**{**parsed, **no_size}):
            blocking.append("size")
        else:
            blocking += [part for part, used in (("price", priced), ("size", bool(sizes))) if used]

    parts = []
    if "price" in blocking:
        prices = [x["price"] for x in (all_matches(**{**parsed, **no_price}) or listings)]
        if low is not None and high is not None and low > high:
            parts.append(f"Your issue is at the price: ${low:g} is above ${high:g}. "
                         "One way it can help is by swapping the two prices.")
        elif low is not None and high is not None:
            nearest = min(prices, key=lambda p: min(abs(p - low), abs(p - high)))
            parts.append(f"Your issue is at the price: nothing matches between ${low:g} and ${high:g}. "
                         f"One way it can help is by widening your price range to include ${nearest:g}.")
        elif high is not None:
            parts.append(f"Your issue is at the price: nothing matches under ${high:g}. "
                         f"One way it can help is by raising your price limit to at least ${min(prices):g}.")
        else:
            parts.append(f"Your issue is at the price: nothing matches over ${low:g}. "
                         f"One way it can help is by lowering your price limit to ${max(prices):g} or less.")
    if "size" in blocking:
        rest = all_matches(**{**parsed, **no_size}) or listings
        suggestions = [size for size, _ in Counter(x["size"] for x in rest).most_common(3)]
        parts.append(f"Your issue is at the size: nothing matches in size {_or_list([s.upper() for s in sizes])}. "
                     f"One way it can help is by trying size {_or_list(suggestions)}.")
    if "words" in blocking:
        categories = sorted({x["category"] for x in listings})
        request = " ".join(w for w in re.findall(r"[a-z0-9'-]+", _without_limits(query.lower()))
                           if w not in FILLER_WORDS)
        parts.append(f'Your issue is at the words: nothing matches "{request}". '
                     f"One way it can help is by trying other words, such as {_or_list(categories)}.")
    return " ".join(parts)


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    The branch (README, Planning Loop): if search_listings returns an empty
    list, session["error"] gets a message naming what the user could change and
    the session is returned without calling suggest_outfit or create_fit_card.
    Otherwise the first result becomes session["selected_item"], goes to
    suggest_outfit with the wardrobe, then to create_fit_card with the outfit.
    Every tool reads its input back out of the session, and the loop records
    in session["received_ids"] the item id it hands to each model tool.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    count = 0

    # Steps 2-3: parse, then search through the MCP server.
    count += 1
    trace.check_iterations(count)
    session["parsed"] = parse_query(session["query"])
    session["search_results"] = call_tool("search_listings", session["parsed"])

    # Step 4, the branch: nothing found means stop here, with a message.
    if not session["search_results"]:
        session["error"] = empty_search_message(session["query"], session["parsed"])
        return session

    # Step 5: the best match.
    session["selected_item"] = session["search_results"][0]

    # Step 6: outfit, from the item and wardrobe read back out of the session.
    count += 1
    trace.check_iterations(count)
    session["received_ids"]["suggest_outfit"] = session["selected_item"]["id"]
    session["outfit_suggestion"] = suggest_outfit(session["selected_item"], session["wardrobe"])

    # Step 7: fit card, from the outfit and the same item.
    count += 1
    trace.check_iterations(count)
    session["received_ids"]["create_fit_card"] = session["selected_item"]["id"]
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], session["selected_item"])
    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
