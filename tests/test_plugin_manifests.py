import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ditto_manifests", ROOT / "ditto.py")
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)


class PluginSkillTest(unittest.TestCase):
    def read(self, name):
        return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")

    def test_exact_skill_names(self):
        expected = {"mine": "mine", "work": "work", "design": "design", "write": "write"}
        for folder, name in expected.items():
            fields = ditto.parse_frontmatter(self.read(folder))
            self.assertEqual(name, fields["name"])

    def test_routing_descriptions_are_mutually_bounded(self):
        mine = self.read("mine").lower()
        work = self.read("work").lower()
        design = self.read("design").lower()
        write = self.read("write").lower()
        self.assertIn("explicitly asks", mine)
        self.assertIn("do not use for design", work)
        self.assertIn("ui, ux, visual", design)
        self.assertIn("marketing, social, replies", write)
        self.assertNotIn("depth beats token efficiency", mine)

    def test_domain_loaders_use_only_profile_path_command(self):
        self.assertIn("plugin profile-path --domain work", self.read("work"))
        self.assertIn("plugin profile-path --domain design", self.read("design"))
        self.assertIn("plugin profile-path --domain write", self.read("write"))


class PluginManifestTest(unittest.TestCase):
    def test_codex_manifest_exposes_only_static_skills(self):
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual("ditto", manifest["name"])
        self.assertEqual("./skills/", manifest["skills"])
        self.assertEqual("#141414", manifest["interface"]["brandColor"])
        self.assertFalse(any(".ditto" in json.dumps(value) for value in manifest.values()))

    def test_marketplace_points_to_repository_root(self):
        market = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        plugin = next(item for item in market["plugins"] if item["name"] == "ditto")
        self.assertEqual("./", plugin["source"]["path"])

    def test_claude_manifest_is_static_and_leak_free(self):
        manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual("ditto", manifest["name"])
        self.assertEqual("MIT", manifest["license"])
        self.assertFalse(any(".ditto" in json.dumps(value) for value in manifest.values()))

    def test_claude_marketplace_points_to_repository_root(self):
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual("ditto", market["name"])
        plugin = next(item for item in market["plugins"] if item["name"] == "ditto")
        self.assertEqual("./", plugin["source"])
        self.assertFalse(plugin["source"].startswith(".."))

    def test_plugin_tree_contains_no_generated_profile(self):
        forbidden = {"active-profile.json", "current.json", "you.md", "you-designer.md", "you-writer.md", "appendix.md"}
        found = {
            path.name
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.parts and "examples" not in path.parts
        }
        self.assertTrue(forbidden.isdisjoint(found))

    def test_skills_sh_bootstrap_is_outside_native_plugin_discovery(self):
        self.assertTrue((ROOT / ".agents" / "skills" / "ditto" / "SKILL.md").is_file())
        self.assertFalse((ROOT / "skills" / "ditto" / "SKILL.md").exists())
        native = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual({"mine", "work", "design", "write"}, native)


class DocumentationTruthTest(unittest.TestCase):
    def test_failed_frozen_calibration_permanently_guards_the_quality_default(self):
        calibration = json.loads(
            (ROOT / "tests" / "fixtures" / "bounded-calibration-baseline.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            "9778cb1eb2fcdbd7aafed01600fc7a1ceaf59f99943d54b692b0aaff9efaab09",
            calibration["frozen_checklist_sha256"],
        )
        self.assertEqual(22, sum(calibration["required"].values()))
        self.assertEqual(5, sum(calibration["baseline"]["recovered"].values()))
        if ditto.QUALITY_DEFAULT_MODE == "bounded":
            passing = calibration["passing_bounded_run"]
            self.assertIsNotNone(passing, "bounded cannot be the quality default without a new frozen-gate run")
            self.assertEqual(calibration["required"], passing["recovered"])
        else:
            self.assertEqual("full", ditto.QUALITY_DEFAULT_MODE)

    def test_every_public_mining_surface_calls_preview_a_starter_profile(self):
        notice = "Quick preview creates a starter profile from selected history, not the full profile."
        for relative in ("README.md", "skills/mine/SKILL.md", ".agents/skills/ditto/SKILL.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(notice, text, relative)
            self.assertIn("full-history quality default", text.lower(), relative)

    def test_public_docs_separate_local_extractor_from_model_processing(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        runtime = (ROOT / "ditto.py").read_text(encoding="utf-8")
        sentence = "Selected redacted text is processed by the model provider you choose."
        self.assertIn(sentence, readme)
        self.assertIn(sentence, security)
        self.assertIn("DISABLE_TELEMETRY=1", security)
        self.assertNotIn("The mining step runs in *your* coding agent, on *your* machine. Nothing gets uploaded", readme)
        self.assertNotIn("100% local. Your logs never leave your machine.", runtime)
        self.assertIn(sentence, runtime)

    def test_npx_bootstrap_is_bounded_and_separate_from_native_routing(self):
        skill = (ROOT / ".agents" / "skills" / "ditto" / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("plugin preflight", skill)
        self.assertIn("planned_worker_calls", skill)
        self.assertIn("core profile", skill)
        self.assertIn("native ditto:mine is not available", skill)
        self.assertNotIn("depth beats token efficiency", skill)
        self.assertNotIn("fetch it from main", skill)

    def test_plugin_discovers_exactly_four_skills(self):
        discovered = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual({"mine", "work", "design", "write"}, discovered)

    def test_readme_preserves_the_explicit_npx_install(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("npx skills add ohad6k/ditto@ditto", readme)
        self.assertIn("run ditto", readme)
        self.assertIn("plugin-install command itself", readme)
        self.assertIn("zero mining model calls", readme)
        self.assertIn("host interaction", readme)

    def test_readme_faq_matches_current_receipts_and_supported_sources(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("(18/20)", readme)
        self.assertNotIn("Claude Code, Codex, and Cursor", readme)
        self.assertIn("Codex, Claude Code, and Copilot CLI", readme)
        self.assertIn("distinct supporting sessions", readme)


if __name__ == "__main__":
    unittest.main()
