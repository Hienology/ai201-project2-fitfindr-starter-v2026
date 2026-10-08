# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

A user describes the second-hand item they want in plain words, such as
`vintage graphic tee under $30`, and FitFindr searches the listings for the
products that best suit that description, including its price, size, style and
color. It takes the best match and creates a fashion recommendation: one or two
outfits that pair the find with pieces from the user's own wardrobe, or general
styling advice if the wardrobe is empty. It then writes a short caption the user
could post about the find, with its price and platform. If nothing matches, it
stops and tells the user which part of the query blocked the search and how to
change it.


---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters the listings in `data/listings.json` by hard limits, scores what is left by how well it matches the request's words, drops weak partial matches, and returns the best matches first. Every comparison ignores case, and a word matches its plural: before comparing, a trailing "s" (words over 3 letters) or "es" (over 4 letters) may be stripped from either word. Filler words (a, an, the, for, in, with, and) are ignored.
  - **Hard limits:** price between `min_price` and `max_price`, both inclusive. Size: a listing passes if every piece of at least one requested size appears among the pieces of its `size`, where pieces are split on spaces, `/`, `(` and `)`. So `8` and `US 8` match `US 8` but not `US 8.5`, and `M` matches `M`, `S/M` and `M/L`. A limit that is `None` is skipped.
  - **Request words:** every word of `description`, `style_tags`, `colors`, `category` and `condition`. An item in `style_tags` or `colors` with more than one word (e.g. `dark blue`) is a **phrase**.
  - **Points per word** (each word earns only its single best source): 1 if it matches any word of the listing's `style_tags` or `colors`, its `category` (by name, or through the map `tee`/`shirt` → tops, `jacket` → outerwear, `sneakers` → shoes), or its `condition`. A word from `description` can instead earn 2 if it appears in the listing's `title`, or 1 if it appears in the listing's `description`. Add 0.5 when the word is exactly one of the listing's single-word tag or color values.
  - **Phrases:** if the listing has the whole phrase (as one of its tag or color values, or as adjacent words in its title or description), the phrase earns its words' points plus 0.5, replacing its words' separate points (whichever is higher).
  - **Cutoff:** each phrase counts as one term (1 if the listing has the whole phrase, otherwise the share of its words found anywhere in the listing); every other word counts as one term (found anywhere in the listing's tags, colors, title, description, category or condition, or not). A listing is kept only if it scores above 0 and covers more than half of the terms.
  - **Order:** highest score first; ties go to the cheaper listing, then to the one earlier in `data/listings.json`. At most `config.SEARCH_RESULT_LIMIT` (10) are returned.
- **Inputs:** the first three keep the starter's order, so `search_listings('graphic tee', max_price=30)` still works.
  - `description` (`str`): the request's remaining words, e.g. `"track jacket"`; may be `""`. Garment words such as `jacket` stay here; the tool maps them to a category itself.
  - `size` (`str | list[str] | None`): one or more sizes, e.g. `"S or M"` or `["US 8"]`.
  - `max_price` (`float | None`): highest price in dollars, inclusive.
  - `min_price` (`float | None`): lowest price in dollars, inclusive.
  - `style_tags` (`str | list[str] | None`): the user's style words, e.g. `"vintage, graphic tee"`.
  - `colors` (`str | list[str] | None`): the user's color words, e.g. `"dark blue"`.
  - `category` (`str | list[str] | None`): category names: `tops`, `bottoms`, `outerwear`, `shoes`, `accessories`.
  - `condition` (`str | list[str] | None`): `excellent`, `good` or `fair`.
  - A string is split into a list on commas and on the word "or". `None` means that input is not used.
- **Returns:** a `list[dict]` of at most 10 listings, best match first. Each dict is the listing unchanged from the data, with all 11 fields: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition` (str), `price` (float), `colors` (list[str]), `brand` (str or None), `platform` (str).
- **When it has nothing:** returns an empty list `[]`, never `None` and never an exception, when no listing passes the hard limits and the cutoff. That includes a request where none of the words match anything, and a request with no words at all. The planning loop branches on this empty list.

### `suggest_outfit`

- **What it does:** Asks the model, through `generate()` with fixed rules passed as `system=`, for one or two outfits built around the found item. The prompt gives the item's title, category, colors, style tags, condition and price, and its brand only when it is not `None`. If the wardrobe has items, the prompt lists each item's name, category and colors, and the rules require every outfit to use the new item plus pieces from the wardrobe, named word for word as written there; capital letters may differ (e.g. `Chunky white sneakers` may appear as "chunky white sneakers"). If the wardrobe is empty, the rules ask instead for general styling advice for the item: the kinds of pieces, colors and occasions that suit it. In both cases the rules also tell the model to refer to the item by its name, to mention no brand unless one is given, and to write plain text with no headings, bullet points or markdown.
- **Inputs:**
  - `new_item` (`dict`): one listing dict as returned by `search_listings`, with the 11 fields listed above.
  - `wardrobe` (`dict`): `{"items": [...]}`, where each item is a dict with `id` (str), `name` (str), `category` (str), `colors` (list[str]), `style_tags` (list[str]) and `notes` (str). `items` may be an empty list.
- **Returns:** a non-empty `str` of plain text: one or two outfits, each one or two sentences long, each naming the new item and the wardrobe pieces it uses. With an empty wardrobe, a short paragraph (two to four sentences) of general styling advice.
- **When it has nothing:** an empty wardrobe is not an error; it returns the general styling advice above. If the model replies with an empty string, it returns a fixed fallback instead of `""`: `Style the <title before the dash> with simple basics in <its first color> or neutral tones.` If `generate()` raises `ModelUnavailable` (the model could not be reached), the tool calls it once more with the same prompt; if that also fails, or if `generate()` raises any other error (still rate limited after its own five attempts, or the session's call budget used up), the error passes through to the caller.

### `create_fit_card`

- **What it does:** Asks the model, through `generate()` with fixed rules passed as `system=`, for a caption someone would post about the find. The rules require it to read like a social post rather than a product description; to mention the item, its price (written as whole dollars, e.g. `$38`) and its platform exactly once each; to describe the vibe specifically, using the outfit and the item's style tags; to use the last word of the item's name (e.g. `tee`) only inside that name, dropping it from any style tag that contains it; to write plain text with no hashtags, emoji or markdown; and never to mention a brand when the listing's `brand` is `None`.
- **Inputs:**
  - `outfit` (`str`): the text `suggest_outfit` returned.
  - `new_item` (`dict`): the same listing dict that went into `suggest_outfit`.
- **Returns:** a `str` caption of two to four sentences, in plain text.
- **When it has nothing:** if `outfit` is empty or only whitespace, it does not call the model and returns `Can't write a fit card: there is no outfit suggestion to describe.` If the model replies with an empty string, it returns a fixed two-sentence fallback caption: `Thrifted the <title before the dash> for $<price> on <platform>. Simple basics, easy outfit.` Before returning a model caption, it checks it against every brand name that appears in `data/listings.json`; if the caption names any brand other than the listing's own, it returns the fallback caption instead. Model errors are handled as in `suggest_outfit`: one retry on `ModelUnavailable`, then any error passes through to the caller.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that tells the user what they could change, and return the session without calling `suggest_outfit` or `create_fit_card`, so `outfit_suggestion` and `fit_card` stay `None`. Otherwise, take the first result (the best-scoring listing), store it in `session["selected_item"]`, call `suggest_outfit` with it and the wardrobe, then call `create_fit_card` with that outfit and the same item.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** with regular expressions and word lists built from `data/listings.json`; no model call. The query is lowercased and matched with the same plural rule as `search_listings`.

- `under $X` sets `max_price`, `over $X` sets `min_price`, and `between $X and $Y` sets both.
- `size X` or `in size X` sets `size`, keeping several sizes as written (e.g. `S or M`).
- Filler words (a, an, the, for, in, with, and) are dropped.
- Adjacent words that together form a multi-word tag or color value from the data (e.g. `graphic tee`, `dark blue`) become one item in `style_tags` or `colors`.
- A single word that equals a single-word tag, color or condition value goes to `style_tags`, `colors` or `condition`.
- Every other word goes to `description`, including garment words (`jacket`, `tee`) and category names (`top`, `outerwear`), so they can still earn title points. The parse never fills `category`; `search_listings` gives these words their category point itself.

**What moves through the session:** in this order, each tool reading its input back out of the session:

1. `query`: the user's text, set by `new_session`, which also starts `received_ids` as `{}`.
2. `parsed`: the 8 inputs above, as a dict.
3. `search_results`: everything `search_listings` returned, called through the MCP server as `call_tool("search_listings", session["parsed"])` (`mcp_server.py`, via `mcp_client.py`). The empty-search message's own checks call `tools.all_matches` directly.
4. The branch: if `session["search_results"]` is empty, `error` is set and the session is returned.
5. `selected_item`: `session["search_results"][0]`.
6. `outfit_suggestion`: `suggest_outfit(session["selected_item"], session["wardrobe"])`; the loop records the `id` it passed in `session["received_ids"]["suggest_outfit"]`.
7. `fit_card`: `create_fit_card(session["outfit_suggestion"], session["selected_item"])`; the loop records the `id` it passed in `session["received_ids"]["create_fit_card"]`.

Steps 1 to 5 are deterministic (no randomness and no model call), so they produce the same session values on every try of the same query; only steps 6 and 7 call the model, so only they can differ between tries.

`trace.check_iterations(count)` is called on each pass, as the stop condition.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   For a casual look, pair the Y2K Baby Tee — Butterfly Print with the baggy straight-leg jeans, dark wash and the chunky white sneakers. Add the black crossbody bag to complete the outfit.

For a slightly edgy vibe, wear the Y2K Baby Tee — Butterfly Print under the oversized grey crewneck sweatshirt with the wide-leg khaki trousers and the black combat boots.

  Fit card: Scored this cute Y2K Baby Tee on depop for only $18. Styled it for a casual look with baggy straight-leg jeans, dark wash and chunky white sneakers, finishing the outfit with a black crossbody bag. Such a nostalgic y2k vintage piece to add to the rotation.

0 model calls this session, 2 served from cache
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print([(x['id'], x['title'], x['price']) for x in search_listings('graphic tee', max_price=30)])"
[('lst_006', 'Graphic Tee — 2003 Tour Bootleg Style', 24.0), ('lst_015', 'Vintage Graphic Hoodie — Faded Black', 26.0), ('lst_002', 'Y2K Baby Tee — Butterfly Print', 18.0), ('lst_033', 'Vintage Band Tee — Faded Grey', 19.0), ('lst_017', 'Mesh Long-Sleeve Top — Black', 15.0), ('lst_012', 'Oversized Crewneck Sweatshirt — Vintage Navy', 20.0)]

$ python -c "from tools import search_listings; r = search_listings('designer ballgown', size='XXS', max_price=5); print(type(r).__name__, r)"
list []
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[1], get_example_wardrobe()))"
For a casual look, pair the Y2K Baby Tee — Butterfly Print with the baggy straight-leg jeans, dark wash and the chunky white sneakers. Add the black crossbody bag to complete the outfit.

