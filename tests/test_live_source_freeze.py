import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DITTO = ROOT / "ditto.py"


def message(text, timestamp):
    return json.dumps({
        "type": "response_item",
        "timestamp": timestamp,
        "payload": {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": text}],
        },
    }) + "\n"


class LiveSourceFreezeTest(unittest.TestCase):
    def test_frozen_regular_run_survives_live_history_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            logs.mkdir()
            source = logs / "session.jsonl"
            source.write_text(
                message("specific working preference", "2026-01-01T00:00:00Z"),
                encoding="utf-8",
            )
            home = root / "private"

            result = subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "plugin",
                    "freeze",
                    "--path",
                    str(logs),
                    "--ditto-home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            frozen = json.loads(result.stdout)
            plan_path = Path(frozen["run_dir"]) / "plan.json"
            segment_path = Path(frozen["selected_segments"][0]["segment_path"])
            frozen_plan = plan_path.read_bytes()
            frozen_segment = segment_path.read_bytes()

            with source.open("a", encoding="utf-8") as handle:
                handle.write(message("approval changed live history", "2026-01-01T00:01:00Z"))

            refreshed = subprocess.run(
                [
                    sys.executable,
                    str(DITTO),
                    "plugin",
                    "preflight",
                    "--path",
                    str(logs),
                    "--ditto-home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            refreshed_plan = json.loads(refreshed.stdout)

            self.assertNotEqual(frozen["approval_hash"], refreshed_plan["approval_hash"])
            self.assertEqual(frozen_plan, plan_path.read_bytes())
            self.assertEqual(frozen_segment, segment_path.read_bytes())
            self.assertNotIn(b"approval changed live history", frozen_segment)
            self.assertEqual(1, frozen["valid_sessions"])
            self.assertEqual(1, frozen["planned_worker_calls"])
            self.assertEqual(1, frozen["planned_reducer_calls"])


if __name__ == "__main__":
    unittest.main()
