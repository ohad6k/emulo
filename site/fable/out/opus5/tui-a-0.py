import os
import sys

WIDTH = 100
NAME_W = 24
STATUS_W = 9
BAR_W = 44
TIME_W = 8
INDENT = "  "
RULE_W = len(INDENT) + 2 + NAME_W + STATUS_W + BAR_W + 1 + TIME_W

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

RESULT = "failed"


def _color_enabled():
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM", "") == "dumb":
        return False
    return sys.stdout.isatty()


if _color_enabled():
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    GREY = "\033[90m"
else:
    RESET = BOLD = DIM = GREEN = RED = GREY = ""


STYLES = {
    "ok": ("\u2714", "ok", GREEN),
    "failed": ("\u2716", "failed", RED),
    "skipped": ("\u25cb", "skipped", GREY),
}


def paint(text, *codes):
    if not codes or not any(codes):
        return text
    return "".join(codes) + text + RESET


def duration(secs):
    return "{:.1f}s".format(secs)


def truncate(text, width):
    if len(text) <= width:
        return text
    return text[: width - 1] + "\u2026"


def bar(secs, longest, color):
    if longest <= 0 or secs <= 0:
        return paint("\u2500" * BAR_W, GREY, DIM)
    filled = int(round(secs / longest * BAR_W))
    filled = max(1, min(BAR_W, filled))
    track = paint("\u2501" * filled, color)
    rest = paint("\u2500" * (BAR_W - filled), GREY, DIM)
    return track + rest


def main():
    longest = max(secs for _, _, secs in steps)
    total = sum(secs for _, _, secs in steps)
    counts = {"ok": 0, "failed": 0, "skipped": 0}
    for _, status, _ in steps:
        counts[status] = counts.get(status, 0) + 1

    heading = paint("DEPLOY REPORT", BOLD)
    meta = paint(
        "{} steps  \u00b7  {} elapsed".format(len(steps), duration(total)), GREY, DIM
    )
    pad = RULE_W - len("DEPLOY REPORT") - len("{} steps  \u00b7  {} elapsed".format(len(steps), duration(total)))
    pad = max(2, pad)

    print()
    print(INDENT + heading + " " * pad + meta)
    print(INDENT + paint("\u2500" * RULE_W, GREY, DIM))

    failed_index = None
    for i, (name, status, secs) in enumerate(steps):
        glyph, label, color = STYLES.get(status, ("\u2022", status, ""))
        if status == "failed":
            failed_index = i

        cell_name = truncate(name, NAME_W - 1).ljust(NAME_W)
        cell_status = label.ljust(STATUS_W)
        cell_time = (duration(secs) if secs > 0 else "\u2013").rjust(TIME_W)

        if status == "skipped":
            row = (
                paint(glyph + " ", GREY, DIM)
                + paint(cell_name, GREY, DIM)
                + paint(cell_status, GREY, DIM)
                + bar(secs, longest, color)
                + " "
                + paint(cell_time, GREY, DIM)
            )
        else:
            row = (
                paint(glyph + " ", color)
                + cell_name
                + paint(cell_status, color)
                + bar(secs, longest, color)
                + " "
                + paint(cell_time, BOLD if status == "failed" else "")
            )
        print(INDENT + row)

        if status == "failed" and i + 1 < len(steps):
            note = "\u2514\u2500 pipeline stopped here; remaining steps skipped"
            print(INDENT + "  " + paint(note, GREY, DIM))

    print(INDENT + paint("\u2500" * RULE_W, GREY, DIM))

    if RESULT == "failed":
        verdict = paint(" FAILED ", BOLD, RED)
        glyph = paint("\u2716", RED)
    else:
        verdict = paint(" PASSED ", BOLD, GREEN)
        glyph = paint("\u2714", GREEN)

    breakdown = "{} ok  \u00b7  {} failed  \u00b7  {} skipped  \u00b7  {} total".format(
        counts.get("ok", 0),
        counts.get("failed", 0),
        counts.get("skipped", 0),
        duration(total),
    )
    tail = ""
    if failed_index is not None:
        tail = "  \u2014  {} failed after {}".format(
            steps[failed_index][0], duration(steps[failed_index][2])
        )

    print(INDENT + glyph + verdict + paint(breakdown + tail, GREY, DIM))
    print()


if __name__ == "__main__":
    main()
