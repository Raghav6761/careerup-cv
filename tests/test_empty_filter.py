"""
Unit tests for _is_empty_content and _filter_list in export_utils.py.
Run with: python -m unittest tests.test_empty_filter -v
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from export_utils import _is_empty_content, _filter_list


class TestIsEmptyContent(unittest.TestCase):
    # ── blank / whitespace ───────────────────────────────────────────────────
    def test_empty_string(self):
        self.assertTrue(_is_empty_content(""))

    def test_whitespace_only(self):
        self.assertTrue(_is_empty_content("   "))

    # ── Hebrew explicit placeholders ─────────────────────────────────────────
    def test_lo_tzuyan(self):
        self.assertTrue(_is_empty_content("לא צוין"))

    def test_lo_tzuyayn(self):
        self.assertTrue(_is_empty_content("לא צויין"))

    def test_lo_tzuyaynu(self):
        self.assertTrue(_is_empty_content("לא צויינו"))

    def test_lo_tzuynu(self):
        self.assertTrue(_is_empty_content("לא צוינו"))

    def test_lo_kayam(self):
        self.assertTrue(_is_empty_content("לא קיים"))

    def test_lo_mula(self):
        self.assertTrue(_is_empty_content("לא מולא"))

    # ── Hebrew regex: any "לא + word" phrase ─────────────────────────────────
    def test_lo_hoznu_with_context(self):
        self.assertTrue(_is_empty_content("לא הוזנו מיומנויות"))

    def test_lo_tzuynu_with_suffix(self):
        self.assertTrue(_is_empty_content("לא צוינו קורסים או הסמכות ייעודיים"))

    def test_lo_kayamet_with_context(self):
        self.assertTrue(_is_empty_content("לא קיימות הסמכות"))

    def test_lo_tzuyan_trailing_period(self):
        self.assertTrue(_is_empty_content("לא צוין."))

    # ── English placeholders ─────────────────────────────────────────────────
    def test_not_specified(self):
        self.assertTrue(_is_empty_content("not specified"))

    def test_na(self):
        self.assertTrue(_is_empty_content("n/a"))

    def test_none(self):
        self.assertTrue(_is_empty_content("none"))

    def test_not_provided(self):
        self.assertTrue(_is_empty_content("not provided"))

    # ── Real content should NOT be filtered ──────────────────────────────────
    def test_real_hebrew_content(self):
        self.assertFalse(_is_empty_content("פיתוח תוכנה ב-Python ו-JavaScript"))

    def test_real_english_content(self):
        self.assertFalse(_is_empty_content("Developed backend services using Python"))

    def test_real_single_word(self):
        self.assertFalse(_is_empty_content("Python"))

    def test_hebrew_positive_statement(self):
        self.assertFalse(_is_empty_content("ניסיון של 5 שנים בפיתוח"))


class TestFilterList(unittest.TestCase):
    def test_removes_placeholders(self):
        items = ["Python", "לא צוינו", "JavaScript", "not specified", ""]
        result = _filter_list(items)
        self.assertEqual(result, ["Python", "JavaScript"])

    def test_all_placeholders(self):
        self.assertEqual(_filter_list(["לא צוין", "לא צויינו", "n/a"]), [])

    def test_empty_input(self):
        self.assertEqual(_filter_list([]), [])

    def test_all_real(self):
        items = ["Python", "React", "Node.js"]
        self.assertEqual(_filter_list(items), items)


if __name__ == "__main__":
    unittest.main()
