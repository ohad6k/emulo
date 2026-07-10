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


if __name__ == "__main__":
    unittest.main()
