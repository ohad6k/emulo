#!/usr/bin/env python3
"""Render the deploy report as a scannable table.

Same five steps, same statuses, same durations, same final result as the
original script — laid out so the failing step is findable at a glance.
Prints once to stdout and exits. Colour is dropped when stdout is not a
terminal, so piping to a file or a log collector stays readable.
"""

import sys

STEPS = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

TITLE = "deploy report"
BAR_CELLS = 34

SGR = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "grey": "\033[90m",
    "invert": "\033[7m",
}

# mark and colour per status. Status words are printed exactly as the data
# holds them, so a reader can search the log for "failed".
STATUS_STYLE = {
    "ok": ("+", "green"),
    "failed": ("x", "red"),
    "skipped": ("-", "grey"),
}

USE_COLOUR = sys.stdout.isatty()


def paint(text, *names):
    """Wrap text in SGR codes. Pad before painting, never after."""
    if not USE_COLOUR or not names:
        return text
    return "".join(SGR[n] for n in names) + text + SGR["reset"]


def duration(secs):
    return "{:.1f}s".format(secs)


def bar(secs, longest, cells=BAR_CELLS):
    """Length proportional to the slowest step. Zero seconds draws nothing."""
    if longest <= 0 or secs <= 0:
        return ""
    units = secs / longest * cells
    full = int(units)
    out = "\u2588" * full
    if units - full >= 0.5:
        out += "\u258c"
    return out or "\u258c"


def join_names(names):
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def main():
    name_w = max(len(name) for name, _, _ in STEPS)
    status_w = max(len(status) for _, status, _ in STEPS)
    dur_w = max(len(duration(secs)) for _, _, secs in STEPS)
    longest = max(secs for _, _, secs in STEPS)
    total = sum(secs for _, _, secs in STEPS)

    rule_w = 2 + 1 + 2 + name_w + 2 + status_w + 2 + dur_w + 2 + BAR_CELLS
    rule = "\u2500" * rule_w

    failed = [name for name, status, _ in STEPS if status == "failed"]
    skipped = [name for name, status, _ in STEPS if status == "skipped"]
    result = "failed" if failed else "ok"
    result_colour = "red" if failed else "green"

    lines = []

    # Header: title on the left, the verdict on the right, so the answer is
    # visible without reading the table.
    badge = " " + result.upper() + " "
    gap = rule_w - len(TITLE) - len(badge)
    lines.append(
        paint(TITLE, "bold") + " " * max(gap, 1) + paint(badge, result_colour, "invert")
    )
    lines.append(paint(rule, "grey"))

    for name, status, secs in STEPS:
        mark, colour = STATUS_STYLE[status]
        row = (
            "  "
            + paint(mark, colour, "bold")
            + "  "
            + name.ljust(name_w)
            + "  "
            + paint(status.ljust(status_w), colour)
            + "  "
            + duration(secs).rjust(dur_w)
            + "  "
            + paint(bar(secs, longest), colour)
        )
        lines.append(row.rstrip())

    lines.append(paint(rule, "grey"))

    detail = ""
    if failed:
        detail = "{} failed".format(join_names(failed))
        if skipped:
            detail += "; {} skipped".format(join_names(skipped))
    lines.append(
        "  result: "
        + paint(result, result_colour, "bold")
        + (paint("  \u2014  " + detail, "grey") if detail else "")
    )
    lines.append(
        paint(
            "  {} steps, {} total".format(len(STEPS), duration(total)),
            "grey",
        )
    )

    print("\n".join(lines))


if __name__ == "__main__":
    main()
