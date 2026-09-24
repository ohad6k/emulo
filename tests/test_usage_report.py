import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMULO = ROOT / "emulo.py"
sys.path.insert(0, str(ROOT))

import emulo  # noqa: E402


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def codex_turn(text, minute=0):
    return {
        "timestamp": f"2026-07-08T10:{minute:02d}:00Z",
        "payload": {"type": "message", "role": "user", "content": [{"text": text}]},
    }


def record(*texts, session_id="s1", source="codex", date="2026-07-08"):
    return {
        "session_id": session_id,
        "source": source,
        "messages": [
            {"date": date, "text": text, "ordinal": index}
            for index, text in enumerate(texts)
        ],
    }


def by_key(report, key):
    for item in report["findings"]:
        if item["key"] == key:
            return item
    return None


def clean_keys(report):
    return {item["title"] for item in report["clean"]}


class RepeatSendTest(unittest.TestCase):
    def test_three_identical_substantive_sends_are_flagged(self):
        ask = "what MCP tools do you have from the gateway"
        report = emulo.usage_report([record(ask, ask, ask)])
        finding = by_key(report, "repeat_sends")
        self.assertIsNotNone(finding)
        self.assertEqual(finding["occurrences"], 3)
        self.assertEqual(finding["receipts"][0]["count"], 3)

    def test_case_and_punctuation_differences_still_count_as_the_same_send(self):
        report = emulo.usage_report([record(
            "run the migration now",
            "Run the migration now.",
            "run  the migration now!",
        )])
        self.assertIsNotNone(by_key(report, "repeat_sends"))

    def test_repeated_approvals_are_not_a_finding(self):
        # Measured on the real corpus: without the word floor this check is
        # almost entirely "ok"/"yes" sent three times, which is approval.
        for filler in ("ok", "yes", "ok do it"):
            report = emulo.usage_report([record(filler, filler, filler)])
            self.assertIsNone(by_key(report, "repeat_sends"), filler)

    def test_two_sends_are_a_retry_not_a_loop(self):
        ask = "please regenerate the release notes"
        self.assertIsNone(by_key(emulo.usage_report([record(ask, ask)]), "repeat_sends"))

    def test_identical_asks_far_apart_are_not_a_loop(self):
        ask = "please regenerate the release notes"
        report = emulo.usage_report([record(
            ask, "unrelated work here", "more unrelated work", ask, "and again", ask,
        )])
        self.assertIsNone(by_key(report, "repeat_sends"))

    def test_a_run_inside_one_session_does_not_span_sessions(self):
        ask = "please regenerate the release notes"
        report = emulo.usage_report([
            record(ask, session_id="a"),
            record(ask, session_id="b"),
            record(ask, session_id="c"),
        ])
        self.assertIsNone(by_key(report, "repeat_sends"))


class CorrectionTest(unittest.TestCase):
    def test_correction_openers_are_counted(self):
        messages = ["no that is wrong, use the other file"] * 2 + ["ok"] * 2
        report = emulo.usage_report([record(*messages)])
        self.assertEqual(report["correction_rate"], 50)

    def test_no_need_is_not_a_correction(self):
        report = emulo.usage_report([record(
            "no need for the repo i think",
            "no worries about the lint",
            "no problem",
        )])
        self.assertEqual(report["correction_rate"], 0)

    def test_correction_below_the_rate_bar_is_reported_but_not_flagged(self):
        messages = ["no this is wrong"] + ["ordinary work message here"] * 99
        report = emulo.usage_report([record(*messages)])
        self.assertEqual(report["correction_rate"], 1)
        self.assertIsNone(by_key(report, "corrections"))
        self.assertIn("Messages that open like a correction.", clean_keys(report))

    def test_correction_above_the_rate_bar_is_flagged(self):
        messages = ["no this is wrong"] * 10 + ["ordinary work message here"] * 40
        report = emulo.usage_report([record(*messages)])
        self.assertEqual(report["correction_rate"], 20)
        self.assertIsNotNone(by_key(report, "corrections"))

    def test_a_correction_mid_sentence_is_not_an_opener(self):
        report = emulo.usage_report([record(
            "the test asserts the wrong column so it never fails",
        )])
        self.assertEqual(report["correction_rate"], 0)


