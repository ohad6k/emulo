# ditto — mining prompt

After running `ditto.py`, paste this into your coding agent (Claude Code / Codex / Cursor). It works two ways:

- **Fan-out (best):** tell your agent to spawn one sub-agent per file in `ditto-out/chunks/`, each running the prompt below on its chunk, then merge all reports with the reducer at the bottom.
- **Simple:** run the prompt below once per chunk yourself, paste the outputs together, then run the reducer.

---

## per-chunk prompt

```
You are mining a chunk of ONE person's real messages to AI coding assistants,
across months and several projects. The file contains ONLY their own words —
mostly short directives, occasionally long specs — each prefixed with a [date].

Read the ENTIRE file at: <path-to-chunk>
If it is long, read it in slices until you have covered ALL of it. Do not
sample the top and guess the rest — the middle of the file counts as much
as the start.

Extract a dense, SPECIFIC profile. Ban generic filler ("they want working code",
"they value quality"). Every bullet must be something a stranger could NOT have
guessed — grounded in what they actually wrote. Cite dates. Prefer verbatim quotes.

Return markdown with these EXACT headers:

## DECISIONS & PIVOTS
Concrete choices / direction-changes and (if visible) why.

## VOICE & LANGUAGE
How they actually write: recurring phrases, tics, spelling patterns, tone, how
they give orders, how they show frustration or approval. 6-10 verbatim short quotes.

## STUCK-POINTS & FRICTION
What repeatedly trips them up. Recurring bugs, tools that fail them, what they
ask for over and over, what makes them angry.

## REJECTIONS & DISLIKES
What they push back on, correct, or hate. What they say NOT to do.

## WORK-STYLE & OPERATING RHYTHM
Pace, when they spec vs one-line, how they delegate, verification habits.

## GOALS & DRIVES
What they're reaching for. Quote the raw ambition where it appears.

## RULES THEY STATE
Any rule/law they repeat unprompted ("only done when X", "never Y").

## SHARPEST QUOTES
The 5-8 lines that most capture who they are.

Be information-dense. Your whole response IS the data. No preamble.
```

---

## reducer prompt (run once over all the chunk reports)

```
Below are N independent profiles of the same person, each mined from a different
slice of their history. Merge them into ONE model.

Rank every trait by how many of the N reports independently surfaced it. A trait
found in many reports is the real them; a trait in one report is noise — cut it or
mark it low-confidence.

Every trait you keep gets a receipt: mark how many of the N reports found it,
inline, like `**done means it runs live** (18/20)`. A trait without a strong
count doesn't belong in the profile.

Output a tight `you.md` an AI agent reads before any task. Start the file with
this EXACT frontmatter so it installs as a skill unchanged (do not skip it):

---
name: you
description: <one line: this person's working profile — laws, taste, voice — so the agent acts like them, not a stranger>
---

Then the body, with sections:
- Who they are (one paragraph)
- Their laws (rules they state, ranked by frequency)
- How to talk to them
- How they work / build
- Their taste (produce this / reject that)
- Their voice (for writing copy as them)
- Their failure modes (protect them from these)
- The one throughline

Keep it lean — it loads on every task. Put deep evidence/quotes in a separate
appendix file, not in you.md.

ALSO write `ditto-out/card.json` — the shareable card. Exact shape:

{
  "archetype": "<2-4 word label for how this person operates, specific not generic — e.g. 'Ship-First Skeptic', 'Proof-or-It-Didn't-Happen'>",
  "laws": [
    {"text": "<their #1 law, their words>", "count": "18/20"},
    {"text": "<law 2>", "count": "15/20"},
    {"text": "<law 3>", "count": "14/20"}
  ],
  "truth": "<the ONE uncomfortable/surprising thing the reports agree on that they never wrote down anywhere>"
}

Counts are real report counts, never invented. Then tell the user to run
`python ditto.py --card` to see their card.
```

---

## lenses (optional — the same logs, a different self)

The default reducer produces a **working self**: laws, taste, rules — tuned so an
agent acts like you on a task. But the same raw chunks hold more than one self. Run
the reducer again with one of these swapped-in framings to mine a different lens from
the exact same reports. Same material, different cut.

**Thinking self** — how you reason, not what you rule. Replace the reducer's section
list with:
```
- How they break a problem down (first move, how they narrow it)
- How they debug (what they do when something is wrong)
- What they do when stuck (escalate, rebuild, step away, ask)
- How they decide (by reference, by feel, by proof, by analogy)
- How they verify they were right
- Their reasoning tics (the questions they ask themselves out loud)
- The one thing about how they think that they'd never say out loud
```

**Designer self** — how you make taste calls. Replace the section list with:
```
- What they reject on sight (the cardinal design sin, in their words)
- What "good" looks like to them (the words they reach for)
- How they brief a look (reference-first? by feel? by spec?)
- How they tell a real redesign from a reskin
- Their non-negotiables (contrast, motion, layout, whatever recurs)
- What they're actually chasing (the feeling, not the pixels)
- The taste rule they enforce but never wrote down
```

Keep the same ranking discipline (count how many reports found each), the same
"no filler a stranger could guess" bar, and write each lens to its own file
(`you-thinking.md`, `you-designer.md`) so they stack alongside `you.md`.
See [`examples/`](examples/) for all three mined from one real history.
