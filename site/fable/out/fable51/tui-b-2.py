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


def c(code, text):
    return f"\033[{code}m{text}\033[0m" if COLOR else text


BOLD, DIM = "1", "2"
GREEN, RED, YELLOW = "32", "31", "33"

STYLE = {
    "ok": ("✓", GREEN, "ok"),
    "failed": ("✗", RED, "failed"),
    "skipped": ("-", DIM, "skipped"),
}


def fmt_secs(secs):
    return f"{secs:.1f}s" if secs else "--"


def line(text, char="─"):
    return c(DIM, char * WIDTH) if text is None else text


rows = []
for i, (name, status, secs) in enumerate(steps, 1):
    icon, color, label = STYLE[status]
    idx = c(DIM, f"{i}/{len(steps)}")
    name_col = name.ljust(28)
    if status == "skipped":
        name_col = c(DIM, name_col)
    status_col = c(color, f"{icon} {label}").ljust(20 + (9 if COLOR else 0))
    time_col = c(DIM, fmt_secs(secs).rjust(8))
    rows.append(f"  {idx}  {name_col} {status_col} {time_col}")

total = sum(secs for _, _, secs in steps)
done = sum(1 for _, s, _ in steps if s == "ok")
failed = [n for n, s, _ in steps if s == "failed"]
skipped = sum(1 for _, s, _ in steps if s == "skipped")

print()
print("  " + c(BOLD, "Deploy report"))
print(line(None))
print("\n".join(rows))
print(line(None))
if failed:
    result = c(f"{BOLD};{RED}", "✗ FAILED")
    detail = f"stopped at '{failed[0]}' · {done} passed · {skipped} skipped · {fmt_secs(total)} total"
else:
    result = c(f"{BOLD};{GREEN}", "✓ PASSED")
    detail = f"{done} passed · {fmt_secs(total)} total"
print(f"  {result}  {c(DIM, detail)}")
print()
