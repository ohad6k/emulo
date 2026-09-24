#!/usr/bin/env python3
"""Deploy report — a compact, aligned summary of a five-step deploy."""

import os
import sys

WIDTH = 100
MARGIN = "  "
INNER = WIDTH - 2 * len(MARGIN)

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

RESULT = "failed"

# ---------------------------------------------------------------- capabilities

USE_COLOR = (
    sys.stdout.isatty()
    and os.environ.get("TERM", "") != "dumb"
    and "NO_COLOR" not in os.environ
)

try:
    "─█░✔✖·".encode(sys.stdout.encoding or "ascii")
    UNICODE = True
except (UnicodeEncodeError, LookupError):
    UNICODE = False


def paint(text, *codes):
    if not USE_COLOR or not codes:
        return text
    return "\x1b[" + ";".join(str(c) for c in codes) + "m" + text + "\x1b[0m"


BOLD, DIM = 1, 2
GREEN, RED, GREY = 32, 31, 90

STATUS = {
    #            glyph   ascii   color  bar color
    "ok":      ("\u2714", "OK",  GREEN, GREEN),
    "failed":  ("\u2716", "XX",  RED,   RED),
    "skipped": ("\u00b7", "--",  GREY,  GREY),
}

RULE = ("\u2500" if UNICODE else "-") * INNER
THIN = ("\u2504" if UNICODE else "-") * INNER


def visible_len(text):
    out, i = 0, 0
    while i < len(text):
        if text[i] == "\x1b":
            i = text.find("m", i) + 1
            continue
        out += 1
        i += 1
    return out


def pad_between(left, right, width=INNER):
    gap = max(1, width - visible_len(left) - visible_len(right))
    return left + " " * gap + right


# ---------------------------------------------------------------------- pieces

BAR_W = 40


def bar(fraction):
    """A proportional bar, with sub-cell precision where Unicode allows."""
    if not UNICODE:
        n = int(round(fraction * BAR_W))
        return "#" * n + "." * (BAR_W - n)

    full, empty = "\u2588", "\u2591"
    eighths = " \u258f\u258e\u258d\u258c\u258b\u258a\u2589"
    exact = fraction * BAR_W
    whole = int(exact)
    out = full * whole
    used = whole
    part = int((exact - whole) * 8)
    if part and used < BAR_W:
        out += eighths[part]
        used += 1
    return (out + empty * (BAR_W - used))[:BAR_W]


def duration(secs, status):
    if status == "skipped":
        return "\u2014" if UNICODE else "-"
    return "{:.1f}s".format(secs)


# ----------------------------------------------------------------------- print

longest = max(secs for _, _, secs in steps) or 1.0
total = sum(secs for _, _, secs in steps)
counts = {}
for _, status, _ in steps:
    counts[status] = counts.get(status, 0) + 1

sep = " \u00b7 " if UNICODE else " | "
tally = sep.join(
    paint("{} {}".format(counts[s], s), STATUS[s][2])
    for s in ("ok", "failed", "skipped")
    if s in counts
)

print()
print(MARGIN + pad_between(paint("DEPLOY REPORT", BOLD), tally))
print(MARGIN + paint(RULE, DIM))

for i, (name, status, secs) in enumerate(steps, 1):
    glyph, ascii_glyph, color, bar_color = STATUS[status]
    mark = glyph if UNICODE else ascii_glyph

    index = paint("{}/{}".format(i, len(steps)), DIM)
    label = name if status != "skipped" else paint(name, DIM)
    track = "" if status == "skipped" else paint(bar(secs / longest), bar_color)

    left = "{}  {}  {}".format(
        index,
        paint(mark.ljust(2 if not UNICODE else 1), color),
        label,
    )
    left += " " * max(1, 34 - visible_len(left))
    left += paint(status.ljust(8), color if status != "skipped" else GREY)
    left += track

    print(MARGIN + pad_between(left, duration(secs, status).rjust(7)))

print(MARGIN + paint(THIN, DIM))

failed = [name for name, status, _ in steps if status == "failed"]
skipped = counts.get("skipped", 0)

verdict_glyph, verdict_ascii, verdict_color, _ = STATUS[RESULT]
verdict = "{}  {}".format(
    verdict_glyph if UNICODE else verdict_ascii,
    RESULT.upper(),
)

detail = []
if failed:
    detail.append("stopped at " + failed[0])
if skipped:
    detail.append("{} step{} not run".format(skipped, "" if skipped == 1 else "s"))
detail.append("{:.1f}s total".format(total))

print(
    MARGIN
    + pad_between(
        paint(verdict, BOLD, verdict_color),
        paint(sep.join(detail), DIM),
    )
)
print()
