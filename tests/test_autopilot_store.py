import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from emulo_autopilot import contracts
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

    def _approved_candidate(
        self,
        statement="Verify the live URL before claiming deployment is complete.",
        domain="work",
        decision="approve",
        policy_class="review",
    ):
        candidate = candidate_fixture(statement=statement)
        candidate["domain"] = domain
        candidate["candidate_id"] = contracts.candidate_identity(candidate)
        self.store.put_candidate(candidate)
        self.store.append_decision(
            decision_fixture(
                candidate["candidate_id"],
                decision=decision,
                reason="founder-review" if decision == "approve" else "contradiction",
                policy_class=policy_class,
            )
        )
        return candidate

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

    def test_generation_head_is_absent_until_activation(self):
        self.assertIsNone(self.store.get_head())

    def test_activation_requires_newest_explicit_approval(self):
        missing = candidate_fixture()["candidate_id"]
        with self.assertRaisesRegex(ValueError, "candidate"):
            self.store.activate([missing], "2026-07-16T12:00:00Z")

        candidate = candidate_fixture(statement="Keep release claims evidence-bound.")
        self.store.put_candidate(candidate)
        with self.assertRaisesRegex(ValueError, "approval"):
            self.store.activate(
                [candidate["candidate_id"]], "2026-07-16T12:00:00Z"
            )

        self.store.append_decision(
            decision_fixture(
                candidate["candidate_id"],
                decision="reject",
                reason="contradiction",
                policy_class="review",
            )
        )
        with self.assertRaisesRegex(ValueError, "approval"):
            self.store.activate(
                [candidate["candidate_id"]], "2026-07-16T12:00:00Z"
            )

        unsafe = self._approved_candidate(
            statement="Publish without review.", policy_class="reject"
        )
        with self.assertRaisesRegex(ValueError, "policy"):
            self.store.activate(
                [unsafe["candidate_id"]], "2026-07-16T12:00:00Z"
            )

    def test_activation_is_deterministic_additive_and_idempotent(self):
        work_b = self._approved_candidate(statement="Run tests before release.")
        work_a = self._approved_candidate(statement="Keep a rollback checkpoint.")
        design = self._approved_candidate(
            statement="Change structure before visual polish.", domain="design"
        )

        first = self.store.activate(
            [work_b["candidate_id"], work_a["candidate_id"]],
            "2026-07-16T12:00:00Z",
        )
        self.assertEqual(
            sorted([work_a["candidate_id"], work_b["candidate_id"]]),
            first["candidate_ids"],
        )
        expected_work = (
            "# Emulo Autopilot overlay: work\n\n"
            "Evidence-backed personal rules supplementing the active Emulo profile:\n\n"
            + "".join(
                "- " + candidate["statement"] + "\n"
                for candidate in sorted(
                    [work_a, work_b], key=lambda item: item["candidate_id"]
                )
            )
        )
        self.assertEqual(expected_work, self.store.read_active_domain("work"))
        self.assertIsNone(self.store.read_active_domain("design"))

        same = self.store.activate(
            [work_a["candidate_id"]], "2026-07-16T12:01:00Z"
        )
        self.assertEqual(first, same)

        second = self.store.activate(
            [design["candidate_id"]], "2026-07-16T12:02:00Z"
        )
        self.assertEqual(first["generation_id"], second["parent_generation_id"])
        self.assertEqual(expected_work, self.store.read_active_domain("work"))
        self.assertIn(design["statement"], self.store.read_active_domain("design"))

    def test_generation_reads_fail_closed_on_tampering(self):
        candidate = self._approved_candidate()
        generation = self.store.activate(
            [candidate["candidate_id"]], "2026-07-16T12:00:00Z"
        )
        root = self.home / "autopilot" / "generations" / generation["generation_id"]

        head_path = self.home / "autopilot" / "head.json"
        head_bytes = head_path.read_bytes()
        head_path.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "head is corrupt"):
            self.store.get_head()
        head_path.write_bytes(head_bytes)

        artifact = root / "work.md"
        artifact_bytes = artifact.read_bytes()
        artifact.write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "generation is corrupt"):
            self.store.get_generation(generation["generation_id"])
        artifact.write_bytes(artifact_bytes)

        manifest = root / "generation.json"
        manifest_bytes = manifest.read_bytes()
        manifest.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "generation is corrupt"):
            self.store.get_generation(generation["generation_id"])
        manifest.write_bytes(manifest_bytes)

        (root / "extra.txt").write_text("unexpected", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "generation is corrupt"):
            self.store.get_generation(generation["generation_id"])

    def test_failed_head_write_preserves_previous_pointer(self):
        first_candidate = self._approved_candidate(statement="Keep the first rule.")
        first = self.store.activate(
            [first_candidate["candidate_id"]], "2026-07-16T12:00:00Z"
        )
        head_path = self.home / "autopilot" / "head.json"
        before = head_path.read_bytes()
        second_candidate = self._approved_candidate(statement="Keep the second rule.")
        real_write = self.store.atomic_write_json

        def fail_head(path, value):
            if Path(path).name == "head.json":
                raise OSError("injected head failure")
            return real_write(path, value)

        with mock.patch.object(self.store, "atomic_write_json", side_effect=fail_head):
            with self.assertRaisesRegex(OSError, "injected head failure"):
                self.store.activate(
                    [second_candidate["candidate_id"]],
                    "2026-07-16T12:01:00Z",
                )

        self.assertEqual(before, head_path.read_bytes())
        self.assertEqual(first["generation_id"], self.store.get_head()["generation_id"])

    def test_rollback_is_append_only_and_restores_exact_target(self):
        first_candidate = self._approved_candidate(statement="Keep the first rule.")
        first = self.store.activate(
            [first_candidate["candidate_id"]], "2026-07-16T12:00:00Z"
        )
        first_bytes = self.store.read_domain(first["generation_id"], "work")
        second_candidate = self._approved_candidate(statement="Keep the second rule.")
        second = self.store.activate(
            [second_candidate["candidate_id"]], "2026-07-16T12:01:00Z"
        )

        with self.assertRaisesRegex(ValueError, "ancestor"):
            self.store.rollback("gen_" + "f" * 20, "2026-07-16T12:02:00Z")

        rolled_back = self.store.rollback(
            first["generation_id"], "2026-07-16T12:03:00Z"
        )
        self.assertEqual("rollback", rolled_back["operation"])
        self.assertEqual(second["generation_id"], rolled_back["parent_generation_id"])
        self.assertEqual(first["candidate_ids"], rolled_back["candidate_ids"])
        self.assertEqual(first_bytes, self.store.read_active_domain("work"))
        generations = self.home / "autopilot" / "generations"
        self.assertTrue((generations / first["generation_id"]).is_dir())
        self.assertTrue((generations / second["generation_id"]).is_dir())
        self.assertTrue((generations / rolled_back["generation_id"]).is_dir())

    def test_candidate_inventory_is_sorted_and_fails_closed(self):
        second = candidate_fixture(statement="Second inventory rule.")
        first = candidate_fixture(statement="First inventory rule.")
        self.store.put_candidate(second)
        self.store.put_candidate(first)
        self.assertEqual(
            sorted([first["candidate_id"], second["candidate_id"]]),
            [item["candidate_id"] for item in self.store.list_candidates()],
        )

        root = self.home / "autopilot" / "candidates"
        (root / "notes.txt").write_text("unexpected", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unexpected candidate"):
            self.store.list_candidates()

    def test_generation_inventory_is_sorted_and_fails_closed(self):
        first_candidate = self._approved_candidate(statement="Inventory one.")
        first = self.store.activate(
            [first_candidate["candidate_id"]], "2026-07-16T12:00:00Z"
        )
        second_candidate = self._approved_candidate(statement="Inventory two.")
        second = self.store.activate(
            [second_candidate["candidate_id"]], "2026-07-16T12:01:00Z"
        )
        self.assertEqual(
            sorted([first["generation_id"], second["generation_id"]]),
            [item["generation_id"] for item in self.store.list_generations()],
        )

        root = self.home / "autopilot" / "generations"
        (root / "notes.txt").write_text("unexpected", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unexpected generation"):
            self.store.list_generations()

    def test_lock_inventory_is_missing_visible_and_corrupt_safe(self):
        self.assertIsNone(self.store.get_lock())
        context = self.store.lock("activate")
        record = context.__enter__()
        try:
            self.assertEqual(record, self.store.get_lock())
        finally:
            context.__exit__(None, None, None)

        lock = self.home / "autopilot" / "lock.json"
        lock.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "lock record"):
            self.store.get_lock()


if __name__ == "__main__":
    unittest.main()
