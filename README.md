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

- **What it does:** Asks the model, through `generate()` with fixed rules passed as `system=`, for a caption someone would post about the find. The rules require it to read like a social post rather than a product description; to mention the item, its price (written as whole dollars, e.g. `$38`) and its platform exactly once each; to describe the vibe specifically, using the outfit and the item's style tags; to use the last word of the item's name (e.g. `tee`) only inside that name, dropping it from any style tag that contains it; to write plain text with no hashtags, emoji or markdown; never to mention a brand when the listing's `brand` is `None`; and, when it has a brand, to put the brand only right before the item's name, never in place of it.
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

If step 6 or 7 can't reach the model (`ModelUnavailable`, after the tool's one retry), `run_agent` puts a message in `session["error"]` in the same pattern as the empty-search message, naming the item it found, the step that failed, the specific cause and what to do (e.g. "…couldn't reach the model to suggest an outfit, because it rejected your API key. One way it can help is by checking GEMINI_API_KEY in your .env file…"), and returns the session; the later fields stay `None`.

`trace.check_iterations(count)` is called on each pass, as the stop condition.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query** (since unit 4, every run also prints its trace)

```
$ python app.py ask 'vintage graphic tee under $30'
[1] parse_query
      in:  vintage graphic tee under $30
      out: max_price=30.0, style_tags='vintage, graphic tee'
[2] search_listings (via MCP)
      in:  max_price=30.0, style_tags='vintage, graphic tee'
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
      →    branch: found, selected_item = lst_002 Y2K Baby Tee — Butterfly Print
[3] suggest_outfit
      in:  lst_002 Y2K Baby Tee — Butterfly Print + wardrobe of 10 items
      out: For a casual look, pair the Y2K Baby Tee — Butterfly Print with the baggy straight-leg jeans, dark wash and th…
      →    received_ids: {'suggest_outfit': 'lst_002'}
[4] create_fit_card
      in:  outfit + lst_002 Y2K Baby Tee — Butterfly Print
      out: Scored this cute Y2K Baby Tee on depop for only $18. Styled it for a casual look with baggy straight-leg jeans…
      →    received_ids: {'suggest_outfit': 'lst_002', 'create_fit_card': 'lst_002'}

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

From `results/run_2026-10-08_0037_before.md` (`python run_eval.py --label
before`, 16 scenarios, 5 tries each, cache off, temperature 0.9). This is my
second before run. The first, `results/run_2026-10-07_2229_before.md`, had only
the original scenarios and met all five criteria, which showed criterion 4 was
too easy (see Verdicts and Diagnoses). So I revised it in `criteria.md` before
running again, adding five more items, and this run is the before for the
improvement. Criterion 4 gets one row per item, because the revision has 25
tries. Criterion 5's five try columns are its five queries, one try each,
because the message is built without the model and is the same on every try.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | at least 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. State, found path (`vintage graphic tee under $30`) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. State, stop path (`designer ballgown size XXS under $5`) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card, original: `lst_002` Y2K Baby Tee | 5 of 5, all differ | PASS | PASS | PASS | PASS | PASS | MET (5/5, all differ) |
| 4. Revised: `lst_006` Graphic Tee (`bootleg graphic tee`) | 5 of 5, all differ | PASS | PASS | PASS | PASS | PASS | 5/5 |
| 4. Revised: `lst_033` Vintage Band Tee (`faded band tee`) | 5 of 5, all differ | PASS | PASS | PASS | PASS | PASS | 5/5 |
| 4. Revised: `lst_024` Vintage Polo Shirt (`polo shirt`) | 5 of 5, all differ | PASS | PASS | PASS | PASS | FAIL | 4/5 |
| 4. Revised: `lst_029` Silk Button-Down (`silk button-down`) | 5 of 5, all differ | PASS | PASS | PASS | PASS | PASS | 5/5 |
| 4. Revised: `lst_020` Henley Long Sleeve (`henley`) | 5 of 5, all differ | PASS | PASS | PASS | PASS | PASS | 5/5 |
| 4. Revised, all five items | 25 of 25 | | | | | | **MISSED (24/25)** |
| 5. Empty-search message (price · size · words · size in combination · price, size and words) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Real output, one try per criterion**, pasted as text from
`results/run_2026-10-08_0037_before.md`. Every try was produced by
`run_eval.py::main` calling `agent.py::run_agent`. The search goes through
`mcp_client.call_tool` to `mcp_server.py::search_listings`, the fit card comes
from `tools.py::create_fit_card`, and the empty-search message from
`agent.py::empty_search_message`. Each excerpt is trimmed to the lines its
criterion is judged on; the full tries, with outfits and traces, are in the log.

Criterion 1, `matching query completes`, try 1:

```
- stopped early: no
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
- search_results: 10

