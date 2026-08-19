"""Unit tests for the card display layer of emulo.py.

The card is the one artifact users screenshot and post, and it renders text a
language model wrote into a fixed-width terminal frame and into HTML. Only the
happy path was covered (one subprocess run in test_emulo.py, one HTML label
assertion in test_profile_store.py); everything below is the malformed-input,
boundary and layout behaviour that a regression would otherwise reach the
screenshot before anyone noticed.
"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("emulo_card", ROOT / "emulo.py")
emulo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(emulo)


def sample_card(**overrides):
    card = {
        "archetype": "Proof-First Builder",
        "laws": [
            {"text": "done means it runs live in production for a real user", "count": "18/20"},
            {"text": "fix the one thing", "count": "15/20"},
            {"text": "no filler in the report", "count": "9/20"},
        ],
        "truth": "asks the agent to explain his own system back to him",
        "stats": {
            "sessions": 1656,
            "messages": 7678,
            "tokens": 2950000,
            "first_date": "2025-11-02",
            "last_date": "2026-07-08",
        },
    }
    card.update(overrides)
    return card


def render_terminal_card(card, columns=80, stream=None):
    """Render the static card and return its stdout as a string."""
    buf = stream if stream is not None else io.StringIO()
    size = os.terminal_size((columns, 48))
    with mock.patch.object(shutil, "get_terminal_size", return_value=size):
        with contextlib.redirect_stdout(buf):
            emulo.print_card(card, still=True)
    return buf.getvalue()


def frame_lines(rendered):
    return [line for line in rendered.split("\n") if line.strip()]


class TokenAndDateFormattingTest(unittest.TestCase):
    def test_fmt_tokens_switches_units_at_the_exact_boundaries(self):
        self.assertEqual("0", emulo.fmt_tokens(0))
        self.assertEqual("999", emulo.fmt_tokens(999))
        self.assertEqual("1K", emulo.fmt_tokens(1000))
        self.assertEqual("999K", emulo.fmt_tokens(999_999))
        self.assertEqual("1.0M", emulo.fmt_tokens(1_000_000))
        self.assertEqual("3.0M", emulo.fmt_tokens(2_950_000))

    def test_fmt_tokens_truncates_thousands_instead_of_rounding_up(self):
        # 1999 tokens must never read as "2K" on a card people screenshot
        self.assertEqual("1K", emulo.fmt_tokens(1999))

    def test_months_between_counts_an_inclusive_span(self):
        self.assertEqual(9, emulo.months_between("2025-11-02", "2026-07-08"))
        self.assertEqual(1, emulo.months_between("2026-07-01", "2026-07-31"))
        self.assertEqual(12, emulo.months_between("2025-01-05", "2025-12-31"))

    def test_months_between_clamps_a_reversed_range_to_one_month(self):
        self.assertEqual(1, emulo.months_between("2026-07-08", "2025-11-02"))

    def test_months_between_returns_zero_for_unparseable_dates(self):
        for first, last in (
            ("", ""),
            ("not-a-date", "2026-07-08"),
            ("2025-11-02", "nope"),
            ("2025", "2026"),
            ("2026-7-8", "2026-09-01"),
        ):
            with self.subTest(first=first, last=last):
                self.assertEqual(0, emulo.months_between(first, last))

    @unittest.expectedFailure
    def test_months_between_survives_null_dates(self):
        # BUG: months_between catches (ValueError, IndexError) but a card.json
        # with `"first_date": null` yields None, and None[:4] raises TypeError.
        # That escapes both print_card and render_card_html, so `emulo --card`
        # tracebacks on a reducer that emitted nulls instead of empty strings.
        # Fix is one word: add TypeError to the except tuple. Not fixing here.
        self.assertEqual(0, emulo.months_between(None, None))


class LawBarTest(unittest.TestCase):
    def test_bar_is_always_exactly_the_requested_width(self):
        for count in ("18/20", "0/20", "20/20", "1/3"):
            with self.subTest(count=count):
                self.assertEqual(26, len(emulo._law_bar(count)))
                self.assertEqual(40, len(emulo._law_bar(count, width=40)))

    def test_bar_fills_in_proportion_to_the_ratio(self):
        self.assertEqual("█" * 23 + "░" * 3, emulo._law_bar("18/20"))
        self.assertEqual("░" * 26, emulo._law_bar("0/20"))
        self.assertEqual("█" * 26, emulo._law_bar("20/20"))

    def test_bar_clamps_ratios_outside_zero_to_one(self):
        self.assertEqual("█" * 10, emulo._law_bar("30/20", width=10))
        self.assertEqual("░" * 10, emulo._law_bar("-5/20", width=10))

    def test_zero_denominator_does_not_divide_by_zero(self):
        self.assertEqual("█" * 10, emulo._law_bar("18/0", width=10))

    def test_non_ratio_counts_get_no_bar(self):
        # these are the shapes a reducer actually emits when it drifts:
        # a prose count, a bare number, a null, an over-split string
        for count in ("2 sessions", "abc", "5", "", None, "1/2/3", "x/y"):
            with self.subTest(count=count):
                self.assertIsNone(emulo._law_bar(count))


class CardHtmlTest(unittest.TestCase):
    def test_mined_text_is_html_escaped_in_every_slot(self):
        html = emulo.render_card_html(sample_card(
            archetype="<script>alert(1)</script>",
            laws=[{"text": "ships & <b>proves</b>", "count": "<i>9/20</i>"}],
            truth="he said 5 > 3 & meant it",
        ))
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("ships &amp; &lt;b&gt;proves&lt;/b&gt;", html)
        self.assertIn("5 &gt; 3 &amp; meant it", html)
        # the grade cell reads from the same law and must be escaped too
        self.assertNotIn("<i>9/20</i>", html)

    def test_only_the_first_three_laws_are_rendered(self):
        laws = [{"text": f"law number {i}", "count": f"{i}/20"} for i in range(1, 6)]
        html = emulo.render_card_html(sample_card(laws=laws))
        self.assertEqual(3, html.count("<div class=law>"))
        self.assertIn("LEX III", html)
        self.assertNotIn("law number 4", html)
        self.assertNotIn("law number 5", html)

    def test_missing_stats_drop_their_cells_instead_of_printing_zeroes(self):
        html = emulo.render_card_html(sample_card(stats={}))
        self.assertNotIn("<div class=stat>", html)
        self.assertNotIn("messages on record", html)
        self.assertIn("&nbsp;", html)
        # no date range means no arrow line
        self.assertNotIn("&rarr;", html)

    def test_zero_valued_stats_are_treated_as_absent(self):
        html = emulo.render_card_html(sample_card(stats={"sessions": 0, "tokens": 0}))
        self.assertNotIn("sessions</span>", html)
        self.assertNotIn("tokens of me", html)

    def test_grade_falls_back_when_the_top_law_has_no_count(self):
        self.assertIn("&mdash;", emulo.render_card_html(sample_card(laws=[{"text": "a law"}])))
        self.assertIn("&mdash;", emulo.render_card_html(sample_card(laws=[])))

    def test_truth_block_is_omitted_when_there_is_no_truth(self):
        html = emulo.render_card_html(sample_card(truth=""))
        self.assertNotIn("the uncomfortable one", html)

    def test_art_is_relative_to_out_dir_and_remote_without_one(self):
        remote = "https://raw.githubusercontent.com/ohad6k/emulo/main/assets/emulo.png"
        with_dir = emulo.render_card_html(sample_card(_out_dir=str(ROOT / "emulo-out")))
        self.assertIn('src="../assets/emulo.png"', with_dir)
        # the remote copy stays as the onerror fallback
        self.assertIn(remote, with_dir)
        without = emulo.render_card_html(sample_card())
        self.assertIn(f'src="{remote}"', without)

    def test_html_has_no_unfilled_format_placeholders(self):
        html = emulo.render_card_html(sample_card())
        for slot in ("{archetype}", "{stats}", "{laws}", "{truth}", "{grade}", "{range}"):
            self.assertNotIn(slot, html)

    @unittest.expectedFailure
    def test_html_renders_with_null_dates(self):
        # same TypeError as test_months_between_survives_null_dates: a card.json
        # carrying JSON nulls for the dates crashes the HTML writer too.
        emulo.render_card_html(sample_card(stats={"sessions": 3, "first_date": None, "last_date": None}))


class LoadCardTest(unittest.TestCase):
    def test_stats_json_overrides_stats_embedded_in_card_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "card.json").write_text(
                json.dumps({"archetype": "a", "stats": {"sessions": 1, "tokens": 10}}),
                encoding="utf-8",
            )
            (out / "stats.json").write_text(
                json.dumps({"sessions": 1656, "messages": 7678}), encoding="utf-8"
            )
            card = emulo.load_card(str(out))
            self.assertEqual(1656, card["stats"]["sessions"])
            self.assertEqual(7678, card["stats"]["messages"])
            # keys only present in card.json survive the merge
            self.assertEqual(10, card["stats"]["tokens"])

    def test_card_stats_are_kept_when_no_stats_json_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "card.json").write_text(
                json.dumps({"archetype": "a", "stats": {"sessions": 7}}), encoding="utf-8"
            )
            self.assertEqual(7, emulo.load_card(str(out))["stats"]["sessions"])

    def test_a_card_without_stats_gains_an_empty_stats_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "card.json").write_text(json.dumps({"archetype": "a"}), encoding="utf-8")
            (out / "stats.json").write_text(json.dumps({"sessions": 3}), encoding="utf-8")
            self.assertEqual({"sessions": 3}, emulo.load_card(str(out))["stats"])

    def test_missing_card_exits_one_with_the_mining_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                with self.assertRaises(SystemExit) as raised:
                    emulo.load_card(tmp)
            self.assertEqual(1, raised.exception.code)
            self.assertIn("no card found", buf.getvalue())
            self.assertIn("MINING_PROMPT.md", buf.getvalue())

    def test_explicit_card_path_wins_over_the_out_dir_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "card.json").write_text(json.dumps({"archetype": "default"}), encoding="utf-8")
            (out / "other.json").write_text(json.dumps({"archetype": "explicit"}), encoding="utf-8")
            card = emulo.load_card(str(out), card_path=str(out / "other.json"))
            self.assertEqual("explicit", card["archetype"])


class TerminalCardLayoutTest(unittest.TestCase):
    def test_every_framed_line_is_the_same_width_at_every_terminal_size(self):
        # the whole point of the card is that the box closes; a padding
        # regression shows up as a torn right edge in the screenshot.
        card = sample_card()
        for columns in (40, 62, 80, 103, 106, 107, 120, 200):
            with self.subTest(columns=columns):
                lines = frame_lines(render_terminal_card(card, columns=columns))
                self.assertEqual(1, len(set(len(line) for line in lines)), set(len(l) for l in lines))
                self.assertTrue(lines[0].startswith("╭"))
                self.assertTrue(lines[-1].startswith("╰"))

    def test_narrow_and_wide_layouts_both_carry_the_data_column(self):
        narrow = render_terminal_card(sample_card(), columns=80)
        wide = render_terminal_card(sample_card(), columns=140)
        for rendered in (narrow, wide):
            self.assertIn("PROOF-FIRST BUILDER", rendered)
            self.assertIn("1,656 sessions", rendered)
            self.assertIn("3.0M tokens", rendered)
            self.assertIn("9 months", rendered)
            self.assertIn("THE UNCOMFORTABLE ONE", rendered)
            self.assertIn("LEX III", rendered)
        # the wide layout puts the engraving beside the data, so it is shorter
        self.assertLess(len(frame_lines(wide)), len(frame_lines(narrow)))

    def test_long_law_text_wraps_instead_of_overflowing_the_frame(self):
        card = sample_card(laws=[{"text": "prove it end to end " * 12, "count": "3/20"}])
        lines = frame_lines(render_terminal_card(card, columns=80))
        self.assertEqual(1, len(set(len(line) for line in lines)))

    def test_a_count_without_a_ratio_is_printed_as_plain_text(self):
        card = sample_card(laws=[{"text": "counts distinct sessions", "count": "12 sessions"}])
        rendered = render_terminal_card(card, columns=80)
        self.assertIn("12 sessions", rendered)
        self.assertNotIn("░", rendered)  # no partial bar drawn

    def test_only_three_laws_reach_the_terminal_card(self):
        laws = [{"text": f"law number {i}", "count": f"{i}/20"} for i in range(1, 6)]
        rendered = render_terminal_card(sample_card(laws=laws), columns=80)
        self.assertIn("law number 3", rendered)
        self.assertNotIn("law number 4", rendered)

    def test_an_empty_card_still_renders_a_closed_frame(self):
        rendered = render_terminal_card({}, columns=80)
        lines = frame_lines(rendered)
        self.assertEqual(1, len(set(len(line) for line in lines)))
        # the brand mark and footer are fixed, so a card with no mined content
        # degrades to an empty frame instead of a traceback
        self.assertIn(emulo._CARD_LOGO[0].rstrip(), rendered)
        self.assertIn("your working profile", rendered)
        self.assertNotIn("THE UNCOMFORTABLE ONE", rendered)

    def test_static_card_emits_no_ansi_when_stdout_is_not_a_tty(self):
        self.assertNotIn("\x1b", render_terminal_card(sample_card(), columns=120))

    def test_no_color_env_disables_the_accent_palette(self):
        tty = mock.Mock()
        tty.isatty.return_value = True
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            with mock.patch.object(sys, "stdout", tty):
                self.assertEqual({""}, set(emulo._card_colors().values()))


class AsciiOnlyStream(io.StringIO):
    """A cp437-style console: anything above ASCII blows up on write."""

    def write(self, text):
        for index, char in enumerate(text):
            if ord(char) > 127:
                raise UnicodeEncodeError("charmap", text, index, index + 1, "undefined")
        return super().write(text)


class PlainFallbackTest(unittest.TestCase):
    def test_a_console_that_cannot_draw_blocks_gets_the_ascii_card(self):
        stream = AsciiOnlyStream()
        rendered = render_terminal_card(sample_card(), columns=80, stream=stream)
        self.assertNotIn("│", rendered)
        self.assertIn("+---", rendered)
        self.assertIn("PROOF-FIRST BUILDER", rendered)
        self.assertIn("1,656 sessions | 3.0M tokens | 9 months", rendered)
        self.assertIn("the uncomfortable one:", rendered)
        self.assertIn("[18/20]", rendered)

    def test_plain_card_rows_all_share_the_border_width(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            emulo._print_card_plain(sample_card(), sample_card()["stats"], 9)
        lines = [line for line in buf.getvalue().split("\n") if line]
        self.assertEqual(1, len(set(len(line) for line in lines)))

    def test_plain_card_omits_missing_sections(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            emulo._print_card_plain({"archetype": "a", "laws": [], "truth": ""}, {}, 0)
        rendered = buf.getvalue()
        self.assertNotIn("uncomfortable", rendered)
        self.assertNotIn("months", rendered)


class ShowCardTest(unittest.TestCase):
    def test_show_card_writes_html_beside_the_card_and_never_opens_a_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "emulo-out"
            out.mkdir()
            (out / "card.json").write_text(json.dumps(sample_card()), encoding="utf-8")
            buf = io.StringIO()
            size = os.terminal_size((80, 48))
            with mock.patch.object(shutil, "get_terminal_size", return_value=size):
                with mock.patch("webbrowser.open") as opener:
                    with contextlib.redirect_stdout(buf):
                        emulo.show_card(str(out), no_open=True, still=True)
            opener.assert_not_called()
            html = (out / "card.html").read_text(encoding="utf-8")
            self.assertIn("Proof-First Builder", html)
            self.assertIn("18/20", html)
            self.assertIn("wrote:", buf.getvalue())

    def test_show_card_html_points_at_the_repo_art_relative_to_out_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "emulo-out"
            out.mkdir()
            (out / "card.json").write_text(json.dumps(sample_card()), encoding="utf-8")
            size = os.terminal_size((80, 48))
            with mock.patch.object(shutil, "get_terminal_size", return_value=size):
                with mock.patch("webbrowser.open"):
                    with contextlib.redirect_stdout(io.StringIO()):
                        emulo.show_card(str(out), no_open=True, still=True)
            html = (out / "card.html").read_text(encoding="utf-8")
            # a temp dir on another volume cannot be relative to the repo, and
            # the writer must fall back to the remote asset rather than crash
            self.assertIn("assets/emulo.png", html)


class FrontmatterStrippingTest(unittest.TestCase):
    def test_frontmatter_block_is_removed_from_the_profile_body(self):
        text = "---\nname: you\ndescription: profile\n---\n- done means live\n"
        self.assertEqual("- done means live", emulo.strip_frontmatter(text))

    def test_text_without_frontmatter_is_only_trimmed(self):
        self.assertEqual("- done means live", emulo.strip_frontmatter("\n- done means live\n\n"))

    def test_unterminated_frontmatter_is_left_intact(self):
        # better to leak the header than to swallow the whole profile
        text = "---\nname: you\n"
        self.assertEqual("---\nname: you", emulo.strip_frontmatter(text))

    def test_a_body_containing_a_rule_line_keeps_that_rule(self):
        text = "---\nname: you\n---\nintro\n\n---\n\nmore\n"
        self.assertEqual("intro\n\n---\n\nmore", emulo.strip_frontmatter(text))

    def test_cursor_rule_replaces_frontmatter_with_the_mdc_header(self):
        rule = emulo.cursor_rule("---\nname: you\ndescription: d\n---\n- done means live\n")
        self.assertTrue(rule.startswith("---\ndescription: emulo user profile\n"))
        self.assertIn("alwaysApply: true", rule)
        self.assertIn("- done means live", rule)
        self.assertNotIn("name: you", rule)


class InstallDestinationTest(unittest.TestCase):
    def test_each_target_maps_to_its_documented_path(self):
        repo = os.path.join("R:", os.sep, "repo")
        home = os.path.join("H:", os.sep, "home")
        cases = {
            "claude": os.path.join(home, ".claude", "skills", "you", "SKILL.md"),
            "codex": os.path.join(home, ".codex", "skills", "you", "SKILL.md"),
            "cursor": os.path.join(repo, ".cursor", "rules", "you.mdc"),
            "agents": os.path.join(repo, "AGENTS.md"),
            "gemini": os.path.join(repo, "GEMINI.md"),
            "opencode": os.path.join(home, ".config", "opencode", "AGENTS.md"),
        }
        for target, expected in cases.items():
            with self.subTest(target=target):
                self.assertEqual(expected, emulo.install_destination(target, repo, home))

    def test_home_targets_never_write_inside_the_repo(self):
        repo = os.path.join("R:", os.sep, "repo")
        home = os.path.join("H:", os.sep, "home")
        for target in ("claude", "codex", "opencode"):
            with self.subTest(target=target):
                self.assertNotIn("repo", emulo.install_destination(target, repo, home))

    def test_an_unknown_target_is_rejected_rather_than_guessed(self):
        with self.assertRaisesRegex(ValueError, "unknown target"):
            emulo.install_destination("windsurf", "repo", "home")


if __name__ == "__main__":
    unittest.main()
