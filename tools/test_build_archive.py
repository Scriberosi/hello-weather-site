import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from build_archive import (
    _month_label,
    build_feed,
    build_index,
    issue_summary,
    issue_title,
)
from check_page import _required_for, check_page


ISSUE = """<!DOCTYPE html>
<html lang="en"><head>
<title>A warm, dry September · September 2026 · Hello Weather</title>
<meta name="description" content="Warmer and drier than usual.">
</head><body><h1>A warm, dry September</h1></body></html>
"""


class BuildArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.issues = self.root / "issues"
        self.issues.mkdir()
        (self.issues / "2026-09.html").write_text(ISSUE, encoding="utf-8")
        (self.issues / "2026-08.html").write_text(
            ISSUE.replace("September", "August"), encoding="utf-8"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_issue_title_reads_the_headline_not_the_document_title(self):
        self.assertEqual(issue_title(self.issues / "2026-09.html"),
                         "A warm, dry September")

    def test_index_lists_issues_newest_first(self):
        out = self.issues / "index.html"
        build_index(sorted(self.issues.glob("20*.html")), out)
        html = out.read_text(encoding="utf-8")

        self.assertLess(html.index("2026-09"), html.index("2026-08"))
        self.assertIn('href="2026-09.html"', html)
        self.assertIn("<!DOCTYPE html>", html)

    def test_feed_is_valid_atom_with_absolute_links(self):
        out = self.root / "feed.xml"
        build_feed(sorted(self.issues.glob("20*.html")), out,
                   "https://scriberosi.github.io/hello-weather-site")
        xml = out.read_text(encoding="utf-8")

        self.assertIn('<feed xmlns="http://www.w3.org/2005/Atom">', xml)
        self.assertIn(
            "https://scriberosi.github.io/hello-weather-site/issues/2026-09.html",
            xml,
        )
        self.assertEqual(xml.count("<entry>"), 2)

    def test_index_excludes_itself(self):
        out = self.issues / "index.html"
        build_index(sorted(self.issues.glob("20*.html")), out)
        build_index(sorted(self.issues.glob("20*.html")), out)

        self.assertNotIn('href="index.html"', out.read_text(encoding="utf-8"))

    # --- Structural / accessibility checks on the generated archive output ---

    def test_issue_summary_reads_the_meta_description(self):
        self.assertEqual(issue_summary(self.issues / "2026-09.html"),
                         "Warmer and drier than usual.")

    def test_generated_index_is_a_sound_accessible_document(self):
        out = self.issues / "index.html"
        build_index(sorted(self.issues.glob("20*.html")), out)
        html = out.read_text(encoding="utf-8")

        # Landmarks a screen reader and the structural checker both rely on.
        self.assertIn('lang="en"', html)
        self.assertIn('<meta charset="utf-8">', html)
        self.assertIn(
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            html,
        )
        # The archive is its own document; it does not carry the single-page
        # site's landmark anchors, so check_page must not require them.
        self.assertEqual(_required_for(html), set())
        self.assertEqual(check_page(out, out.parent, required=_required_for(html)), [])

    def test_generated_index_links_the_shared_styles_relatively(self):
        out = self.issues / "index.html"
        build_index(sorted(self.issues.glob("20*.html")), out)
        html = out.read_text(encoding="utf-8")

        # Relative hrefs keep the archive working under the GitHub Pages base
        # path; an absolute or off-origin stylesheet would break there.
        self.assertIn('href="../assets/site.css"', html)
        self.assertIn('href="../assets/magazine.css"', html)
        self.assertNotIn('href="/assets', html)
        self.assertNotIn("http://", html)

    def test_generated_index_offers_the_feed_and_a_way_back(self):
        out = self.issues / "index.html"
        build_index(sorted(self.issues.glob("20*.html")), out)
        html = out.read_text(encoding="utf-8")

        self.assertIn('type="application/atom+xml"', html)
        self.assertIn('href="../index.html"', html)

    def test_feed_entries_carry_titles_summaries_and_stable_ids(self):
        out = self.root / "feed.xml"
        build_feed(sorted(self.issues.glob("20*.html")), out,
                   "https://scriberosi.github.io/hello-weather-site")
        xml = out.read_text(encoding="utf-8")

        self.assertIn("<title>A warm, dry September</title>", xml)
        self.assertIn("<summary>Warmer and drier than usual.</summary>", xml)
        self.assertEqual(xml.count("<id>"), 3)  # one feed id + two entry ids

    def test_feed_trailing_slash_on_site_url_is_normalised(self):
        out = self.root / "feed.xml"
        build_feed(sorted(self.issues.glob("20*.html")), out,
                   "https://scriberosi.github.io/hello-weather-site/")
        xml = out.read_text(encoding="utf-8")

        self.assertNotIn("hello-weather-site//issues", xml)

    # --- Escaping, feed validity, determinism and empty/degraded states ---

    def test_titles_and_summaries_are_escaped_exactly_once(self):
        # An h1 and description that already contain entities must not be
        # double-escaped: &amp; must stay &amp;, never become &amp;amp;.
        (self.issues / "2026-10.html").write_text(
            '<!DOCTYPE html><html lang="en"><head>'
            '<meta name="description" content="2 &lt; 3, warm &amp; dry, '
            'it&#39;s &quot;mild&quot;.">'
            "</head><body><h1>Warm &amp; dry</h1></body></html>",
            encoding="utf-8",
        )
        page = self.issues / "2026-10.html"
        self.assertEqual(issue_title(page), "Warm & dry")
        self.assertEqual(issue_summary(page), '2 < 3, warm & dry, it\'s "mild".')

        index_out = self.issues / "index.html"
        build_index(sorted(self.issues.glob("20*.html")), index_out)
        feed_out = self.root / "feed.xml"
        build_feed(sorted(self.issues.glob("20*.html")), feed_out,
                   "https://example.test")
        for text in (index_out.read_text(encoding="utf-8"),
                     feed_out.read_text(encoding="utf-8")):
            self.assertIn("Warm &amp; dry", text)
            self.assertNotIn("&amp;amp;", text)
            self.assertIn("2 &lt; 3", text)
            self.assertNotIn("&amp;lt;", text)

    def test_feed_declares_an_author_and_parses_as_atom(self):
        out = self.root / "feed.xml"
        build_feed(sorted(self.issues.glob("20*.html")), out,
                   "https://example.test")
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(out.read_text(encoding="utf-8"))
        self.assertEqual(root.tag, "{http://www.w3.org/2005/Atom}feed")
        # A feed-level author is required unless every entry carries one; every
        # entry here inherits this one (RFC 4287 4.2.1).
        author = root.find("a:author/a:name", ns)
        self.assertIsNotNone(author)
        self.assertTrue((author.text or "").strip())
        for child in ("title", "id", "updated"):
            self.assertIsNotNone(root.find(f"a:{child}", ns), child)
        entries = root.findall("a:entry", ns)
        self.assertEqual(len(entries), 2)
        for entry in entries:
            for child in ("title", "id", "updated", "summary", "link"):
                self.assertIsNotNone(entry.find(f"a:{child}", ns), child)

    def test_feed_rebuilds_to_identical_bytes(self):
        paths = sorted(self.issues.glob("20*.html"))
        first = self.root / "feed-1.xml"
        second = self.root / "feed-2.xml"
        build_feed(paths, first, "https://example.test")
        build_feed(paths, second, "https://example.test")
        # No wall-clock value leaks in, so two rebuilds are byte-identical.
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertIn("<updated>2026-09-01T00:00:00Z</updated>",
                      first.read_text(encoding="utf-8"))

    def test_summary_is_inside_the_card_link(self):
        out = self.issues / "index.html"
        build_index(sorted(self.issues.glob("20*.html")), out)
        html = out.read_text(encoding="utf-8")
        # The summary span is part of the <a>, so the whole card is a hit target.
        self.assertIn(
            '<span class="archive__title">A warm, dry September</span>'
            '<span class="archive__summary">Warmer and drier than usual.'
            "</span></a>",
            html,
        )

    def test_a_blank_summary_is_omitted(self):
        (self.issues / "2026-07.html").write_text(
            '<!DOCTYPE html><html lang="en"><head><title>x</title></head>'
            "<body><h1>No description here</h1></body></html>",
            encoding="utf-8",
        )
        out = self.issues / "index.html"
        build_index(sorted(self.issues.glob("20*.html")), out)
        html = out.read_text(encoding="utf-8")
        self.assertIn(
            '<span class="archive__title">No description here</span></a>', html)
        self.assertNotIn('<span class="archive__summary"></span>', html)

    def test_empty_archive_shows_a_message_not_an_empty_list(self):
        out = self.issues / "index.html"
        build_index([], out)
        html = out.read_text(encoding="utf-8")
        self.assertIn('<p class="archive__empty">No issues yet.</p>', html)
        self.assertNotIn('<ul class="archive__list">', html)
        self.assertEqual(check_page(out, out.parent, required=set()), [])

    def test_empty_feed_is_deterministic_and_parses(self):
        out = self.root / "feed.xml"
        build_feed([], out, "https://example.test")
        text = out.read_text(encoding="utf-8")
        ET.fromstring(text)  # still well-formed Atom
        self.assertNotIn("<entry>", text)
        self.assertIn("<updated>1970-01-01T00:00:00Z</updated>", text)

    def test_month_label_is_english_regardless_of_locale(self):
        # Fixed month names, not strftime("%B"), so LC_TIME cannot localise them.
        self.assertEqual(_month_label("2026-09"), "September 2026")
        self.assertEqual(_month_label("2026-01"), "January 2026")

    def test_every_emitted_class_has_a_selector_in_the_stylesheet(self):
        # Guards against class-name drift between the generator and the sheet:
        # a rename on either side would otherwise ship unstyled HTML.
        css = (Path(__file__).resolve().parents[1] / "assets"
               / "magazine.css").read_text(encoding="utf-8")
        populated = self.issues / "index.html"
        build_index(sorted(self.issues.glob("20*.html")), populated)
        empty = self.issues / "empty.html"
        build_index([], empty)
        classes: set[str] = set()
        for out in (populated, empty):
            for group in re.findall(r'class="([^"]+)"',
                                    out.read_text(encoding="utf-8")):
                classes.update(group.split())
        # Sanity: we actually scanned both the populated and empty outputs.
        self.assertIn("archive__summary", classes)
        self.assertIn("archive__empty", classes)
        missing = [c for c in sorted(classes) if f".{c}" not in css]
        self.assertEqual(missing, [], f"classes with no selector: {missing}")


if __name__ == "__main__":
    unittest.main()
