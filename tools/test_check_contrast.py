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


if __name__ == "__main__":
    unittest.main()
