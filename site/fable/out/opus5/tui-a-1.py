#!/usr/bin/env python3
"""Deploy report: a compact, scannable terminal summary of a build pipeline."""

import sys

STEPS = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

# ---------------------------------------------------------------- layout ----
PAD = 2          # left margin
GLYPH_W = 3      # status glyph + spacing
NAME_W = 26      # step name + dotted leader
STATUS_W = 10    # status word
DUR_W = 8        # duration, right aligned
GAP = 2
BAR_W = 28
WIDTH = PAD + GLYPH_W + NAME_W + STATUS_W + DUR_W + GAP + BAR_W  # 79 of 100 cols

# ----------------------------------------------------------------- color ----
COLOR = sys.stdout.isatty()


def paint(text, *codes):
    if not COLOR or not codes:
        return text
    return "\033[" + ";".join(str(c) for c in codes) + "m" + text + "\033[0m"


DIM, BOLD, RED, GREEN, GREY, WHITE = 2, 1, 31, 32, 90, 97

STYLE = {
    #  glyph, color, bar-color
    "ok":      ("+", GREEN, GREEN),
    "failed":  ("x", RED, RED),
    "skipped": ("-", GREY, GREY),
}


def rule(char="\u2500"):
    return paint(" " * PAD + char * (WIDTH - PAD), DIM)


def main():
    total = sum(secs for _, _, secs in STEPS)
    slowest = max((secs for _, _, secs in STEPS), default=0.0) or 1.0
    counts = {"ok": 0, "failed": 0, "skipped": 0}
    for _, status, _ in STEPS:
        counts[status] = counts.get(status, 0) + 1
    failures = [(n, s) for n, st, s in STEPS if st == "failed"]
    result = "failed" if failures else "ok"

    # ---- header
    title = paint("DEPLOY REPORT", BOLD, WHITE)
    meta = paint(f"{len(STEPS)} steps \u00b7 {total:.1f}s total", DIM)
    plain_len = len("DEPLOY REPORT") + len(f"{len(STEPS)} steps \u00b7 {total:.1f}s total")
    print()
    print(" " * PAD + title + " " * (WIDTH - PAD - plain_len) + meta)
    print(rule())

    # ---- rows
    for name, status, secs in STEPS:
        glyph, color, bar_color = STYLE.get(status, ("?", WHITE, WHITE))

        leader_len = max(NAME_W - len(name) - 2, 1)
        name_cell = (
            paint(name, BOLD if status == "failed" else 0)
            + " "
            + paint("\u00b7" * leader_len, DIM)
            + " "
        )

        if secs > 0:
            filled = max(1, round(BAR_W * secs / slowest))
            bar = paint("\u2588" * filled, bar_color) + paint(
                "\u2591" * (BAR_W - filled), DIM
            )
        else:
            bar = paint("\u2591" * BAR_W, DIM)

        print(
            " " * PAD
            + paint(glyph.ljust(GLYPH_W), color)
            + name_cell
            + paint(status.ljust(STATUS_W), color if status != "ok" else DIM)
            + paint(f"{secs:.1f}s".rjust(DUR_W), DIM if status == "skipped" else 0)
            + " " * GAP
            + bar
        )

    # ---- footer
    print(rule())

    if result == "failed":
        banner = paint(" FAILED ", BOLD, 41, WHITE)
        fname, fsecs = failures[0]
        detail = paint(f"{fname} failed after {fsecs:.1f}s", RED)
    else:
        banner = paint(" PASSED ", BOLD, 42, WHITE)
        detail = paint(f"all {len(STEPS)} steps completed", GREEN)

    print(" " * PAD + banner + "  " + detail)

    tally = " \u00b7 ".join(
        f"{counts[k]} {k}" for k in ("ok", "failed", "skipped") if counts.get(k)
    )
    print(" " * PAD + paint(f"{tally} \u00b7 {total:.1f}s elapsed", DIM))

    skipped = [n for n, st, _ in STEPS if st == "skipped"]
    if skipped:
        print(
            " " * PAD
            + paint("not run: " + ", ".join(skipped), DIM)
        )
    print()


if __name__ == "__main__":
    main()
