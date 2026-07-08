# roadmap

ditto's core is focused: extract real AI coding history, mine the user's working profile, and install it where agents already read context.

The roadmap is about making that loop safer, easier to install, and portable across more agent tools.

## next

### more log sources

Add adapters for other AI coding tools when their local logs are accessible.

Likely targets:

- Cursor
- Cline
- Continue
- Windsurf

Goal: make the profile portable across the tools people already use.

### counterweight profiles

Ditto starts as a mirror: mine how you actually work.

The same profile can also power a counterweight agent: not "act like me", but "protect me from my defaults."

Examples:

- challenge me when I overbuild
- ask for constraints when I drift
- force proof when I accept vague "done"
- catch repeated blind spots

Goal: use the profile to improve the human, not only imitate them.

## contributions wanted

The most useful contributions right now are practical and easy to audit:

- sample JSONL formats from other tools
- redaction pattern improvements
- install-path fixes for specific agents
- better mining prompts
- examples of useful `you.md` sections

Do not send private logs or a full personal profile unless you really mean to make it public.
