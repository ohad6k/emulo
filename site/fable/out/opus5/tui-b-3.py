#!/usr/bin/env python3
"""deploy report — one-shot terminal summary. prints once and exits."""

import os
import sys

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

# ---- layout ---------------------------------------------------------------
GUTTER = "  "
NAME_W = max(len(name) for name, _, _ in steps)
STATUS_W = max(len(status) for _, status, _ in steps)
DUR_W = 7
BAR_W = 30
RULE_W = (
    len(GUTTER) + 1 + 2 + NAME_W + 2 + STATUS_W + 2 + DUR_W + 3 + BAR_W
)

# ---- color ----------------------------------------------------------------
COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None and os.environ.get("TERM") != "dumb"

RESET = "\x1b[0m"
DIM = "2"
FAINT = "38;5;240"
BOLD = "1"
RED = "31"
GREEN = "32"


def paint(text, *codes):
    if not COLOR or not codes:
        return text
    return "\x1b[" + ";".join(codes) + "m" + text + RESET


STYLE = {
    "ok": {"mark": "\u2713", "mark_codes": (GREEN,), "status_codes": (FAINT,), "bar_codes": (FAINT,)},
    "failed": {"mark": "\u2717", "mark_codes": (RED, BOLD), "status_codes": (RED, BOLD), "bar_codes": (RED,)},
    "skipped": {"mark": "\u00b7", "mark_codes": (FAINT,), "status_codes": (FAINT,), "bar_codes": (FAINT,)},
}
FALLBACK = {"mark": "\u00b7", "mark_codes": (), "status_codes": (), "bar_codes": ()}

# ---- derived facts (nothing invented) -------------------------------------
peak = max((secs for _, _, secs in steps), default=0.0) or 1.0
total = sum(secs for _, _, secs in steps)
tally = {}
for _, status, _ in steps:
    tally[status] = tally.get(status, 0) + 1
failed_step = next((name for name, status, _ in steps if status == "failed"), None)
result = "failed" if failed_step else ("ok" if all(s == "ok" for _, s, _ in steps) else "done")

rule = paint("\u2500" * RULE_W, FAINT)

# ---- render ---------------------------------------------------------------
out = []
out.append("")
out.append(GUTTER + paint("deploy report", BOLD))
out.append(GUTTER + rule)
out.append("")

for name, status, secs in steps:
    style = STYLE.get(status, FALLBACK)
    filled = 0 if secs <= 0 else max(1, round(secs / peak * BAR_W))
    bar = paint("\u2501" * filled, *style["bar_codes"]) + paint("\u2500" * (BAR_W - filled), FAINT)

    name_cell = name.ljust(NAME_W)
    if status == "skipped":
        name_cell = paint(name_cell, FAINT)

    out.append(
        GUTTER
        + paint(style["mark"], *style["mark_codes"])
        + "  "
        + name_cell
        + "  "
        + paint(status.ljust(STATUS_W), *style["status_codes"])
        + "  "
        + paint(("%.1fs" % secs).rjust(DUR_W), FAINT if status == "skipped" else DIM)
        + "   "
        + bar
    )

out.append("")
out.append(GUTTER + rule)

counts = ", ".join("%d %s" % (tally[k], k) for k in ("ok", "failed", "skipped") if k in tally)
sep = paint("  \u00b7  ", FAINT)
summary = [
    paint("result", FAINT) + "  " + paint(result, RED, BOLD) if result == "failed" else paint("result", FAINT) + "  " + paint(result, GREEN, BOLD)
]
if failed_step:
    summary.append(paint("stopped at ", FAINT) + failed_step)
summary.append(paint(counts, FAINT))
summary.append(paint("%.1fs total" % total, FAINT))

out.append(GUTTER + sep.join(summary))
out.append("")

print("\n".join(out))
