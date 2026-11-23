"""Validate the public GitHub Pages showcase from repository files only."""

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.image_alts = []
        self.ids = set()
        self.headings = []
        self.current_heading = None
        self.meta_description = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag in {"a", "link", "script", "img"}:
            reference = values.get("href") or values.get("src")
            if reference:
                self.links.append(reference)
        if tag == "img":
            self.image_alts.append(values.get("alt", ""))
        if tag == "meta" and values.get("name") == "description":
            self.meta_description = bool(values.get("content", "").strip())
        if tag in {"h1", "h2", "h3"}:
            self.current_heading = tag

    def handle_endtag(self, tag):
        if tag == self.current_heading:
            self.current_heading = None

    def handle_data(self, data):
        if self.current_heading and data.strip():
            self.headings.append((self.current_heading, data.strip()))


class PublicSiteTests(unittest.TestCase):
    def setUp(self):
        self.html = (SITE / "index.html").read_text(encoding="utf-8")
        self.css = (SITE / "styles.css").read_text(encoding="utf-8")
        self.js = (SITE / "script.js").read_text(encoding="utf-8")
        self.parser = SiteParser()
        self.parser.feed(self.html)

    def test_main_files_exist(self):
        for filename in ["index.html", "styles.css", "script.js", "favicon.svg", ".nojekyll"]:
            with self.subTest(filename=filename):
                self.assertTrue((SITE / filename).is_file())

    def test_referenced_local_assets_exist(self):
        for reference in self.parser.links:
            parsed = urlparse(reference)
            if parsed.scheme or reference.startswith("//") or reference.startswith("#"):
                continue
            path = (SITE / unquote(parsed.path)).resolve()
            with self.subTest(reference=reference):
                self.assertTrue(path.is_relative_to(SITE.resolve()))
                self.assertTrue(path.is_file())

    def test_navigation_targets_exist(self):
        for target in re.findall(r'href="#([^"]+)"', self.html):
            with self.subTest(target=target):
                self.assertIn(target, self.parser.ids)

    def test_accessibility_basics(self):
        self.assertTrue(any(tag == "h1" for tag, _ in self.parser.headings))
        self.assertTrue(self.parser.meta_description)
        self.assertTrue(self.parser.image_alts)
        self.assertTrue(all(alt.strip() for alt in self.parser.image_alts))
        self.assertIn('href="#main"', self.html)
        self.assertIn("prefers-reduced-motion", self.css)

    def test_real_screenshots_used(self):
        images = {
            "discount-approval.png": "discount_approval.png",
            "security-escalation.png": "security_escalation.png",
            "incomplete-lead.png": "incomplete_lead.png",
        }
        for site_name, doc_name in images.items():
            with self.subTest(site_name=site_name):
                self.assertTrue((SITE / "assets" / site_name).read_bytes() ==
                                (ROOT / "docs" / "screenshots" / doc_name).read_bytes())
                self.assertIn(site_name, self.js + self.html)

    def test_no_exaggerated_deployment_claims(self):
        self.assertIn("Not a live CRM service", self.html)
        self.assertIn("Synthetic", self.html)
        self.assertIn("live login unverified", self.html)
        self.assertNotIn("Start free trial", self.html)
        self.assertNotIn("Trusted by", self.html)


if __name__ == "__main__":
    unittest.main()
