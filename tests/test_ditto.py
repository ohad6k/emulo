import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DITTO = ROOT / "ditto.py"


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


class DittoCliTest(unittest.TestCase):
    def test_dry_run_counts_without_writing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            out = root / "ditto-out"
            write_jsonl(logs / "codex.jsonl", [
                {
                    "timestamp": "2026-07-08T10:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"text": "done means live proof. token=abc123456789"}],
                    },
                },
                {
                    "timestamp": "2026-07-08T10:01:00Z",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"text": "ignore assistant text"}],
                    },
                },
            ])
            write_jsonl(logs / "claude.jsonl", [
                {
                    "timestamp": "2026-07-08T11:00:00Z",
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": "do not touch files outside the task",
                    },
                },
            ])

            result = subprocess.run(
                [sys.executable, str(DITTO), "--path", str(logs), "--out", str(out), "--dry-run"],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("dry run: no files written", result.stdout)
            self.assertIn("jsonl files: 2", result.stdout)
            self.assertIn("sessions: 2", result.stdout)
            self.assertIn("your messages: 2", result.stdout)
            self.assertIn("secrets/PII redacted: 1", result.stdout)
            self.assertFalse(out.exists())

    def test_run_writes_redacted_corpus_and_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            out = root / "ditto-out"
            write_jsonl(logs / "codex.jsonl", [
                {
                    "timestamp": "2026-07-08T10:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"text": "api_key=supersecret123 do the smallest fix"}],
                    },
                },
                {
                    "timestamp": "2026-07-08T10:01:00Z",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"text": "assistant output should not appear"}],
                    },
                },
            ])

            result = subprocess.run(
                [sys.executable, str(DITTO), "--path", str(logs), "--out", str(out), "--chunks", "1"],
                check=True,
                capture_output=True,
                text=True,
            )

            corpus = (out / "you-corpus.txt").read_text(encoding="utf-8")
            chunk = (out / "chunks" / "chunk-01.txt").read_text(encoding="utf-8")

            self.assertIn("sessions: 1", result.stdout)
            self.assertIn("api_key=[REDACTED]", corpus)
            self.assertNotIn("supersecret123", corpus)
            self.assertNotIn("assistant output should not appear", corpus)
            self.assertEqual(corpus, chunk)

    def test_install_codex_writes_skill_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            profile = root / "you.md"
            profile.write_text(
                "---\nname: you\ndescription: test profile\n---\n\n# profile\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "--install",
                    str(profile),
                    "--target",
                    "codex",
                    "--home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            dest = home / ".codex" / "skills" / "you" / "SKILL.md"
            self.assertEqual(profile.read_text(encoding="utf-8"), dest.read_text(encoding="utf-8"))

            second = subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "--install",
                    str(profile),
                    "--target",
                    "codex",
                    "--home",
                    str(home),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("destination already exists", second.stdout)

    def test_install_agents_appends_marked_block_without_deleting_existing_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            agents = repo / "AGENTS.md"
            agents.write_text("# existing rules\n\nkeep this\n", encoding="utf-8")
            profile = root / "you.md"
            profile.write_text(
                "---\nname: you\ndescription: test profile\n---\n\n# profile\n\n- done means live\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "--install",
                    str(profile),
                    "--target",
                    "agents",
                    "--repo",
                    str(repo),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            installed = agents.read_text(encoding="utf-8")
            self.assertIn("keep this", installed)
            self.assertIn("<!-- ditto profile:start -->", installed)
            self.assertIn("- done means live", installed)
            self.assertNotIn("name: you", installed)

    def test_install_cursor_writes_mdc_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            profile = root / "you.md"
            profile.write_text(
                "---\nname: you\ndescription: test profile\n---\n\n# profile\n\n- keep answers short\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "--install",
                    str(profile),
                    "--target",
                    "cursor",
                    "--repo",
                    str(repo),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            rule = (repo / ".cursor" / "rules" / "you.mdc").read_text(encoding="utf-8")
            self.assertTrue(rule.startswith("---\ndescription: ditto user profile\nalwaysApply: true\n---"))
            self.assertIn("- keep answers short", rule)
            self.assertNotIn("name: you", rule)

    def test_dedupe_collapses_repeated_long_messages_keeps_short(self):
        long_spec = "PLEASE IMPLEMENT THIS PLAN: " + ("do the thing carefully. " * 20)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            out = root / "ditto-out"
            rows = []
            # same long spec pasted into three sessions + short "yes" repeated three times
            for i in range(3):
                rows.append({
                    "timestamp": f"2026-07-0{i+1}T10:00:00Z",
                    "payload": {"type": "message", "role": "user", "content": [{"text": long_spec}]},
                })
                rows.append({
                    "timestamp": f"2026-07-0{i+1}T10:01:00Z",
                    "payload": {"type": "message", "role": "user", "content": [{"text": "yes"}]},
                })
            write_jsonl(logs / "codex.jsonl", rows)

            result = subprocess.run(
                [sys.executable, str(DITTO), "--path", str(logs), "--out", str(out), "--chunks", "1"],
                check=True, capture_output=True, text=True,
            )
            self.assertIn("duplicate specs/rules collapsed: 2", result.stdout)
            corpus = (out / "you-corpus.txt").read_text(encoding="utf-8")
            self.assertEqual(corpus.count("PLEASE IMPLEMENT THIS PLAN"), 1)   # long spec kept once
            self.assertEqual(corpus.count("\nyes"), 3)                        # every short "yes" kept

            # --no-dedupe keeps all three copies
            out2 = root / "ditto-out2"
            subprocess.run(
                [sys.executable, str(DITTO), "--path", str(logs), "--out", str(out2), "--chunks", "1", "--no-dedupe"],
                check=True, capture_output=True, text=True,
            )
            corpus2 = (out2 / "you-corpus.txt").read_text(encoding="utf-8")
            self.assertEqual(corpus2.count("PLEASE IMPLEMENT THIS PLAN"), 3)

    def test_run_writes_stats_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            out = root / "ditto-out"
            write_jsonl(logs / "codex.jsonl", [
                {
                    "timestamp": "2025-11-02T10:00:00Z",
                    "payload": {"type": "message", "role": "user", "content": [{"text": "first message"}]},
                },
                {
                    "timestamp": "2026-07-08T10:00:00Z",
                    "payload": {"type": "message", "role": "user", "content": [{"text": "last message"}]},
                },
            ])

            subprocess.run(
                [sys.executable, str(DITTO), "--path", str(logs), "--out", str(out), "--chunks", "1"],
                check=True,
                capture_output=True,
                text=True,
            )

            stats = json.loads((out / "stats.json").read_text(encoding="utf-8"))
            self.assertEqual(stats["sessions"], 1)
            self.assertEqual(stats["messages"], 2)
            self.assertEqual(stats["first_date"], "2025-11-02")
            self.assertEqual(stats["last_date"], "2026-07-08")

    def test_card_renders_terminal_and_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "ditto-out"
            out.mkdir()
            (out / "card.json").write_text(json.dumps({
                "archetype": "Proof-First Builder",
                "laws": [
                    {"text": "done means it runs live", "count": "18/20"},
                    {"text": "fix the one thing", "count": "15/20"},
                ],
                "truth": "asks the agent to explain his own system back",
            }), encoding="utf-8")
            (out / "stats.json").write_text(json.dumps({
                "sessions": 1656,
                "messages": 7678,
                "tokens": 2950000,
                "first_date": "2025-11-02",
                "last_date": "2026-07-08",
            }), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(DITTO), "--card", "--out", str(out), "--no-open"],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("PROOF-FIRST BUILDER", result.stdout)
            self.assertIn("[18/20]", result.stdout)
            self.assertIn("1,656 sessions", result.stdout)
            self.assertIn("9 months", result.stdout)
            html = (out / "card.html").read_text(encoding="utf-8")
            self.assertIn("Proof-First Builder", html)
            self.assertIn("18/20", html)
            self.assertIn("3.0M", html)
            self.assertIn("&rarr;", html)
            self.assertNotIn("�", html)

    def test_card_without_card_json_fails_with_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "ditto-out"
            out.mkdir()
            result = subprocess.run(
                [sys.executable, str(DITTO), "--card", "--out", str(out), "--no-open"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no card found", result.stdout)

    def test_zero_valid_sessions_fails_without_writing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            logs.mkdir()
            (logs / "bad.jsonl").write_text("{}\nnot-json\n", encoding="utf-8")
            out = root / "out"
            result = subprocess.run(
                [sys.executable, str(DITTO), "--path", str(logs), "--out", str(out)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no valid user sessions", result.stderr)
            self.assertFalse(out.exists())

    def test_install_rejects_substring_frontmatter_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "bad.md"
            profile.write_text(
                "---\nnotname: you\nnotdescription: wrong\n---\nbody\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "--install",
                    str(profile),
                    "--target",
                    "codex",
                    "--home",
                    str(root / "home"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exact name and description", result.stderr)


if __name__ == "__main__":
    unittest.main()
