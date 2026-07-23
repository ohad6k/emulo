"""A card.json whose stats carry JSON nulls must still render.

A reducer that emits `"first_date": null` instead of `""` used to crash
`emulo --card`: months_between() did `None[:4]`, which raises TypeError, and
TypeError was not in the except tuple, so the traceback escaped both
print_card() and render_card_html().

Missing dates degrade the same way every other missing stat does on this card:
months_between() returns 0 and both renderers already skip the months row when
it is falsy.
"""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMULO = ROOT / "emulo.py"
SPEC = importlib.util.spec_from_file_location("emulo_card_nulls", EMULO)
emulo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(emulo)


def card_with(stats):
    return {
        "archetype": "Proof-First Builder",
        "laws": [{"text": "Always prove done.", "count": "12 sessions"}],
        "truth": "you ship faster than you verify",
        "stats": stats,
    }


class MonthsBetweenNullDatesTest(unittest.TestCase):
    def test_null_dates_degrade_to_zero_instead_of_raising(self):
        self.assertEqual(emulo.months_between(None, None), 0)
        self.assertEqual(emulo.months_between(None, "2026-07-01"), 0)
        self.assertEqual(emulo.months_between("2025-11-01", None), 0)

    def test_non_string_dates_degrade_to_zero(self):
        # a reducer emitting an epoch int or a list is just as unrenderable
        self.assertEqual(emulo.months_between(20251101, 20260701), 0)
        self.assertEqual(emulo.months_between(["2025-11-01"], ["2026-07-01"]), 0)
        self.assertEqual(emulo.months_between({}, {}), 0)

    def test_empty_and_malformed_strings_still_degrade_to_zero(self):
        self.assertEqual(emulo.months_between("", ""), 0)
        self.assertEqual(emulo.months_between("not-a-date", "also-not"), 0)

    def test_real_dates_still_compute_the_span_inclusive(self):
        self.assertEqual(emulo.months_between("2025-11-03", "2026-07-21"), 9)
        self.assertEqual(emulo.months_between("2026-07-01", "2026-07-21"), 1)


class CardRendersWithNullDatesTest(unittest.TestCase):
    def test_render_card_html_survives_null_dates_and_omits_months(self):
        html = emulo.render_card_html(card_with({
            "sessions": 1656,
            "tokens": 3_000_000,
            "first_date": None,
            "last_date": None,
        }))
        self.assertIn("1,656", html)
        self.assertNotIn("<span>months</span>", html)

    def test_render_card_html_keeps_months_when_dates_are_real(self):
        html = emulo.render_card_html(card_with({
            "sessions": 1656,
            "first_date": "2025-11-03",
            "last_date": "2026-07-21",
        }))
        self.assertIn("<span>months</span>", html)

    def test_print_card_survives_null_dates(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            emulo.print_card(card_with({
                "sessions": 1656,
                "first_date": None,
                "last_date": None,
            }), still=True)
        out = buf.getvalue()
        self.assertIn("1,656 sessions", out)
        self.assertNotIn("months", out)


class CardCliWithNullDatesTest(unittest.TestCase):
    def test_emulo_card_exits_clean_on_a_card_with_null_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "emulo-out"
            out.mkdir()
            card_path = out / "card.json"
            card_path.write_text(json.dumps(card_with({
                "sessions": 1656,
                "messages": 42000,
                "tokens": 3_000_000,
                "first_date": None,
                "last_date": None,
            })), encoding="utf-8")
            env = dict(os.environ, EMULO_NO_ANIM="1", PYTHONIOENCODING="utf-8")
            result = subprocess.run(
                [sys.executable, str(EMULO), "--card", str(card_path),
                 "--out", str(out), "--no-open", "--still"],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertTrue((out / "card.html").exists())


if __name__ == "__main__":
    unittest.main()
