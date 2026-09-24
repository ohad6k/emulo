#!/usr/bin/env python3
import sys

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

WIDTH = 100
use_color = sys.stdout.isatty()


def c(code, text):
    return f"\x1b[{code}m{text}\x1b[0m" if use_color else text


BOLD, DIM = "1", "2"
GREEN, RED, YELLOW = "32", "31", "33"

STYLES = {
    "ok": ("✔", GREEN, "ok"),
    "failed": ("✘", RED, "FAILED"),
    "skipped": ("–", DIM, "skipped"),
}

name_w = max(len(name) for name, _, _ in steps)
status_w = max(len(label) for _, _, label in STYLES.values())
total = sum(secs for _, _, secs in steps)
ran = sum(1 for _, s, _ in steps if s != "skipped")

print()
print(c(BOLD, "  Deploy report"))
print(c(DIM, "  " + "─" * (WIDTH - 4)))
print()

for i, (name, status, secs) in enumerate(steps, 1):
    icon, color, label = STYLES[status]
    duration = f"{secs:6.1f}s" if status != "skipped" else c(DIM, f"{'—':>7}")
    line = (
        f"  {c(DIM, f'{i}/{len(steps)}')}  "
        f"{c(color, icon)}  "
        f"{name:<{name_w}}   "
        f"{c(color, f'{label:<{status_w}}')}   "
        f"{duration}"
    )
    print(line)

print()
print(c(DIM, "  " + "─" * (WIDTH - 4)))
print(
    f"  {c(BOLD + ';' + RED, '✘ Result: FAILED')}"
    f"   {c(DIM, f'{ran} of {len(steps)} steps ran · failed at')} "
    f"{c(RED, 'run tests')}"
    f"   {c(DIM, f'· total {total:.1f}s')}"
)
print()
