import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ditto_store", ROOT / "ditto.py")
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)


def evidence_fixture():
    return {
        "ev-aaaaaaaa-done": {
            "kind": "inferred",
            "sessions": {"s1"},
            "strata": {"codex:2026-Q1"},
            "quote_count": 1,
            "quotes": [{"session_id": "s1", "date": "2026-01-01", "text": "done means live"}],
            "contradictions": [],
        },
        "ev-bbbbbbbb-proof": {
            "kind": "inferred",
            "sessions": {"s2"},
            "strata": {"codex:2026-Q2"},
            "quote_count": 1,
            "quotes": [{"session_id": "s2", "date": "2026-02-01", "text": "show me it works"}],
            "contradictions": [],
        },
    }


def run_plan_fixture(report_set_hash, segment_hash="a" * 64):
    return {
        "report_set_hash": report_set_hash,
        "source_coverage": {"sources": ["codex"], "first_date": "2026-01-01", "last_date": "2026-02-01"},
        "selected_source_tokens": 20000,
        "segment_hashes": [segment_hash],
        "adequate_strata": True,
    }


def make_valid_pack(path, report_set_hash):
    path.mkdir(parents=True, exist_ok=True)
    rule_text = "Always prove done."
    implication = "Run the relevant verification before reporting completion."
    (path / "you.md").write_text(
        "---\nname: ditto-work-profile\ndescription: evidence-backed working profile\n---\n\n"
        + rule_text + "\n" + implication + "\n",
        encoding="utf-8",
    )
    (path / "appendix.md").write_text(
        "# receipts\n\n## ev-aaaaaaaa-done\n- s1 2026-01-01: done means live\n\n"
        "## ev-bbbbbbbb-proof\n- s2 2026-02-01: show me it works\n",
        encoding="utf-8",
    )
    (path / "card.json").write_text(
        json.dumps({"archetype": "Proof-First Builder", "laws": [{"text": rule_text, "count": "2 sessions"}], "truth": ""}),
        encoding="utf-8",
    )
    draft = {
        "schema_version": "1",
        "profile_id": "default",
        "report_set_hash": report_set_hash,
        "domains": {
            "work": {
                "status": "active",
                "file": "you.md",
                "rules": [{
                    "text": rule_text,
                    "implication": implication,
                    "kind": "inferred",
                    "evidence_ids": ["ev-aaaaaaaa-done", "ev-bbbbbbbb-proof"],
                }],
            },
            "design": {"status": "inactive", "reason": "insufficient evidence", "deepen_instruction": "run ditto and deepen design"},
            "write": {"status": "inactive", "reason": "insufficient evidence", "deepen_instruction": "run ditto and deepen write"},
        },
    }
    (path / "draft-manifest.json").write_text(json.dumps(draft), encoding="utf-8")
    return str(path)


