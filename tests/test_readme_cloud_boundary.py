"""Guards the README's commercial boundary.

Rewritten 2026-08-16. This file used to assert the presence of an
"Open source and Emulo Pro" section that sold a hosted continuity layer and
linked to `emulo.vercel.app/#pricing`. That layer is not purchasable: both Polar
products are private, `PAID_CHECKOUT_ENABLED` is "false", and the pricing pane
was withdrawn from the site on 2026-07-26 (`docs/site-pro-pricing-withdrawn.md`).
The link therefore pointed at a page with no pricing on it.

The guard now runs the other way, matching `tests/test_site_pricing.py`: it fails
if a hosted-Pro promise, a price, or a checkout surface reappears in the README
while none of it can actually be bought. Flip it back deliberately, in the same
commit that makes checkout real, so the README and the product can never
disagree again.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

SECTION = "## Open source and privacy"

# Anything here means the README is selling something a reader cannot buy.
FORBIDDEN_PATTERNS = [
    # \b so this does not fire on "Emulo Proof v1", which is a different thing.
    r"Emulo Pro\b",
    r"emulo\.vercel\.app/#pricing",
    r"workers\.dev/account",
    r"\$9\b",
    r"\$79\b",
    r"\$300\b",
    r"buy\.polar\.sh",
]


class ReadmeCloudBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = README.read_text(encoding="utf-8")

    def test_readme_states_the_local_boundary(self):
        self.assertIn(SECTION, self.readme)
        section = self.readme.split(SECTION, 1)[1].split("\n## ", 1)[0]
        self.assertIn("MIT", section)
        self.assertIn("without an account", section)
        # The one honest exception has to stay stated, not quietly dropped.
        self.assertIn("hosted model", section)
        self.assertIn("local model", section)

    def test_readme_sells_nothing_that_cannot_be_bought(self):
        for pattern in FORBIDDEN_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIsNone(
                    re.search(pattern, self.readme),
                    f"README offers {pattern!r} but there is no live checkout for it. "
                    "If checkout is now real, update this guard in the same commit.",
                )


if __name__ == "__main__":
    unittest.main()
