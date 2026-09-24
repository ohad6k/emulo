#!/usr/bin/env python3
"""Print a deploy report: 5 steps, each with a status and duration, then the result."""

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

USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def style(text, *codes):
    if not USE_COLOR or not codes:
        return text
    return "\033[" + ";".join(codes) + "m" + text + "\033[0m"


BOLD = "1"
DIM = "2"
GREEN = "32"
RED = "31"
YELLOW = "33"

STATUS = {
    "ok": ("ok", (GREEN,)),
    "failed": ("FAILED", (RED, BOLD)),
    "skipped": ("skipped", (DIM,)),
}

# Column layout (fits in 100 columns):
#   #  step                       status    duration  note
COL_NUM = 3
COL_STEP = 26
COL_STATUS = 9
COL_DUR = 9


def row(num, name, status, dur, note=""):
    return "  ".join(
        [
            num.rjust(COL_NUM),
            name.ljust(COL_STEP),
            status.ljust(COL_STATUS),
            dur.rjust(COL_DUR),
            note,
        ]
    ).rstrip()


def main():
    rule = style("─" * WIDTH, DIM)
    first_failure = next((n for n, s, _ in steps if s == "failed"), None)

    print(style("Deploy report", BOLD))
    print(rule)
    print(style(row("#", "Step", "Status", "Duration", "Note"), DIM))

    for i, (name, status, secs) in enumerate(steps, start=1):
        label, codes = STATUS[status]
        dur = "%.1fs" % secs
        note = ""
        if status == "skipped":
            dur = style(dur, DIM)
            if first_failure:
                note = style('not run because "%s" failed' % first_failure, DIM)
        elif status == "failed":
            note = style("see the test output above this report", RED)
        # pad the label before styling so the ANSI codes do not break alignment
        line = row(str(i), name, label.ljust(COL_STATUS), dur.rjust(COL_DUR), note)
        if USE_COLOR:
            line = line.replace(label.ljust(COL_STATUS), style(label.ljust(COL_STATUS), *codes), 1)
        print(line)

    print(rule)

    passed = sum(1 for _, s, _ in steps if s == "ok")
    failed = sum(1 for _, s, _ in steps if s == "failed")
    skipped = sum(1 for _, s, _ in steps if s == "skipped")
    total_secs = sum(secs for _, _, secs in steps)
    result = "failed" if failed else "ok"

    result_label = style("FAILED", RED, BOLD) if result == "failed" else style("OK", GREEN, BOLD)
    print(
        "Result: %s   %d passed, %d failed, %d skipped   %.1fs total"
        % (result_label, passed, failed, skipped, total_secs)
    )

    if result == "failed":
        print()
        print('Next: fix "%s", then run the deploy again. Skipped steps run once it passes.' % first_failure)

    sys.exit(1 if result == "failed" else 0)


if __name__ == "__main__":
    main()
