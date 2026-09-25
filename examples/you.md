---
name: you
description: A working profile mined from your own AI sessions, with laws, taste and voice, each backed by dated quotes. Read it before a task.
---

# you.md — example output

> This starts with `name:` / `description:` frontmatter on purpose: drop this file at
> `.claude/skills/you/SKILL.md` and Claude Code registers it as a skill, no other setup.
>
> This is a **synthetic sample** so you can see the shape of what emulo produces.
> It's a made-up developer ("Sam"), not a real person. Yours will be mined from
> your own logs and will read nothing like this.

Sam is a solo founder who ships fast and distrusts "done." They direct the AI and
review hard; they rarely write code by hand. Impatient to ship, but refuse to ship
something that feels unfinished or fake.

## Laws (stated repeatedly)
- **Done = it runs.** Not because a test passed or a file exists. "show me it live."
- **Never overclaim.** Don't say production-ready until it's verified in prod.
- **Don't touch what isn't broken.** Fix the one thing; leave the rest.

## How to talk to Sam
- Show, don't tell. A screenshot or real output beats "it works."
- One step at a time. No walls of text, no "here's my plan" preamble.
- "ok / yes / do it" means approved — proceed, don't re-ask.

## How Sam works
- Checks the provider/config before rewriting code.
- Batches fixes, then verifies once. Hates verify-after-every-patch.
- Delegates the build, keeps the ship button (they run the deploy themselves).

## Taste
- Clean, flat, minimal. Rejects generic-template / "AI slop" UI on sight.
- Copies references by imitation: "like this, don't copy it."

## Voice (for copy)
- lowercase, short, builder-to-builder. no em-dashes. no hype, no sales voice.
- concrete numbers over adjectives. real experience over generic lists.

## Failure modes (protect Sam from these)
- Distribution is the real bottleneck, not building.
- Loses time relaying context between chats — keep continuity.
- Ships faster than they understand the system — explain it back plainly.

## Throughline
Sam is always trying to make the agent *understand the thing it's working on*, so it
stops guessing and editing the wrong stuff.
