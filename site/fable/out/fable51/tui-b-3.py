#!/usr/bin/env python3
"""Deploy report: five steps, per-step status and duration, final result."""

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
    if not use_color:
        return text
    return f"\033[{code}m{text}\033[0m"


BOLD = "1"
DIM = "2"
GREEN = "32"
RED = "31"
YELLOW = "33"

STATUS_STYLE = {
    "ok": ("✔", GREEN, "ok"),
    "failed": ("✘", RED, "failed"),
    "skipped": ("–", DIM, "skipped"),
}


def fmt_secs(secs):
    return f"{secs:.1f}s"


name_w = max(len(name) for name, _, _ in steps)
status_w = max(len(label) for _, _, label in STATUS_STYLE.values())
secs_w = max(len(fmt_secs(s)) for _, _, s in steps)

lines = []
lines.append("")
lines.append(c(BOLD, "Deploy report"))
lines.append(c(DIM, "─" * WIDTH))

for i, (name, status, secs) in enumerate(steps, start=1):
    icon, color, label = STATUS_STYLE[status]
    idx = c(DIM, f"{i}/{len(steps)}")
    mark = c(color, icon)
    status_txt = c(color, label.ljust(status_w))
    name_txt = name.ljust(name_w)
    if status == "skipped":
        name_txt = c(DIM, name_txt)
        secs_txt = c(DIM, "--".rjust(secs_w))
    else:
        secs_txt = c(DIM, fmt_secs(secs).rjust(secs_w))
    lines.append(f"  {idx}  {mark}  {name_txt}  {status_txt}  {secs_txt}")

lines.append(c(DIM, "─" * WIDTH))

counts = {"ok": 0, "failed": 0, "skipped": 0}
for _, status, _ in steps:
    counts[status] += 1
total = sum(secs for _, _, secs in steps)

failed_names = [name for name, status, _ in steps if status == "failed"]
result_txt = c(BOLD + ";" + RED, "FAILED") if failed_names else c(BOLD + ";" + GREEN, "OK")
summary = (
    f"{c(GREEN, str(counts['ok']) + ' ok')}  "
    f"{c(RED, str(counts['failed']) + ' failed')}  "
    f"{c(DIM, str(counts['skipped']) + ' skipped')}  "
    f"{c(DIM, 'total ' + fmt_secs(total))}"
)
lines.append(f"  Result: {result_txt}   {summary}")
if failed_names:
    lines.append(c(DIM, f"  Failed at: {', '.join(failed_names)}. Remaining steps were skipped."))
lines.append("")

print("\n".join(lines))
