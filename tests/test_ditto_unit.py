"""In-process unit tests that exercise every branch of ditto.py.

The subprocess tests in test_ditto.py validate the CLI end to end. These
tests import ditto directly so coverage can measure ditto.py's own lines,
targeting 100% block coverage.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ditto  # noqa: E402


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def write_raw(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def run_main(argv):
    out = io.StringIO()
    code = None
    with mock.patch.object(sys, "argv", ["ditto.py"] + argv), \
            contextlib.redirect_stdout(out):
        try:
            ditto.main()
        except SystemExit as exc:
            code = exc.code
    return out.getvalue(), code


class TmpTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)


class RedactTest(unittest.TestCase):
    def test_redact_replaces_known_secrets(self):
        self.assertIn("[OPENAI_KEY]", ditto.redact("key sk-" + "a" * 30))
        self.assertEqual(ditto.redact("api_key=hunter2"), "api_key=[REDACTED]")

    def test_redact_leaves_clean_text_untouched(self):
        self.assertEqual(ditto.redact("just prose here"), "just prose here")


class IsPastedLogTest(unittest.TestCase):
    def test_short_text_is_never_a_log(self):
        self.assertFalse(ditto.is_pasted_log("one\ntwo\nthree"))

    def test_traceback_heavy_text_is_a_log(self):
        dump = "\n".join([
            "Traceback (most recent call last):",
            '  File "app.py", line 3, in <module>',
            "    at com.foo.Bar(Bar.java:12)",
            "RuntimeException: boom",
        ])
        self.assertTrue(ditto.is_pasted_log(dump))

    def test_prose_with_four_lines_is_not_a_log(self):
        prose = "we should\nkeep the fix small\nand add a test\nthen ship"
        self.assertFalse(ditto.is_pasted_log(prose))


class UserMessagesTest(TmpTest):
    def test_copilot_user_message_is_extracted(self):
        f = self.tmp / "sess" / "events.jsonl"
        write_jsonl(f, [{
            "type": "user.message",
            "timestamp": "2026-07-04T04:14:03.574Z",
            "data": {"content": "keep answers short"},
        }])
        self.assertEqual(ditto.user_messages(f), [("2026-07-04", "keep answers short")])

    def test_copilot_system_source_is_skipped(self):
        f = self.tmp / "sess" / "events.jsonl"
        write_jsonl(f, [{
            "type": "user.message",
            "timestamp": "2026-07-04T04:14:04.433Z",
            "data": {"content": "steering text", "source": "system"},
        }])
        self.assertEqual(ditto.user_messages(f), [])

    def test_copilot_empty_content_is_skipped(self):
        f = self.tmp / "sess" / "events.jsonl"
        write_jsonl(f, [{
            "type": "user.message",
            "timestamp": "2026-07-04T04:14:04.433Z",
            "data": {"content": ""},
        }])
        self.assertEqual(ditto.user_messages(f), [])

    def test_codex_list_content_extracted_assistant_skipped(self):
        f = self.tmp / "codex.jsonl"
        write_jsonl(f, [
            {"timestamp": "2026-07-08T10:00:00Z",
             "payload": {"type": "message", "role": "user",
                         "content": [{"text": "do the smallest fix"}]}},
            {"timestamp": "2026-07-08T10:01:00Z",
             "payload": {"type": "message", "role": "assistant",
                         "content": [{"text": "ignore me"}]}},
        ])
        self.assertEqual(ditto.user_messages(f), [("2026-07-08", "do the smallest fix")])

    def test_claude_string_content_extracted(self):
        f = self.tmp / "claude.jsonl"
        write_jsonl(f, [{
            "timestamp": "2026-07-08T11:00:00Z",
            "type": "user",
            "message": {"role": "user", "content": "prove it with a test"},
        }])
        self.assertEqual(ditto.user_messages(f), [("2026-07-08", "prove it with a test")])

    def test_non_string_non_list_content_yields_nothing(self):
        f = self.tmp / "weird.jsonl"
        write_jsonl(f, [{
            "timestamp": "2026-07-08T11:00:00Z",
            "type": "user",
            "message": {"role": "user", "content": 123},
        }])
        self.assertEqual(ditto.user_messages(f), [])

    def test_lines_without_markers_and_bad_json_are_skipped(self):
        f = self.tmp / "mixed.jsonl"
        # First line has no role/user/user.message marker -> pre-filter skip.
        # Second line has "user" but is invalid json -> json.loads skip.
        write_raw(f, ['{"foo": "bar"}', '{"user": '])
        self.assertEqual(ditto.user_messages(f), [])

    def test_angle_bracket_and_pasted_log_content_are_dropped(self):
        f = self.tmp / "drop.jsonl"
        pasted = "\n".join([
            "Traceback (most recent call last):",
            '  File "x.py", line 1, in <module>',
            "    at a.b(C.java:2)",
            "Exception in thread",
        ])
        write_jsonl(f, [
            {"timestamp": "2026-07-08T11:00:00Z", "type": "user",
             "message": {"role": "user", "content": "<env injected>"}},
            {"timestamp": "2026-07-08T11:01:00Z", "type": "user",
             "message": {"role": "user", "content": pasted}},
        ])
        self.assertEqual(ditto.user_messages(f), [])

    def test_unreadable_path_returns_empty(self):
        self.assertEqual(ditto.user_messages(self.tmp / "does-not-exist.jsonl"), [])


class DiscoverFilesTest(TmpTest):
    def test_finds_nested_jsonl_and_dedupes_roots(self):
        (self.tmp / "a").mkdir()
        (self.tmp / "b").mkdir()
        (self.tmp / "a" / "one.jsonl").write_text("{}", encoding="utf-8")
        (self.tmp / "b" / "two.jsonl").write_text("{}", encoding="utf-8")
        found = ditto.discover_files([str(self.tmp), str(self.tmp)])
        self.assertEqual(len(found), 2)
        self.assertTrue(all(p.endswith(".jsonl") for p in found))


class SessionLabelTest(unittest.TestCase):
    def test_parent_dir_is_prefixed(self):
        self.assertEqual(
            ditto.session_label("/x/session-state/abc-123/events.jsonl"),
            "abc-123/events.jsonl")

    def test_bare_filename_has_no_prefix(self):
        self.assertEqual(ditto.session_label("events.jsonl"), "events.jsonl")


class MineFilesTest(TmpTest):
    def _codex(self, name, text):
        f = self.tmp / name
        write_jsonl(f, [{
            "timestamp": "2026-07-08T10:00:00Z",
            "payload": {"type": "message", "role": "user",
                        "content": [{"text": text}]},
        }])
        return f

    def test_counts_redactions_and_skips_empty_sessions(self):
        secret = self._codex("secret.jsonl", "api_key=topsecret ship it")
        clean = self._codex("clean.jsonl", "keep it small")
        empty = self.tmp / "empty.jsonl"
        write_jsonl(empty, [{"timestamp": "t", "payload": {
            "type": "message", "role": "assistant", "content": [{"text": "nope"}]}}])
        result = ditto.mine_files([str(secret), str(clean), str(empty)])
        self.assertEqual(result["sessions"], 2)
        self.assertEqual(result["messages"], 2)
        self.assertEqual(result["redactions"], 1)
        self.assertTrue(any("api_key=[REDACTED]" in b for b in result["blocks"]))

    def test_no_redact_leaves_secret_and_counts_zero(self):
        secret = self._codex("secret.jsonl", "api_key=topsecret ship it")
        result = ditto.mine_files([str(secret)], no_redact=True)
        self.assertEqual(result["redactions"], 0)
        self.assertTrue(any("topsecret" in b for b in result["blocks"]))


class WriteOutputsTest(TmpTest):
    def test_empty_blocks_write_empty_corpus_and_no_chunks(self):
        out = self.tmp / "out"
        count = ditto.write_outputs([], str(out), 5)
        self.assertEqual(count, 0)
        self.assertEqual((out / "you-corpus.txt").read_text(encoding="utf-8"), "")
        self.assertEqual(list((out / "chunks").iterdir()), [])

    def test_chunking_writes_midloop_and_flushes_remainder(self):
        out = self.tmp / "out"
        blocks = ["a" * 10, "b" * 10, "c" * 5]
        count = ditto.write_outputs(blocks, str(out), 3)
        self.assertEqual(count, 3)
        names = sorted(p.name for p in (out / "chunks").iterdir())
        self.assertEqual(names, ["chunk-01.txt", "chunk-02.txt", "chunk-03.txt"])


class PrintCountsTest(unittest.TestCase):
    def _run(self, no_redact):
        result = {"sessions": 1, "messages": 2, "chars": 40, "redactions": 3}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ditto.print_counts(result, no_redact)
        return buf.getvalue()

    def test_redaction_on_and_off_labels(self):
        self.assertNotIn("redaction OFF", self._run(False))
        self.assertIn("redaction OFF", self._run(True))

    def test_duplicates_line_shown_when_present(self):
        result = {"sessions": 1, "messages": 2, "chars": 40,
                  "redactions": 0, "duplicates": 3}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ditto.print_counts(result)
        self.assertIn("duplicate specs/rules collapsed: 3", buf.getvalue())


class MineFilesDedupeTest(TmpTest):
    LONG = "x" * (ditto.DEDUPE_MIN_LEN + 10)

    def _codex(self, name, text, ts="2026-07-08T10:00:00Z"):
        f = self.tmp / name
        row = {"payload": {"type": "message", "role": "user",
                           "content": [{"text": text}]}}
        if ts is not None:
            row["timestamp"] = ts
        write_jsonl(f, [row])
        return str(f)

    def test_verbatim_long_duplicate_is_collapsed(self):
        a = self._codex("a.jsonl", self.LONG)
        b = self._codex("b.jsonl", self.LONG)  # same long text, different session
        result = ditto.mine_files([a, b])
        self.assertEqual(result["sessions"], 1)     # b is all-duplicate, skipped
        self.assertEqual(result["messages"], 1)
        self.assertEqual(result["duplicates"], 1)

    def test_no_dedupe_keeps_both_copies(self):
        a = self._codex("a.jsonl", self.LONG)
        b = self._codex("b.jsonl", self.LONG)
        result = ditto.mine_files([a, b], dedupe=False)
        self.assertEqual(result["sessions"], 2)
        self.assertEqual(result["messages"], 2)
        self.assertEqual(result["duplicates"], 0)

    def test_missing_timestamp_leaves_dates_empty(self):
        a = self._codex("a.jsonl", "no timestamp here", ts=None)
        result = ditto.mine_files([a])
        self.assertEqual(result["first_date"], "")
        self.assertEqual(result["last_date"], "")
        self.assertEqual(result["messages"], 1)

    def test_dates_track_min_and_max(self):
        a = self._codex("a.jsonl", "later", ts="2026-07-20T10:00:00Z")
        b = self._codex("b.jsonl", "earlier", ts="2026-02-01T10:00:00Z")
        result = ditto.mine_files([a, b])
        self.assertEqual(result["first_date"], "2026-02-01")
        self.assertEqual(result["last_date"], "2026-07-20")


class CardHelpersTest(unittest.TestCase):
    def test_months_between_valid(self):
        self.assertEqual(ditto.months_between("2026-01-15", "2026-07-20"), 7)

    def test_months_between_invalid_returns_zero(self):
        self.assertEqual(ditto.months_between("bad", "worse"), 0)

    def test_fmt_tokens_scales(self):
        self.assertEqual(ditto.fmt_tokens(2_500_000), "2.5M")
        self.assertEqual(ditto.fmt_tokens(3_000), "3K")
        self.assertEqual(ditto.fmt_tokens(42), "42")

    def test_esc_escapes_html_metacharacters(self):
        self.assertEqual(ditto.esc("<a&b>"), "&lt;a&amp;b&gt;")


def _full_card():
    return {
        "archetype": "the closer",
        "laws": [
            {"text": "prove it with a test", "count": "7/8"},
            {"text": "ship the complete thing", "count": "5"},
            {"text": "no fluff", "count": ""},
        ],
        "truth": "you rewrite more than you admit",
        "stats": {
            "sessions": 1042, "tokens": 750_000, "messages": 1623,
            "first_date": "2026-02-01", "last_date": "2026-07-20",
        },
    }


class LoadCardTest(TmpTest):
    def test_missing_card_exits(self):
        with self.assertRaises(SystemExit) as ctx, \
                contextlib.redirect_stdout(io.StringIO()):
            ditto.load_card(str(self.tmp))
        self.assertEqual(ctx.exception.code, 1)

    def test_loads_card_without_stats(self):
        (self.tmp / "card.json").write_text(
            json.dumps({"archetype": "x"}), encoding="utf-8")
        card = ditto.load_card(str(self.tmp))
        self.assertEqual(card["archetype"], "x")
        self.assertNotIn("stats", card)

    def test_merges_stats_json_when_present(self):
        (self.tmp / "card.json").write_text(
            json.dumps({"archetype": "x", "stats": {"sessions": 1}}),
            encoding="utf-8")
        (self.tmp / "stats.json").write_text(
            json.dumps({"tokens": 999}), encoding="utf-8")
        card = ditto.load_card(str(self.tmp))
        self.assertEqual(card["stats"]["sessions"], 1)
        self.assertEqual(card["stats"]["tokens"], 999)

    def test_explicit_card_path(self):
        p = self.tmp / "custom.json"
        p.write_text(json.dumps({"archetype": "y"}), encoding="utf-8")
        card = ditto.load_card(str(self.tmp), str(p))
        self.assertEqual(card["archetype"], "y")


class PrintCardTest(unittest.TestCase):
    def _render(self, card):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ditto.print_card(card)
        return buf.getvalue()

    def test_full_card_shows_all_sections(self):
        out = self._render(_full_card())
        self.assertIn("THE CLOSER", out)
        self.assertIn("1,042 sessions", out)
        self.assertIn("750K tokens", out)
        self.assertIn("prove it with a test", out)
        self.assertIn("the uncomfortable one:", out)

    def test_minimal_card_omits_optional_sections(self):
        out = self._render({})
        self.assertNotIn("the uncomfortable one:", out)


class RenderCardHtmlTest(unittest.TestCase):
    def test_full_card_html_contains_fields(self):
        card = _full_card()
        card["_out_dir"] = "/tmp/does-not-matter"
        html = ditto.render_card_html(card)
        self.assertIn("<!doctype html>", html)
        self.assertIn("the closer", html)
        self.assertIn("LEX I", html)
        self.assertIn("ranked by how many of 8 agents", html)

    def test_minimal_card_uses_fallbacks(self):
        html = ditto.render_card_html({})
        self.assertIn("&mdash;", html)               # grade fallback
        self.assertIn("ranked by how many agents", html)

    def test_local_art_used_when_asset_present(self):
        card = _full_card()
        card["_out_dir"] = "/tmp/out"
        html = ditto.render_card_html(card)
        self.assertIn("ditto.png", html)

    def test_remote_art_when_asset_absent(self):
        with mock.patch.object(ditto.os.path, "exists", return_value=False):
            html = ditto.render_card_html(_full_card())
        self.assertIn("raw.githubusercontent.com", html)

    def test_relpath_valueerror_falls_back_to_remote(self):
        card = _full_card()
        card["_out_dir"] = "/tmp/out"
        with mock.patch.object(ditto.os.path, "relpath",
                               side_effect=ValueError):
            html = ditto.render_card_html(card)
        self.assertIn("raw.githubusercontent.com", html)

    def test_reports_scans_past_laws_without_slash(self):
        card = _full_card()
        card["laws"] = [
            {"text": "first", "count": "5"},          # no slash, loop continues
            {"text": "second", "count": "9/12"},      # slash, sets reports
        ]
        html = ditto.render_card_html(card)
        self.assertIn("ranked by how many of 12 agents", html)


class ShowCardTest(TmpTest):
    def _seed(self):
        (self.tmp / "card.json").write_text(
            json.dumps(_full_card()), encoding="utf-8")

    def test_no_open_writes_html_without_browser(self):
        self._seed()
        with mock.patch("webbrowser.open") as opener, \
                contextlib.redirect_stdout(io.StringIO()):
            ditto.show_card(str(self.tmp), no_open=True)
        opener.assert_not_called()
        self.assertTrue((self.tmp / "card.html").exists())

    def test_opens_browser_when_allowed(self):
        self._seed()
        with mock.patch("webbrowser.open") as opener, \
                contextlib.redirect_stdout(io.StringIO()):
            ditto.show_card(str(self.tmp), no_open=False)
        opener.assert_called_once()

    def test_browser_error_is_swallowed(self):
        self._seed()
        with mock.patch("webbrowser.open", side_effect=RuntimeError), \
                contextlib.redirect_stdout(io.StringIO()):
            ditto.show_card(str(self.tmp), no_open=False)
        self.assertTrue((self.tmp / "card.html").exists())


class MainCardTest(TmpTest):
    def test_card_flag_renders_from_out_dir(self):
        out = self.tmp / "out"
        out.mkdir()
        (out / "card.json").write_text(
            json.dumps(_full_card()), encoding="utf-8")
        with mock.patch("webbrowser.open"):
            text, code = run_main(["--card", "--out", str(out), "--no-open"])
        self.assertIsNone(code)
        self.assertIn("THE CLOSER", text)

    def test_card_flag_missing_file_exits(self):
        out = self.tmp / "out"
        out.mkdir()
        text, code = run_main(["--card", "--out", str(out)])
        self.assertEqual(code, 1)
        self.assertIn("no card found", text)


class FrontmatterTest(unittest.TestCase):
    def test_strip_frontmatter_variants(self):
        self.assertEqual(ditto.strip_frontmatter("no fm here"), "no fm here")
        self.assertEqual(ditto.strip_frontmatter("---\nname: x"), "---\nname: x")
        self.assertEqual(
            ditto.strip_frontmatter("---\nname: x\n---\n\nbody text\n"), "body text")

    def test_has_skill_frontmatter_variants(self):
        self.assertFalse(ditto.has_skill_frontmatter("plain"))
        self.assertFalse(ditto.has_skill_frontmatter("---\nname: x"))
        self.assertFalse(ditto.has_skill_frontmatter("---\nname: x\n---\n"))
        self.assertTrue(
            ditto.has_skill_frontmatter("---\nname: x\ndescription: y\n---\n"))

    def test_cursor_rule_wraps_body(self):
        rule = ditto.cursor_rule("---\nname: x\ndescription: y\n---\n\nbe brief\n")
        self.assertTrue(rule.startswith("---\ndescription: ditto user profile\n"))
        self.assertIn("be brief", rule)
        self.assertNotIn("name: x", rule)


class InstallDestinationTest(unittest.TestCase):
    def test_all_targets_and_unknown(self):
        self.assertTrue(ditto.install_destination("claude", "/repo", "/home").endswith(
            "/.claude/skills/you/SKILL.md"))
        self.assertTrue(ditto.install_destination("codex", "/repo", "/home").endswith(
            "/.codex/skills/you/SKILL.md"))
        self.assertTrue(ditto.install_destination("cursor", "/repo", "/home").endswith(
            "/.cursor/rules/you.mdc"))
        self.assertTrue(ditto.install_destination("agents", "/repo", "/home").endswith(
            "/AGENTS.md"))
        self.assertTrue(ditto.install_destination("gemini", "/repo", "/home").endswith(
            "/GEMINI.md"))
        with self.assertRaises(ValueError):
            ditto.install_destination("bogus", "/repo", "/home")


class InstallProfileTest(TmpTest):
    FM = "---\nname: you\ndescription: d\n---\n\n# profile\n\n- be brief\n"
    NO_FM = "# just a heading\n"

    def _profile(self, text):
        p = self.tmp / "you.md"
        p.write_text(text, encoding="utf-8")
        return str(p)

    def _call(self, *args, **kwargs):
        buf = io.StringIO()
        code = None
        with contextlib.redirect_stdout(buf):
            try:
                ditto.install_profile(*args, **kwargs)
            except SystemExit as exc:
                code = exc.code
        return buf.getvalue(), code

    def test_missing_profile_exits(self):
        _, code = self._call(str(self.tmp / "nope.md"), "codex",
                             str(self.tmp), str(self.tmp))
        self.assertEqual(code, 1)

    def test_codex_requires_skill_frontmatter(self):
        out, code = self._call(self._profile(self.NO_FM), "codex",
                              str(self.tmp), str(self.tmp))
        self.assertEqual(code, 1)
        self.assertIn("must start with skill frontmatter", out)

    def test_dry_run_agents_and_file_targets(self):
        out_a, _ = self._call(self._profile(self.FM), "agents",
                             str(self.tmp), str(self.tmp), dry_run=True)
        self.assertIn("would append", out_a)
        out_c, _ = self._call(self._profile(self.FM), "codex",
                             str(self.tmp), str(self.tmp), dry_run=True)
        self.assertIn("would write profile file", out_c)

    def test_agents_new_file_created(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        self._call(self._profile(self.FM), "agents", str(repo), str(self.tmp))
        text = (repo / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith(ditto.DITTO_START))
        self.assertIn("- be brief", text)

    def test_agents_appends_without_deleting_existing(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        (repo / "AGENTS.md").write_text("# rules\n\nkeep this\n", encoding="utf-8")
        self._call(self._profile(self.FM), "agents", str(repo), str(self.tmp))
        text = (repo / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("keep this", text)
        self.assertIn(ditto.DITTO_START, text)

    def test_agents_existing_block_needs_yes_then_replaces(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        # Seed an existing ditto block.
        self._call(self._profile(self.FM), "agents", str(repo), str(self.tmp))
        # Without --yes it refuses.
        out, code = self._call(self._profile(self.FM), "agents",
                              str(repo), str(self.tmp))
        self.assertEqual(code, 1)
        self.assertIn("already exists", out)
        # With yes=True it replaces in place.
        new = self._profile(
            "---\nname: you\ndescription: d\n---\n\n# profile\n\n- new line\n")
        self._call(new, "agents", str(repo), str(self.tmp), yes=True)
        text = (repo / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("- new line", text)
        self.assertEqual(text.count(ditto.DITTO_START), 1)

    def test_cursor_writes_mdc(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        self._call(self._profile(self.FM), "cursor", str(repo), str(self.tmp))
        rule = (repo / ".cursor" / "rules" / "you.mdc").read_text(encoding="utf-8")
        self.assertIn("alwaysApply: true", rule)

    def test_codex_write_then_refuse_then_overwrite(self):
        home = self.tmp / "home"
        prof = self._profile(self.FM)
        self._call(prof, "codex", str(self.tmp), str(home))
        dest = home / ".codex" / "skills" / "you" / "SKILL.md"
        self.assertEqual(dest.read_text(encoding="utf-8"), self.FM)
        # Second run without --yes refuses.
        out, code = self._call(prof, "codex", str(self.tmp), str(home))
        self.assertEqual(code, 1)
        self.assertIn("destination already exists", out)
        # With yes=True it overwrites.
        _, code2 = self._call(prof, "codex", str(self.tmp), str(home), yes=True)
        self.assertIsNone(code2)


class MainTest(TmpTest):
    def _codex_log(self, root):
        write_jsonl(root / "codex.jsonl", [{
            "timestamp": "2026-07-08T10:00:00Z",
            "payload": {"type": "message", "role": "user",
                        "content": [{"text": "keep it small"}]},
        }])

    def test_install_requires_target(self):
        prof = self.tmp / "you.md"
        prof.write_text("body", encoding="utf-8")
        out, code = run_main(["--install", str(prof)])
        self.assertEqual(code, 1)
        self.assertIn("--install requires --target", out)

    def test_install_dispatches_to_install_profile(self):
        prof = self.tmp / "you.md"
        prof.write_text("---\nname: you\ndescription: d\n---\n\nbody\n", encoding="utf-8")
        out, code = run_main([
            "--install", str(prof), "--target", "codex", "--home", str(self.tmp / "h")])
        self.assertIsNone(code)
        self.assertIn("installed:", out)

    def test_path_source_writes_corpus(self):
        logs = self.tmp / "logs"
        self._codex_log(logs)
        out_dir = self.tmp / "out"
        out, code = run_main(["--path", str(logs), "--out", str(out_dir), "--chunks", "1"])
        self.assertIsNone(code)
        self.assertIn("wrote:", out)
        self.assertIn("keep it small", (out_dir / "you-corpus.txt").read_text(encoding="utf-8"))

    def test_no_logs_found_exits(self):
        out, code = run_main(["--path", str(self.tmp / "empty"), "--out", str(self.tmp / "o")])
        self.assertEqual(code, 1)
        self.assertIn("no session logs found", out)

    def test_auto_source_scans_all_three(self):
        codex_root = self.tmp / "codex"
        claude_root = self.tmp / "claude"
        copilot_root = self.tmp / "copilot"
        self._codex_log(codex_root)
        write_jsonl(copilot_root / "s" / "events.jsonl", [{
            "type": "user.message", "timestamp": "2026-07-04T04:00:00Z",
            "data": {"content": "prove it"}}])
        patched = {
            "codex": [str(codex_root)],
            "claude": [str(claude_root)],
            "copilot": [str(copilot_root)],
        }
        with mock.patch.object(ditto, "SOURCES", patched):
            out, code = run_main(["--source", "auto", "--out", str(self.tmp / "out"), "--dry-run"])
        self.assertIsNone(code)
        self.assertIn("dry run: no files written", out)
        self.assertIn("your messages: 2", out)

    def test_explicit_copilot_source(self):
        copilot_root = self.tmp / "copilot"
        write_jsonl(copilot_root / "s" / "events.jsonl", [{
            "type": "user.message", "timestamp": "2026-07-04T04:00:00Z",
            "data": {"content": "ship the complete thing"}}])
        with mock.patch.object(ditto, "SOURCES", {"copilot": [str(copilot_root)]}):
            out, code = run_main(["--source", "copilot", "--out", str(self.tmp / "out")])
        self.assertIsNone(code)
        self.assertIn("ship the complete thing",
                      (self.tmp / "out" / "you-corpus.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
