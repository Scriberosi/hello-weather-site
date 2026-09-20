import unittest

from check_contrast import check_contrast, contrast_ratio, overlay_white

PASSING = """
:root {
  --text: #0d1b2a;
  --text-muted: #33414f;
  --bg-from: #99afc3;
  --bg-to: #e4eaef;
  --surface-alpha: 0.5;
}
@media (prefers-color-scheme: dark) {
  :root {
    --text: #f6f8fc;
    --text-muted: #c6d2e2;
    --bg-from: #10151f;
    --bg-to: #333d4f;
    --surface-alpha: 0.08;
  }
}
"""


class ContrastTest(unittest.TestCase):
    def test_known_ratio(self):
        self.assertAlmostEqual(contrast_ratio((0, 0, 0), (255, 255, 255)), 21.0, places=2)

    def test_overlay_lightens_towards_white(self):
        self.assertEqual(overlay_white((0, 0, 0), 1.0), (255, 255, 255))
        self.assertEqual(overlay_white((0, 0, 0), 0.0), (0, 0, 0))

    def test_shipped_tokens_pass(self):
        self.assertEqual(check_contrast(PASSING), [])

    def test_muted_text_too_faint_is_reported(self):
        bad = PASSING.replace("--text-muted: #33414f;", "--text-muted: #9aa6b2;")
        problems = check_contrast(bad)
        self.assertTrue(any("text-muted" in p for p in problems), problems)

    def test_dark_scheme_is_checked_too(self):
        bad = PASSING.replace("--text: #f6f8fc;", "--text: #2a2f36;")
        problems = check_contrast(bad)
        self.assertTrue(any("dark" in p for p in problems), problems)

    def test_a_token_less_extension_stylesheet_has_nothing_to_check(self):
        # assets/magazine.css only references tokens; it defines none, so the
        # contrast it inherits is gated on assets/site.css, not on itself.
        extension = ".issue { color: var(--text); background: var(--surface); }"
        self.assertEqual(check_contrast(extension, is_extension=True), [])

    def test_a_primary_stylesheet_missing_its_palette_is_reported(self):
        # Regression: the token-less skip must apply to declared extensions
        # only. A non-empty primary stylesheet lacking the palette is a defect,
        # not a silent pass.
        broken = ".issue { color: rebeccapurple; }"
        problems = check_contrast(broken)
        self.assertTrue(problems)
        self.assertTrue(any("surface-alpha" in p for p in problems), problems)
        # Declared as an extension, the very same file is a no-op.
        self.assertEqual(check_contrast(broken, is_extension=True), [])


if __name__ == "__main__":
    unittest.main()
