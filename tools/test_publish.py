import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from publish import decide_month, default_month, validate_month, write_issue


class ValidateMonthTests(unittest.TestCase):
    def test_accepts_a_real_month(self):
        self.assertEqual(validate_month("2026-09"), "2026-09")

    def test_rejects_shell_metacharacters(self):
        for bad in [
            "$(touch pwned)",
            "2026-09; rm -rf /",
            "2026-09 && ls",
            "`id`",
            "../../etc/passwd",
            "2026-09\n",
            "2026-09 ",
        ]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_month(bad)

    def test_rejects_malformed_or_impossible_months(self):
        for bad in ["2026-13", "2026-00", "2026-9", "26-09", "2026-091",
                    "2026/09", "2026-1a", ""]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_month(bad)

    def test_rejects_non_ascii_digits(self):
        # Arabic-Indic digits look like 2026-09 but are not ASCII [0-9].
        with self.assertRaises(ValueError):
            validate_month("\u0662\u0660\u0662\u0666-\u0660\u0669")


class DecideMonthTests(unittest.TestCase):
    def test_valid_explicit_month_is_used(self):
        self.assertEqual(decide_month("2026-09"), "2026-09")

    def test_blank_input_falls_back_to_the_previous_month(self):
        self.assertEqual(default_month(date(2026, 1, 15)), "2025-12")
        self.assertEqual(default_month(date(2026, 3, 1)), "2026-02")
        self.assertEqual(default_month(date(2026, 12, 31)), "2026-11")
        # An empty explicit input defers to the default rather than failing.
        self.assertEqual(decide_month(""), default_month())
        self.assertEqual(decide_month(None), default_month())

    def test_malicious_input_is_rejected(self):
        with self.assertRaises(ValueError):
            decide_month("$(touch pwned)")


class WriteIssueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.issues = self.root / "issues"

    def tearDown(self):
        self.tmp.cleanup()

    def _response(self, month, html="<h1>Hi</h1>", generator="app"):
        path = self.root / "response.json"
        path.write_text(
            json.dumps({"month": month, "rendered_html": html,
                        "generator": generator}),
            encoding="utf-8",
        )
        return path

    def test_writes_the_issue_for_a_matching_month(self):
        target = write_issue(self._response("2026-09"), "2026-09", self.issues)
        self.assertTrue(target.is_file())
        self.assertEqual(target.name, "2026-09.html")
        self.assertEqual(target.read_text(encoding="utf-8"), "<h1>Hi</h1>")

    def test_a_response_month_mismatch_is_refused(self):
        with self.assertRaises(ValueError):
            write_issue(self._response("2026-08"), "2026-09", self.issues)
        self.assertFalse((self.issues / "2026-09.html").exists())

    def test_an_existing_issue_is_never_overwritten(self):
        self.issues.mkdir()
        existing = self.issues / "2026-09.html"
        existing.write_text("KEEP", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            write_issue(self._response("2026-09"), "2026-09", self.issues)
        self.assertEqual(existing.read_text(encoding="utf-8"), "KEEP")

    def test_traversal_in_the_requested_month_is_refused(self):
        with self.assertRaises(ValueError):
            write_issue(
                self._response("../../etc/passwd"),
                "../../etc/passwd",
                self.issues,
            )

    def test_a_response_missing_rendered_html_is_refused(self):
        path = self.root / "response.json"
        path.write_text(json.dumps({"month": "2026-09"}), encoding="utf-8")
        with self.assertRaises(KeyError):
            write_issue(path, "2026-09", self.issues)


if __name__ == "__main__":
    unittest.main()
