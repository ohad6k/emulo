# Feedback log

What users actually said, where they said it, and what ditto does about it. Updated as feedback lands.

## The signal so far

Two independent users skipped or discounted the work-profile because it overlapped with rules they already maintain, and both called the mining/voice side the valuable part. The voice profile is the wedge. Nobody else mines how you write from your real sessions; everybody already has a rules file.

## By source

### Voice registers (Reddit, 2026-07-13)

> Ran it on ~120 sessions. Skipped the work-profile (overlapped with my existing memory setup), but the voice-profile is a game changer. I built a couple skills to load my voice before I write anything. One problem: ditto averages the voice I use with friends, family, and coworkers, so when I message my boss it feels too casual. Could ditto split the voice into a casual and a professional register?

- **Signal:** strongest feature validation yet, plus the sharpest feature request. The single averaged voice is a real defect.
- **Action:** voice registers (casual / professional / shared laws) with the register inferred from task context, not asked. In progress.

### Session logs as raw material (Reddit, 2026-07-13)

> Session logs are a gold mine. I use them all the time to create, update, and delete skills, agent instructions, and permissions. Claude does something similar with its fewer-permission-prompts command. I also manage multiple session conflicts through a dedicated controller session instead of worktrees.

- **Signal:** validates the core bet (sessions > hand-written rules). Also hints at a wider product: mining sessions for *skills and permissions*, not just profile. Overlaps with the roadmap's workflow-mining item.
- **Action:** none now; fold into workflow mining when it opens.

### Prior art: Command Code "Taste" (Reddit, 2026-07-13)

> Looks interesting, but reminds me of the "Taste" introduced by Command Code. https://commandcode.ai/docs/taste

- **Signal:** positioning. People map ditto onto whatever nearest neighbor they know.
- **Action:** sharpen the "mined from raw session logs, not authored" line everywhere; consider a short comparison note in the README (rules/memory/bmad/taste/soul.md in one table).

### Independent clone: blackbox (Reddit, 2026-07-13)

> I made my own version: https://github.com/cgallic/blackbox

- **Signal:** the idea is hot enough that people build their own the week they see it. Distribution speed matters more than feature depth.
- **Action:** keep shipping; the moat is the mining quality (receipts, bounded passes, registers), not the idea.

### "It's called claude rules / memory / bmad" (Reddit, 2026-07-12)

- **Signal:** same positioning gap as the Taste comment, hostile flavor. The one-line answer that works: rules and memory are hand-written by you; ditto is mined from your real sessions, you don't write anything.
- **Action:** same as Taste — the differentiation line has to survive a skim.

### Issue #7 — SOUL.md, layers, and the graph direction (TomLucidor, aplaceforallmystuff)

The richest thread on the repo. Landed so far: the three lenses (`examples/lenses/`), the unified-system doc, and the corrected layering (credit aplaceforallmystuff):

- graph memory = what you know
- ditto = how you work
- voice/persona = how you sound
- soul.md = who the agent is

Banked for later: atoms-with-links reducer output, SQLite-based local graph (no server), optional local embeddings for per-task retrieval (v2), spill-the-beans elicitation pass (roadmap: optional elicitation), profile drift/versioning (roadmap: profile drift).

### Issue #3 — adapters for more agents

Hermes Agent spec is complete in-thread (SQLite `state.db`, per-OS paths, WAL, user-messages-only). Cursor/Windsurf storage docs claimed by balaredde. All adapter code held until the ditto.py rewrite lands. Two potential adapter owners waiting.

### Issue #1 — share what ditto found (theconsultant)

147 sessions, ~4 months. Called the mined traits "pretty accurate", including a trust-gated manual-publish pattern they'd never written down anywhere, with a verbatim receipt. First public testimonial with real output.

## Standing conclusions

1. **Lead with voice.** The work-profile fights every existing rules file for territory; the voice/writing side has no incumbent.
2. **Registers, not one voice.** Averaging registers is the known defect of the winning feature; fixing it is the highest-leverage code change.
3. **Positioning needs one skimmable line.** "Mined from your raw session logs — you don't write it" answers rules, memory, bmad, Taste, and soul.md in one breath.
4. **The moat is mining quality.** Receipts, bounded passes, register separation. Clones can copy the idea in a weekend; they can't copy the discipline.
