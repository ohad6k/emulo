"""Keep visible offers and search metadata consistent.

The page currently offers free software and a manually delivered Profile Build.
Withdrawn subscription offers must not survive in structured data. These static
checks do not establish the state of any payment provider or deployed checkout.
"""

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "index.html"
ACCOUNT_URL = "https://emulo-production.ohad1306.workers.dev/account"

# Former subscription prices, excluded from the current public offer.
MONTHLY = "12"
YEARLY = "99"

# Prices that were once published and can never quietly return.
RETIRED = ("$9 ", "$79", "$108", "Save 27%", "Coming soon")


class SitePricingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = SITE.read_text(encoding="utf-8")

    def pricing(self):
        return self.html.split('id="pricing"', 1)[1].split("</section>", 1)[0]

    def head(self):
        return self.html.split("</head>", 1)[0]

    def test_pricing_section_is_reachable(self):
        self.assertIn('href="#pricing"', self.html)
        self.assertIn('id="pricing"', self.html)

    def test_free_tier_is_not_weakened(self):
        pricing = self.pricing()
        for text in ("Free and open source", "MIT", "you.md", "No subscription",
                     "$0", "Get Emulo"):
            self.assertIn(text, pricing)
        self.assertIn("local", pricing.lower())

    def test_the_pane_sells_only_what_can_be_delivered_today(self):
        """The subscription cannot be sold: the gated scan never invokes an
        engine and its policy directory does not exist, so a buyer would unlock
        nothing. The pane sells the Profile Build instead, which is delivered by
        hand and needs no code path."""
        pricing = self.pricing()
        self.assertIn("Profile Build", pricing)
        self.assertIn("$300", pricing)
        self.assertIn("ohadkrispin@gmail.com", pricing)
        self.assertIn("emulo verify you.md --json", pricing)
        for closed in ("Choose monthly", "Choose annual", ACCOUNT_URL,
                       f"${MONTHLY} ", f"${YEARLY} "):
            with self.subTest(closed=closed):
                self.assertNotIn(closed, pricing)

    def test_visible_prices_and_structured_data_agree(self):
        """Search metadata must never advertise an offer absent from the page."""
        schemas = [json.loads(raw) for raw in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            self.head(), re.S,
        )]
        software = next(item for item in schemas if item.get("@type") == "SoftwareApplication")
        offers = {item["price"] for item in software["offers"]}
        visible = set(re.findall(r"\$(\d+)\b", self.pricing()))
        self.assertTrue(
            offers <= visible,
            f"schema.org prices {sorted(offers)} include offers absent from "
            f"the visible page {sorted(visible)}",
        )
        self.assertEqual(software["offers"], [{
            "@type": "Offer", "name": "Open-source Emulo",
            "price": "0", "priceCurrency": "USD",
        }])

    def test_retired_prices_never_return(self):
        for rejected in RETIRED:
            with self.subTest(rejected=rejected):
                self.assertNotIn(rejected, self.html)

    def test_pro_claims_only_what_the_licence_actually_gates(self):
        """`cli.py` gates exactly one feature, scan-sessions. Everything else
        stays free. The page must not imply the subscription buys more than
        that, and it must not sell the desktop app or the Museum, which are no
        longer part of the offer."""
        pricing = self.pricing()
        self.assertIn("I never ask for your session logs", pricing)
        for sold in ("/ month", "/ year", "Add Pro"):
            with self.subTest(sold=sold):
                self.assertNotIn(sold, pricing)
        for overclaim in ("unlimited", "available today", "encrypted sync",
                          "five devices", "museum", "the app"):
            with self.subTest(overclaim=overclaim):
                self.assertNotIn(overclaim, pricing.lower())


    def test_checkout_is_closed_until_a_real_payment_unlocks_it(self):
        """Nothing in the shipped product fetches a licence lease, so the paid
        gate cannot pass on any machine. Until one real payment is proven to
        unlock scan-sessions, the site must not take money and must not serve
        the desktop bundle."""
        self.assertNotIn("workers.dev/account", self.html)
        for gone in ("Choose monthly", "Choose annual", "/download?start=1"):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, self.html)
        for dead in ("download.html", "releases.json", "emulo-pro-1.0.0.zip"):
            with self.subTest(dead=dead):
                self.assertFalse((SITE.parent / dead).exists(),
                                 f"{dead} must not ship while checkout is closed")

    def test_static_site_leaks_no_secret_or_product_id(self):
        for host in ("checkout.polar.sh", "sandbox.polar.sh", "buy.polar.sh"):
            self.assertNotIn(host, self.html)
        self.assertNotRegex(
            self.html,
            re.compile(r"(?:polar_(?:oat|sk)|github_client_secret|polar_webhook_secret)", re.I),
        )
        for product_id in (
            # archived 2026-08-16
            "ce99808b-4e11-4cec-bc31-d9654d558e08",
            "b6535378-b1bd-40ee-bd37-96a03abec2f2",
            # live, and still server-side only
            "3eb4351f-8b45-483f-be7b-a0a438d4625a",
            "2bb776aa-81f1-4d36-b3d3-b1802f942d76",
        ):
            with self.subTest(product_id=product_id):
                self.assertNotIn(product_id, self.html)


if __name__ == "__main__":
    unittest.main()
