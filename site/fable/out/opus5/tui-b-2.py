#!/usr/bin/env python3
"""deploy report — single-pass terminal summary. writes to stdout and exits."""

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

RESET = "\x1b[0m"
BRIGHT = "\x1b[38;5;255m"
TEXT = "\x1b[38;5;252m"
MUTED = "\x1b[38;5;245m"
FAINT = "\x1b[38;5;239m"
BAD = "\x1b[38;5;203m"

GLYPH_W = 3
NAME_W = 24
STATUS_W = 9
BAR_W = 30
GAP = 2
DUR_W = 8
WIDTH = GLYPH_W + NAME_W + STATUS_W + BAR_W + GAP + DUR_W
GUTTER = "  "

GLYPH = {"ok": "\u2713", "failed": "\u2717", "skipped": "\u00b7"}


def paint(text, color):
    return color + text + RESET


def rule(char="\u2500", color=FAINT):
    return GUTTER + paint(char * WIDTH, color)


def spread(left, right):
    """left text and right text on one line, flush to the report width."""
    pad = max(1, WIDTH - len(left) - len(right))
    return left + " " * pad + right


def bar_cells(secs, longest):
    if longest <= 0 or secs <= 0:
        return 0
    return max(1, int(round(secs / longest * BAR_W)))


def render_row(name, status, secs, longest):
    glyph = GLYPH.get(status, "\u00b7")
    duration = "{:.1f}s".format(secs)
    fill = "\u2588" * bar_cells(secs, longest)

    if status == "failed":
        glyph_color, name_color, status_color, bar_color, dur_color = (
            BAD,
            BRIGHT,
            BAD,
            BAD,
            BRIGHT,
        )
    elif status == "ok":
        glyph_color, name_color, status_color, bar_color, dur_color = (
            TEXT,
            TEXT,
            MUTED,
            FAINT,
            MUTED,
        )
    else:
        glyph_color, name_color, status_color, bar_color, dur_color = (
            FAINT,
            FAINT,
            FAINT,
            FAINT,
            FAINT,
        )

    return (
        GUTTER
        + paint(glyph.ljust(GLYPH_W), glyph_color)
        + paint(name.ljust(NAME_W), name_color)
        + paint(status.ljust(STATUS_W), status_color)
        + paint(fill.ljust(BAR_W), bar_color)
        + " " * GAP
        + paint(duration.rjust(DUR_W), dur_color)
    )


def main():
    longest = max(secs for _, _, secs in steps)
    total = sum(secs for _, _, secs in steps)
    counts = {"ok": 0, "failed": 0, "skipped": 0}
    for _, status, _ in steps:
        counts[status] = counts.get(status, 0) + 1

    failed_names = [name for name, status, _ in steps if status == "failed"]
    result = "failed" if failed_names else "ok"

    out = []
    out.append("")
    out.append(
        GUTTER
        + spread(
            paint("deploy report", BRIGHT),
            paint("{} steps  \u00b7  {:.1f}s".format(len(steps), total), FAINT),
        )
    )
    out.append(rule())
    out.append("")

    for name, status, secs in steps:
        out.append(render_row(name, status, secs, longest))

    out.append("")
    out.append(rule())

    tally = "{} ok  \u00b7  {} failed  \u00b7  {} skipped".format(
        counts.get("ok", 0), counts.get("failed", 0), counts.get("skipped", 0)
    )
    verdict_color = BAD if result == "failed" else BRIGHT
    left = (
        GUTTER
        + paint("result".ljust(GLYPH_W + 5), MUTED)
        + paint(result, verdict_color)
    )
    if failed_names:
        left += paint("  \u00b7  stopped at " + failed_names[0], MUTED)
    right = paint(tally + "  \u00b7  {:.1f}s total".format(total), FAINT)
    pad = max(1, WIDTH + len(GUTTER) - _visible_len(left) - _visible_len(right))
    out.append(left + " " * pad + right)
    out.append("")

    print("\n".join(out))


def _visible_len(s):
    """length of a string ignoring ANSI escape sequences."""
    count = 0
    i = 0
    while i < len(s):
        if s[i] == "\x1b":
            while i < len(s) and s[i] != "m":
                i += 1
            i += 1
            continue
        count += 1
        i += 1
    return count


if __name__ == "__main__":
    main()