class RestatedContextTest(unittest.TestCase):
    def test_restated_context_needs_repetition_before_it_is_flagged(self):
        two = emulo.usage_report([record("i told you to keep the dark theme"),
                                  record("as i said, keep the dark theme")])
        self.assertIsNone(by_key(two, "restated_context"))

    def test_restated_context_is_flagged_with_its_marker(self):
        report = emulo.usage_report([record(
            "i told you to keep the dark theme",
            "as i said, the header stays fixed",
            "like i said, no new dependencies",
        )])
        finding = by_key(report, "restated_context")
        self.assertIsNotNone(finding)
        self.assertEqual(finding["occurrences"], 3)
        self.assertEqual(
            {receipt["marker"] for receipt in finding["receipts"]},
            {"i told you", "as i said", "like i said"},
        )

    def test_quote_is_windowed_onto_a_buried_marker(self):
        buried = ("x" * 400) + " i already told you the header stays fixed " + ("y" * 400)
        report = emulo.usage_report([record(buried, buried + "!", buried + "?")])
        finding = by_key(report, "restated_context")
        self.assertIsNotNone(finding)
        # A receipt whose quote does not contain the evidence cannot be checked.
        for receipt in finding["receipts"]:
            self.assertIn("i already told you", receipt["text"])


class QuotedTextTest(unittest.TestCase):
    """A marker inside quoted or pasted text is not you restating anything.

    The rule: text inside a ``` fence, on a line starting with ">", or inside a
    double-quoted span is masked before the restated-context markers and the
    correction openers are matched. What is left is what you wrote yourself.
    """

    def _restated(self, *texts):
        _, _, restated, _ = emulo.usage_findings([record(*texts)])
        return restated

    def _corrections(self, *texts):
        _, _, _, corrections = emulo.usage_findings([record(*texts)])
        return corrections

    def test_marker_inside_a_pasted_paragraph_to_proofread_is_not_counted(self):
        self.assertEqual(self._restated(
            'proofread this for me:\n\n"As I said in the last update, the launch '
            'moves to Friday and nobody needs to change anything."'
        ), [])

    def test_marker_inside_a_curly_quoted_paragraph_is_not_counted(self):
        self.assertEqual(self._restated(
            "fix the grammar: “as i said, we ship when its ready”"
        ), [])

    def test_marker_inside_a_fenced_block_is_not_counted(self):
        self.assertEqual(self._restated(
            "tighten this reply\n```\nLike I said on the call, the budget is fixed.\n```"
        ), [])

    def test_marker_inside_a_quoted_email_line_is_not_counted(self):
        self.assertEqual(self._restated(
            "> like I said last week, the invoice is overdue\n\nhelp me answer this politely"
        ), [])

    def test_genuine_as_i_said_still_counts(self):
        restated = self._restated("as I said, use pnpm not npm")
        self.assertEqual(len(restated), 1)
        self.assertEqual(restated[0]["marker"], "as i said")

    def test_genuine_marker_next_to_a_quote_still_counts(self):
        restated = self._restated(
            '> like I said last week\n\nas i said, reply "no" to that email'
        )
        self.assertEqual(len(restated), 1)
        self.assertEqual(restated[0]["marker"], "as i said")

    def test_receipt_windows_on_the_counted_marker_not_the_quoted_one(self):
        quoted = '"' + ("like i said in the memo " * 12) + '"'
        restated = self._restated(quoted + " " + ("z" * 200) + " i told you the header stays fixed")
        self.assertEqual(len(restated), 1)
        self.assertEqual(restated[0]["marker"], "i told you")
        self.assertIn("i told you the header stays fixed", restated[0]["text"])

    def test_correction_opener_inside_a_quote_is_not_a_correction(self):
        self.assertEqual(self._corrections(
            '"No, we cannot ship on Friday" is what my manager wrote, draft a reply',
            "> wrong address, please resend\n\nwhat does this customer want",
            "```\nno such file or directory\n```\nwhy does the build say this",
        ), [])

    def test_correction_after_a_quoted_line_still_counts(self):
        self.assertEqual(len(self._corrections(
            "> I switched the config to yaml\n\nno, keep it as json",
        )), 1)


