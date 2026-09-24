#!/usr/bin/env python3
"""Deploy report."""

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


def c(code, text):
    if not USE_COLOR:
        return text
    return "\x1b[" + code + "m" + text + "\x1b[0m"


BOLD = "1"
DIM = "2"
GREEN = "32"
RED = "31"
YELLOW = "33"

STATUS = {
    "ok":      ("✓", GREEN,  "ok"),
    "failed":  ("✗", RED,    "failed"),
    "skipped": ("-", YELLOW, "skipped"),
}


def fmt_secs(secs):
    if secs == 0:
        return "--"
    return "%.1fs" % secs


def line(char="─"):
    return c(DIM, char * WIDTH)


# Column layout (100 cols)
#   idx   icon  name                                          status     duration
IDX_W = 4
ICON_W = 2
NAME_W = 48
STATUS_W = 10
DUR_W = 10

total = sum(s for _, _, s in steps)
n_ok = sum(1 for _, st, _ in steps if st == "ok")
n_failed = sum(1 for _, st, _ in steps if st == "failed")
n_skipped = sum(1 for _, st, _ in steps if st == "skipped")
overall = "failed" if n_failed else "ok"

print()
print(c(BOLD, "Deploy report"))
print(line())

header = (
    "".ljust(IDX_W)
    + "".ljust(ICON_W)
    + "step".ljust(NAME_W)
    + "status".ljust(STATUS_W)
    + "duration".rjust(DUR_W)
)
print(c(DIM, header))

for i, (name, status, secs) in enumerate(steps, 1):
    icon, color, label = STATUS[status]
    idx = ("%d." % i).ljust(IDX_W)
    name_cell = name.ljust(NAME_W)
    status_cell = label.ljust(STATUS_W)
    dur_cell = fmt_secs(secs).rjust(DUR_W)

    if status == "skipped":
        row = c(DIM, idx + icon.ljust(ICON_W) + name_cell + status_cell + dur_cell)
    else:
        row = (
            idx
            + c(color, icon).ljust(ICON_W + (len(c(color, icon)) - len(icon)))
            + name_cell
            + c(color, label) + " " * (STATUS_W - len(label))
            + dur_cell
        )
    print(row)

print(line())

summary_left = (
    c(GREEN, "%d ok" % n_ok)
    + c(DIM, " · ")
    + c(RED, "%d failed" % n_failed)
    + c(DIM, " · ")
    + c(YELLOW, "%d skipped" % n_skipped)
)
plain_left = "%d ok · %d failed · %d skipped" % (n_ok, n_failed, n_skipped)
total_str = "total " + fmt_secs(total)
pad = WIDTH - len(plain_left) - len(total_str)
print(summary_left + " " * max(pad, 1) + c(DIM, total_str))

failed_names = [name for name, st, _ in steps if st == "failed"]
if failed_names:
    print()
    print(c(RED, "✗ ") + c(BOLD, "Result: failed") + c(DIM, "  (%s)" % ", ".join(failed_names)))
    skipped_names = [name for name, st, _ in steps if st == "skipped"]
    if skipped_names:
        print(c(DIM, "  Not run: " + ", ".join(skipped_names)))
else:
    print()
    print(c(GREEN, "✓ ") + c(BOLD, "Result: ok"))
print()

sys.exit(1 if overall == "failed" else 0)
