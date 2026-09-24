import sys

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

WIDTH = 100
COLOR = sys.stdout.isatty()


def paint(text, code):
    if not COLOR:
        return text
    return "\033[" + code + "m" + text + "\033[0m"


BOLD = "1"
DIM = "2"
GREEN = "32"
RED = "31"
YELLOW = "33"

STATUS_STYLE = {
    "ok": ("ok", GREEN, "\u2713"),
    "failed": ("failed", RED, "\u2717"),
    "skipped": ("skipped", DIM, "-"),
}

name_width = max(len(name) for name, _, _ in steps)
status_width = max(len(s) for s, _, _ in STATUS_STYLE.values())

print()
print(paint("deploy report", BOLD))
print(paint("\u2500" * WIDTH, DIM))

total = 0.0
failed_step = None
for number, (name, status, secs) in enumerate(steps, start=1):
    label, color, mark = STATUS_STYLE[status]
    total += secs
    if status == "failed" and failed_step is None:
        failed_step = name

    duration = "%6.1fs" % secs if status != "skipped" else "      -"
    line = "  %s  %d. %-*s  %-*s  %s" % (
        paint(mark, color),
        number,
        name_width,
        name,
        status_width,
        paint(label, color),
        duration,
    )
    if status == "skipped":
        line = paint(line, DIM) if not COLOR else line
    print(line)

print(paint("\u2500" * WIDTH, DIM))
print("  total time %.1fs" % total)

if failed_step is None:
    print(paint("result: passed", BOLD + ";" + GREEN))
else:
    skipped = [name for name, status, _ in steps if status == "skipped"]
    print(paint("result: failed", BOLD + ";" + RED))
    print("  stopped at %s. Not run: %s." % (paint(failed_step, BOLD), ", ".join(skipped)))
print()
