"""`emulo --version` prints the version and exits 0.

It used to fail with "unrecognized arguments: --version" and exit 2, so the
one command a user runs to say which build a bug report is about did not work.
"""

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMULO = ROOT / "emulo.py"
SPEC = importlib.util.spec_from_file_location("emulo_version_flag", EMULO)
emulo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(emulo)


class VersionFlagTest(unittest.TestCase):
    def test_version_prints_the_release_and_exits_zero(self):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        result = subprocess.run(
            [sys.executable, str(EMULO), "--version"],
            capture_output=True, text=True, env=env, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "emulo " + emulo.EMULO_VERSION)
        self.assertEqual(result.stderr, "")

    def test_version_writes_nothing(self):
        before = set(os.listdir(ROOT))
        subprocess.run([sys.executable, str(EMULO), "--version"], capture_output=True, cwd=str(ROOT))
        self.assertEqual(set(os.listdir(ROOT)), before)


if __name__ == "__main__":
    unittest.main()
