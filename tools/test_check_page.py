import tempfile
import unittest
from pathlib import Path

from check_page import check_page

GOOD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>T</title><link rel="stylesheet" href="assets/site.css"></head>
<body><h1>T</h1><nav><a href="#one">One</a></nav>
<h2 id="one">One</h2>
<img src="assets/shots/a.webp" alt="A real description" width="10" height="10">
<p>Claim<a class="cite" href="#src-1">1</a></p>
<h2 id="sources">Sources</h2><ol><li id="src-1">A source</li></ol>
</body></html>"""


class CheckPageTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "assets" / "shots").mkdir(parents=True)
        (self.dir / "assets" / "site.css").write_text("")
        (self.dir / "assets" / "shots" / "a.webp").write_bytes(
            b"RIFF" + (0).to_bytes(4, "little") + b"WEBPVP8L"
            + (0).to_bytes(4, "little")
            + bytes([0x2F])
            + (9 | (9 << 14)).to_bytes(4, "little")
        )

    def write(self, html):
        path = self.dir / "index.html"
        path.write_text(html)
        return path

    def check(self, html, **kwargs):
        kwargs.setdefault("required", set())
        return check_page(self.write(html), self.dir, **kwargs)

    def test_good_page_has_no_problems(self):
        self.assertEqual(self.check(GOOD), [])

    def test_dangling_fragment_link_is_reported(self):
        html = GOOD.replace('href="#one"', 'href="#missing"')
        self.assertIn("missing", " ".join(self.check(html)))

    def test_missing_image_file_is_reported(self):
        html = GOOD.replace("a.webp", "gone.webp")
        self.assertIn("gone.webp", " ".join(self.check(html)))

    def test_image_without_alt_is_reported(self):
        html = GOOD.replace('alt="A real description"', 'alt=""')
        self.assertIn("alt", " ".join(self.check(html)))

    def test_image_without_dimensions_is_reported(self):
        html = GOOD.replace('width="10" height="10"', "")
        self.assertIn("width", " ".join(self.check(html)))

    def test_declared_dimensions_must_match_the_file(self):
        html = GOOD.replace('width="10" height="10"', 'width="99" height="10"')
        self.assertIn("99", " ".join(self.check(html)))

    def test_skipped_heading_level_is_reported(self):
        html = GOOD.replace('<h2 id="one">One</h2>', '<h4 id="one">One</h4>')
        self.assertIn("heading", " ".join(self.check(html)).lower())

    def test_offorigin_resource_is_reported(self):
        html = GOOD.replace(
            '<link rel="stylesheet" href="assets/site.css">',
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css">',
        )
        self.assertIn("off-origin", " ".join(self.check(html)).lower())

    def test_required_anchor_missing_is_reported(self):
        self.assertIn("rivers", " ".join(self.check(GOOD, required={"rivers"})))


if __name__ == "__main__":
    unittest.main()
