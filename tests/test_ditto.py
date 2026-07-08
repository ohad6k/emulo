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


if __name__ == "__main__":
    unittest.main()
