import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from proof.cli import main
from proof.manifest import build_manifest, build_pairs, build_system_freeze


TASK_IDS = (
    "work-primary", "work-held-out", "design-primary", "design-held-out",
    "write-primary", "write-held-out",
)


def frozen_manifest():
    systems = []
    for index, host in enumerate(("codex", "claude"), start=1):
        systems.append(
            build_system_freeze(
                host, f"{host.title()} Stable", f"model-{index}", "1.0",
                ["provider", host], ["installer", host], f"{index:064x}",
                f"{index + 2:064x}", f"{index + 4:064x}", "quota", "cost"
            )
        )
    fixtures = {task_id: f"{i + 10:064x}" for i, task_id in enumerate(TASK_IDS)}
    instructions = {task_id: f"{i + 20:064x}" for i, task_id in enumerate(TASK_IDS)}
    pairs = build_pairs(
        systems, fixtures, instructions, "9" * 64,
        {family: {"time_seconds": 60, "max_turns": 2} for family in ("work", "design", "write")},
        "8" * 64,
    )
    return build_manifest(
        systems, pairs, "9" * 64, "7" * 64, "6" * 64,
        ["synthetic CLI test"], "2026-07-15T00:00:00Z"
    )


class ProofCliTest(unittest.TestCase):
    def write_manifest(self, root):
        path = root / "manifest.json"
        path.write_text(json.dumps(frozen_manifest()), encoding="utf-8")
        return path

    def test_validate_prints_json_and_manifest_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_manifest(Path(tmp))
            stdout = io.StringIO()
            stderr = io.StringIO()

            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["validate", "--manifest", str(path)])

            self.assertEqual(0, code)
            value = json.loads(stdout.getvalue())
            self.assertTrue(value["valid"])
            self.assertRegex(value["manifest_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual("", stderr.getvalue())

    @mock.patch("proof.cli.execute_cell")
    def test_execute_cell_without_execute_flag_fails_before_runner(self, execute):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.write_manifest(root)
            target_cell = frozen_manifest()["pairs"][0]["cells"][0]["cell_id"]
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "execute-cell", "--manifest", str(path), "--cell-id", target_cell,
                        "--run-root", str(root / "run"), "--approval", "0" * 64,
                    ]
                )

            self.assertEqual(2, code)
            self.assertIn("--execute", stderr.getvalue())
            execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
