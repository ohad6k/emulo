#!/usr/bin/env python3
"""Deploy report: prints the result of each pipeline step and the overall outcome."""

import sys

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

WIDTH = 100
USE_COLOR = sys.stdout.isatty()


def paint(text, code):
    if not USE_COLOR:
        return text
    return "\033[" + code + "m" + text + "\033[0m"


BOLD = "1"
DIM = "2"
GREEN = "32"
RED = "31"
YELLOW = "33"

STATUS_STYLE = {
    "ok": ("✔", "ok", GREEN),
    "failed": ("✖", "failed", RED),
    "skipped": ("–", "skipped", YELLOW),
}


def fmt_duration(secs):
    if secs == 0.0:
        return "—"
    return "%.1fs" % secs


name_width = max(len(name) for name, _, _ in steps)
status_width = max(len(label) for _, label, _ in STATUS_STYLE.values())
duration_width = max(len(fmt_duration(secs)) for _, _, secs in steps)

total = sum(secs for _, _, secs in steps)
failed_step = next((name for name, status, _ in steps if status == "failed"), None)
counts = {"ok": 0, "failed": 0, "skipped": 0}
for _, status, _ in steps:
    counts[status] = counts.get(status, 0) + 1

lines = []
lines.append(paint("Deploy report", BOLD))
lines.append(paint("─" * WIDTH, DIM))

for index, (name, status, secs) in enumerate(steps, start=1):
    mark, label, colour = STATUS_STYLE.get(status, ("?", status, ""))
    step_no = "%d/%d" % (index, len(steps))
    padded_name = name.ljust(name_width)
    padded_status = label.ljust(status_width)
    duration = fmt_duration(secs).rjust(duration_width)
    if status == "skipped":
        line = "  " + paint(step_no + "  " + mark + "  " + padded_name + "  " + padded_status + "  " + duration, DIM)
    else:
        line = (
            "  "
            + paint(step_no, DIM)
            + "  "
            + paint(mark, colour)
            + "  "
            + padded_name
            + "  "
            + paint(padded_status, colour)
            + "  "
            + paint(duration, DIM)
        )
    lines.append(line)

lines.append(paint("─" * WIDTH, DIM))

summary = "%d ok, %d failed, %d skipped in %.1fs" % (
    counts["ok"], counts["failed"], counts["skipped"], total
)
if failed_step is not None:
    result = paint("✖ Result: failed", BOLD + ";" + RED)
    lines.append(result + "  " + paint(summary, DIM))
    lines.append("  The pipeline stopped at " + paint(failed_step, BOLD) + ". Later steps were not run.")
else:
    result = paint("✔ Result: passed", BOLD + ";" + GREEN)
    lines.append(result + "  " + paint(summary, DIM))

print("\n".join(lines))
