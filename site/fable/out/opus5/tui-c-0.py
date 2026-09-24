#!/usr/bin/env python3
"""Deploy report.

Prints the outcome of a deploy run once, to stdout, and exits.
Same information as before: five steps, each step's status and duration,
and the final result. Laid out for a 100-column terminal.
"""

import sys

STEPS = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

RESULT = "failed"

WIDTH = 100
NAME_W = 22
STATUS_W = 9
TIME_W = 8
BAR_W = 50

# --- terminal capabilities ---------------------------------------------------


def use_color():
    return sys.stdout.isatty()


def use_unicode():
    enc = (sys.stdout.encoding or "").lower()
    return "utf" in enc


COLOR = use_color()
UNICODE = use_unicode()

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
GREEN = "\x1b[32m"
RED = "\x1b[31m"
GREY = "\x1b[90m"
RED_BADGE = "\x1b[41m\x1b[97m\x1b[1m"
GREEN_BADGE = "\x1b[42m\x1b[30m\x1b[1m"


def paint(text, *codes):
    if not COLOR or not codes:
        return text
    return "".join(codes) + text + RESET


# --- glyphs and rules --------------------------------------------------------

GLYPHS = {
    "ok": ("\u2713", "+"),
    "failed": ("\u2717", "x"),
    "skipped": ("\u2013", "-"),
}

STYLES = {
    "ok": (GREEN,),
    "failed": (RED, BOLD),
    "skipped": (GREY,),
}

RULE_CHAR = "\u2500" if UNICODE else "-"
BAR_FULL = "\u2588" if UNICODE else "#"
BAR_PARTS = "\u258f\u258e\u258d\u258c\u258b\u258a\u2589"


def glyph(status):
    full, ascii_alt = GLYPHS[status]
    return full if UNICODE else ascii_alt


def rule():
    return paint(RULE_CHAR * WIDTH, DIM)


def bar(seconds, longest):
    """A proportional bar for the step's duration."""
    if seconds <= 0 or longest <= 0:
        return ""
    units = (seconds / longest) * BAR_W
    full = int(units)
    out = BAR_FULL * full
    if UNICODE:
        remainder = units - full
        if remainder >= 0.125:
            out += BAR_PARTS[int(remainder * 8) - 1]
    elif units - full >= 0.5:
        out += BAR_FULL
    return out


def spread(left, right):
    """Left text at column 0, right text flush to column WIDTH."""
    gap = WIDTH - len(left) - len(right)
    if gap < 1:
        gap = 1
    return left + " " * gap + right


def seconds(value):
    return "{:.1f}s".format(value)


# --- report ------------------------------------------------------------------


def main():
    longest = max(secs for _, _, secs in STEPS)
    total = sum(secs for _, _, secs in STEPS)
    counts = {"ok": 0, "failed": 0, "skipped": 0}
    for _, status, _ in STEPS:
        counts[status] += 1

    failed = [name for name, status, _ in STEPS if status == "failed"]
    passing = RESULT == "ok"

    sep = " \u00b7 " if UNICODE else " | "

    print()
    print(
        spread(
            paint("deploy report", BOLD),
            paint("{} steps".format(len(STEPS)) + sep + seconds(total), DIM),
        )
    )
    print(rule())

    for name, status, secs in STEPS:
        mark = paint(glyph(status), *STYLES[status])
        label = name.ljust(NAME_W)
        if status == "failed":
            label = paint(name, BOLD).ljust(NAME_W + (len(paint("", BOLD)) if COLOR else 0))
            label = paint(name, BOLD) + " " * (NAME_W - len(name))
        word = paint(status.ljust(STATUS_W), *STYLES[status])
        took = seconds(secs).rjust(TIME_W)
        took = paint(took, DIM) if status == "skipped" else took
        meter = paint(bar(secs, longest), *STYLES[status])
        print(" {} {}{}{}  {}".format(mark, label, word, took, meter).rstrip())

    print(rule())

    tally = sep.join(
        [
            "{} ok".format(counts["ok"]),
            "{} failed".format(counts["failed"]),
            "{} skipped".format(counts["skipped"]),
        ]
    )
    print(spread(" " + paint(tally, DIM), paint("total " + seconds(total), DIM)))
    print()

    if passing:
        badge = paint(" PASSED ", GREEN_BADGE)
        detail = "all {} steps ran in {}".format(len(STEPS), seconds(total))
    else:
        badge = paint(" FAILED ", RED_BADGE)
        if failed:
            stopped = failed[0]
            after = next(s for n, _, s in STEPS if n == stopped)
            skipped = [n for n, st, _ in STEPS if st == "skipped"]
            detail = "{} failed after {}".format(stopped, seconds(after))
            if skipped:
                detail += "; {} did not run".format(" and ".join(skipped))
        else:
            detail = "no step reported a failure"

    print(" {}  {}".format(badge, detail))
    print()


if __name__ == "__main__":
    main()
