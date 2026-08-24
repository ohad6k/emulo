"""The declared Python floor is a promise, and nothing was checking it.

pyproject.toml says ``requires-python = ">=3.8"``. For six weeks emulo.py carried three
``dict | dict`` merges, which is 3.9+ syntax that parses everywhere and only detonates at
runtime, and CI could not see it because it tested a single modern interpreter. An outside
contributor found it by reading (PR #44).

Running the suite on 3.8 is necessary but not sufficient: the three broken call sites were in
functions no test executes, so an execution lane alone goes green with the bug still in place.
This test walks the AST instead, which sees unexecuted paths.

It is a tripwire for the specific constructs that have actually bitten or plausibly could, not
a proof of 3.8 compatibility. The proof is the 3.8 lane in CI; this catches what that lane
cannot reach.
"""

import ast
from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parent.parent

# Everything the floor promise covers: py-modules in pyproject.toml names only emulo.
# The [pro] extra (emulo_autopilot/) is deliberately excluded: cryptography's own floor
# is 3.9, so pro code may use 3.9 syntax.
COVERED = [REPO / "emulo.py"]


def _floor_violations(path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    future = any(
        isinstance(n, ast.ImportFrom) and n.module == "__future__"
        for n in tree.body
    )
    out = []

    def flag(node, why):
        out.append(f"{path.name}:{node.lineno}: {why}")

    for node in ast.walk(tree):
        # dict | dict and dict |= dict, 3.9+. Flag any BitOr where either side is a dict
        # display or comprehension: that is the pattern that shipped, and a name-only
        # ``a | b`` merge cannot be told from an int OR without type inference.
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            if isinstance(node.left, (ast.Dict, ast.DictComp)) or \
               isinstance(node.right, (ast.Dict, ast.DictComp)):
                flag(node, "dict | dict merge is 3.9+; use {**a, **b}")
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.BitOr) and \
           isinstance(node.value, (ast.Dict, ast.DictComp)):
            flag(node, "d |= {...} is 3.9+; use d.update({...})")
        # str.removeprefix / removesuffix, 3.9+.
        if isinstance(node, ast.Attribute) and \
           node.attr in ("removeprefix", "removesuffix"):
            flag(node, f".{node.attr}() is 3.9+")
        # match statements, 3.10+. ast.Match does not exist on older interpreters.
        if sys.version_info >= (3, 10) and isinstance(node, ast.Match):
            flag(node, "match statement is 3.10+")
        # Annotations evaluate at runtime without the future import, so builtin generics
        # (3.9+) and X | Y unions (3.10+) raise on import.
        if not future:
            anns = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                anns = [a.annotation for a in
                        node.args.args + node.args.kwonlyargs + node.args.posonlyargs
                        if a.annotation] + ([node.returns] if node.returns else [])
            elif isinstance(node, ast.AnnAssign):
                anns = [node.annotation]
            for a in anns:
                s = ast.unparse(a)
                if any(s.startswith(g + "[") for g in ("list", "dict", "tuple", "set",
                                                       "frozenset", "type")):
                    flag(a, f"builtin generic annotation {s!r} is 3.9+ at runtime "
                            "(add `from __future__ import annotations`)")
                if " | " in s:
                    flag(a, f"union annotation {s!r} is 3.10+ at runtime "
                            "(add `from __future__ import annotations`)")
    return out


class PythonFloorTest(unittest.TestCase):

    def test_covered_files_exist(self):
        # If a covered file is renamed away, the floor test must fail loudly rather than
        # silently guard nothing. That is how the bootstrap pin check almost retired itself.
        for path in COVERED:
            self.assertTrue(path.exists(), f"{path} is gone; update COVERED in this test")

    def test_no_syntax_above_the_declared_floor(self):
        problems = []
        for path in COVERED:
            problems.extend(_floor_violations(path))
        self.assertEqual(problems, [],
                         "requires-python promises 3.8, but:\n  " + "\n  ".join(problems))


if __name__ == "__main__":
    unittest.main()
