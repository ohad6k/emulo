#!/usr/bin/env python3
"""Deploy report.

Prints the outcome of a deploy run: the five steps, each step's status and
duration, and the final result. Runs once and exits.
"""

import os
import sys

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

WIDTH = 100

# Use colour only when stdout is a terminal and NO_COLOR is not set.
USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def paint(text, code):
    if not USE_COLOR:
        return text
    return "\033[%sm%s\033[0m" % (code, text)


BOLD = "1"
DIM = "2"
GREEN = "32"
RED = "31"
YELLOW = "33"

# Glyph, colour, and label for each status. The label is the status word
# from the run, unchanged, so it can be searched for.
STATUS = {
    "ok": ("\u2714", GREEN, "ok"),
    "failed": ("\u2718", RED, "failed"),
    "skipped": ("\u2013", DIM, "skipped"),
}


def fmt_secs(secs):
    return "%.1fs" % secs


def main():
    total = sum(secs for _, _, secs in steps)
    failed = [name for name, status, _ in steps if status == "failed"]
    skipped = [name for name, status, _ in steps if status == "skipped"]
    passed = [name for name, status, _ in steps if status == "ok"]
    result = "failed" if failed else "ok"

    rule = "\u2500" * WIDTH

    # Column widths.
    idx_w = len(str(len(steps)))
    name_w = max(len(name) for name, _, _ in steps)
    status_w = max(len(label) for _, _, label in STATUS.values())
    secs_w = max(len(fmt_secs(secs)) for _, _, secs in steps)

    print(paint("deploy report", BOLD))
    print(paint(rule, DIM))

    for i, (name, status, secs) in enumerate(steps, start=1):
        glyph, colour, label = STATUS[status]
        idx = str(i).rjust(idx_w)
        line = "  %s %s  %s  %s  %s" % (
            paint(glyph, colour),
            paint(idx, DIM),
            name.ljust(name_w),
            paint(label.ljust(status_w), colour),
            paint(fmt_secs(secs).rjust(secs_w), DIM),
        )
        print(line)

    print(paint(rule, DIM))

    # Summary: what happened, then what it means.
    summary = "%d ok, %d failed, %d skipped in %s" % (
        len(passed),
        len(failed),
        len(skipped),
        fmt_secs(total),
    )
    print("  " + paint(summary, DIM))

    if failed:
        first = failed[0]
        print("  " + paint("failed at: %s" % first, RED))
        if skipped:
            print("  " + paint("not run:   %s" % ", ".join(skipped), DIM))

    result_colour = RED if failed else GREEN
    print()
    print("  " + paint("result: %s" % result, BOLD + ";" + result_colour))

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
