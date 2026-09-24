#!/usr/bin/env python3
"""Deploy report — prints a formatted summary of pipeline steps to stdout."""

import os
import sys

WIDTH = 100

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

result = "failed"


def use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"


COLOR = use_color()


def paint(text: str, *codes: str) -> str:
    if not COLOR or not codes:
        return text
    return "\033[" + ";".join(codes) + "m" + text + "\033[0m"


BOLD, DIM = "1", "2"
GREEN, RED, YELLOW, CYAN = "32", "31", "33", "36"

STATUS_STYLE = {
    "ok":      ("✔", "passed",  (GREEN,)),
    "failed":  ("✘", "FAILED",  (RED, BOLD)),
    "skipped": ("–", "skipped", (DIM,)),
}

NAME_W = 26
STATUS_W = 10
DUR_W = 8


def fmt_duration(secs: float) -> str:
    if secs <= 0:
        return "—"
    if secs >= 60:
        m, s = divmod(secs, 60)
        return f"{int(m)}m {s:04.1f}s"
    return f"{secs:.1f}s"


def bar(secs: float, total: float, width: int) -> str:
    if total <= 0 or secs <= 0:
        return " " * width
    filled = max(1, round(width * secs / total))
    return "█" * filled + " " * (width - filled)


def main() -> None:
    total = sum(s for _, _, s in steps)
    ran = [s for s in steps if s[1] != "skipped"]
    bar_w = WIDTH - (4 + NAME_W + 2 + STATUS_W + 2 + DUR_W + 3) - 2

    # Header
    print()
    print(paint(" DEPLOY REPORT ", BOLD, CYAN))
    print(paint("─" * WIDTH, DIM))
    print(
        "  "
        + paint("#", DIM).ljust(2 + (10 if COLOR else 0))
        + paint("step".ljust(NAME_W), DIM)
        + "  "
        + paint("status".ljust(STATUS_W), DIM)
        + "  "
        + paint("time".rjust(DUR_W), DIM)
        + "   "
        + paint("share of total", DIM)
    )
    print(paint("─" * WIDTH, DIM))

    # Rows
    for i, (name, status, secs) in enumerate(steps, 1):
        icon, label, style = STATUS_STYLE.get(status, ("?", status, ()))
        idx = paint(f"{i} ", DIM)
        nm = name.ljust(NAME_W)
        if status == "skipped":
            nm = paint(nm, DIM)
        st = paint(f"{icon} {label}".ljust(STATUS_W), *style)
        du = fmt_duration(secs).rjust(DUR_W)
        if status == "skipped":
            du = paint(du, DIM)
        b = paint(bar(secs, total, bar_w), *style) if secs > 0 else ""
        print(f"  {idx} {nm}  {st}  {du}   {b}")

    print(paint("─" * WIDTH, DIM))

    # Summary counts
    counts = {}
    for _, status, _ in steps:
        counts[status] = counts.get(status, 0) + 1
    parts = []
    for key in ("ok", "failed", "skipped"):
        if counts.get(key):
            _, label, style = STATUS_STYLE[key]
            parts.append(paint(f"{counts[key]} {label.lower()}", *style))
    summary = paint(" · ", DIM).join(parts)
    print(
        f"  {summary}"
        + paint(f"   {len(ran)}/{len(steps)} steps ran", DIM)
        + paint(f"   total {fmt_duration(total)}", DIM)
    )

    # Failure hint
    failed = [n for n, s, _ in steps if s == "failed"]
    if failed:
        print()
        first = failed[0]
        after = [n for n, s, _ in steps if s == "skipped"]
        hint = f"  Pipeline stopped at \"{first}\""
        if after:
            hint += f"; skipped: {', '.join(after)}"
        print(paint(hint, YELLOW))

    # Final result
    print()
    if result == "ok":
        banner = paint("  ✔  RESULT: SUCCESS  ", BOLD, GREEN)
    else:
        banner = paint(f"  ✘  RESULT: {result.upper()}  ", BOLD, RED)
    print(banner)
    print()


if __name__ == "__main__":
    main()