class ProfilePackValidationTest(unittest.TestCase):
    def test_inferred_rule_requires_two_distinct_sessions(self):
        reports = {
            "ev-a": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []},
            "ev-b": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q2"}, "quote_count": 1, "contradictions": []},
        }
        rule = {"text": "Always prove done.", "implication": "Run verification before reporting completion.", "kind": "inferred", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "two distinct sessions"):
            ditto.validate_rule(rule, reports, require_cross_strata=True)

    def test_explicit_rule_allows_one_uncontradicted_receipt(self):
        reports = {"ev-a": {"kind": "explicit", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []}}
        rule = {"text": "Never use em dashes.", "implication": "Replace em dashes before returning public copy.", "kind": "explicit", "confidence": "low-frequency", "evidence_ids": ["ev-a"]}
        ditto.validate_rule(rule, reports, require_cross_strata=False)

    def test_rule_with_contradiction_cannot_be_installed(self):
        reports = {
            "ev-a": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []},
            "ev-b": {"kind": "inferred", "sessions": {"s2"}, "strata": {"codex:2026-Q2"}, "quote_count": 1, "contradictions": [{"session_id": "s3"}]},
        }
        rule = {"text": "Always prove done.", "implication": "Run verification before reporting completion.", "kind": "inferred", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "unresolved contradiction"):
            ditto.validate_rule(rule, reports, require_cross_strata=True)

    def test_generic_rule_cannot_be_installed(self):
        reports = {
            "ev-a": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []},
            "ev-b": {"kind": "inferred", "sessions": {"s2"}, "strata": {"codex:2026-Q2"}, "quote_count": 1, "contradictions": []},
        }
        rule = {"text": "Follow best practices.", "implication": "Write good code.", "kind": "inferred", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "generic"):
            ditto.validate_rule(rule, reports, require_cross_strata=True)

    def test_active_domain_requires_exact_profile_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(make_valid_pack(Path(tmp) / "pack", "c" * 64))
            (pack / "you.md").write_text("---\nname: wrong\ndescription: x\n---\nAlways prove done.\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ditto-work-profile"):
                ditto.validate_profile_pack(str(pack), evidence_fixture(), run_plan_fixture("c" * 64))

    def test_profile_file_cannot_escape_pack_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(make_valid_pack(Path(tmp) / "pack", "c" * 64))
            draft_path = pack / "draft-manifest.json"
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            draft["domains"]["work"]["file"] = "../outside.md"
            draft_path.write_text(json.dumps(draft), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe profile path"):
                ditto.validate_profile_pack(str(pack), evidence_fixture(), run_plan_fixture("c" * 64))

    def test_profile_id_rejects_windows_reserved_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(make_valid_pack(Path(tmp) / "pack", "c" * 64))
            draft_path = pack / "draft-manifest.json"
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            draft["profile_id"] = "CON"
            draft_path.write_text(json.dumps(draft), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "profile_id"):
                ditto.validate_profile_pack(str(pack), evidence_fixture(), run_plan_fixture("c" * 64))

    def test_profile_pack_requires_all_three_domain_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(make_valid_pack(Path(tmp) / "pack", "c" * 64))
            draft_path = pack / "draft-manifest.json"
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            del draft["domains"]["write"]
            draft_path.write_text(json.dumps(draft), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly work, design, and write"):
                ditto.validate_profile_pack(str(pack), evidence_fixture(), run_plan_fixture("c" * 64))

    def test_appendix_requires_the_exact_private_quote_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(make_valid_pack(Path(tmp) / "pack", "c" * 64))
            appendix = pack / "appendix.md"
            appendix.write_text(appendix.read_text(encoding="utf-8").replace("done means live", "made-up summary"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "appendix"):
                ditto.validate_profile_pack(str(pack), evidence_fixture(), run_plan_fixture("c" * 64))

    def test_new_card_labels_use_session_receipts(self):
        html = ditto.render_card_html({
            "archetype": "Proof-First Builder",
            "laws": [{"text": "Always prove done.", "count": "12 sessions"}],
            "truth": "",
            "stats": {},
        })
        self.assertIn("12 sessions", html)
        self.assertIn("distinct session receipts", html)
        self.assertNotIn("how many agents", html)


class AtomicProfileStoreTest(unittest.TestCase):
    def test_activation_failure_preserves_previous_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            first_hash = "c" * 64
            first = make_valid_pack(Path(tmp) / "first", report_set_hash=first_hash)
            ditto.activate_profile_pack(home, first, evidence_fixture(), run_plan_fixture(first_hash), fail_after=None)
            before = Path(home, "profiles", "default", "current.json").read_bytes()
            active_before = Path(home, "active-profile.json").read_bytes()
            for index, failure_point in enumerate(("version-stage", "version-rename", "pointer-write")):
                second_hash = format(index + 13, "x") * 64
                second = make_valid_pack(Path(tmp) / failure_point, report_set_hash=second_hash)
                with self.subTest(failure_point=failure_point):
                    with self.assertRaisesRegex(RuntimeError, "injected"):
                        ditto.activate_profile_pack(
                            home,
                            second,
                            evidence_fixture(),
                            run_plan_fixture(second_hash),
                            fail_after=failure_point,
                        )
                    self.assertEqual(before, Path(home, "profiles", "default", "current.json").read_bytes())
                    self.assertEqual(active_before, Path(home, "active-profile.json").read_bytes())

    def test_plugin_uninstall_directory_is_never_profile_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = ditto.resolve_ditto_home(str(Path(tmp) / "private"))
            self.assertNotIn("plugins", Path(home).parts)

    def test_cached_reduction_reactivates_same_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            report_set_hash = "e" * 64
            pack = make_valid_pack(Path(tmp) / "pack", report_set_hash)
            first = ditto.activate_profile_pack(home, pack, evidence_fixture(), run_plan_fixture(report_set_hash))
            second = ditto.activate_cached_reduction(home, report_set_hash)
            self.assertEqual(first["profile_version"], second["profile_version"])

    def test_tampered_reduction_cache_fails_without_pointer_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            report_set_hash = "9" * 64
            pack = make_valid_pack(Path(tmp) / "pack", report_set_hash)
            ditto.activate_profile_pack(home, pack, evidence_fixture(), run_plan_fixture(report_set_hash))
            current = Path(home, "profiles", "default", "current.json")
            before = current.read_bytes()
            cached_you = Path(home, "cache", "reductions", "1", report_set_hash, "you.md")
            cached_you.write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash"):
                ditto.activate_cached_reduction(home, report_set_hash)
            self.assertEqual(before, current.read_bytes())


if __name__ == "__main__":
    unittest.main()
