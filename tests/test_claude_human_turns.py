import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ditto", ROOT / "ditto.py")
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)


def claude_record(text, **extra):
    record = {
        "type": "user",
        "timestamp": "2026-07-12T00:00:00Z",
        "message": {"role": "user", "content": text},
    }
    record.update(extra)
    return record


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def mine(records):
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "session.jsonl"
        write_jsonl(log, records)
        return [t for _, t in ditto.user_messages(str(log))]


class IsHumanTurnTest(unittest.TestCase):
    def test_harness_markers_disqualify(self):
        self.assertFalse(ditto.is_human_turn({"isMeta": True}))
        self.assertFalse(ditto.is_human_turn({"isSidechain": True}))
        self.assertFalse(ditto.is_human_turn({"toolUseResult": {"ok": True}}))
        self.assertFalse(ditto.is_human_turn({"isCompactSummary": True}))

    def test_origin_kind_is_authoritative(self):
        self.assertTrue(ditto.is_human_turn(
            {"origin": {"kind": "human"}, "promptSource": "sdk"}))
        self.assertFalse(ditto.is_human_turn(
            {"origin": {"kind": "task-notification"}}))

    def test_prompt_source_sdk_only_disqualifies_headless(self):
        # Claude Desktop stamps promptSource="sdk" on typed prompts.
        self.assertTrue(ditto.is_human_turn(
            {"promptSource": "sdk", "entrypoint": "claude-desktop"}))
        self.assertFalse(ditto.is_human_turn(
            {"promptSource": "sdk", "entrypoint": "sdk-cli"}))
        self.assertTrue(ditto.is_human_turn({}))


class ClaudeMiningTest(unittest.TestCase):
    def test_only_human_turns_are_mined(self):
        mined = mine([
            claude_record("a real typed prompt"),
            claude_record("meta record", isMeta=True),
            claude_record("sidechain record", isSidechain=True),
            claude_record("tool result", toolUseResult={"stdout": "x"}),
            claude_record("model-written summary", isCompactSummary=True),
            claude_record("notification", origin={"kind": "task-notification"}),
            claude_record("typed on desktop", promptSource="sdk",
                          entrypoint="claude-desktop", origin={"kind": "human"}),
            claude_record("headless prompt", promptSource="sdk",
                          entrypoint="sdk-cli"),
        ])
        self.assertEqual(["a real typed prompt", "typed on desktop"], mined)

    def test_injected_command_and_notification_turns_are_dropped(self):
        mined = mine([
            claude_record("<command-name>/clear</command-name>"),
            claude_record("<local-command-stdout>output</local-command-stdout>"),
            claude_record("<task-notification>done</task-notification>"),
            claude_record("[Request interrupted by user]"),
            claude_record("still a real prompt"),
        ])
        self.assertEqual(["still a real prompt"], mined)


class SubagentPathFilterTest(unittest.TestCase):
    def test_subagent_transcripts_are_skipped_by_path_component(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(root / "proj" / "main.jsonl", [claude_record("human")])
            write_jsonl(root / "proj" / "subagents" / "agent.jsonl",
                        [claude_record("machine")])
            write_jsonl(root / "my-subagents-notes" / "notes.jsonl",
                        [claude_record("also human")])
            files = ditto.discover_files([str(root)])
            names = {os.path.basename(f) for f in files}
            self.assertEqual({"main.jsonl", "notes.jsonl"}, names)


if __name__ == "__main__":
    unittest.main()
