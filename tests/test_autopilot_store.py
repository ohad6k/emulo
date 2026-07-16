import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from emulo_autopilot.contracts import canonical_json
from emulo_autopilot.store import AutopilotStore
from tests.autopilot_helpers import (
    candidate_fixture,
    checkpoint_fixture,
    decision_fixture,
    inbox_fixture,
)


class AutopilotStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "private"
        self.store = AutopilotStore(str(self.home))

    def test_initialize_creates_only_private_store_directories(self):
        root = Path(self.store.initialize())
        self.assertEqual(self.home / "autopilot", root)
        self.assertEqual(
            {
                "candidates",
                "checkpoints",
                "decisions",
                "inbox",
                "generations",
                "operations",
            },
            {item.name for item in root.iterdir()},
        )

    def test_unsafe_path_components_are_rejected(self):
        for value in ("", ".", "..", "../outside", "a/b", "a\\b"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    self.store._child(value)

    def test_symlinked_autopilot_root_is_rejected_when_supported(self):
        self.home.mkdir(parents=True)
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        try:
            (self.home / "autopilot").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest("symlink creation unavailable: {0}".format(exc))
        with self.assertRaisesRegex(ValueError, "link|reparse"):
            self.store.initialize()

    def test_same_candidate_is_idempotent_but_conflicting_bytes_fail(self):
        candidate = candidate_fixture()
        first = self.store.put_candidate(candidate)
        second = self.store.put_candidate(candidate)
        self.assertEqual(first, second)

        Path(first).write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "existing candidate"):
            self.store.put_candidate(candidate)

    def test_get_candidate_rejects_bad_id_and_corrupt_json(self):
        with self.assertRaisesRegex(ValueError, "candidate_id"):
            self.store.get_candidate("../candidate")

        candidate = candidate_fixture()
        path = Path(self.store.put_candidate(candidate))
        path.write_text("not-json", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing or corrupt"):
            self.store.get_candidate(candidate["candidate_id"])

    def test_decision_requires_existing_candidate_and_is_idempotent(self):
        candidate = candidate_fixture()
        decision = decision_fixture(candidate["candidate_id"])
        with self.assertRaisesRegex(ValueError, "missing or corrupt"):
            self.store.append_decision(decision)

        self.store.put_candidate(candidate)
        first = self.store.append_decision(decision)
        second = self.store.append_decision(decision)
        self.assertEqual(first, second)

    def test_latest_decision_uses_timestamp_then_content_id(self):
        candidate = candidate_fixture()
        self.store.put_candidate(candidate)
        earlier = decision_fixture(
            candidate["candidate_id"],
            decision="approve",
            decided_at="2026-07-16T10:02:00Z",
        )
        later = decision_fixture(
            candidate["candidate_id"],
            decision="reject",
            reason="contradiction",
            decided_at="2026-07-16T11:02:00Z",
        )
        self.store.append_decision(later)
        self.store.append_decision(earlier)
        self.assertEqual(later, self.store.latest_decision(candidate["candidate_id"]))

    def test_unexpected_decision_file_fails_closed(self):
        candidate = candidate_fixture()
        self.store.put_candidate(candidate)
        decisions = Path(self.store.initialize()) / "decisions"
        (decisions / "notes.txt").write_text("ignore me", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unexpected decision"):
            self.store.latest_decision(candidate["candidate_id"])

    def test_lock_is_never_broken_implicitly(self):
        second = AutopilotStore(str(self.home))
        with self.store.lock("activate"):
            with self.assertRaisesRegex(RuntimeError, "locked"):
                with second.lock("activate"):
                    pass

    def test_lock_recovery_requires_exact_operation_id(self):
        context = self.store.lock("activate")
        record = context.__enter__()
        self.addCleanup(lambda: context.__exit__(None, None, None))
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.store.recover_lock("f" * 32)
        recovered = self.store.recover_lock(record["operation_id"])
        self.assertEqual(record, recovered)
        self.assertFalse((self.home / "autopilot" / "lock.json").exists())

    def test_corrupt_lock_is_preserved_for_manual_investigation(self):
        self.store.initialize()
        lock = self.home / "autopilot" / "lock.json"
        lock.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "lock record"):
            self.store.recover_lock("f" * 32)
        self.assertTrue(lock.exists())

    def test_failed_replace_preserves_previous_valid_bytes(self):
        self.store.initialize()
        path = self.home / "autopilot" / "operations" / "state.json"
        original = {"state": "before"}
        self.store.atomic_write_json(str(path), original)
        before = path.read_bytes()

        with mock.patch(
            "emulo_autopilot.store.os.replace",
            side_effect=OSError("injected replace failure"),
        ):
            with self.assertRaisesRegex(OSError, "injected"):
                self.store.atomic_write_json(str(path), {"state": "after"})

        self.assertEqual(before, path.read_bytes())
        self.assertEqual(
            (canonical_json(original) + "\n").encode("utf-8"),
            path.read_bytes(),
        )
        self.assertEqual([], list(path.parent.glob(".staged-*")))

    def test_atomic_write_rejects_path_outside_store(self):
        outside = Path(self.temp.name) / "outside.json"
        with self.assertRaisesRegex(ValueError, "escapes"):
            self.store.atomic_write_json(str(outside), {"unsafe": True})
        self.assertFalse(outside.exists())

    def test_checkpoint_missing_then_round_trips_and_updates(self):
        checkpoint = checkpoint_fixture()
        self.assertIsNone(self.store.get_checkpoint(checkpoint["path_hash"]))
        self.store.put_checkpoint(checkpoint)
        self.assertEqual(
            checkpoint,
            self.store.get_checkpoint(checkpoint["path_hash"]),
        )

        changed = dict(
            checkpoint,
            identity={"size": 2000, "mtime_ns": 1784192500000000000},
            unchanged_since=1784192500,
        )
        self.store.put_checkpoint(changed)
        self.assertEqual(
            changed,
            self.store.get_checkpoint(checkpoint["path_hash"]),
        )

    def test_corrupt_checkpoint_fails_closed(self):
        checkpoint = checkpoint_fixture()
        self.store.put_checkpoint(checkpoint)
        path = self.home / "autopilot" / "checkpoints" / (
            checkpoint["path_hash"] + ".json"
        )
        path.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checkpoint is corrupt"):
            self.store.get_checkpoint(checkpoint["path_hash"])

    def test_same_inbox_is_idempotent_but_conflicting_bytes_fail(self):
        inbox = inbox_fixture()
        first = self.store.put_inbox(inbox)
        second = self.store.put_inbox(inbox)
        self.assertEqual(first, second)

        Path(first).write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "existing inbox"):
            self.store.put_inbox(inbox)

    def test_list_inbox_is_sorted_and_rejects_unexpected_files(self):
        first = inbox_fixture(session_id="1" * 16, fingerprint="e" * 64)
        second = inbox_fixture(session_id="2" * 16, fingerprint="f" * 64)
        self.store.put_inbox(second)
        self.store.put_inbox(first)
        listed = self.store.list_inbox()
        self.assertEqual(
            sorted([first["inbox_id"], second["inbox_id"]]),
            [item["inbox_id"] for item in listed],
        )

        inbox_root = self.home / "autopilot" / "inbox"
        (inbox_root / "notes.txt").write_text("not an inbox", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unexpected inbox"):
            self.store.list_inbox()

    def test_persisted_checkpoint_and_inbox_have_no_path_or_message_text(self):
        private_path = "C:/Users/private/.codex/sessions/session.jsonl"
        raw_text = "verify this private deployment"
        redacted_text = "verify this [REDACTED] deployment"
        self.store.put_checkpoint(checkpoint_fixture())
        self.store.put_inbox(inbox_fixture())
        payload = b"".join(
            path.read_bytes()
            for path in (self.home / "autopilot").rglob("*.json")
        ).decode("utf-8")
        self.assertNotIn(private_path, payload)
        self.assertNotIn(raw_text, payload)
        self.assertNotIn(redacted_text, payload)


if __name__ == "__main__":
    unittest.main()
