---
name: emulo
description: Load the user's Emulo profile, rules mined from their own local AI coding session logs (Claude Code, Codex, Copilot CLI, OpenCode, Google Antigravity), each with dated quotes. Read it before working on their task.
emoji: 🐦‍⬛
homepage: https://github.com/ohad6k/emulo
metadata:
  openclaw:
    install:
      - kind: uv
        package: emulo
        bins: [emulo]
---

# Emulo profile

Load the user's Emulo working profile: rules mined from their own coding
sessions, each with dated quotes. Read it before working on their task.

Emulo mines the user's own AI coding sessions (Claude Code, Codex, Copilot CLI,
OpenCode, Google Antigravity) into a `you.md` working profile: their laws, their
taste, their voice, and the failure modes they want you to protect them from.

## Use this before working on their task

If the profile is not installed yet, this writes it into the project's `AGENTS.md`
(it prints where it wrote and returns nothing to read). Do not run it yourself before
you name the exact folder to the user and get their yes. Tell them it writes the whole
profile, including quotes from their own sessions, into that AGENTS.md, which is usually
committed and shared, so suggest keeping it out of version control:

```
emulo --install you.md --target agents --repo .
```

Or call it through the MCP server:

```
uvx emulo mcp
```

The MCP server exposes one tool, `load_emulo_profile`, which returns the
profile for the domain you are about to work in (`work`, `design`, `write`, or
`video`). It serves only a profile activated by Emulo's agent mining flow; with
none active, it returns a recovery instruction.

## What you get

The profile is mined from the user's real sessions, not a questionnaire. It
carries:

- **Laws** they never want broken, each with receipts from real sessions
- **Taste** in design and code, including what they reject on sight
- **Voice** for anything written in their name
- **Failure modes** to protect them from

## Privacy

Mining runs locally against session logs already on the machine. The profile is
the user's own file. Nothing is uploaded by this skill.

Previously published as `ditto-profile`. The project was renamed to Emulo in
v0.5.0; see <https://github.com/ohad6k/emulo/releases/tag/v0.5.0>.
