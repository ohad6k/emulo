# the unified system — where ditto fits

A common question: how does ditto sit alongside graph memory (Obsidian, llm-wiki),
published-writing personas (soul.md), and skill mergers? They aren't competitors. They're
**different layers of you, each mined from different raw material.** This is the map.

## three layers, three raw materials

```
  what you KNOW  ─────────►  graph memory        (obsidian, llm-wiki)
                             notes, docs, links you wrote on purpose

  how you WORK  ──────────►  ditto  ⟵ this repo   (~/.claude, ~/.codex .jsonl)
                             raw session logs — what you never wrote down

  how you SOUND  ─────────►  soul.md              (tweets, essays, posts)
                             you performing for an audience
```

Each answers a different question, so they **stack** — they don't overlap:

| layer | source | what it captures | you wrote it on purpose? |
|---|---|---|---|
| graph memory | notes / wiki | facts, decisions, knowledge | yes |
| **ditto** | raw session logs | how you decide, reject, get stuck | **no** |
| soul.md | published writing | voice, opinions, style | yes (for an audience) |

ditto is the only one that reads the material you **never curated**. That's the whole point:
your notes and posts are the you that you edited; your session logs are the you that just worked.

## the deliberate limit
ditto will not mine your notes, `CLAUDE.md`, or rules file as source. That would just reflect the
rules you already wrote back at you — which is what `/init` does. It only mines the raw `.jsonl`.

## how they compose in practice
- `you.md` is plain markdown. Drop it in your vault and link it from your graph like any other note.
- Feed `you.md` into `soul.md` as one more source if you want the voice side too.
- `you.md` installs as a completely standard skill, so any loader or skill-merger (borg, etc.)
  handles it unchanged. It's the one skill a merger should absorb verbatim — it *is* your conventions.

## more than one self from the same logs
The default `you.md` is your **working self** — laws and taste, tuned for an agent doing a task.
But the same raw chunks hold other selves. Run the reducer with a different framing (see
[`MINING_PROMPT.md`](../MINING_PROMPT.md) → lenses) and you get:

- **[working self](lenses/you-working.md)** — laws, taste, voice (the default)
- **[thinking self](lenses/you-thinking.md)** — how you reason, debug, and decide
- **[designer self](lenses/you-designer.md)** — how you make taste calls

All three in `examples/lenses/` are mined from one real 8-month history (the repo author's own),
so you can see the same person cut three ways. Same raw you, different lens.
