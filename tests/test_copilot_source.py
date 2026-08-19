import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("emulo", ROOT / "emulo.py")
emulo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(emulo)


# Copilot CLI writes one events.jsonl per session under
# ~/.copilot/session-state/<session-id>/. Tests build that exact layout under a
# temp `.copilot` root so source_kind() (which routes on the path component)
# behaves the way it does on a real machine.
def session_dir(root, session_id):
    path = Path(root) / ".copilot" / "session-state" / session_id
    path.mkdir(parents=True)
    return path


def write_events(root, session_id, records, raw_lines=(), compact=False):
    path = session_dir(root, session_id) / "events.jsonl"
    separators = (",", ":") if compact else None
    body = "".join(json.dumps(r, separators=separators) + "\n" for r in records)
    body += "".join(line + "\n" for line in raw_lines)
    path.write_text(body, encoding="utf-8")
    return str(path)


def user_message(text, timestamp="2026-07-01T20:35:24.573Z", source=None, **data_extra):
    """A user.message event shaped like the real ones on disk.

    transformedContent is what the harness actually sent the model: the typed
    text wrapped in <current_datetime>/<system_reminder> blocks. Only `content`
    is prose the human typed, so it carries a distinct marker here.
    """
    data = {
        "content": text,
        "transformedContent": (
            "<current_datetime>2026-07-01T23:35:24.572+03:00</current_datetime>\n\n"
            f"{text}\n<system_reminder>harness expansion</system_reminder>"
        ),
        "attachments": [],
        "delivery": "idle",
        "agentMode": "plan",
    }
    if source is not None:
        data["source"] = source
    data.update(data_extra)
    return {
        "type": "user.message",
        "data": data,
        "id": "evt-1",
        "parentId": None,
        "timestamp": timestamp,
    }


class CopilotDiscoveryTest(unittest.TestCase):
    def test_discovers_one_events_file_per_session_and_ignores_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = write_events(tmp, "sess-a", [user_message("ship the fix tonight")])
            second = write_events(tmp, "sess-b", [user_message("done means live proof")])
            # Copilot keeps non-transcript state next to events.jsonl; none of it
            # is a session and none of it may enter discovery.
            state = Path(tmp) / ".copilot" / "session-state"
            (state / "sess-a" / "workspace.yaml").write_text("cwd: /repo\n", encoding="utf-8")
            (state / "sess-a" / "checkpoints").mkdir()
            (state / "sess-a" / "checkpoints" / "cp1.json").write_text("{}", encoding="utf-8")

            self.assertEqual([first, second], emulo.discover_files([str(state)]))

    def test_subagents_transcripts_are_dropped_by_path_component(self):
        with tempfile.TemporaryDirectory() as tmp:
            kept = write_events(tmp, "sess-a", [user_message("keep this one")])
            state = Path(tmp) / ".copilot" / "session-state"
            nested = state / "sess-a" / "subagents" / "sub-1"
            nested.mkdir(parents=True)
            (nested / "events.jsonl").write_text(
                json.dumps(user_message("agent-to-agent traffic")) + "\n", encoding="utf-8"
            )
            # a directory that merely contains the word must still be mined
            lookalike = state / "my-subagents-notes"
            lookalike.mkdir()
            (lookalike / "events.jsonl").write_text(
                json.dumps(user_message("notes I typed")) + "\n", encoding="utf-8"
            )

            found = emulo.discover_files([str(state)])
            self.assertEqual(sorted([kept, str(lookalike / "events.jsonl")]), found)

    def test_missing_or_empty_root_is_quiet(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([], emulo.discover_files([tmp]))
            self.assertEqual([], emulo.discover_files([str(Path(tmp) / "nope")]))

    def test_registered_in_sources_under_dot_copilot(self):
        self.assertIn("copilot", emulo.SOURCES)
        self.assertEqual(1, len(emulo.SOURCES["copilot"]))
        self.assertTrue(
            emulo.SOURCES["copilot"][0].endswith(str(Path(".copilot") / "session-state"))
        )


class CopilotExtractionTest(unittest.TestCase):
    def test_mines_typed_content_not_the_harness_expansion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_events(tmp, "sess-a", [user_message("verify before you claim")])
            mined = emulo.user_messages(path)
            self.assertEqual([("2026-07-01", "verify before you claim")], mined)
            # transformedContent is the model-facing string; mining it would pull
            # harness-injected blocks into the corpus.
            self.assertNotIn("system_reminder", mined[0][1])

    def test_compact_and_spaced_serialization_both_mine(self):
        # The line-marker fast path matches raw text before json.loads, so both
        # `"type":"user.message"` (what Copilot writes) and the spaced form must
        # survive it.
        with tempfile.TemporaryDirectory() as tmp:
            compact = write_events(tmp, "sess-a", [user_message("compact line")], compact=True)
            spaced = write_events(tmp, "sess-b", [user_message("spaced line")])
            self.assertEqual([("2026-07-01", "compact line")], emulo.user_messages(compact))
            self.assertEqual([("2026-07-01", "spaced line")], emulo.user_messages(spaced))

    def test_system_source_events_are_dropped_and_typed_turns_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_events(tmp, "sess-a", [
                user_message("first thing I typed"),
                user_message("steering injected by the harness", source="system"),
                user_message("second thing I typed", source="user"),
                # current Copilot builds omit data.source entirely; absence must
                # never be read as a system injection
                user_message("third thing I typed"),
            ])
            self.assertEqual(
                ["first thing I typed", "second thing I typed", "third thing I typed"],
                [t for _, t in emulo.user_messages(path)],
            )

    def test_non_user_event_types_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_events(tmp, "sess-a", [
                {"type": "session.info", "data": {"cwd": "/repo"},
                 "timestamp": "2026-07-01T20:00:00.000Z"},
                {"type": "assistant.message", "data": {"content": "model reply"},
                 "timestamp": "2026-07-01T20:30:00.000Z"},
                user_message("only this is mine"),
                {"type": "tool.execution_start", "data": {"name": "bash", "content": "ls"},
                 "timestamp": "2026-07-01T20:36:00.000Z"},
                {"type": "system.message", "data": {"content": "context compacted"},
                 "timestamp": "2026-07-01T20:37:00.000Z"},
                {"type": "subagent.started", "data": {"content": "delegating"},
                 "timestamp": "2026-07-01T20:38:00.000Z"},
            ])
            self.assertEqual([("2026-07-01", "only this is mine")], emulo.user_messages(path))

    def test_malformed_line_is_skipped_and_later_turns_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_events(
                tmp, "sess-a",
                [user_message("before the tear", timestamp="2026-07-01T20:35:24.573Z")],
                raw_lines=[
                    '{"type":"user.message","data":{"content":"half written',   # torn write
                    "",                                                          # blank line
                    "not json at all",
                ],
            )
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(
                    user_message("after the tear", timestamp="2026-07-02T09:00:00.000Z")) + "\n")
            self.assertEqual(
                [("2026-07-01", "before the tear"), ("2026-07-02", "after the tear")],
                emulo.user_messages(path),
            )

    def test_empty_session_yields_nothing_and_is_not_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = session_dir(tmp, "sess-empty") / "events.jsonl"
            empty.write_text("", encoding="utf-8")
            no_turns = write_events(tmp, "sess-quiet", [
                {"type": "session.info", "data": {"cwd": "/repo"},
                 "timestamp": "2026-07-01T20:00:00.000Z"},
            ])
            self.assertEqual([], emulo.user_messages(str(empty)))
            self.assertEqual([], emulo.user_messages(no_turns))

            stats = emulo.mine_files([str(empty), no_turns])
            self.assertEqual(0, stats["sessions"])
            self.assertEqual(0, stats["messages"])

    def test_injected_context_and_pasted_logs_are_not_mined(self):
        with tempfile.TemporaryDirectory() as tmp:
            traceback = (
                "Traceback (most recent call last):\n"
                '  File "emulo.py", line 400, in user_messages\n'
                "    texts = [data.get('content', '')]\n"
                "AttributeError: 'NoneType' object has no attribute 'get'\n"
            )
            path = write_events(tmp, "sess-a", [
                user_message("# AGENTS.md instructions\n\nalways run the suite"),
                user_message(traceback),
                user_message("   \n  "),
                user_message("this one is real"),
            ])
            self.assertEqual([("2026-07-01", "this one is real")], emulo.user_messages(path))


