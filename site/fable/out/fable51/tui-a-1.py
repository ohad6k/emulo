#!/usr/bin/env python3
"""Deploy report — pretty terminal output."""

import sys

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

result = "failed"

WIDTH = 100
USE_COLOR = sys.stdout.isatty()


def c(code, text):
    if not USE_COLOR:
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


BOLD = "1"
DIM = "2"
GREEN = "32"
RED = "31"
YELLOW = "33"

STATUS_STYLE = {
    "ok": ("✔", GREEN, "ok"),
    "failed": ("✘", RED, "FAILED"),
    "skipped": ("–", DIM, "skipped"),
}


def fmt_secs(secs):
    return f"{secs:6.1f}s"


def line(ch="─"):
    return c(DIM, ch * WIDTH)


# Header
print()
print(c(BOLD, " Deploy report"))
print(line())

# Column header
name_w = 50
print(
    c(DIM, f"   {'#':<3} {'step':<{name_w}} {'status':<10} {'duration':>9}")
)
print(line("╌"))

# Steps
total = 0.0
for i, (name, status, secs) in enumerate(steps, 1):
    icon, color, label = STATUS_STYLE.get(status, ("?", "", status))
    total += secs
    dur = fmt_secs(secs) if status != "skipped" else c(DIM, "     –  ")
    name_cell = name if status != "skipped" else c(DIM, name)
    print(
        f" {c(color, icon)} "
        f"{c(DIM, f'{i:<3}')} "
        f"{name_cell:<{name_w + (len(name_cell) - len(name))}} "
        f"{c(color, f'{label:<10}')} "
        f"{dur:>9}"
    )

print(line("╌"))

# Summary
counts = {"ok": 0, "failed": 0, "skipped": 0}
for _, status, _ in steps:
    counts[status] = counts.get(status, 0) + 1

summary = (
    f"{c(GREEN, str(counts['ok']) + ' ok')}  "
    f"{c(RED, str(counts['failed']) + ' failed')}  "
    f"{c(DIM, str(counts['skipped']) + ' skipped')}"
)
print(f"   {summary}{'':>{2}}{c(DIM, 'total'):>{WIDTH - 40}} {fmt_secs(total)}")

# Failure detail
failed_steps = [name for name, status, _ in steps if status == "failed"]
if failed_steps:
    print()
    for name in failed_steps:
        print(f" {c(RED, '▶')} Step {c(BOLD, repr(name))} failed; later steps were skipped.")

print(line())

# Final result
if result == "ok":
    banner = c(f"{BOLD};{GREEN}", " RESULT: OK ")
else:
    banner = c(f"{BOLD};{RED}", f" RESULT: {result.upper()} ")
print(banner)
print()

sys.exit(0 if result == "ok" else 1)
