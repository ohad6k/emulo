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
    return "\033[" + code + "m" + text + "\033[0m"


BOLD = "1"
DIM = "2"
GREEN = "32"
RED = "31"
YELLOW = "33"

STATUS_STYLE = {
    "ok": ("✔", GREEN, "ok"),
    "failed": ("✖", RED, "failed"),
    "skipped": ("−", DIM, "skipped"),
}


def fmt_secs(secs):
    if secs == 0:
        return "--"
    return "%.1fs" % secs


total = sum(s for _, _, s in steps)
failed = [n for n, st, _ in steps if st == "failed"]
result_ok = not failed

# Header
print()
print(c(BOLD, "  Deploy report"))
print(c(DIM, "  " + "─" * (WIDTH - 4)))

# Steps
name_w = max(len(n) for n, _, _ in steps) + 2
for i, (name, status, secs) in enumerate(steps, 1):
    icon, color, label = STATUS_STYLE.get(status, ("•", "0", status))
    num = c(DIM, "%d/%d" % (i, len(steps)))
    icon_s = c(color, icon)
    name_s = c(DIM, name) if status == "skipped" else name
    label_s = c(color, label.ljust(8))
    dur = fmt_secs(secs).rjust(7)
    dur_s = c(DIM, dur)
    print("  %s  %s  %s  %s  %s" % (num, icon_s, name_s.ljust(name_w) if not USE_COLOR or status != "skipped" else name_s + " " * (name_w - len(name)), label_s, dur_s))

print(c(DIM, "  " + "─" * (WIDTH - 4)))

# Result
if result_ok:
    print("  " + c(BOLD + ";" + GREEN, "✔ Deploy succeeded") + c(DIM, "   total %.1fs" % total))
else:
    print("  " + c(BOLD + ";" + RED, "✖ Deploy failed") + c(DIM, "   total %.1fs" % total))
    print(c(DIM, "  failed at: ") + ", ".join(c(RED, n) for n in failed))
    skipped = [n for n, st, _ in steps if st == "skipped"]
    if skipped:
        print(c(DIM, "  not run:   " + ", ".join(skipped)))
print()

sys.exit(0 if result_ok else 1)