class RewordLoopTest(unittest.TestCase):
    def test_near_identical_consecutive_asks_are_flagged(self):
        report = emulo.usage_report([record(
            "make the release notes shorter and drop the roadmap section",
            "make the release notes shorter and drop the roadmap part",
            "make the release notes much shorter and drop the roadmap part",
        )])
        self.assertIsNotNone(by_key(report, "reword_loops"))

    def test_a_repasted_block_is_not_a_reworded_ask(self):
        # The only thing this check caught on a real corpus was a pasted
        # pygame banner sent three times, not a person rephrasing anything.
        block = "pygame 2.6.1 (SDL 2.28.4, Python 3.11.4)\n" + "\n".join(
            f"[hud] line {index} of the same pasted banner" for index in range(8)
        )
        report = emulo.usage_report([record(block, block + "\nx", block + "\ny")])
        self.assertIsNone(by_key(report, "reword_loops"))

    def test_unrelated_consecutive_asks_are_not_a_loop(self):
        report = emulo.usage_report([record(
            "make the release notes shorter and drop the roadmap section",
            "now bump the version and tag it for the public release",
            "write a migration guide for the storage layer change",
        )])
        self.assertIsNone(by_key(report, "reword_loops"))


class ReportShapeTest(unittest.TestCase):
    def test_receipts_do_not_repeat_the_same_quote(self):
        report = emulo.usage_report([record(
            *["i told you to keep the dark theme"] * 8, session_id="a"
        )])
        finding = by_key(report, "restated_context")
        quotes = [receipt["text"] for receipt in finding["receipts"]]
        self.assertEqual(len(quotes), len(set(quotes)))

    def test_every_flagged_finding_carries_receipts(self):
        report = emulo.usage_report([record(
            "i told you to keep the dark theme",
            "as i said, the header stays fixed",
            "like i said, no new dependencies",
        )])
        self.assertTrue(report["findings"])
        for finding in report["findings"]:
            self.assertTrue(finding["receipts"], finding["key"])

    def test_empty_corpus_does_not_crash(self):
        report = emulo.usage_report([])
        self.assertEqual(report["sessions"], 0)
        self.assertEqual(report["messages"], 0)
        self.assertEqual(report["findings"], [])

    def test_stats_describe_the_corpus(self):
        report = emulo.usage_report([record("one two three four five six", "ok")])
        self.assertEqual(report["messages"], 2)
        self.assertEqual(report["short_prompts"], 1)
        self.assertEqual(report["sources"], {"codex": 1})


class WordingTest(unittest.TestCase):
    """The checks match text. They cannot know why you repeated something.

    0.6.3 printed causes as facts ("the agent was already told", "the model had
    already given everything that prompt could get"). A text match cannot see
    either, so the wording describes what was counted and offers the fix as a
    possibility.
    """

    CAUSE_CLAIMS = (
        "already given everything", "was already told", "already given and lost",
        "paid for twice", "usually means", "rather than the model", "the gap a profile closes",
    )

    def _all_findings(self):
        report = emulo.usage_report([record(
            *["what MCP tools do you have from the gateway"] * 3,
            "i told you to keep the dark theme",
            "as i said, the header stays fixed",
            "like i said, no new dependencies",
            "make the release notes shorter and drop the roadmap section",
            "make the release notes shorter and drop the roadmap part",
            "make the release notes much shorter and drop the roadmap part",
            "no, keep it as json",
        )])
        return report

    def test_every_check_fires_on_this_fixture(self):
        keys = {item["key"] for item in self._all_findings()["findings"]}
        self.assertEqual(keys, {"repeat_sends", "restated_context", "reword_loops", "corrections"})

    def test_no_finding_states_a_cause_as_fact(self):
        for item in self._all_findings()["findings"]:
            text = (item["title"] + " " + item["meaning"]).lower()
            for claim in self.CAUSE_CLAIMS:
                self.assertNotIn(claim, text, item["key"])

    def test_no_dashes_in_report_wording(self):
        for item in self._all_findings()["findings"]:
            for field in ("title", "meaning"):
                self.assertNotIn("—", item[field], item["key"])
                self.assertNotIn("–", item[field], item["key"])

    def test_keys_are_unchanged_for_json_consumers(self):
        self.assertEqual(
            {item["key"] for item in self._all_findings()["findings"]},
            {"repeat_sends", "restated_context", "reword_loops", "corrections"},
        )


