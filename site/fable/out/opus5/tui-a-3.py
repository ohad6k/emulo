#!/usr/bin/env python3
"""Deploy report: a compact, aligned summary of a five-step pipeline."""

import sys

WIDTH = 100
NAME_W = 26
STATUS_W = 10
DUR_W = 8
BAR_W = WIDTH - (4 + NAME_W + STATUS_W + DUR_W + 3)

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

RESULT = "failed"

COLOR = sys.stdout.isatty()


def sgr(*codes):
    return "\033[" + ";".join(str(c) for c in codes) + "m" if COLOR else ""


RESET = sgr(0)
BOLD = sgr(1)
DIM = sgr(2)
GREEN = sgr(32)
RED = sgr(31)
GREY = sgr(90)
BADGE_FAIL = sgr(1, 41, 97)
BADGE_OK = sgr(1, 42, 30)

STYLES = {
    "ok": (GREEN, "\u2714", GREEN),
    "failed": (RED, "\u2716", RED),
    "skipped": (GREY, "\u2013", GREY),
}


def paint(text, style):
    """Colorize without disturbing the caller's width math."""
    return f"{style}{text}{RESET}" if style else text


def cell(text, width, style="", align="left"):
    pad = " " * max(0, width - len(text))
    return pad + paint(text, style) if align == "right" else paint(text, style) + pad


def bar(fraction, width):
    """Proportional bar with eighth-block precision, padded to `width`."""
    blocks = " \u258f\u258e\u258d\u258c\u258b\u258a\u2589\u2588"
    exact = max(0.0, fraction) * width
    full = int(exact)
    out = "\u2588" * full
    partial = int(round((exact - full) * 8))
    if partial:
        out += blocks[partial]
    elif not out and exact > 0:
        out = blocks[1]
    return out[:width].ljust(width)


def rule(char="\u2500"):
    return paint(char * WIDTH, DIM)


tally = {"ok": 0, "failed": 0, "skipped": 0}
for _, status, _ in steps:
    tally[status] = tally.get(status, 0) + 1

total_secs = sum(secs for _, _, secs in steps)
longest = max((secs for _, _, secs in steps), default=0.0)

summary = "  \u00b7  ".join(
    f"{tally['ok']} ok",
    ) if False else "  \u00b7  ".join(
    [f"{tally['ok']} ok", f"{tally['failed']} failed", f"{tally['skipped']} skipped"]
)

print()
title = "DEPLOY REPORT"
print(paint(title, BOLD) + " " * max(1, WIDTH - len(title) - len(summary)) + paint(summary, DIM))
print(rule())

for index, (name, status, secs) in enumerate(steps, start=1):
    text_style, mark, bar_style = STYLES.get(status, ("", "\u00b7", ""))

    leader_len = max(1, NAME_W - len(name) - 2)
    name_cell = (
        paint(name, "" if status != "skipped" else GREY)
        + " "
        + paint("\u00b7" * leader_len, DIM)
        + " "
    )

    duration = f"{secs:.1f}s"
    dur_cell = cell(duration, DUR_W, DIM if secs == 0 else "", align="right")

    if secs > 0 and longest > 0:
        graph = paint(bar(secs / longest, BAR_W), bar_style)
    else:
        graph = paint("not run".ljust(BAR_W), DIM)

    print(
        " "
        + paint(mark, text_style)
        + "  "
        + name_cell
        + cell(status, STATUS_W, text_style)
        + dur_cell
        + "  "
        + graph
    )

print(rule())

if RESULT == "ok":
    badge, badge_style, tail = " PASSED ", BADGE_OK, "all steps completed"
else:
    badge, badge_style, tail = " FAILED ", BADGE_FAIL, "run tests failed \u2014 build and deploy were not attempted"

footer_right = f"{total_secs:.1f}s total"
left = paint(badge, badge_style) + "  " + tail
visible_left = len(badge) + 2 + len(tail)
print(left + " " * max(1, WIDTH - visible_left - len(footer_right)) + paint(footer_right, DIM))
print()
