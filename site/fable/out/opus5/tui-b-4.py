steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

RESULT = "failed"

# ---- presentation ---------------------------------------------------------

import os
import sys

COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None and os.environ.get("TERM") != "dumb"


def c(text, *codes):
    if not COLOR or not codes:
        return text
    return "\033[" + ";".join(codes) + "m" + text + "\033[0m"


BOLD = "1"
DIM = "2"
RED = "31"

MARGIN = "  "
NAME_W = 22
STATUS_W = 8
BAR_W = 40
DUR_W = 7
RULE_W = 1 + 2 + NAME_W + 2 + STATUS_W + 2 + BAR_W + 2 + DUR_W

GLYPH = {"ok": "\u2713", "failed": "\u2717", "skipped": "\u00b7"}

longest = max(secs for _, _, secs in steps) or 1.0
ran = [s for s in steps if s[1] != "skipped"]
total = sum(secs for _, _, secs in steps)
stopped_at = next((name for name, status, _ in steps if status == "failed"), None)

# header
summary = "%d of %d steps ran   %.1fs total" % (len(ran), len(steps), total)
title = "deploy report"
print()
print(MARGIN + c(title, BOLD) + " " * (RULE_W - len(title) - len(summary)) + c(summary, DIM))
print(MARGIN + c("\u2500" * RULE_W, DIM))
print()

# steps
for name, status, secs in steps:
    filled = 0 if status == "skipped" else max(1, round(BAR_W * secs / longest))
    bar = c("\u2501" * filled, RED if status == "failed" else DIM) + c("\u2500" * (BAR_W - filled), DIM)

    if status == "failed":
        glyph = c(GLYPH[status], RED, BOLD)
        label = c(name.ljust(NAME_W), BOLD)
        word = c(status.ljust(STATUS_W), RED)
        dur = c(("%.1fs" % secs).rjust(DUR_W), BOLD)
    elif status == "skipped":
        glyph = c(GLYPH[status], DIM)
        label = c(name.ljust(NAME_W), DIM)
        word = c(status.ljust(STATUS_W), DIM)
        dur = c(("%.1fs" % secs).rjust(DUR_W), DIM)
    else:
        glyph = GLYPH[status]
        label = name.ljust(NAME_W)
        word = c(status.ljust(STATUS_W), DIM)
        dur = ("%.1fs" % secs).rjust(DUR_W)

    print(MARGIN + glyph + "  " + label + "  " + word + "  " + bar + "  " + dur)

print()
print(MARGIN + c("\u2500" * RULE_W, DIM))

# result
line = MARGIN + c("result", DIM) + "  " + c(RESULT, RED, BOLD)
if stopped_at:
    line += c("   stopped at " + stopped_at, DIM)
print(line)
print()
