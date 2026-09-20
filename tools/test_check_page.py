import tempfile
import unittest
from pathlib import Path

from check_page import REQUIRED_ANCHORS, _required_for, check_page

# A magazine issue page, shaped like templates/magazine/issue.html.j2: an
# <article class="issue">, one h1, no landmark anchors, inline SVG figures, and
# an episode nav whose fragment links resolve to their sections.
ISSUE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>A warm, dry September</title>
<link rel="stylesheet" href="../assets/site.css">
<link rel="stylesheet" href="../assets/magazine.css"></head>
<body><article class="issue">
<header class="issue__head"><h1>A warm, dry September</h1></header>
<figure class="issue__spine"><svg role="img"><title>Spine</title></svg></figure>
<nav class="issue__anchors"><a href="#e1">warm spell</a></nav>
<section class="issue__section"><h2>What the month did</h2></section>
<section class="issue__section"><h2>Episodes</h2>
<section class="issue__episode" id="e1"><h3>The warm spell</h3></section></section>
<section class="issue__section"><h2>By the numbers</h2></section>
<footer class="issue__foot"><a href="https://open-meteo.com/">Open-Meteo</a></footer>
</article></body></html>"""

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

    def test_the_single_page_site_still_requires_its_landmarks(self):
        self.assertEqual(_required_for(GOOD), REQUIRED_ANCHORS)

    def test_a_magazine_issue_page_requires_no_landmark_anchors(self):
        self.assertEqual(_required_for(ISSUE), set())

    def test_the_archive_index_requires_no_landmark_anchors(self):
        self.assertEqual(_required_for('<main class="archive">'), set())

    def test_a_well_formed_issue_page_passes_the_generic_checks(self):
        # No landmark anchors are required, but the episode nav must still
        # resolve, the heading order must hold, and there is exactly one h1.
        self.assertEqual(self.check(ISSUE, required=_required_for(ISSUE)), [])

    def test_a_dangling_episode_anchor_is_still_reported_on_an_issue_page(self):
        broken = ISSUE.replace('id="e1"', 'id="e2"')
        problems = self.check(broken, required=_required_for(broken))
        self.assertIn("e1", " ".join(problems))


class SiteDiscoverabilityTest(unittest.TestCase):
    """The magazine and its feed must be reachable from the public page."""

    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.index = (self.root / "index.html").read_text(encoding="utf-8")

    def test_the_page_links_to_a_deployable_magazine_archive(self):
        self.assertIn('href="issues/index.html"', self.index)
        self.assertTrue((self.root / "issues" / "index.html").is_file())

    def test_the_page_advertises_a_deployable_atom_feed(self):
        self.assertIn('rel="alternate"', self.index)
        self.assertIn('type="application/atom+xml"', self.index)
        self.assertIn('href="feed.xml"', self.index)
        self.assertTrue((self.root / "feed.xml").is_file())

    def test_full_bleed_issue_spine_cannot_create_page_overflow(self):
        css = (self.root / "assets" / "magazine.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"html\s*\{[^}]*overflow-x:\s*clip")


if __name__ == "__main__":
    unittest.main()
