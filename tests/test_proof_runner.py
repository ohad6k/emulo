import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from proof.canonical import canonical_bytes, sha256_bytes
from proof.fixtures import tree_hash
from proof.runner import audit_clean_home, execute_cell, prepare_cell


ROOT = Path(__file__).resolve().parents[1]


def manifest():
    return {
        "systems": [
            {
                "system_id": "system-a",
                "host": "codex",
                "run_argv": ["provider", "run"],
                "ditto_install_argv": ["installer", "run"],
            }
        ]
    }


def cell(cell_id="cell-a", condition="cold"):
    return {
        "cell_id": cell_id,
        "pair_id": "pair-a",
        "system_id": "system-a",
        "host": "codex",
        "task_id": "work-primary",
        "instruction_sha256": sha256_bytes(b"frozen\n"),
        "condition": condition,
        "profile_manifest_sha256": None,
        "fixture_sha256": "",
        "budget": {"time_seconds": 60, "max_turns": 2},
    }


def create_run_root(base):
    run_root = base / "run"
    fixture = run_root / "sealed-fixtures" / "work-primary"
    fixture.mkdir(parents=True)
    (fixture / "brief.md").write_text("frozen\n", encoding="utf-8", newline="\n")
    return run_root, tree_hash(fixture)


class RunnerTest(unittest.TestCase):
    def test_execute_requires_flag_and_exact_manifest_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root, fixture_hash = create_run_root(Path(tmp))
            frozen_cell = cell()
            frozen_cell["fixture_sha256"] = fixture_hash

            with self.assertRaisesRegex(PermissionError, "explicit approval"):
                execute_cell(manifest(), frozen_cell, run_root, execute=False, approval="")
            with self.assertRaisesRegex(PermissionError, "manifest hash"):
                execute_cell(
                    manifest(), frozen_cell, run_root, execute=True, approval="0" * 64
                )

    def test_pair_cells_get_different_workspaces_and_homes(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root, fixture_hash = create_run_root(Path(tmp))
            cold_cell = cell("cell-cold", "cold")
            cold_cell["fixture_sha256"] = fixture_hash
            ditto_cell = cell("cell-ditto", "ditto")
            ditto_cell["fixture_sha256"] = fixture_hash

            cold = prepare_cell(manifest(), cold_cell, run_root)
            ditto = prepare_cell(manifest(), ditto_cell, run_root)

            self.assertNotEqual(cold.workspace, ditto.workspace)
            self.assertNotEqual(cold.home, ditto.home)
            self.assertEqual(cold.fixture_sha256, ditto.fixture_sha256)
            self.assertEqual("frozen\n", (cold.workspace / "brief.md").read_text("utf-8"))

    def test_prepare_rejects_instruction_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root, fixture_hash = create_run_root(Path(tmp))
            frozen_cell = cell()
            frozen_cell["fixture_sha256"] = fixture_hash
            frozen_cell["instruction_sha256"] = "0" * 64

            with self.assertRaisesRegex(ValueError, "instruction hash mismatch"):
                prepare_cell(manifest(), frozen_cell, run_root)

    def test_clean_home_rejects_native_personalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            (home / "AGENTS.md").write_text("private rules", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "persistent context"):
                audit_clean_home(home)

    def test_prepare_rejects_run_root_inside_repository(self):
        frozen_cell = cell()
        frozen_cell["fixture_sha256"] = "a" * 64

        with self.assertRaisesRegex(ValueError, "outside repository"):
            prepare_cell(manifest(), frozen_cell, ROOT / "proof-private-test")

    @mock.patch("proof.runner.subprocess.run")
    def test_execute_uses_argv_shell_false_and_isolated_environment(self, run):
        run.return_value = subprocess.CompletedProcess(
            ["provider", "run"], 0, stdout="ok", stderr=""
        )
        with tempfile.TemporaryDirectory() as tmp:
            run_root, fixture_hash = create_run_root(Path(tmp))
            frozen_manifest = manifest()
            frozen_cell = cell()
            frozen_cell["fixture_sha256"] = fixture_hash
            approval = sha256_bytes(canonical_bytes(frozen_manifest))

            prepared, completed, installed_hash = execute_cell(
                frozen_manifest,
                frozen_cell,
                run_root,
                execute=True,
                approval=approval,
            )

            self.assertEqual(0, completed.returncode)
            self.assertIsNone(installed_hash)
            run.assert_called_once()
            _, kwargs = run.call_args
            self.assertFalse(kwargs["shell"])
            self.assertEqual(prepared.workspace, kwargs["cwd"])
            self.assertEqual(str(prepared.home), kwargs["env"]["HOME"])
            self.assertEqual(str(prepared.home), kwargs["env"]["USERPROFILE"])

    @mock.patch("proof.runner.subprocess.run")
    def test_ditto_condition_installs_before_provider_and_hashes_home(self, run):
        def effect(argv, **kwargs):
            if argv[0] == "installer":
                installed = Path(kwargs["env"]["DITTO_HOME"])
                installed.mkdir(parents=True)
                (installed / "profile.txt").write_text("frozen profile", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

        run.side_effect = effect
        with tempfile.TemporaryDirectory() as tmp:
            run_root, fixture_hash = create_run_root(Path(tmp))
            frozen_manifest = manifest()
            frozen_cell = cell(condition="ditto")
            frozen_cell["fixture_sha256"] = fixture_hash
            expected = Path(tmp) / "expected-home" / ".ditto"
            expected.mkdir(parents=True)
            (expected / "profile.txt").write_text(
                "frozen profile", encoding="utf-8"
            )
            frozen_cell["profile_manifest_sha256"] = tree_hash(expected.parent)

            _, _, installed_hash = execute_cell(
                frozen_manifest,
                frozen_cell,
                run_root,
                execute=True,
                approval=sha256_bytes(canonical_bytes(frozen_manifest)),
            )

            self.assertEqual(2, run.call_count)
            self.assertEqual(["installer", "run"], run.call_args_list[0].args[0])
            self.assertEqual(["provider", "run"], run.call_args_list[1].args[0])
            self.assertRegex(installed_hash, r"^[0-9a-f]{64}$")

    @mock.patch("proof.runner.subprocess.run")
    def test_ditto_setup_rejects_noop_or_extra_persistent_context(self, run):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            expected = base / "expected-home" / ".ditto"
            expected.mkdir(parents=True)
            (expected / "profile.txt").write_text("frozen", encoding="utf-8")
            expected_hash = tree_hash(expected.parent)

            for mode in ("noop", "extra"):
                with self.subTest(mode=mode):
                    run_root, fixture_hash = create_run_root(base / mode)
                    frozen_manifest = manifest()
                    frozen_cell = cell(cell_id=f"cell-{mode}", condition="ditto")
                    frozen_cell["fixture_sha256"] = fixture_hash
                    frozen_cell["profile_manifest_sha256"] = expected_hash

                    def effect(argv, **kwargs):
                        if argv[0] == "installer" and mode == "extra":
                            home = Path(kwargs["env"]["DITTO_HOME"])
                            home.mkdir(parents=True)
                            (home / "profile.txt").write_text("frozen", encoding="utf-8")
                            (Path(kwargs["env"]["HOME"]) / "AGENTS.md").write_text(
                                "unapproved context", encoding="utf-8"
                            )
                        return subprocess.CompletedProcess(
                            argv, 0, stdout="ok", stderr=""
                        )

                    run.side_effect = effect
                    with self.assertRaisesRegex(
                        ValueError, "installed context does not match"
                    ):
                        execute_cell(
                            frozen_manifest,
                            frozen_cell,
                            run_root,
                            execute=True,
                            approval=sha256_bytes(canonical_bytes(frozen_manifest)),
                        )


if __name__ == "__main__":
    unittest.main()
