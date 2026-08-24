import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from emulo_autopilot import cli, contracts
from emulo_autopilot.store import AutopilotStore
from tests.autopilot_helpers import candidate_fixture

try:
    import cryptography  # noqa: F401 - presence check only
    HAS_CRYPTO = True
except ImportError:  # pragma: no cover - exercised only in a core-only install
    HAS_CRYPTO = False


class AutopilotCliTest(unittest.TestCase):
    NOW = 1784210400
    NOW_TEXT = "2026-07-16T14:00:00Z"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = self.temp.name
        self.store = AutopilotStore(self.home)

    def _candidate(self, statement, risk_categories=None):
        candidate = candidate_fixture(
            statement=statement,
            risk_categories=risk_categories,
        )
        candidate["candidate_id"] = contracts.candidate_identity(candidate)
        self.store.put_candidate(candidate)
        return candidate

    def invoke(self, *arguments, secret_reader=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = 0
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                cli.main(
                    ["--emulo-home", self.home] + list(arguments),
                    clock=lambda: self.NOW,
                    secret_reader=(
                        (lambda _prompt: "")
                        if secret_reader is None
                        else secret_reader
                    ),
                )
        except SystemExit as exc:
            code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_status_and_queue_are_json(self):
        candidate = self._candidate("Review this local CLI rule.")
        code, stdout, stderr = self.invoke("status")
        self.assertEqual(0, code)
        self.assertEqual("", stderr)
        self.assertEqual("ready", json.loads(stdout)["health"])

        code, stdout, stderr = self.invoke("queue")
        self.assertEqual(0, code)
        self.assertEqual("", stderr)
        item = json.loads(stdout)["items"][0]
        self.assertEqual(candidate["candidate_id"], item["candidate_id"])
        self.assertEqual("pending", item["decision"])

    def test_review_activate_history_and_rollback_work_end_to_end(self):
        first_candidate = self._candidate("Keep the first CLI rule.")
        code, stdout, stderr = self.invoke(
            "review",
            first_candidate["candidate_id"],
            "approve",
            "--reason",
            "founder-review",
        )
        self.assertEqual((0, ""), (code, stderr))
        self.assertEqual(self.NOW_TEXT, json.loads(stdout)["decided_at"])

        code, stdout, stderr = self.invoke(
            "activate", first_candidate["candidate_id"]
        )
        self.assertEqual((0, ""), (code, stderr))
        first = json.loads(stdout)
        self.assertEqual("activate", first["operation"])

        second_candidate = self._candidate("Keep the second CLI rule.")
        self.invoke(
            "review",
            second_candidate["candidate_id"],
            "approve",
            "--reason",
            "founder-review",
        )
        code, stdout, stderr = self.invoke(
            "activate", second_candidate["candidate_id"]
        )
        self.assertEqual((0, ""), (code, stderr))
        second = json.loads(stdout)

        code, stdout, stderr = self.invoke("history")
        history = json.loads(stdout)
        self.assertEqual((0, ""), (code, stderr))
        self.assertEqual(second["generation_id"], history["active_generation_id"])
        self.assertEqual(2, len(history["generations"]))

        code, stdout, stderr = self.invoke(
            "rollback", first["generation_id"]
        )
        self.assertEqual((0, ""), (code, stderr))
        rollback = json.loads(stdout)
        self.assertEqual("rollback", rollback["operation"])
        self.assertEqual(second["generation_id"], rollback["parent_generation_id"])
        self.assertEqual(first["candidate_ids"], rollback["candidate_ids"])

    def test_rejected_policy_approval_is_json_error(self):
        candidate = self._candidate(
            "Use an unknown risky action.", risk_categories=["novel-risk"]
        )
        code, stdout, stderr = self.invoke(
            "review",
            candidate["candidate_id"],
            "approve",
            "--reason",
            "founder-review",
        )
        self.assertEqual(1, code)
        self.assertEqual("", stdout)
        error = json.loads(stderr)
        self.assertEqual("error", error["status"])
        self.assertIn("policy rejects", error["error"])

    def test_lock_recovery_requires_the_exact_visible_id(self):
        context = self.store.lock("activation-test")
        record = context.__enter__()
        try:
            code, stdout, stderr = self.invoke("status")
            status = json.loads(stdout)
            self.assertEqual((0, ""), (code, stderr))
            self.assertEqual(record["operation_id"], status["lock"]["operation_id"])

            code, stdout, stderr = self.invoke("recover-lock", "f" * 32)
            self.assertEqual(1, code)
            self.assertEqual("", stdout)
            self.assertIn("does not match", json.loads(stderr)["error"])

            code, stdout, stderr = self.invoke(
                "recover-lock", record["operation_id"]
            )
            self.assertEqual((0, ""), (code, stderr))
            recovered = json.loads(stdout)
            self.assertEqual(record["operation_id"], recovered["operation_id"])
            self.assertNotIn("pid", recovered)
            self.assertNotIn("hostname", recovered)
        finally:
            context.__exit__(None, None, None)

    @unittest.skipUnless(HAS_CRYPTO, "continuity commands need the [pro] extra")
    def test_continuity_init_outputs_the_recovery_secret_once(self):
        code, stdout, stderr = self.invoke("continuity-init")

        self.assertEqual((0, ""), (code, stderr))
        result = json.loads(stdout)
        secret = result["recovery_secret"]
        self.assertRegex(secret, r"^[A-Za-z0-9_-]{43}$")
        self.assertEqual(1, stdout.count(secret))
        self.assertTrue(Path(result["recovery_kit_path"]).is_file())

    @unittest.skipUnless(HAS_CRYPTO, "continuity commands need the [pro] extra")
    def test_continuity_recover_reads_the_secret_without_echoing_it(self):
        from emulo_autopilot.continuity_onboarding import initialize_continuity

        source = initialize_continuity(Path(self.home) / "source")
        secret = source["recovery_secret"]

        code, stdout, stderr = self.invoke(
            "continuity-recover",
            source["recovery_kit_path"],
            secret_reader=lambda prompt: secret,
        )

        self.assertEqual((0, ""), (code, stderr))
        self.assertEqual("emulo.continuity-recovery/v1", json.loads(stdout)["schema_version"])
        self.assertNotIn(secret, stdout + stderr)

    @unittest.skipUnless(HAS_CRYPTO, "continuity commands need the [pro] extra")
    def test_continuity_connect_reads_pairing_code_without_echoing_token_or_code(self):
        from emulo_autopilot import continuity_onboarding

        continuity_onboarding.initialize_continuity(self.home)
        pairing_code = "P" * 43
        device_token = "T" * 43
        captured = {}

        def fake_connect(home, server, code, label, version):
            captured.update(
                home=home,
                server=server,
                code=code,
                label=label,
                version=version,
            )
            return {
                "schema_version": "emulo.continuity-connect/v1",
                "server": server,
                "device_id": "dev_0123456789abcdef0123456789abcdef",
            }

        with mock.patch.object(
            continuity_onboarding,
            "connect_continuity",
            side_effect=fake_connect,
        ):
            code, stdout, stderr = self.invoke(
                "continuity-connect",
                "--label",
                "Work laptop",
                "--server",
                "https://emulo.example",
                secret_reader=lambda prompt: pairing_code,
            )

        self.assertEqual((0, ""), (code, stderr))
        self.assertEqual(pairing_code, captured["code"])
        self.assertNotIn(pairing_code, stdout + stderr)
        self.assertNotIn(device_token, stdout + stderr)

    @unittest.skipUnless(HAS_CRYPTO, "continuity commands need the [pro] extra")
    def test_continuity_status_is_local_and_base_status_does_not_load_crypto(self):
        from emulo_autopilot.continuity_onboarding import initialize_continuity

        initialize_continuity(self.home)
        code, stdout, stderr = self.invoke("continuity-status")
        self.assertEqual((0, ""), (code, stderr))
        status = json.loads(stdout)
        self.assertTrue(status["initialized"])
        self.assertFalse(status["connected"])
        self.assertEqual(0, status["pending_count"])

        real_import = __import__

        def guarded_import(name, *args, **kwargs):
            if name == "cryptography" or name.startswith("cryptography."):
                raise AssertionError("base status loaded optional crypto")
            return real_import(name, *args, **kwargs)

        parsed = cli.build_parser().parse_args(
            ["--emulo-home", self.home, "status"]
        )
        with mock.patch("builtins.__import__", side_effect=guarded_import):
            self.assertEqual("ready", cli.execute(parsed)["health"])

    @unittest.skipUnless(HAS_CRYPTO, "continuity commands need the [pro] extra")
    def test_continuity_push_retry_and_pull_use_connected_material(self):
        from emulo_autopilot import continuity, continuity_onboarding

        master_key = b"M" * 32
        device_id = "dev_0123456789abcdef0123456789abcdef"
        transport = object()
        connected = (master_key, device_id, transport)

        with (
            mock.patch.object(
                continuity_onboarding,
                "load_connected_continuity",
                return_value=connected,
            ),
            mock.patch.object(
                continuity,
                "push_active",
                return_value={"status": "stored", "head": "gen_0123456789abcdef0123"},
            ) as pushed,
        ):
            code, stdout, stderr = self.invoke("continuity-push")
        self.assertEqual((0, ""), (code, stderr))
        self.assertEqual("stored", json.loads(stdout)["status"])
        pushed.assert_called_once()
        pushed_store, pushed_key, pushed_device, pushed_transport = pushed.call_args.args
        self.assertEqual(self.store.emulo_home, pushed_store.emulo_home)
        self.assertEqual((master_key, device_id, transport), (pushed_key, pushed_device, pushed_transport))

        with (
            mock.patch.object(
                continuity_onboarding,
                "load_connected_continuity",
                return_value=connected,
            ),
            mock.patch.object(
                continuity,
                "retry_pending",
                return_value={"uploaded": 2},
            ) as retried,
        ):
            code, stdout, stderr = self.invoke("continuity-retry")
        self.assertEqual((0, ""), (code, stderr))
        self.assertEqual(2, json.loads(stdout)["uploaded"])
        retried.assert_called_once()
        retried_store, retried_transport = retried.call_args.args
        self.assertEqual(self.store.emulo_home, retried_store.emulo_home)
        self.assertIs(transport, retried_transport)

        conflict = {
            "status": "conflict",
            "localHead": "gen_0123456789abcdef0123",
            "remoteHead": "gen_ffffffffffffffffffff",
        }
        with (
            mock.patch.object(
                continuity_onboarding,
                "load_connected_continuity",
                return_value=connected,
            ),
            mock.patch.object(
                continuity,
                "pull_remote_head",
                return_value=conflict,
            ),
        ):
            code, stdout, stderr = self.invoke("continuity-pull")
        self.assertEqual((0, ""), (code, stderr))
        result = json.loads(stdout)
        self.assertEqual(conflict["localHead"], result["localHead"])
        self.assertIn("Neither branch was overwritten", result["message"])


if __name__ == "__main__":
    unittest.main()
