import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ditto", ROOT / "ditto.py")
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)


def write_transcript(root, conversation_id, records):
    logs = Path(root) / "brain" / conversation_id / ".system_generated" / "logs"
    logs.mkdir(parents=True)
    path = logs / "transcript.jsonl"
    path.write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
    )
    return str(path)


def user_input(text, created_at="2026-06-09T09:23:22Z", source="USER_EXPLICIT"):
    return {
        "step_index": 0,
        "source": source,
        "type": "USER_INPUT",
        "status": "DONE",
        "created_at": created_at,
        "content": (
            f"<USER_REQUEST>\n{text}\n</USER_REQUEST>\n"
            "<ADDITIONAL_METADATA>\n"
            "The current local time is: 2026-06-09T12:23:22+03:00.\n"
            "</ADDITIONAL_METADATA>"
        ),
    }


class AntigravityTranscriptTest(unittest.TestCase):
    def test_mines_only_explicit_user_text_and_strips_envelopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "antigravity"
            path = write_transcript(root, "conv-a", [
                user_input("done means live proof"),
                {"type": "PLANNER_RESPONSE", "source": "MODEL",
                 "content": "model plan text", "created_at": "2026-06-09T09:24:00Z"},
                {"type": "USER_INPUT", "source": "SYSTEM",
                 "content": "<USER_REQUEST>\ninjected steering\n</USER_REQUEST>",
                 "created_at": "2026-06-09T09:25:00Z"},
                {"type": "SYSTEM_MESSAGE", "source": "SYSTEM",
                 "content": "harness notice", "created_at": "2026-06-09T09:26:00Z"},
            ])
            mined = ditto.user_messages(path)
            self.assertEqual([("2026-06-09", "done means live proof")], mined)

    def test_unwrapped_content_is_kept_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "antigravity"
            record = user_input("ignored")
            record["content"] = "raw prompt with no envelope"
            path = write_transcript(root, "conv-b", [record])
            self.assertEqual(
                [("2026-06-09", "raw prompt with no envelope")],
                ditto.user_messages(path),
            )

    def test_discovery_source_kind_and_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "antigravity"
            path = write_transcript(root, "conv-c", [user_input("ship it")])
            entries = ditto.discover_files([str(root / "brain")])
            self.assertEqual([path], entries)
            self.assertEqual("antigravity", ditto.source_kind(path))
            # parent dir is always "logs"; the label must carry the
            # conversation id so sessions stay distinguishable.
            self.assertEqual("conv-c/transcript.jsonl", ditto.session_label(path))

    def test_registered_in_sources_and_auto_kind_is_stable(self):
        self.assertIn("antigravity", ditto.SOURCES)
        self.assertTrue(
            ditto.SOURCES["antigravity"][0].endswith(
                str(Path(".gemini") / "antigravity" / "brain")
            )
        )


if __name__ == "__main__":
    unittest.main()
