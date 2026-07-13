---
name: mine
description: Use only when the user explicitly asks to run, set up, update, re-mine, or deepen Ditto from real local AI coding-session history.
---

# Ditto mine

Mine only real user-authored `.jsonl` sessions. Never synthesize a profile from rules files, memory, or a typed self-description.

1. Resolve `DITTO_PY` to `ditto.py` two directories above this skill, falling back to `./ditto.py` only in a direct checkout. Confirm Python 3 exists.
2. The full-history quality default reads all eligible history. Run `python "$DITTO_PY" plugin freeze`, which freezes the selected local segments without model calls. Show valid sessions, post-dedupe source tokens, selected source tokens, cache hits, planned worker calls, and planned reducer calls, retain the exact `approval_hash`, `run_id`, selected segment/report paths, and `pack_path`, then wait for explicit cost approval before model work.
3. Only when the user explicitly asks for a quick preview, run freeze with `--preview`. Say this exactly before approval: `Quick preview creates a starter profile from selected history, not the full profile.` Never call preview the default, the full profile, or equivalent in quality to full-history mining.
4. After approval, use only the retained frozen run and paths; live history added after the freeze belongs to a later update. Do not use the legacy `plugin preflight` then `plugin prepare` sequence for live regular mining.
5. Run one fast worker for each uncached selected segment. Each reads only its segment and the per-segment contract in `MINING_PROMPT.md`, writes its assigned JSON report, and runs the read-only `plugin validate-report` command until accepted.
6. Cache each accepted report with `plugin cache-report`; stop on rejection.
7. Run one strongest-available reducer over only the validated reports and the combined reducer contract. It writes the complete assigned pack and self-validates with `plugin validate-pack`.
8. Activate only the validated pack with `plugin activate`, then run `plugin status` and render the card. Report active version, domain states, selected source tokens, actual worker/reducer passes, cache reuse, and targeted-deepen instructions.

Every prepared mode requires explicit approval of its displayed plan. Installation itself scans no logs and schedules zero mining calls. An identical update schedules zero additional Ditto mining calls, although the host task still has normal interaction overhead.

Adaptive receipt/scout stages are experimental and excluded from the Plugin release path. Run `--stage A` only when a developer explicitly requests experimental adaptive-recall testing; never select it automatically or use it for release calibration.
