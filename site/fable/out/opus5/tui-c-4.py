#!/usr/bin/env python3
"""Print the report for one deploy run.

Same data as before: five steps, each step's status, each step's duration,
and the final result. Only the presentation changed.

Reads left to right: the step order, what happened, how long it took, and
how that time compares to the rest of the run. Status is a word, not a
symbol, so a screen reader carries the line. Colour repeats the word, it
never replaces it, and it is dropped when stdout is not a terminal.
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

BAR_W = 28
GUTTER = "  "

USE_COLOR = sys.stdout.isatty()
CODES = {"bold": "1", "dim": "2", "red": "31", "green": "32", "grey": "90"}
STATUS_STYLE = {
    "ok": ("green",),
    "failed": ("bold", "red"),
    "skipped": ("grey",),
}


def style(text, *names):
    """Wrap text in ANSI codes, or return it unchanged outside a terminal."""
    if not USE_COLOR or not names:
        return text
    return "\033[" + ";".join(CODES[n] for n in names) + "m" + text + "\033[0m"


def secs(value):
    return "{:.1f}s".format(value)


def main():
    name_w = max(len(name) for name, _, _ in STEPS)
    status_w = max(len(status) for _, status, _ in STEPS)
    dur_w = max(len(secs(value)) for _, _, value in STEPS)
    index_w = len(str(len(STEPS))) + 1  # "5."

    # Column widths, then the full rule width, computed from plain text so
    # the escape codes never throw the alignment off.
    lead_w = len(GUTTER) + index_w + 1 + name_w + 3
    row_w = lead_w + status_w + 2 + dur_w + 2 + BAR_W

    longest = max(value for _, _, value in STEPS) or 1.0
    total = sum(value for _, _, value in STEPS)
    counts = []
    for status in ("ok", "failed", "skipped"):
        n = sum(1 for _, s, _ in STEPS if s == status)
        if n:
            counts.append("{} {}".format(n, status))
    counts.append(secs(total) + " total")
    summary = " \u00b7 ".join(counts)

    title = "deploy report"
    gap = max(1, row_w - len(title) - len(summary))
    print()
    print(style(title, "bold") + " " * gap + style(summary, "grey"))
    print(style("\u2500" * row_w, "grey"))

    for i, (name, status, value) in enumerate(STEPS, start=1):
        marker = "{}.".format(i).rjust(index_w)
        dots = "." * (name_w + 2 - len(name))
        duration = secs(value).rjust(dur_w)

        if value > 0:
            filled = max(1, round(value / longest * BAR_W))
            bar = style("\u2588" * filled, *STATUS_STYLE[status])
        else:
            bar = ""

        name_field = name if status == "failed" else name
        line = (
            GUTTER
            + style(marker, "grey")
            + " "
            + style(name_field, *(("bold",) if status == "failed" else ()))
            + " "
            + style(dots, "grey")
            + "  "
            + style(status.ljust(status_w), *STATUS_STYLE[status])
            + "  "
            + style(duration, *(("grey",) if value == 0 else ()))
            + "  "
            + bar
        )
        print(line)

    print(style("\u2500" * row_w, "grey"))

    failed = [(i, name, value) for i, (name, s, value) in enumerate(STEPS, start=1) if s == "failed"]
    skipped = [name for name, s, _ in STEPS if s == "skipped"]

    print(GUTTER + style("result: ", "bold") + style(RESULT, *STATUS_STYLE.get(RESULT, ("bold",))))

    if failed:
        i, name, value = failed[0]
        detail = "stopped at step {} of {}, {}, after {}.".format(i, len(STEPS), name, secs(value))
        if skipped:
            detail += " Skipped: " + ", ".join(skipped) + "."
    else:
        detail = "{} steps completed in {}.".format(len(STEPS), secs(total))
    print(GUTTER + style(detail, "grey"))
    print()


if __name__ == "__main__":
    main()