For a slightly edgy vibe, wear the Y2K Baby Tee — Butterfly Print under the oversized grey crewneck sweatshirt with the wide-leg khaki trousers and the black combat boots.
```

```
$ AI201_CACHE=0 python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('Pair it with baggy straight-leg jeans, dark wash and chunky white sneakers.', load_listings()[1]))"
Scored this gorgeous Y2K Baby Tee on depop for only $18. The white, pink, and purple butterfly print gives off such a nostalgic vibe when paired with baggy dark wash straight-leg jeans and chunky white sneakers. I am obsessed with how it blends that early 2000s energy with a touch of vintage charm.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* Claude to turn my `search_listings` decisions into the
  four Tool Inventory lines.
- *What came back:* a draft, plus a check that implemented it word for word. The
  first wording let style words like "vintage" and "leather" earn title points,
  which broke 4 test queries (`brown leather bag` returned a leather belt).
- *What I changed:* title points are limited to words from `description`; then I
  reviewed the lines.

**Moment 2**

- *What I asked for:* to test my first `search_listings` design (filters on
  style tags, colors, category, condition and price) on the starter's six
  example queries before building it.
- *What came back:* `silk slip dress in midi length under $40` returned 33
  listings with Levi's jeans first, and `platform sneakers size 8` put US 7 Mary
  Janes first, because garment words like "dress" matched no field and my design
  had no size filter.
- *What I changed:* I kept the starter's three inputs and added my fields as
  extra ones, turned the size filter on, and matched leftover words against
  listing titles. The slip dress and the US 8 sneakers then came first.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->
`search_listings` is registered in `mcp_server.py` with the same 8 typed inputs
as the Tool Inventory, and `run_agent` now calls it with
`call_tool("search_listings", session["parsed"])` instead of calling the
function directly; `suggest_outfit` and `create_fit_card` are still direct
calls. Nothing behaved differently: on 25 queries the MCP results were identical
to the direct call (same listings, same order, still a list, `price` still a
float, `brand` still `None` where empty), and an empty search still comes back
as `[]`, so the branch works unchanged. The empty-search message's own checks
still call `tools.all_matches` directly, not through MCP.



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