class InjectedContextTest(unittest.TestCase):
    """The IDE's own preamble is not something the user typed.

    Found by running --coach over a real corpus: 743 of these blocks were being
    read as user messages, and their near-verbatim repetition made them the
    loudest finding in the report. They pollute mining the same way.
    """

    def test_ide_setup_preamble_is_treated_as_injected(self):
        self.assertTrue(emulo.is_injected_context(
            "# Context from my IDE setup:\n\n## Active file: docs/plan.md"
        ))
        self.assertTrue(emulo.is_injected_context(
            "# Context from my IDE setup:\n\n## Open tabs:\n- a.py\n- b.py"
        ))

    def test_files_mentioned_preamble_is_treated_as_injected(self):
        self.assertTrue(emulo.is_injected_context(
            "# Files mentioned by the user:\n\n## clipboard-1.png: C:/tmp/clipboard-1.png"
        ))

    def test_a_user_writing_about_their_ide_is_not_injected(self):
        self.assertFalse(emulo.is_injected_context(
            "the context from my IDE setup keeps leaking into the prompt"
        ))

    def test_injected_preamble_never_reaches_the_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            logs = Path(tmp) / "logs"
            block = "# Context from my IDE setup:\n\n## Active file: docs/plan.md"
            write_jsonl(logs / "session.jsonl", [
                codex_turn(block, 0), codex_turn(block, 1), codex_turn(block, 2),
                codex_turn("ship the release notes when the suite is green", 3),
            ])
            proc = subprocess.run(
                [sys.executable, str(EMULO), "--coach", "--path", str(logs), "--json"],
                capture_output=True, text=True, cwd=tmp,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report["messages"], 1)
            self.assertEqual(report["findings"], [])


