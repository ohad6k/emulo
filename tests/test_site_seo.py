"""Every page in the sitemap names itself as canonical, and article pages carry valid TechArticle data."""

import json
import re
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
BASE = "https://emulo.vercel.app"
ARTICLES = {"/agent-profile", "/placebo", "/bench", "/fable"}
# scan.html carries no absolute URL at all (site/scan.test.cjs), so it cannot name a canonical.
NO_ABSOLUTE_URLS = {"/scan"}


def page_for(url_path):
    if url_path == "/":
        return SITE / "index.html"
    direct = SITE / f"{url_path.strip('/')}.html"
    return direct if direct.exists() else SITE / url_path.strip("/") / "index.html"


class SiteSeoTest(unittest.TestCase):
    def setUp(self):
        sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
        self.paths = [u[len(BASE):] or "/" for u in re.findall(r"<loc>([^<]+)</loc>", sitemap)]

    def test_every_sitemap_page_is_its_own_canonical(self):
        for path in [p for p in self.paths if p not in NO_ABSOLUTE_URLS]:
            html = page_for(path).read_text(encoding="utf-8")
            with self.subTest(path=path):
                canon = re.findall(r'<link rel="canonical" href="([^"]+)"', html)
                self.assertEqual(canon, [BASE + ("/" if path == "/" else path)])

    def test_articles_carry_dated_tech_article(self):
        for path in ARTICLES & set(self.paths):
            html = page_for(path).read_text(encoding="utf-8")
            with self.subTest(path=path):
                blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
                self.assertEqual(len(blocks), 1)
                data = json.loads(blocks[0])
                self.assertEqual(data["@type"], "TechArticle")
                self.assertEqual(data["url"], BASE + path)
                self.assertRegex(data["datePublished"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertGreaterEqual(data["dateModified"], data["datePublished"])


if __name__ == "__main__":
    unittest.main()
