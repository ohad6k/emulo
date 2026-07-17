import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


class ReadmeCloudBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = README.read_text(encoding="utf-8")

    def test_readme_separates_open_source_emulo_from_emulo_pro(self):
        self.assertIn("## Open source and Emulo Pro", self.readme)
        section = self.readme.split("## Open source and Emulo Pro", 1)[1]
        self.assertIn("MIT", section)
        self.assertIn("without an account", section)
        self.assertIn("Emulo Pro", section)
        self.assertIn("https://emulo.vercel.app/#pricing", section)

    def test_public_source_does_not_imply_public_credentials_or_customer_data(self):
        section = self.readme.split("## Open source and Emulo Pro", 1)[1]
        self.assertIn("Worker source", section)
        self.assertIn("never stored in Git", section)
        self.assertIn("model-provider tokens", section)


if __name__ == "__main__":
    unittest.main()
