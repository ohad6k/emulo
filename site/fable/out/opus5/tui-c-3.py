#!/usr/bin/env python3
"""Deploy report.

Prints the five deploy steps with status and duration, the verdict above the
fold, and what to do next. stdout only, one pass, no timing of its own.
Laid out for a 100-column terminal.
"""

import sys

STEPS = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

NAME_W = 24
STATUS_W = 9
TIME_W = 9
BAR_W = 40
RULE_W = 2 + 2 + NAME_W + STATUS_W + TIME_W + 2 + BAR_W

COLOR = sys.stdout.isatty()

STATUS_COLOR = {"ok": "32", "failed": "31", "skipped": "2"}


def encodable(text):
    """True when the current stdout encoding can carry this text."""
    try:
        text.encode(sys.stdout.encoding or "ascii")
        return True
    except (UnicodeEncodeError, LookupError):
        return False


if encodable("✓✗·─█"):
    MARK = {"ok": "✓", "failed": "✗", "skipped": "·"}
    RULE_CHAR, BAR_CHAR = "─", "█"
else:
    MARK = {"ok": "+", "failed": "x", "skipped": "-"}
    RULE_CHAR, BAR_CHAR = "-", "#"


def paint(text, code):
    if not COLOR or not code:
        return text
    return "\033[" + code + "m" + text + "\033[0m"


def seconds(value):
    return "%.1fs" % value


def join(names):
    """'a', 'a and b', 'a, b and c'."""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def bar(value, longest):
    if value <= 0 or longest <= 0:
        return ""
    filled = max(1, int(round(value / longest * BAR_W)))
    return BAR_CHAR * filled


def main():
    failed = [name for name, status, _ in STEPS if status == "failed"]
    skipped = [name for name, status, _ in STEPS if status == "skipped"]
    ran = [step for step in STEPS if step[1] != "skipped"]
    longest = max(secs for _, _, secs in STEPS)
    total = sum(secs for _, _, secs in STEPS)
    result = "failed" if failed else "ok"

    # Verdict first: a reader who sees only two lines still knows what happened.
    print(paint("deploy report", "1"))
    if failed:
        first = failed[0]
        position = [name for name, _, _ in STEPS].index(first) + 1
        secs = [s for n, _, s in STEPS if n == first][0]
        headline = "failed at step %d of %d: %s (%s)." % (
            position,
            len(STEPS),
            first,
            seconds(secs),
        )
        if skipped:
            headline += " " + join(skipped) + " did not run."
    else:
        headline = "all %d steps ok in %s." % (len(STEPS), seconds(total))
    print(paint(headline, "31" if failed else "32"))
    print()

    header = "  " + "  " + "step".ljust(NAME_W) + "status".ljust(STATUS_W)
    header += "duration".rjust(TIME_W)
    print(paint(header, "2"))
    print(paint("  " + RULE_CHAR * (RULE_W - 2), "2"))

    for name, status, secs in STEPS:
        code = STATUS_COLOR[status]
        row = "  "
        row += paint(MARK[status], code) + " "
        row += name.ljust(NAME_W)
        row += paint(status.ljust(STATUS_W), code)
        row += seconds(secs).rjust(TIME_W)
        row += "  " + paint(bar(secs, longest), code)
        print(row.rstrip())

    print(paint("  " + RULE_CHAR * (RULE_W - 2), "2"))
    totals = "  " + ("%d steps" % len(STEPS)).ljust(2 + NAME_W + STATUS_W)
    totals += seconds(total).rjust(TIME_W)
    totals += "  " + "%d run, %d skipped" % (len(ran), len(skipped))
    print(paint(totals, "2"))
    print()

    print("result: " + paint(result, STATUS_COLOR[result]))
    if failed:
        check = "what to check: the %s output above this report. " % join(failed)
        check += "Fix it and re-run; %s have not run yet." % join(skipped) if len(
            skipped
        ) > 1 else check + "Fix it and re-run."
        print(check)


if __name__ == "__main__":
    main()
