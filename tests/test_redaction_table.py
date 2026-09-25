import importlib.util
import re
import unittest
from pathlib import Path

from tests.redaction_table import MISSES, NEGATIVES, ROWS, STRUCTURAL_TOKENS

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("emulo_redaction_table", ROOT / "emulo.py")
emulo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(emulo)


def security_section():
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    start = text.index("## Redaction coverage and limits")
    end = text.index("\n## ", start + 1)
    return text[start:end]


class RedactionTableTest(unittest.TestCase):
    def test_every_documented_pattern_redacts_its_sample(self):
        for row in ROWS:
            with self.subTest(doc=row["doc"], text=row["input"]):
                self.assertEqual(row["expected"], emulo.redact(row["input"]))

    def test_the_documented_miss_is_still_a_miss(self):
        # SECURITY.md says these pass through. If one starts being redacted,
        # the doc is wrong: update both together.
        for row in MISSES:
            with self.subTest(doc=row["doc"]):
                self.assertEqual(row["expected"], emulo.redact(row["input"]))

    def test_words_that_contain_a_key_prefix_are_left_alone(self):
        for row in NEGATIVES:
            with self.subTest(text=row["input"]):
                self.assertEqual(row["expected"], emulo.redact(row["input"]))

    def test_security_md_names_exactly_the_tested_set(self):
        section = security_section()
        documented = set(re.findall(r"`[^`]+`", section))
        claimed = {row["doc"] for row in ROWS + MISSES if row["doc"].startswith("`")}
        self.assertEqual(set(), claimed - documented, "tested but not named in SECURITY.md")
        self.assertEqual(set(), documented - claimed - STRUCTURAL_TOKENS,
                         "named in SECURITY.md but no row tests it")
        for row in ROWS + MISSES:
            self.assertIn(row["doc"], section, row["doc"])


if __name__ == "__main__":
    unittest.main()