class CopilotSessionIdentityTest(unittest.TestCase):
    def test_source_kind_and_per_session_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = write_events(tmp, "33e9c951-f45c", [user_message("one")])
            second = write_events(tmp, "c280372f-13b5", [user_message("two")])

            self.assertEqual("copilot", emulo.source_kind(first))
            # every Copilot transcript is named events.jsonl, so the label has to
            # carry the session id or all block headers collapse to one string
            self.assertEqual("33e9c951-f45c/events.jsonl", emulo.session_label(first))
            self.assertNotEqual(emulo.session_label(first), emulo.session_label(second))
            self.assertNotEqual(emulo.stable_session_id(first), emulo.stable_session_id(second))

    def test_mine_files_tags_records_as_copilot_with_real_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_events(tmp, "sess-a", [
                user_message("start the run", timestamp="2026-07-01T20:35:24.573Z"),
                user_message("harness steering", source="system",
                             timestamp="2026-07-01T20:36:00.000Z"),
                user_message("ship it", timestamp="2026-07-03T08:12:00.000Z"),
            ])
            stats = emulo.mine_files([path])
            self.assertEqual(1, stats["sessions"])
            self.assertEqual(2, stats["messages"])

            record = stats["records"][0]
            self.assertEqual("copilot", record["source"])
            self.assertEqual("2026-07-01", record["first_date"])
            self.assertEqual("2026-07-03", record["last_date"])
            self.assertEqual(["start the run", "ship it"],
                             [m["text"] for m in record["messages"]])
            self.assertIn("source:copilot", record["text"])
            self.assertNotIn("harness steering", record["text"])

    def test_redaction_runs_on_copilot_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_events(tmp, "sess-a", [
                user_message("push with token ghp_abcdefghijklmnopqrstuvwxyz012345"),
            ])
            stats = emulo.mine_files([path])
            self.assertEqual(1, stats["redactions"])
            self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz012345", stats["records"][0]["text"])
            self.assertIn("[GITHUB_TOKEN]", stats["records"][0]["text"])


if __name__ == "__main__":
    unittest.main()
