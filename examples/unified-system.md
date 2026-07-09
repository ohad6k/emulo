# the unified system — where ditto fits

A common question: how does ditto sit alongside graph memory (Obsidian, llm-wiki),
voice/persona tools, agent-identity files (soul.md), and skill mergers? They aren't
competitors. They're **different layers, each built from different raw material.** This is the map.
(The soul.md row here follows the correction from [@aplaceforallmystuff](https://github.com/aplaceforallmystuff),
who builds soul.md into cerebro.)

## four layers, four raw materials

```
  what you KNOW  ───────►  graph memory      (obsidian, llm-wiki)
                           notes and links you wrote on purpose

  how you WORK  ────────►  ditto  <- this repo (~/.claude, ~/.codex .jsonl)
                           raw session logs, what you never wrote down

  how you SOUND  ───────►  voice / persona   (your tweets, essays, style)
                           the way you talk, for copy in your voice

  who the AGENT is  ────►  soul.md           (its values, boundaries)
                           the AI's own identity, formed working with you
```

Each answers a different question, so they **stack** instead of overlapping:

| layer | source | what it captures |
|---|---|---|
| graph memory | notes / wiki | facts, decisions, knowledge |
| **ditto** | raw session logs | how *you* decide, reject, get stuck |
| voice / persona | your writing | how you sound |
| soul.md | your working relationship with the agent | who the *agent* is |

ditto and soul.md are near mirror-images: **ditto profiles the human from the logs, soul.md lets
the agent articulate itself.** ditto is the one that reads the material you **never curated** —
your session logs are the you that just worked, not the you that you edited.

## the deliberate limit
ditto will not mine your notes, `CLAUDE.md`, or rules file as source. That would just reflect the
rules you already wrote back at you — which is what `/init` does. It only mines the raw `.jsonl`.

## how they compose in practice
- `you.md` is plain markdown. Drop it in your vault and link it from your graph like any other note.
- ditto and soul.md pair naturally: run ditto for your side, soul.md for the agent's. Skill-mergers like agent-borg can absorb `you.md` into a bigger second-brain setup.
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
