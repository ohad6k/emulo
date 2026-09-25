# Emulo in OpenClaw and Hermes Agent

OpenClaw and Hermes Agent read the same skill format Emulo writes, so a mined profile can be copied into either one without an adapter or a format change.

What has been checked, and when: skill discovery only, in July 2026, on earlier versions (Windows, OpenClaw 2026.6.11 and Hermes Agent 0.18.2), before the project was renamed from Ditto to Emulo. The profile skill showed `✓ ready` in `openclaw skills list` and `enabled` in `hermes skills list`. None of this has been re-verified since, and neither host was part of the September 2026 host-by-host load test. In one July OpenClaw test (gpt-5.5 agent turns), the skill alone was not reliably read in a one-shot turn; with the profile put into the workspace `USER.md`, the answer to the same one-line prompt differed from a cold install's. That was one prompt with no placebo, so it shows the answer changed, not that it got better.

## Why copy it in

Both runtimes build their picture of you forward, session by session, starting from empty memory files. A fresh Hermes install has an empty `memories/` directory; a fresh OpenClaw agent starts blank and fills `USER.md` over time. Emulo has already mined a profile from your real Claude Code, Codex, Copilot CLI, OpenCode or Antigravity history, so you can hand that profile to a fresh install instead of starting it empty.

This guide covers one direction: mined profile into the runtime. Mining OpenClaw or Hermes sessions as an Emulo source is separate work, tracked in [issue #3](https://github.com/ohad6k/emulo/issues/3).

## Prerequisite

Mine your profile first (see the [Quickstart](../README.md#quickstart)), then install it for Claude Code:

```bash
emulo --install you.md --target claude
```

That writes the profile skill to `~/.claude/skills/you/SKILL.md`. The steps below copy that folder.

## OpenClaw

Copy the profile skill into the OpenClaw workspace:

```bash
# macOS / Linux
cp -r ~/.claude/skills/you ~/.openclaw/workspace/skills/you
```

```powershell
# Windows
Copy-Item -Recurse ~\.claude\skills\you ~\.openclaw\workspace\skills\you
```

Then check:

```
openclaw skills list
```

Look for a row named `you` with source `openclaw-workspace`. The July check showed a `✓ ready` row under the old name; it has not been repeated with the `you` skill.

OpenClaw also scans the shared `~/.agents/skills` directory, so if your profile already lives there it is picked up with no copying. Keep the profile in one location so a single `you` skill resolves.

Then seed the workspace `USER.md`. It is OpenClaw's standing picture of you and is injected into every session, so the profile does not wait on the agent deciding to open a skill:

```bash
# take the profile body (below the frontmatter) into the workspace USER.md
tail -n +5 ~/.claude/skills/you/SKILL.md > ~/.openclaw/workspace/USER.md
```

`tail -n +5` skips the four lines of frontmatter Emulo writes by default. If your `you.md` had its own, longer frontmatter, skip to the line after its closing `---` instead.

If you have not onboarded yet, start with `openclaw onboard --skip-bootstrap` so the first-run ritual does not overwrite what you seeded.

## Hermes Agent

Copy the profile skill into the Hermes skills directory:

```bash
# macOS / Linux (HERMES_HOME overrides the base directory)
cp -r ~/.claude/skills/you ~/.hermes/skills/you
```

```powershell
# Windows
Copy-Item -Recurse ~\.claude\skills\you $env:LOCALAPPDATA\hermes\skills\you
```

Then check:

```
hermes skills list
```

Look for a `you` row with source `local`, status `enabled`. The July check showed that under the old name; it has not been repeated with the `you` skill, and whether Hermes reads the skill during a task was not tested.

Deeper seed (optional): `<hermes-home>/memories/USER.md` is Hermes's always-loaded picture of you and it is capped small (about 1,375 characters per the Hermes docs). If you seed it, put only the laws that must never unload; the full profile stays in the skill.

## Naming note

There is an unrelated skill called `ditto` on ClawHub (a memory-graph tool by a different author). Emulo was called Ditto before v0.5.0, so installing `ditto` from a registry gets that other project, not this one. Use the copy steps above, which install your own mined profile.

## Privacy

The mined profile is yours and can contain how you work in detail. Copying it into another runtime's skills directory keeps it on your machine, same as Emulo's default. Publishing it anywhere is your call to make deliberately, not a step in this guide.
