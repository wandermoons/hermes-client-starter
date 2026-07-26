from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DWIGHT = ROOT / "distributions" / "dwight"
SKILLS_ROOT = DWIGHT / "skills"

EXPECTED_SKILLS = {
    "dwight-seo-core",
    "dwight-research-core",
    "dwight-seo-market-intelligence",
    "dwight-seo-performance-audit",
    "dwight-seo-silo-strategy",
    "dwight-seo-content-production",
    "dwight-seo-internal-linking",
    "dwight-wordpress-safe-operations",
    "dwight-brand-voice-extraction",
}


def frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else {}


class DwightCoreStructureTests(unittest.TestCase):
    def test_expected_skill_directories_exist(self) -> None:
        actual = {path.parent.name for path in SKILLS_ROOT.glob("*/SKILL.md")}
        self.assertEqual(EXPECTED_SKILLS, actual)

    def test_skill_frontmatter_has_unique_name_description_and_version(self) -> None:
        names: list[str] = []
        for path in sorted(SKILLS_ROOT.glob("*/SKILL.md")):
            data = frontmatter(path.read_text(encoding="utf-8"))
            self.assertEqual(path.parent.name, data.get("name"), path)
            self.assertTrue(data.get("description"), path)
            self.assertRegex(str(data.get("version", "")), r"^\d+\.\d+\.\d+$", path)
            names.append(data["name"])
        self.assertEqual(len(names), len(set(names)))

    def test_each_skill_contains_workflow_guardrails_and_verification(self) -> None:
        for path in sorted(SKILLS_ROOT.glob("*/SKILL.md")):
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("workflow", text, path)
            self.assertTrue(
                "guardrail" in text or "sécurité" in text or "safety" in text,
                path,
            )
            self.assertTrue(
                "vérification" in text or "verification" in text or "quality gate" in text,
                path,
            )

    def test_soul_and_core_router_reference_every_specialist_skill(self) -> None:
        soul = (DWIGHT / "SOUL.md").read_text(encoding="utf-8")
        core = (SKILLS_ROOT / "dwight-seo-core" / "SKILL.md").read_text(encoding="utf-8")
        for name in EXPECTED_SKILLS - {"dwight-seo-core"}:
            self.assertIn(f"`{name}`", soul)
            self.assertIn(f"`{name}`", core)
            self.assertTrue((SKILLS_ROOT / name / "SKILL.md").is_file())

    def test_versions_are_bumped_to_0_1_2(self) -> None:
        self.assertEqual("0.1.2", (ROOT / "VERSION").read_text(encoding="utf-8").strip())
        manifest = yaml.safe_load((DWIGHT / "distribution.yaml").read_text(encoding="utf-8"))
        self.assertEqual("0.1.2", str(manifest["version"]))

    def test_manifest_owns_only_explicit_core_skill_directories(self) -> None:
        manifest = yaml.safe_load((DWIGHT / "distribution.yaml").read_text(encoding="utf-8"))
        owned = set(manifest["distribution_owned"])
        self.assertNotIn("skills", owned)
        self.assertNotIn("skills/", owned)
        for name in EXPECTED_SKILLS:
            self.assertIn(f"skills/{name}/", owned)

    def test_all_seven_behavior_scenarios_are_documented(self) -> None:
        scenarios = ROOT / "tests" / "test_dwight_core_prompts.md"
        self.assertTrue(scenarios.is_file())
        text = scenarios.read_text(encoding="utf-8")
        for marker in (
            "SEO sans intégration",
            "Google Search Console",
            "DataForSEO",
            "Brief éditorial",
            "Publication WordPress sans cible",
            "Publication WordPress déjà validée",
            "Brand Voice Guide",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
