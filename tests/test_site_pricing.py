import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "index.html"
ACCOUNT_URL = "https://emulo-production.ohad1306.workers.dev/account"


class SitePricingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = SITE.read_text(encoding="utf-8")

    def test_pricing_is_reachable_and_names_both_product_paths(self):
        self.assertIn('href="#pricing"', self.html)
        self.assertIn('id="pricing"', self.html)
        self.assertIn("Free and open source", self.html)
        self.assertIn("Emulo Pro", self.html)

    def test_approved_prices_and_annual_value_are_visible(self):
        pricing = self.html.split('id="pricing"', 1)[1].split("</section>", 1)[0]
        for text in ("$0", "$9", "$108", "$79", "Save 27%"):
            self.assertIn(text, pricing)
        self.assertIn("Get Emulo", pricing)
        self.assertIn("Choose monthly", pricing)
        self.assertIn("Choose annual", pricing)
        for rejected in (
            "Private beta",
            "Install from GitHub",
            "Open account",
            "Payment truth stays server-side",
        ):
            self.assertNotIn(rejected, pricing)

    def test_pricing_keeps_free_capable_and_does_not_claim_sync_is_live(self):
        pricing = self.html.split('id="pricing"', 1)[1].split("</section>", 1)[0]
        for text in ("Free and open source", "MIT", "local", "No subscription"):
            self.assertIn(text.lower(), pricing.lower())
        self.assertNotIn("available today", pricing.lower())
        self.assertNotIn("unlimited", pricing.lower())

    def test_pro_scope_is_concrete_and_privacy_bounded(self):
        pricing = self.html.split('id="pricing"', 1)[1].split("</section>", 1)[0]
        for text in (
            "End-to-end encrypted",
            "five devices",
            "500 encrypted generations",
            "64 MiB",
            "Conflict-safe",
            "30-day encrypted export",
            "Raw session logs and decryption keys stay local",
        ):
            self.assertIn(text, pricing)

    def test_open_source_local_product_is_not_weakened(self):
        pricing = self.html.split('id="pricing"', 1)[1].split("</section>", 1)[0]
        self.assertIn("MIT", pricing)
        self.assertIn("local", pricing.lower())
        self.assertIn("you.md", pricing)
        self.assertIn("No subscription", pricing)

    def test_paid_intent_uses_authenticated_emulo_account_boundary(self):
        self.assertGreaterEqual(self.html.count(ACCOUNT_URL), 2)
        self.assertNotIn("checkout.polar.sh", self.html)
        self.assertNotIn("sandbox.polar.sh", self.html)
        self.assertNotRegex(
            self.html,
            re.compile(r"(?:polar_(?:oat|sk)|github_client_secret|polar_webhook_secret)", re.I),
        )

    def test_static_site_does_not_embed_production_product_ids(self):
        self.assertNotIn("ce99808b-4e11-4cec-bc31-d9654d558e08", self.html)
        self.assertNotIn("b6535378-b1bd-40ee-bd37-96a03abec2f2", self.html)


if __name__ == "__main__":
    unittest.main()
