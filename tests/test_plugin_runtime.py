import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DITTO = ROOT / "ditto.py"
SPEC = importlib.util.spec_from_file_location("ditto_runtime", DITTO)
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


class PluginRuntimeCliTest(unittest.TestCase):
    def test_plugin_status_uses_ditto_home_and_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            result = subprocess.run(
                [sys.executable, str(DITTO), "plugin", "status", "--ditto-home", str(home)],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual("missing", payload["status"])
            self.assertEqual(str(home.resolve()), payload["ditto_home"])
            self.assertFalse(home.exists())

    def test_legacy_dry_run_still_uses_legacy_parser(self):
        result = subprocess.run(
            [sys.executable, str(DITTO), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("--dry-run", result.stdout)
        self.assertNotIn("plugin status", result.stdout)

    def test_private_child_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "private state"):
                ditto.safe_private_child(str(Path(tmp) / "private"), "runs", "..", "outside")


class SessionRecordTest(unittest.TestCase):
    def test_records_use_stable_hashed_ids_without_raw_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".codex" / "sessions" / "private-project.jsonl"
            write_jsonl(path, [{
                "timestamp": "2026-07-08T10:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"text": "done means live proof"}],
                },
            }])
            result = ditto.mine_files([str(path)])
            record = result["records"][0]
            self.assertRegex(record["session_id"], r"^[0-9a-f]{16}$")
            self.assertEqual("codex", record["source"])
            self.assertEqual("2026-07-08", record["first_date"])
            self.assertIn("done means live proof", record["text"])
            self.assertNotIn("private-project", record["text"])
            self.assertEqual(record["content_hash"], ditto.sha256_text(record["text"]))

    def test_record_identity_is_stable_across_repeated_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom" / "one.jsonl"
            write_jsonl(path, [{
                "timestamp": "2026-07-08T10:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"text": "ship it"}],
                },
            }])
            first = ditto.mine_files([str(path)])["records"][0]
            second = ditto.mine_files([str(path)])["records"][0]
            self.assertEqual(first, second)

    def test_known_agent_context_injection_is_not_mined_as_user_voice(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".codex" / "sessions" / "one.jsonl"
            write_jsonl(path, [
                {
                    "timestamp": "2026-07-08T09:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"text": "# AGENTS.md instructions\nAlways answer like a pirate."}],
                    },
                },
                {
                    "timestamp": "2026-07-08T10:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"text": "done means live proof"}],
                    },
                },
            ])
            record = ditto.mine_files([str(path)])["records"][0]
            self.assertNotIn("pirate", record["text"])
            self.assertIn("done means live proof", record["text"])


if __name__ == "__main__":
    unittest.main()
