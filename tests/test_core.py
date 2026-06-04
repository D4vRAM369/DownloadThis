import unittest

from downloadthis_modern import (
    extract_urls,
    is_dangerous_ytdlp_arg,
    parse_progress_line,
    parse_safe_extra_args,
)


class UrlExtractionTests(unittest.TestCase):
    def test_extracts_urls_from_text(self):
        urls = extract_urls("Uno https://example.com/a y otro www.example.org/b.")

        self.assertEqual(set(urls), {"https://example.com/a", "www.example.org/b"})

    def test_accepts_ytdlp_search_syntax(self):
        self.assertEqual(extract_urls("ytsearch3: massive attack teardrop"),
                         ["ytsearch3: massive attack teardrop"])


class ProgressParserTests(unittest.TestCase):
    def test_parses_detailed_download_line(self):
        info = parse_progress_line(
            "[download]  72.3% of 8.40MiB at 1.23MiB/s ETA 00:04"
        )

        self.assertEqual(info.percent, 72.3)
        self.assertEqual(info.size, "8.40MiB")
        self.assertEqual(info.speed, "1.23MiB/s")
        self.assertEqual(info.eta, "00:04")

    def test_parses_playlist_index(self):
        info = parse_progress_line("[download] Downloading video 7 of 42")

        self.assertEqual(info.item_current, 7)
        self.assertEqual(info.item_total, 42)


class ExtraArgsSecurityTests(unittest.TestCase):
    def test_allows_safe_ytdlp_args(self):
        tokens = parse_safe_extra_args("--retries infinite --user-agent Mozilla/5.0")

        self.assertEqual(tokens, ["--retries", "infinite", "--user-agent", "Mozilla/5.0"])

    def test_blocks_exact_dangerous_flags(self):
        with self.assertRaises(ValueError):
            parse_safe_extra_args("--exec echo-pwned")

    def test_blocks_equals_form_dangerous_flags(self):
        with self.assertRaises(ValueError):
            parse_safe_extra_args("--exec=echo-pwned")

    def test_blocks_dangerous_flags_case_insensitively(self):
        self.assertTrue(is_dangerous_ytdlp_arg("--EXEC=echo-pwned"))


if __name__ == "__main__":
    unittest.main()
