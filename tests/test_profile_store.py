import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
            "video": {"status": "inactive", "reason": "insufficient evidence", "deepen_instruction": "run ditto and deepen video"},
        },
    }
    (path / "draft-manifest.json").write_text(json.dumps(draft), encoding="utf-8")
    return str(path)


class ProfilePackValidationTest(unittest.TestCase):
    def test_validate_pack_command_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            run_id = "20260710T120000Z-1234abcd"
            run_dir = Path(home) / "runs" / run_id
            pack = run_dir / "pack"
            selected = []
            cached_paths = []
            fixtures = [
                ("a" * 64, "s1", "codex", "2026-01-01", "done means live", "done"),
                ("b" * 64, "s2", "claude", "2026-02-01", "show me it works", "proof"),
            ]
            for segment_hash, session_id, source, date, quote, slug in fixtures:
                text = f"===== session:{session_id} source:{source} =====\n[{date}]\n{quote}\n"
                segment = {
                    "segment_hash": segment_hash,
                    "source": source,
                    "first_date": date,
                    "last_date": date,
                    "source_tokens": 10,
                    "session_versions": [{"session_id": session_id, "content_hash": segment_hash}],
                    "text": text,
                }
                segment_path = Path(ditto.segment_file_path(home, segment_hash))
                segment_path.parent.mkdir(parents=True, exist_ok=True)
                segment_path.write_bytes(text.encode("utf-8"))
                report = {
                    "schema_version": "2",
                    "segment_hash": segment_hash,
                    "coverage": {
                        "session_ids": [session_id],
                        "sources": [source],
                        "first_date": date,
                        "last_date": date,
                        "source_tokens": 10,
                    },
                    "domain_coverage": {"work": "evidence", "design": "no-signal", "write": "no-signal", "video": "no-signal"},
                    "evidence": [{
                        "evidence_id": f"ev-{segment_hash[:8]}-{slug}",
                        "domain": "work",
                        "kind": "inferred",
                        "instruction": "Always prove done.",
                        "implication": "Run the relevant verification before reporting completion.",
                        "quotes": [{"session_id": session_id, "date": date, "text": quote}],
                        "contradictions": [],
                    }],
                }
                cached_paths.append(ditto.store_report(report, home, segment))
                selected.append({key: value for key, value in segment.items() if key != "text"})
            report_set_hash = ditto.compute_report_set_hash(sorted(cached_paths))
            for segment in selected:
                cached_report = json.loads(Path(ditto.report_cache_path(home, segment["segment_hash"])).read_text(encoding="utf-8"))
                ditto.validate_report(cached_report, ditto.hydrate_segment(home, segment))
            run_dir.mkdir(parents=True, exist_ok=True)
            plan = {
                "run_id": run_id,
                "run_dir": str(run_dir),
                "pack_path": str(pack),
                "selected_segments": selected,
                "segment_hashes": [item["segment_hash"] for item in selected],
                "report_set_hash": report_set_hash,
                "source_coverage": {"sources": ["claude", "codex"], "first_date": "2026-01-01", "last_date": "2026-02-01"},
                "selected_source_tokens": 20,
                "adequate_strata": True,
            }
            (run_dir / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            make_valid_pack(pack, report_set_hash)

            validated = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "ditto.py"),
                    "plugin",
                    "validate-pack",
                    "--run-id",
                    run_id,
                    "--pack",
                    str(pack),
                    "--ditto-home",
                    home,
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(validated.returncode, 0, validated.stderr)
            payload = json.loads(validated.stdout)
            self.assertEqual(payload, {"report_set_hash": report_set_hash, "status": "valid"})
            self.assertFalse((Path(home) / "active-profile.json").exists())
            self.assertFalse((Path(home) / "profiles").exists())

    def test_inferred_rule_requires_two_distinct_sessions(self):
        reports = {
            "ev-a": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []},
            "ev-b": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q2"}, "quote_count": 1, "contradictions": []},
        }
        rule = {"text": "Always prove done.", "implication": "Run verification before reporting completion.", "kind": "inferred", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "two distinct sessions"):
            ditto.validate_rule(rule, reports, require_cross_strata=True, domain="work")

    def test_explicit_rule_allows_one_uncontradicted_receipt(self):
        reports = {"ev-a": {"kind": "explicit", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []}}
        rule = {"text": "Never use em dashes.", "implication": "Replace em dashes before returning public copy.", "kind": "explicit", "confidence": "low-frequency", "evidence_ids": ["ev-a"]}
        ditto.validate_rule(rule, reports, require_cross_strata=False, domain="work")

    def test_rule_with_contradiction_cannot_be_installed(self):
        reports = {
            "ev-a": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []},
            "ev-b": {"kind": "inferred", "sessions": {"s2"}, "strata": {"codex:2026-Q2"}, "quote_count": 1, "contradictions": [{"session_id": "s3"}]},
        }
        rule = {"text": "Always prove done.", "implication": "Run verification before reporting completion.", "kind": "inferred", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "unresolved contradiction"):
            ditto.validate_rule(rule, reports, require_cross_strata=True, domain="work")

    def test_generic_rule_cannot_be_installed(self):
        reports = {
            "ev-a": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []},
            "ev-b": {"kind": "inferred", "sessions": {"s2"}, "strata": {"codex:2026-Q2"}, "quote_count": 1, "contradictions": []},
        }
        rule = {"text": "Follow best practices.", "implication": "Write good code.", "kind": "inferred", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "generic"):
            ditto.validate_rule(rule, reports, require_cross_strata=True, domain="work")

    def write_register_evidence(self, first="casual", second="casual"):
        return {
            "ev-a": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": [], "register": first},
            "ev-b": {"kind": "inferred", "sessions": {"s2"}, "strata": {"codex:2026-Q2"}, "quote_count": 1, "contradictions": [], "register": second},
        }

    def test_write_rule_requires_a_register(self):
        rule = {"text": "Never open with fair.", "implication": "Rewrite any reply that starts with the banned opener.", "kind": "inferred", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "register"):
            ditto.validate_rule(rule, self.write_register_evidence(), require_cross_strata=True, domain="write")

    def test_write_rule_keeps_its_evidence_register(self):
        rule = {"text": "Never open with fair.", "implication": "Rewrite any reply that starts with the banned opener.", "kind": "inferred", "register": "casual", "evidence_ids": ["ev-a", "ev-b"]}
        ditto.validate_rule(rule, self.write_register_evidence(), require_cross_strata=True, domain="write")

    def test_write_rule_cannot_claim_a_register_its_evidence_lacks(self):
        rule = {"text": "Never open with fair.", "implication": "Rewrite any reply that starts with the banned opener.", "kind": "inferred", "register": "professional", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "match its evidence"):
            ditto.validate_rule(rule, self.write_register_evidence(), require_cross_strata=True, domain="write")

    def test_mixed_register_evidence_reduces_to_shared(self):
        rule = {"text": "Never open with fair.", "implication": "Rewrite any reply that starts with the banned opener.", "kind": "inferred", "register": "shared", "evidence_ids": ["ev-a", "ev-b"]}
        ditto.validate_rule(rule, self.write_register_evidence(second="professional"), require_cross_strata=True, domain="write")

    def test_register_is_rejected_outside_the_write_domain(self):
        evidence = self.write_register_evidence()
        for item in evidence.values():
            del item["register"]
        rule = {"text": "Always prove done.", "implication": "Run verification before reporting completion.", "kind": "inferred", "register": "casual", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "only valid on write"):
            ditto.validate_rule(rule, evidence, require_cross_strata=True, domain="work")

    def test_write_profile_renders_register_sections(self):
        rules = [
            {"text": "Never open with fair.", "implication": "Rewrite the banned opener.", "register": "shared"},
            {"text": "Keep replies builder-to-builder.", "implication": "Drop formal framing in community threads.", "register": "casual"},
            {"text": "Lead with the concrete result.", "implication": "Open boss updates with the verified outcome.", "register": "professional"},
        ]
        profile = ditto.render_domain_profile("write", rules)
        self.assertIn("## Voice laws", profile)
        self.assertIn("## Casual register", profile)
        self.assertIn("## Professional register", profile)
        self.assertLess(profile.index("## Voice laws"), profile.index("## Casual register"))
        self.assertLess(profile.index("## Casual register"), profile.index("## Professional register"))

    def test_write_profile_omits_empty_register_sections(self):
        rules = [{"text": "Never open with fair.", "implication": "Rewrite the banned opener.", "register": "shared"}]
        profile = ditto.render_domain_profile("write", rules)
        self.assertIn("## Voice laws", profile)
        self.assertNotIn("## Casual register", profile)
        self.assertNotIn("## Professional register", profile)

    def test_write_rule_rejects_evidence_without_a_register(self):
        evidence = self.write_register_evidence()
        del evidence["ev-b"]["register"]
        rule = {"text": "Never open with fair.", "implication": "Rewrite any reply that starts with the banned opener.", "kind": "inferred", "register": "shared", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "write evidence that carries a register"):
            ditto.validate_rule(rule, evidence, require_cross_strata=True, domain="write")

    def test_write_profile_sections_split_on_register_headings(self):
        rules = [
            {"text": "Never open with fair.", "implication": "Rewrite the banned opener.", "register": "shared"},
            {"text": "Keep replies builder-to-builder.", "implication": "Drop formal framing in community threads.", "register": "casual"},
            {"text": "Lead with the concrete result.", "implication": "Open boss updates with the verified outcome.", "register": "professional"},
        ]
        sections = ditto.write_profile_sections(ditto.render_domain_profile("write", rules))
        self.assertIn("Never open with fair.", sections["shared"])
        self.assertNotIn("Never open with fair.", sections["casual"])
        self.assertIn("Keep replies builder-to-builder.", sections["casual"])
        self.assertNotIn("Keep replies builder-to-builder.", sections["professional"])
        self.assertIn("Lead with the concrete result.", sections["professional"])

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

    def test_profile_pack_requires_all_four_domain_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(make_valid_pack(Path(tmp) / "pack", "c" * 64))
            draft_path = pack / "draft-manifest.json"
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            del draft["domains"]["write"]
            draft_path.write_text(json.dumps(draft), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "profile pack must contain exactly"):
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
    def test_reduction_cache_rejects_tampered_content_derived_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            report_set_hash = "7" * 64
            pack = make_valid_pack(Path(tmp) / "pack", report_set_hash)
            ditto.activate_profile_pack(home, pack, evidence_fixture(), run_plan_fixture(report_set_hash))
            manifest_path = Path(home, "cache", "reductions", "2", report_set_hash, "manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["profile_version"] = "f" * 20
            manifest_path.write_text(ditto.canonical_json(manifest) + "\n", encoding="utf-8")

            self.assertFalse(ditto.reduction_cache_is_valid(home, report_set_hash))

    def test_reduction_cache_requires_a_usable_work_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            report_set_hash = "8" * 64
            pack = make_valid_pack(Path(tmp) / "pack", report_set_hash)
            ditto.activate_profile_pack(home, pack, evidence_fixture(), run_plan_fixture(report_set_hash))
            manifest_path = Path(home, "cache", "reductions", "2", report_set_hash, "manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["domains"] = {
                domain: {
                    "status": "inactive",
                    "reason": "insufficient evidence",
                    "deepen_instruction": f"run ditto and deepen {domain}",
                }
                for domain in ("work", "design", "write")
            }
            unsigned = dict(manifest)
            unsigned["profile_version"] = ""
            manifest["profile_version"] = ditto.sha256_text(ditto.canonical_json(unsigned))[:20]
            manifest_path.write_text(ditto.canonical_json(manifest) + "\n", encoding="utf-8")

            self.assertFalse(ditto.reduction_cache_is_valid(home, report_set_hash))

    def test_reduction_cache_requires_its_immutable_version_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            report_set_hash = "6" * 64
            pack = make_valid_pack(Path(tmp) / "pack", report_set_hash)
            activated = ditto.activate_profile_pack(
                home, pack, evidence_fixture(), run_plan_fixture(report_set_hash)
            )
            version_dir = Path(
                home, "profiles", "default", "versions", activated["profile_version"]
            )
            shutil.rmtree(version_dir)

            self.assertFalse(ditto.reduction_cache_is_valid(home, report_set_hash))

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
            cached_you = Path(home, "cache", "reductions", "2", report_set_hash, "you.md")
            cached_you.write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash"):
                ditto.activate_cached_reduction(home, report_set_hash)
            self.assertEqual(before, current.read_bytes())


class MigrationTest(unittest.TestCase):
    def test_migration_cli_stage_returns_json_without_cutover(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host_home = root / "home"
            ditto_home = root / "private"
            legacy = host_home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("---\nname: you\ndescription: legacy\n---\nbody\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "ditto.py"),
                    "plugin",
                    "migrate-stage",
                    "--target",
                    "codex",
                    "--home",
                    str(host_home),
                    "--ditto-home",
                    str(ditto_home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual("staged", payload["status"])
            self.assertTrue(legacy.exists())
            self.assertFalse((ditto_home / "active-profile.json").exists())

    def test_cutover_moves_legacy_out_of_discovery_before_pointer_activation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            ditto_home = root / "private"
            legacy = home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("---\nname: you\ndescription: legacy\n---\nlegacy body\n", encoding="utf-8")
            migration = ditto.stage_legacy_migration("codex", str(home), str(ditto_home))
            self.assertTrue(legacy.exists())
            self.assertFalse((ditto_home / "active-profile.json").exists())
            result = ditto.cutover_legacy_migration(migration["migration_id"], str(ditto_home))
            self.assertFalse(legacy.parent.exists())
            self.assertTrue(Path(result["legacy_backup"]).exists())
            self.assertTrue((ditto_home / "active-profile.json").exists())

    def test_failed_cutover_restores_legacy_and_previous_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            ditto_home = root / "private"
            legacy = home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy_bytes = b"---\nname: you\ndescription: legacy\n---\nlegacy body\n"
            legacy.write_bytes(legacy_bytes)
            active = ditto_home / "active-profile.json"
            current = ditto_home / "profiles" / "default" / "current.json"
            report_set_hash = "f" * 64
            pack = make_valid_pack(root / "pack", report_set_hash)
            ditto.activate_profile_pack(str(ditto_home), pack, evidence_fixture(), run_plan_fixture(report_set_hash))
            active_before, current_before = active.read_bytes(), current.read_bytes()
            migration = ditto.stage_legacy_migration("codex", str(home), str(ditto_home))
            with self.assertRaisesRegex(RuntimeError, "injected"):
                ditto.cutover_legacy_migration(migration["migration_id"], str(ditto_home), fail_after="legacy-move")
            self.assertEqual(legacy_bytes, legacy.read_bytes())
            self.assertEqual(active_before, active.read_bytes())
            self.assertEqual(current_before, current.read_bytes())

    def test_successful_cutover_then_rollback_restores_exact_legacy_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            ditto_home = root / "private"
            legacy = home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            original = b"---\nname: you\ndescription: legacy\n---\nlegacy body\n"
            legacy.write_bytes(original)
            migration = ditto.stage_legacy_migration("codex", str(home), str(ditto_home))
            ditto.cutover_legacy_migration(migration["migration_id"], str(ditto_home))
            ditto.rollback_legacy_migration(migration["migration_id"], str(ditto_home))
            self.assertEqual(original, legacy.read_bytes())
            self.assertFalse((ditto_home / "active-profile.json").exists())
            self.assertFalse((ditto_home / "profiles" / "default" / "current.json").exists())

    def test_failed_rollback_restores_cutover_pointers_and_backup_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host_home = root / "home"
            ditto_home = root / "private"
            legacy = host_home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("---\nname: you\ndescription: legacy\n---\nlegacy body\n", encoding="utf-8")
            migration = ditto.stage_legacy_migration("codex", str(host_home), str(ditto_home))
            cutover = ditto.cutover_legacy_migration(migration["migration_id"], str(ditto_home))
            current = ditto_home / "profiles" / "default" / "current.json"
            active = ditto_home / "active-profile.json"
            cutover_current = current.read_bytes()
            cutover_active = active.read_bytes()
            real_restore = ditto.restore_optional
            calls = 0

            def fail_second_pointer(path, data):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("injected pointer restore failure")
                return real_restore(path, data)

            with mock.patch.object(ditto, "restore_optional", side_effect=fail_second_pointer):
                with self.assertRaisesRegex(RuntimeError, "injected"):
                    ditto.rollback_legacy_migration(migration["migration_id"], str(ditto_home))

            self.assertFalse(legacy.exists())
            self.assertTrue(Path(cutover["legacy_backup"]).is_dir())
            self.assertEqual(cutover_current, current.read_bytes())
            self.assertEqual(cutover_active, active.read_bytes())

    def test_stage_accepts_the_skills_sh_core_profile_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            ditto_home = root / "private"
            legacy = home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("---\nname: ditto-work-profile\ndescription: bounded core profile\n---\nbody\n", encoding="utf-8")
            migration = ditto.stage_legacy_migration("codex", str(home), str(ditto_home))
            self.assertEqual("skills-sh-core", migration["legacy_origin"])

    def test_cutover_rejects_tampered_migration_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host_home = root / "home"
            ditto_home = root / "private"
            original = b"---\nname: you\ndescription: legacy\n---\nlegacy body\n"
            legacy = host_home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(original)
            migration = ditto.stage_legacy_migration("codex", str(host_home), str(ditto_home))
            victim = root / "victim" / "SKILL.md"
            victim.parent.mkdir()
            victim.write_bytes(original)
            record_path = ditto_home / "migrations" / (migration["migration_id"] + ".json")
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["legacy_path"] = str(victim)
            record_path.write_text(json.dumps(record), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "migration record"):
                ditto.cutover_legacy_migration(migration["migration_id"], str(ditto_home))

            self.assertTrue(victim.exists())
            self.assertTrue(legacy.exists())

    def test_imported_legacy_profile_is_labeled_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host_home = root / "home"
            ditto_home = root / "private"
            legacy = host_home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("---\nname: you\ndescription: legacy\n---\nlegacy body\n", encoding="utf-8")
            migration = ditto.stage_legacy_migration("codex", str(host_home), str(ditto_home))
            ditto.cutover_legacy_migration(migration["migration_id"], str(ditto_home))
            status = subprocess.run(
                [sys.executable, str(ROOT / "ditto.py"), "plugin", "status", "--ditto-home", str(ditto_home)],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(status.stdout)
            self.assertTrue(payload["legacy_unverified"])
            self.assertIn("update ditto", payload["recovery_instruction"])

    def test_adapter_migration_preserves_unrelated_agents_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            agents = repo / "AGENTS.md"
            agents.write_text("# keep\n\n<!-- ditto profile:start -->\nold\n<!-- ditto profile:end -->\n", encoding="utf-8")
            home = root / "private"
            removed = ditto.migrate_adapter_block("agents", str(repo), str(home), "backup-remove")
            self.assertEqual("# keep\n", agents.read_text(encoding="utf-8").strip() + "\n")
            ditto.migrate_adapter_block("agents", str(repo), str(home), "restore")
            self.assertIn("old", agents.read_text(encoding="utf-8"))
            self.assertTrue(Path(removed["backup_path"]).exists())

    def test_adapter_removal_can_restore_after_final_record_write_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            agents = repo / "AGENTS.md"
            original = "# keep\n\n<!-- ditto profile:start -->\nold\n<!-- ditto profile:end -->\n"
            agents.write_text(original, encoding="utf-8")
            home = root / "private"
            real_write = ditto.atomic_write_text
            record_writes = 0

            def fail_final_record(path, text):
                nonlocal record_writes
                if Path(path).name.startswith("adapter-"):
                    record_writes += 1
                    if record_writes == 2:
                        raise RuntimeError("injected final record failure")
                return real_write(path, text)

            with mock.patch.object(ditto, "atomic_write_text", side_effect=fail_final_record):
                with self.assertRaisesRegex(RuntimeError, "injected"):
                    ditto.migrate_adapter_block("agents", str(repo), str(home), "backup-remove")

            ditto.migrate_adapter_block("agents", str(repo), str(home), "restore")
            self.assertEqual(original, agents.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
