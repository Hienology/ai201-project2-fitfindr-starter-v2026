# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
In my build, the first three steps of a try (parsing the query with regular
expressions, `search_listings`, and the branch) do not vary between tries, so a
fault there would fail all five tries, not one. Only steps 4 and 5, the model
calls in `suggest_outfit` and `create_fit_card`, can vary: a try fails if the
model is still unreachable after one retry, or still rate limited after
`generate()`'s five attempts. One miss in five allows for one such failure; 5 of
5 would assume those critical sections never fail. An empty reply does not fail
a try, because each tool returns fixed fallback text, and a bad key or a runaway
loop would fail every try, so those are setup faults, not what this allowance
covers.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
In my build, the stop path runs only the first three steps (parsing,
`search_listings` and the branch), which do not vary between tries and make no
model call, and the message is built without the model, so it is the same on
every try. The impossible query fails three ways at once: no listing costs $5 or
less (the cheapest is $12), no listing has size XXS, and neither "designer" nor
"ballgown" appears in any listing. So a miss could only come from a bug, which
would fail all five tries rather than one; that is why the target is 5 of 5.

---

## 3. Every later step gets the item search found, or the run stops cleanly

Run the matching query `vintage graphic tee under $30` and the impossible query
`designer ballgown size XXS under $5` five times each, and read the session at
the end of each try. A try passes when its session matches the path it took:

- **Search found listings:** `error` is `None`, `selected_item` has the same
  `id` and the same values in all 11 fields as `search_results[0]`, and
  `received_ids["suggest_outfit"]` and `received_ids["create_fit_card"]` both
  equal that `id`.
- **Search found nothing:** `search_results` is `[]`, `error` is a non-empty
  string, `selected_item`, `outfit_suggestion` and `fit_card` are all `None`,
  and `received_ids` is empty.

A try that crashes in a model call before returning a session is re-run and not
counted. Target: 5 of 5 tries for each query.

**Why this target:**
Steps 1 to 5 of my session flow are plain Python with no model call: the item is
copied from `search_results[0]` into `selected_item`, and the loop records the
`id` it hands to each model tool, so these values do not vary between tries. If
the handoff is right it is right every time, and if a field is lost or the wrong
item is passed, that would show on every try, so 5 of 5 is the only target that
does not excuse a bug. Checking the `id` each tool was given, rather than the
model's text, keeps this criterion about state and not about what the model
writes. A try that crashes is re-run because my safety nets (fallback text and
one retry) exist to keep the run going, and a crash says nothing about state.



---

## 4. The fit card follows its caption rules on every counted try

Run the matching query `vintage graphic tee under $30` five times with the
response cache off (`AI201_CACHE=0`), and check each session's `fit_card`
against that session's `selected_item`. A try passes when its fit card:

- has 2 to 4 sentences (a sentence ends with `.`, `!` or `?`);
- contains exactly one dollar amount equal to the item's price, compared by
  value (`$18` and `$18.00` both count);
- names the item's platform exactly once, ignoring capitals;
- contains the item word, the last word of the item's title before the dash
  (e.g. `tee`), exactly once, ignoring capitals and hyphens;
- names no brand from the brand names in `data/listings.json` other than the
  item's own.

Across the five counted tries, no two fit cards may be word-for-word identical.

A try whose fit card is the fallback caption (`Thrifted the … Simple basics,
easy outfit.`), or that crashes in a model call, is re-run and not counted. A
try is re-run at most twice; if all three attempts end in a fallback or a crash,
it counts as a FAIL. Target: 5 of 5 counted tries pass, and the five fit cards
all differ.

**Why this target:**
The fit card is step 7 of my session flow, the one step whose text the model
writes, so it can differ between tries (temperature 0.9), and every rule here is
something a stranger can count. I set 5 of 5 on counted tries because my safety
nets take the failures out of the count: a crash or an empty reply is re-run,
the fallback caption is a fixed string that is easy to spot, and the tool itself
replaces any caption that names a wrong brand, checked against every brand name
in the data. What is left is whether my prompt rules make the model obey the
caption rules every time; a rounded price, a repeated item word or a one-line
caption is a real miss. The cache is off because identical prompts would
otherwise replay the same caption, and the tries need to be real.


---

## 5. Your choice

<!-- YOU WRITE THIS ONE TOO.

     Pick something you actually care about getting right. Speed, the empty
     wardrobe path, what happens when the model can't be reached, whether the
     search respects a price ceiling — anything, as long as it names a number
     or an observable outcome. -->



**Why this target:**



---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
