import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMULO = ROOT / "emulo.py"

CORPUS = """===== session:aaa111 source:claude =====
[2026-07-20]
done means it runs live, never off a code edit
[2026-07-20]
i hate when there is too much text and containers all around
===== session:bbb222 source:codex =====
[2026-07-21]
done means it runs live, never off a code edit
[2026-07-21]
fix the one thing, dont clean up code that isnt the problem
"""


def build_corpus(root):
    out = root / "emulo-out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "you-corpus.txt").write_text(CORPUS, encoding="utf-8")
    return out


def run_verify(profile, out, *extra):
    return subprocess.run(
        [sys.executable, str(EMULO), "verify", str(profile), "--out", str(out), *extra],
        capture_output=True,
        text=True,
    )


class VerifyReceiptsTest(unittest.TestCase):
    def test_real_quote_is_traced_to_every_session_that_supports_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = build_corpus(root)
            profile = root / "you.md"
            profile.write_text(
                'Ships only what runs: "done means it runs live, never off a code edit".\n',
                encoding="utf-8",
            )
            result = run_verify(profile, out)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("1/1 quotes traced", result.stdout)
            self.assertNotIn("one session", result.stdout)

    def test_invented_quote_fails_the_run(self):
        # The failure this exists to catch: a confident rule whose receipt was
        # never said by anyone.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = build_corpus(root)
            profile = root / "you.md"
            profile.write_text(
                'Values clean architecture: "always prefers hexagonal architecture patterns".\n',
                encoding="utf-8",
            )
            result = run_verify(profile, out)
            self.assertEqual(1, result.returncode)
            self.assertIn("NOT FOUND", result.stdout)
            self.assertIn("appear in no session", result.stdout)
            # A text match cannot know why a quote is missing or what the agent
            # will do with the rule, so the message names possibilities, not causes.
            self.assertNotIn("confidently wrong", result.stdout)
            self.assertNotIn("is invented", result.stdout)
            self.assertIn("paraphrased", result.stdout)
            # one instruction to cut, not two
            self.assertEqual(1, result.stdout.lower().count("cut"), result.stdout)

    def test_single_session_quote_is_flagged_as_context_not_a_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = build_corpus(root)
            profile = root / "you.md"
            profile.write_text(
                'Rejects clutter: "i hate when there is too much text and containers all around".\n',
                encoding="utf-8",
            )
            result = run_verify(profile, out)
            self.assertEqual(0, result.returncode)
            self.assertIn("one session", result.stdout)
            self.assertIn("aaa111", result.stdout)

    def test_prose_between_two_quotes_is_never_read_as_a_quote(self):
        # Regression: pairing quote marks by regex alternation invents a "quote"
        # out of the prose sitting between one span's close and the next's open.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = build_corpus(root)
            profile = root / "you.md"
            profile.write_text(
                'He said "done means it runs live, never off a code edit" and separately '
                'he said "fix the one thing, dont clean up code that isnt the problem".\n',
                encoding="utf-8",
            )
            result = run_verify(profile, out)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("2/2 quotes traced", result.stdout)
            self.assertNotIn("and separately", result.stdout)

    def test_short_quoted_words_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = build_corpus(root)
            profile = root / "you.md"
            profile.write_text('He rejects "cheap" and "slop" on sight.\n', encoding="utf-8")
            result = run_verify(profile, out)
            self.assertEqual(0, result.returncode)
            self.assertIn("no quotes found", result.stdout)

    def test_json_mode_reports_sessions_per_quote(self):
        import json

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = build_corpus(root)
            profile = root / "you.md"
            profile.write_text(
                '"done means it runs live, never off a code edit"\n'
                '"always prefers hexagonal architecture patterns"\n',
                encoding="utf-8",
            )
            result = run_verify(profile, out, "--json")
            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual(2, payload["quotes_checked"])
            self.assertEqual(1, payload["unsupported"])
            supported = [r for r in payload["results"] if r["supported"]]
            self.assertEqual(["aaa111", "bbb222"], supported[0]["sessions"])

    def test_json_report_carries_no_local_paths(self):
        # The report is designed to be sent to someone else, so it must not
        # carry a home directory, a username, or a client's project path.
        import json

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = build_corpus(root)
            profile = root / "you.md"
            profile.write_text(
                '"done means it runs live, never off a code edit"\n', encoding="utf-8"
            )
            result = run_verify(profile, out, "--json")
            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("you.md", payload["profile"])
            blob = json.dumps(payload)
            self.assertNotIn(str(root), blob)
            self.assertNotIn(str(out), blob)
            self.assertNotIn("out", payload)

    def test_missing_corpus_is_an_explicit_error_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "you.md"
            profile.write_text('"done means it runs live, never off a code edit"\n', encoding="utf-8")
            result = run_verify(profile, root / "nothing-here")
            self.assertEqual(2, result.returncode)
            self.assertIn("no mined corpus", result.stderr)


if __name__ == "__main__":
    unittest.main()
