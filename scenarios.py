"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # Criterion 3, found path: error is None, selected_item equals
        # search_results[0], received_ids shows both model tools got its id
        # (visible in each try's trace).
        "name": "state, matching query",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 3, stop path: [], an error message, the later fields None,
        # received_ids empty.
        "name": "state, impossible query",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 4: the same item five times, cache off (run_eval does
        # that), each fit card checked against its caption rules.
        "name": "fit card rules, same item",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 4,
    },
    # Criterion 5: the five impossible queries, one per kind. The message is
    # built without the model, so every try of one query is identical; the run
    # log reads one try per query.
    {"name": "message: price", "query": "corduroy pants under $10", "wardrobe": "example", "criterion": 5},
    {"name": "message: size", "query": "band tee size XS", "wardrobe": "example", "criterion": 5},
    {"name": "message: words", "query": "sequin cocktail gown", "wardrobe": "example", "criterion": 5},
    {"name": "message: size in combination", "query": "platform sneakers size 9", "wardrobe": "example", "criterion": 5},
    {"name": "message: price, size and words", "query": "silk ballgown size XXL over $200", "wardrobe": "example", "criterion": 5},
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