Fit card:
Scored this amazing Y2K Baby Tee on depop for only $18. Pairing it with a baggy dark wash denim and a chunky brown belt gives off the ultimate nostalgic retro energy.
```

Criterion 2, `impossible query stops early`, try 1 (the trace ends after step
2; there is no `suggest_outfit` step):

```
- stopped early: yes — Your issue is at the price: nothing matches under $5. One way it can help is by raising your price limit to at least $12. Your issue is at the size: nothing matches in size XXS. One way it can help is by trying size M, L or S/M. Your issue is at the words: nothing matches "designer ballgown". One way it can help is by trying other words, such as accessories, bottoms, outerwear, shoes or tops.
- selected_item: (none)
- search_results: 0

[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='xxs', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='xxs', max_price=5.0
      out: [] (empty)
      →    branch: empty, stopping with error: Your issue is at the price: …
```

Criterion 3, `state, matching query`, try 1 (the found item's id at the branch,
and the id each model tool was given):

```
[2] search_listings (via MCP)
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
      →    branch: found, selected_item = lst_002 Y2K Baby Tee — Butterfly Print
[3] suggest_outfit
      in:  lst_002 Y2K Baby Tee — Butterfly Print + wardrobe of 10 items
      →    received_ids: {'suggest_outfit': 'lst_002'}
[4] create_fit_card
      in:  outfit + lst_002 Y2K Baby Tee — Butterfly Print
      →    received_ids: {'suggest_outfit': 'lst_002', 'create_fit_card': 'lst_002'}
```

Criterion 4, `fit card rules, two-word brand (lst_024)`, try 5, the miss:

```
- stopped early: no
- selected_item: Vintage Polo Shirt — Forest Green ($18.0, thredUp)
- search_results: 1

Fit card:
Scored this classic Ralph Lauren piece on thredUp for only $18. The vintage preppy earth tones vibe goes so well with my favorite baggy jeans and chunky sneakers for an everyday look.

[4] create_fit_card
      in:  outfit + lst_024 Vintage Polo Shirt — Forest Green
      →    received_ids: {'suggest_outfit': 'lst_024', 'create_fit_card': 'lst_024'}
```

Criterion 5, `message: size in combination` (`platform sneakers size 9`), try 1:

```
- stopped early: yes — Your issue is at the size: nothing matches in size 9. One way it can help is by trying size US 8 or US 7.
- selected_item: (none)
- search_results: 0
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

Verdicts from the before run above, `results/run_2026-10-08_0037_before.md`.

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | A matching query completes all three tools | at least 4 of 5 | MET (5/5) | All five tries ran all three tools and returned a fit card. No try hit a model failure, so the one-miss allowance was not needed. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | Every try stopped with 0 search results, the trace ends after step 2 with no `suggest_outfit` step, and the message names what to change. |
| 3 | Every later step gets the item search found, or the run stops cleanly | 5 of 5 per query | MET (5/5, both paths) | Found path: in every try, the branch line's `selected_item` and both `received_ids` are `lst_002`. The run log prints the item's id, title, price and platform, not all 11 fields, so I judged the 11-field match by the id. `run_agent` sets `session["selected_item"] = session["search_results"][0]` (`agent.py:293`), the same dict, so a matching id means every field matches. Stop path: 0 results, an error message, no outfit or fit card, and no model step in the trace, so nothing was recorded in `received_ids`. |
| 4 | The fit card follows its caption rules on every counted try (original: `lst_002`) | 5 of 5, all differ | MET (5/5) | All five captions have 2 to 4 sentences, `$18` once, `depop` once, `tee` once and no brand, and no two are the same. There were no fallback captions or crashes, so nothing was re-run. |
| 4 | Revised in unit 4: the same rules on five more items | 5 of 5 per item, 25 of 25 | **MISSED (24/25)** | Four items went 5/5. The Polo Shirt went 4/5: try 5, "Scored this classic Ralph Lauren piece…", never names the item, so `shirt` appears 0 times and it fails the item-word rule. 4 of 5 against 5 of 5 is a miss. |
| 5 | The empty-search message names what blocked the search and how to fix it | 5 of 5 | MET (5/5) | For every blocking part of all five queries, the message names the part (`price`, `size`, `words`), quotes my value, and gives a fix from the data. Each message was identical on all five tries and in the first before run. |

**The first run, and why criterion 4 was revised.** My first before run
(`results/run_2026-10-07_2229_before.md`) met all five criteria. Criteria 2, 3
and 5 test steps that do not vary, so 5 of 5 is what a working build should get.
But criterion 4 was low. It ran on one item, `lst_002`, the item I had fixed the
fit-card prompt against in unit 3 (its item word `tee` is also in its style tag
`graphic tee`). So 5 of 5 mostly re-confirmed that fix. I first considered
tightening "all five differ", since 18 of 20 captions opened with "Scored this".
I decided against it: the rest of each caption varied, and that clause is there
to prove the tries are real, not to grade style. So I revised criterion 4
underneath the original to cover five items picked by what could break a rule,
kept the target at 5 of 5 per item, and committed it before running them.

**Diagnoses**

**Criterion 4 (revised), 24/25.**

- *Where:* the model's output in `tools.py::create_fit_card`, step 7 of my
  session flow. It is not the tool's code, the branch or the session: the trace
  shows `create_fit_card` received `lst_024`, and the caption has the right
  price and platform.
- *Mechanism:* for a listing with a brand, the prompt gives both
  `Brand: Ralph Lauren` (from `_item_details`, only when `brand` is not `None`)
  and `Name to use for the item: Vintage Polo Shirt`. Rule 6 allows naming the
  brand. Rule 2 says to mention the item using the name given, but the model
  treated "the Ralph Lauren piece" as that mention, so the name never appeared.
  My brand safeguard only replaces captions that name a *different* brand, so
  nothing caught it.
- *Pattern:* it is one problem, and the name only went missing on items with a
  brand.

| Captions in both before logs | Captions | Opening says "piece"/"find" where the name goes | Item never named |
|---|---|---|---|
| Items with a brand (`lst_024` Polo Shirt; `lst_007` Wrangler Denim Jacket in each run's empty-wardrobe scenario) | 15 | 6 (5 of them with the brand) | 3 |
| Items without a brand | 50 | 1 (Henley try 5, which names the item later) | 0 |

  Two of the three captions that never name the item are the Wrangler jacket's,
  in the empty-wardrobe scenario. That scenario is not part of criterion 4, so
  they don't count toward the verdict, but they show the Polo Shirt was not a
  one-off.



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
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
      in:  vintage graphic tee under $30
      out: max_price=30.0, style_tags='vintage, graphic tee'
[2] search_listings (via MCP)
      in:  max_price=30.0, style_tags='vintage, graphic tee'
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
      →    branch: found, selected_item = lst_002 Y2K Baby Tee — Butterfly Print
[3] suggest_outfit
      in:  lst_002 Y2K Baby Tee — Butterfly Print + wardrobe of 10 items
      out: For a casual look, pair the Y2K Baby Tee — Butterfly Print with the baggy straight-leg jeans, dark wash and th…
      →    received_ids: {'suggest_outfit': 'lst_002'}
[4] create_fit_card
      in:  outfit + lst_002 Y2K Baby Tee — Butterfly Print
      out: Scored this cute Y2K Baby Tee on depop for only $18. Styled it for a casual look with baggy straight-leg jeans…
      →    received_ids: {'suggest_outfit': 'lst_002', 'create_fit_card': 'lst_002'}
```

**Empty search**

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='xxs', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='xxs', max_price=5.0
      out: [] (empty)
      →    branch: empty, stopping with error: Your issue is at the price: nothing matches under $5. One way it can help is by raising your price limit to at least $12. Your issue is at the size: nothing matches in size XXS. One way it can help is by trying size M, L or S/M. Your issue is at the words: nothing matches "designer ballgown". One way it can help is by trying other words, such as accessories, bottoms, outerwear, shoes or tops.
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

**What I changed:** one sentence added to rule 2 of the fit-card prompt
(`FIT_CARD_RULES` in `tools.py`, commit `d68bbac`):

```
2. Mention the item exactly once, using the name given. If a brand is given, it
   may go right before that name, never in place of it: a caption that names the
   brand must still contain the name. The item word given below may appear only
   inside that name: ...
```

The docstring and the Tool Inventory say the same. The new sentence names no
listing from the data, so it is not fitted to the Polo Shirt. Nothing else in
the system changed.

**Which failure it was meant to fix:** the revised criterion 4 miss on
`lst_024`, where the brand took the name's place ("the Ralph Lauren piece") and
the item was never named.

### Run Log — After

From `results/run_2026-10-08_0104_after.md` (`python run_eval.py --label
after`): the same 16 scenarios, 5 tries each, cache off, and the same rows as
the before table.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | at least 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. State, found path (`vintage graphic tee under $30`) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. State, stop path (`designer ballgown size XXS under $5`) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card, original: `lst_002` Y2K Baby Tee | 5 of 5, all differ | PASS | PASS | PASS | PASS | PASS | MET (5/5, all differ) |
| 4. Revised: `lst_006` Graphic Tee (`bootleg graphic tee`) | 5 of 5, all differ | PASS | PASS | PASS | PASS | PASS | 5/5 |
| 4. Revised: `lst_033` Vintage Band Tee (`faded band tee`) | 5 of 5, all differ | PASS | PASS | FAIL | PASS | PASS | 4/5 |
| 4. Revised: `lst_024` Vintage Polo Shirt (`polo shirt`) | 5 of 5, all differ | PASS | PASS | PASS | PASS | PASS | 5/5 |
| 4. Revised: `lst_029` Silk Button-Down (`silk button-down`) | 5 of 5, all differ | PASS | PASS | PASS | PASS | PASS | 5/5 |
| 4. Revised: `lst_020` Henley Long Sleeve (`henley`) | 5 of 5, all differ | PASS | PASS | PASS | PASS | PASS | 5/5 |
| 4. Revised, all five items | 25 of 25 | | | | | | **MISSED (24/25)** |
| 5. Empty-search message (price · size · words · size in combination · price, size and words) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

The miss, `fit card rules, item word in tags (lst_033)`, try 3:

```
- stopped early: no
- selected_item: Vintage Band Tee — Faded Grey ($19.0, depop)
- search_results: 5

Fit card:
Scored this Vintage Band Tee for just $19 on depop. The vintage grunge streetwear vibe looks so sick tucked into wide-leg khaki trousers with chunky white sneakers and a brown leather belt. Can not wait to style this graphic tee with baggy straight-leg jeans and black combat boots for the ultimate dark wash fit.
```

**Did it help, and how do I know:** it fixed the failure it was aimed at, but
the criterion is still missed, 24/25, now on a different item.

| Measure | Before | After |
|---|---|---|
| Criterion 4 revised, Polo Shirt | 4/5 | **5/5** |
| Branded captions where the brand takes the name's place | 4 of 10 | **0 of 10** |
| Branded captions that never name the item | 3 of 10 | 1 of 10 |
| Criterion 4 revised, all five items | 24/25, MISSED | 24/25, MISSED |
| Criteria 1, 2, 3, 5 and criterion 4's original | all MET | all MET, unchanged |

(The branded captions are the Polo Shirt's five plus the Wrangler jacket's five
in the empty-wardrobe scenario.)

- **The targeted failure is gone.** 4 of the 5 Polo Shirt captions now write
  "Ralph Lauren Vintage Polo Shirt", the brand right before the name, which is
  what the new sentence allows. Across both before logs the brand took the
  name's place in 5 of 15 branded captions. If my change did nothing, 0 of 10
  would happen by luck less than 1 time in 50 ((10/15)^10 ≈ 0.017), so I read
  this as a real effect.
- **One branded caption still never names the item:** the Wrangler jacket's
  try 2, "Scored this amazing piece on poshmark for only $42", names neither the
  brand nor the item. The new sentence only applies when the brand is named, so
  it does not cover this shape. It is in the empty-wardrobe scenario, not
  criterion 4.
- **The new miss is a different failure.** The Band Tee's try 3 uses its style
  tag `graphic tee` ("style this graphic tee"), so `tee` appears twice. That is
  the tag problem I fixed in unit 3 coming back. It also happened once outside
  criterion 4: "vintage graphic tee energy" in try 4 of `state, matching query`,
  which criterion 3 doesn't judge on its caption. Across all captions, the tag
  repeat went from 0 of 65 in both before logs to 2 of 45 after.
- **I can't tell whether my change caused it.** If the rate had not changed,
  there is about a 1 in 6 chance both repeats would land in the after run
  ((45 × 44) / (110 × 109) ≈ 0.17), so two cases can't separate a regression
  from chance. A possible cause is that rule 2 is longer now, and the
  instruction to drop the item word from style tags comes after the new brand
  sentence.

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

One criterion is still missed: criterion 4 (revised), problem 1 below. The
other three are problems I found along the way that none of my criteria
measure.

**1. The style tag repeats the item word (criterion 4 revised, 24/25 after the
improvement).**

- *What happened:* in the after run, the Band Tee's try 3 says "style this
  graphic tee", so `tee` appears twice and the try fails. The same thing
  happened in try 4 of `state, matching query` ("vintage graphic tee energy"):
  2 of 45 captions after, 0 of 65 in both before logs.
- *Where and why:* the model's output in `tools.py::create_fit_card`.
  `_item_details` puts every style tag in the prompt (`Style tags: vintage,
  grunge, band tee, graphic tee, streetwear`), and rule 2 then asks the model to
  drop the item word from them. So the code hands the model the exact words it
  is told not to use, and depends on the model obeying every time.
- *What I'd do:* remove the item word from the tags in code before building the
  prompt (`graphic tee` becomes `graphic`, `band tee` becomes `band`), so the
  model never sees `tee` outside the name. That turns a rule the model can break
  into one it can't. Then run the same 16 scenarios again and compare the tag
  repeats with 2 of 45.
- *Why I stopped:* the unit allows one improvement, and I had used it on the
  brand rule. A second change in the same after run would make it impossible to
  tell which change did what. It could have been the stretch "a second
  improvement measured the same way", but I did not declare a stretch.

**2. A caption can call the item just "piece" and never name it.**

- *What happened:* in the after run, try 2 of the empty-wardrobe scenario
  (`lst_007`, Wrangler Denim Jacket) reads: "Scored this amazing piece on
  poshmark for only $42. The light blue wash and cropped silhouette give off
  such a cool vintage vibe. It is going to look so good layered over flowy midi
  dresses for weekend errands." It names neither the brand nor the jacket.
- *Where and why:* the model's output in `tools.py::create_fit_card`. Rule 2
  asks for the name, and my new sentence only covers captions that name the
  brand. In code, `create_fit_card` only checks for an empty reply and for
  other brands, never that the name is there.
- *What I'd do:* check the reply in code. If the caption doesn't contain the
  item's name, retry once, then return the fallback caption, which always names
  it. Criterion 4 re-runs fallback captions without counting them, so I would
  also count how often the check fires. Otherwise it would hide the model's
  misses instead of showing them.
- *Why I stopped:* the same one-improvement rule. It is also in the
  empty-wardrobe scenario, which is not one of my five criteria, so it was not
  the miss my diagnosis pointed at.

**3. A dropped connection hangs the agent instead of reaching my
model-unavailable handler.**

- *What happened:* during my second before run I closed my laptop. The macOS
  sleep log shows "Clamshell Sleep" at 23:25:21, and the run's last output was
  at 23:25:22, inside `create_fit_card` for the Polo Shirt's try 5. At 00:29 the
  process was still waiting, with its connection to Google still listed as
  open. There was no error and no message. `run_eval.py` writes its log only at
  the end, so that run's results were lost, and I re-ran it with the laptop
  kept awake.
- *Where and why:* `generate.py::_get_client` creates the client with
  `genai.Client(api_key=key)` and no timeout, so a read on a dead connection
  waits forever. My handler in `run_agent` only runs when `generate()` raises,
  and it never raised.
- *What I'd do:* give the client a timeout through its HTTP options.
  `generate.py` already turns an error that mentions "timeout" into "Couldn't
  reach the model. Check your internet connection" (`generate.py:218`), and my
  handler maps that to its own message. So a timeout would reach the user as
  "Your issue is at the styling model…" instead of a silent hang.
- *Why I stopped:* `generate.py` is a starter file, not part of my system, and
  the only changes allowed this unit are the MCP move and one improvement. It
  is also not a criterion miss.

**4. Searching by brand finds nothing, and the message blames the words.**

- *What happened:* `ralph lauren polo` returns `[]`, even though a Ralph Lauren
  polo (`lst_024`) is in the data, and the message says: "Your issue is at the
  words: nothing matches "ralph lauren polo". One way it can help is by trying
  other words, such as accessories, bottoms, outerwear, shoes or tops." I tried
  the brand plus the item word for every listing with a brand, and 5 of the 8
  return nothing (`woolrich shirt`, `champion jacket`, `wrangler jacket`,
  `demonia janes`, `ralph lauren shirt`).
- *Where and why:* `tools.py::search_listings` scores query words against style
  tags, colors, category, condition, title and description, but not `brand`.
  So a brand word only counts when it is also written in the title or
  description, which is true for 2 of the 8 branded listings (both Levi's).
  Then the coverage cutoff removes the listing: in `ralph lauren polo` only
  `polo` matches, 1 of 3 words, below my more-than-half rule.
  `empty_search_message` only knows prices, sizes and words, so it blames the
  words and suggests category names, which doesn't help.
- *What I'd do:* score `brand` like a style tag (a point for each matching
  word, plus the exact-value bonus for the whole brand), let
  `empty_search_message` say when a brand matches nothing, and re-run my search
  checks so nothing else changes.
- *Why I stopped:* no criterion covers brand search, so no run measured it. I
  only found it while choosing queries for the criterion 4 revision, and fixing
  it would be a second change to the system this unit.



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
