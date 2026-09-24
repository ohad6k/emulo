#!/usr/bin/env python3
"""Print the deploy report: one line per step, its status, how long it took, and the outcome.

Same five steps and the same numbers as before, laid out so the failure is findable at a glance.
Assumes a terminal 100 columns wide. Colour is used only when stdout is a terminal.
"""

import sys

STEPS = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

BAR_WIDTH = 34
INDENT = "  "

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"

STATUS_COLOUR = {"ok": GREEN, "failed": RED, "skipped": DIM}

COLOUR = sys.stdout.isatty()


def paint(text, code):
    """Wrap text in an ANSI code, or return it unchanged when colour is off."""
    if not COLOUR or not code:
        return text
    return code + text + RESET


def bar(seconds, longest, code):
    """A proportional bar for one step. Zero-length steps get an empty track."""
    track = "\u2591" * BAR_WIDTH
    if seconds <= 0 or longest <= 0:
        return paint(track, DIM)
    filled = max(1, round(seconds / longest * BAR_WIDTH))
    return paint("\u2588" * filled, code) + paint("\u2591" * (BAR_WIDTH - filled), DIM)


def main():
    status_width = max(len(status) for _, status, _ in STEPS)
    name_width = max(len(name) for name, _, _ in STEPS)
    longest = max(seconds for _, _, seconds in STEPS)
    total = sum(seconds for _, _, seconds in STEPS)

    counts = {"ok": 0, "failed": 0, "skipped": 0}
    for _, status, _ in STEPS:
        counts[status] = counts.get(status, 0) + 1

    failed = [name for name, status, _ in STEPS if status == "failed"]
    skipped = [name for name, status, _ in STEPS if status == "skipped"]
    result = "failed" if failed else "ok"

    line_width = (
        len(INDENT) + status_width + 2 + name_width + 2 + BAR_WIDTH + 2 + 7
    )

    print()
    print(INDENT + paint("deploy report", BOLD))
    print(INDENT + paint("\u2500" * (line_width - len(INDENT)), DIM))

    for name, status, seconds in STEPS:
        code = STATUS_COLOUR.get(status, "")
        row = "".join(
            [
                INDENT,
                paint(status.ljust(status_width), code),
                "  ",
                name.ljust(name_width),
                "  ",
                bar(seconds, longest, code),
                "  ",
                ("%.1fs" % seconds).rjust(7),
            ]
        )
        print(row)

    print(INDENT + paint("\u2500" * (line_width - len(INDENT)), DIM))
    print(
        INDENT
        + paint(
            "%d steps: %d ok, %d failed, %d skipped%s%.1fs total"
            % (
                len(STEPS),
                counts["ok"],
                counts["failed"],
                counts["skipped"],
                " " * 3,
                total,
            ),
            DIM,
        )
    )
    print()

    result_code = RED if result == "failed" else GREEN
    print(INDENT + paint("result: " + result, BOLD + result_code))

    if failed:
        print(
            INDENT
            + "%s failed after %.1fs."
            % (
                " and ".join(failed),
                sum(s for n, st, s in STEPS if st == "failed"),
            )
        )
    if skipped:
        print(
            INDENT
            + "%s did not run."
            % " and ".join(skipped)
        )
    print()


if __name__ == "__main__":
    main()
