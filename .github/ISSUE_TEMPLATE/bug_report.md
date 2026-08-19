---
name: Bug report
about: Something in Emulo behaves differently than documented
title: ''
labels: bug
assignees: ''
---

<!--
READ THIS FIRST. Emulo reads your private session logs, so a bug report is the
easiest place to leak your own data by accident.

Do NOT paste or attach:
- your profile (you.md, you-designer.md, you-writer.md, you-video.md, the appendix)
- session transcripts, chunks, you-corpus.txt, or anything out of emulo-out/
- anything under EMULO_HOME (~/.emulo) other than a redacted error message
- absolute paths from your machine, usernames, repo names, or client names
- API keys, tokens, or anything a redactor might have missed

Replace paths with placeholders like <HOME>, <REPO>, <LOGDIR>. If you cannot
describe the bug without private text, say so and we will work out a synthetic
reproduction instead.
-->

**Emulo version**

<!-- `python -m pip show emulo`, or from a checkout: `python -c "import emulo; print(emulo.EMULO_VERSION)"` -->

**OS and Python version**

<!-- e.g. Windows 11 / Python 3.11, macOS 15 / Python 3.12 -->

**How you run Emulo**

<!-- pip/uvx CLI, checkout (`python emulo.py ...`), Claude Code or Codex plugin, skills.sh bootstrap, or the MCP server -->

**Command you ran**

```text
<paste the command, with real paths replaced by <HOME>/<LOGDIR>>
```

**What you expected**


**What happened**

```text
<error text or output, paths redacted>
```

**Anything else**

<!-- Source of the logs (codex / claude / copilot / opencode / antigravity), rough
session counts, or whether it also happens with --dry-run. Counts and shapes are
useful; contents are not. -->

- [ ] I checked this report contains no profile contents, session text, or personal paths.