class CoachCliTest(unittest.TestCase):
    def _run(self, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            logs = Path(tmp) / "logs"
            ask = "what MCP tools do you have from the gateway"
            write_jsonl(logs / "session.jsonl", [
                codex_turn(ask, 0),
                codex_turn(ask, 1),
                codex_turn(ask, 2),
                codex_turn("i told you the header stays fixed", 3),
            ])
            proc = subprocess.run(
                [sys.executable, str(EMULO), "--coach", "--path", str(logs), *extra],
                capture_output=True, text=True, cwd=tmp,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return proc.stdout, Path(tmp)

    def test_coach_reports_the_loop_and_writes_nothing(self):
        stdout, tmp = self._run()
        self.assertIn("emulo usage report", stdout)
        self.assertIn("Messages you sent three or more times in a row, unchanged.", stdout)
        self.assertIn("what MCP tools do you have from the gateway", stdout)
        # The report is a read: it must never leave a corpus behind.
        self.assertFalse((tmp / "emulo-out").exists())

    def test_coach_states_what_it_cannot_see(self):
        stdout, _ = self._run()
        self.assertIn("cost, tokens, tool calls", stdout)

    def test_coach_json_is_machine_readable(self):
        stdout, _ = self._run("--json")
        report = json.loads(stdout)
        self.assertEqual(report["sessions"], 1)
        self.assertTrue(any(item["key"] == "repeat_sends" for item in report["findings"]))

    def test_coach_says_once_that_these_are_text_matches(self):
        stdout, _ = self._run()
        self.assertEqual(stdout.count("text matches"), 1)
        self.assertIn("cannot tell why", stdout)

    def test_coach_json_keeps_its_keys(self):
        stdout, _ = self._run("--json")
        report = json.loads(stdout)
        self.assertEqual(set(report), {
            "sessions", "messages", "first_date", "last_date", "sources",
            "median_words", "short_prompts", "correction_rate", "findings", "clean",
        })
        for item in report["findings"]:
            self.assertEqual(set(item), {"key", "title", "meaning", "occurrences", "flagged", "receipts"})
            for receipt in item["receipts"]:
                self.assertEqual(set(receipt), {"session_id", "source", "date", "ordinal", "text", "marker", "count"})
        for item in report["clean"]:
            self.assertEqual(set(item), {"title", "occurrences"})

    def test_coach_redacts_receipts_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            logs = Path(tmp) / "logs"
            # Assembled at runtime on purpose. Written inline this matches the
            # same REDACTIONS pattern it is testing, and a repo secret scanner
            # cannot tell a fixture key from a real one that leaked.
            fake_key = "sk-" + "abcdefghijklmnopqrstuvwxyz012345"
            secret = f"i told you the key is {fake_key}"
            write_jsonl(logs / "session.jsonl", [codex_turn(secret, 0)])
            proc = subprocess.run(
                [sys.executable, str(EMULO), "--coach", "--path", str(logs), "--json"],
                capture_output=True, text=True, cwd=tmp,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn(fake_key, proc.stdout)


def isolated_env(home):
    """Point every place emulo looks for logs at one directory."""
    env = dict(os.environ)
    for name in ("HOME", "USERPROFILE", "CODEX_HOME", "XDG_DATA_HOME"):
        env[name] = str(home)
    env.pop("HOMEDRIVE", None)
    env.pop("HOMEPATH", None)
    return env


class CoachHistoryEdgeTest(unittest.TestCase):
    def test_coach_with_no_history_at_all_explains_and_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            work = Path(tmp) / "work"
            home.mkdir()
            work.mkdir()
            for extra in ((), ("--json",)):
                proc = subprocess.run(
                    [sys.executable, str(EMULO), "--coach", *extra],
                    capture_output=True, text=True, cwd=work, env=isolated_env(home),
                )
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertIn("no session logs found", proc.stdout)
                self.assertIn("--path", proc.stdout)
                self.assertNotIn("Traceback", proc.stderr)
            self.assertEqual(list(work.iterdir()), [])
            self.assertEqual(list(home.iterdir()), [])

    def test_coach_reads_a_tiny_claude_code_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            work = Path(tmp) / "work"
            work.mkdir()
            rows = [
                {
                    "type": "user",
                    "timestamp": f"2026-09-20T10:0{index}:00Z",
                    "message": {"role": "user", "content": text},
                }
                for index, text in enumerate([
                    "add a dark theme toggle to the settings page",
                    "as i said, keep the header fixed when it scrolls",
                    "ship it when the tests pass",
                ])
            ]
            write_jsonl(home / ".claude" / "projects" / "demo" / "session.jsonl", rows)
            env = isolated_env(home)
            proc = subprocess.run(
                [sys.executable, str(EMULO), "--coach", "--source", "claude"],
                capture_output=True, text=True, cwd=work, env=env,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("emulo usage report", proc.stdout)
            self.assertIn("read 1 sessions, 3 of your messages, 2026-09-20 to 2026-09-20", proc.stdout)
            self.assertIn("Nothing to flag.", proc.stdout)
            self.assertIn("Under the bar:", proc.stdout)
            self.assertIn("(1 seen)", proc.stdout)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertEqual(list(work.iterdir()), [])

            as_json = subprocess.run(
                [sys.executable, str(EMULO), "--coach", "--source", "claude", "--json"],
                capture_output=True, text=True, cwd=work, env=env,
            )
            self.assertEqual(as_json.returncode, 0, as_json.stderr)
            report = json.loads(as_json.stdout)
            self.assertEqual(report["sessions"], 1)
            self.assertEqual(report["messages"], 3)
            self.assertEqual(report["findings"], [])
            self.assertEqual(len(report["clean"]), 4)


if __name__ == "__main__":
    unittest.main()
