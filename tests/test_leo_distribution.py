from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LEO = ROOT / "distributions" / "leo"
SKILLS = LEO / "skills"
EXPECTED_SKILLS = {
    "leo-flexible-sourcing",
    "leo-notion-pipeline",
    "leo-instantly-operations",
    "leo-onboarding",
}
FORBIDDEN_CLIENT_TERMS = (
    "fi" + "ras",
    "ay" + "men",
    "wander" + " labs",
    "wander" + "labs",
    "next" + " rise",
    "next" + "_rise",
)
PERSONAL_PATHS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+"),
    re.compile(r"/home/[A-Za-z0-9._-]+"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\[A-Za-z0-9._-]+", re.IGNORECASE),
)
UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
SECRET_SHAPES = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(r"-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----"),
)


def frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else {}


class LeoDistributionStructureTests(unittest.TestCase):
    def test_required_distribution_files_and_focused_skills_exist(self) -> None:
        for name in ("distribution.yaml", "config.yaml", "SOUL.md"):
            self.assertTrue((LEO / name).is_file(), name)
        actual = {path.parent.name for path in SKILLS.glob("*/SKILL.md")}
        self.assertEqual(EXPECTED_SKILLS, actual)
        self.assertTrue(
            (SKILLS / "leo-flexible-sourcing" / "scripts" / "prepare_candidates.py").is_file()
        )

    def test_manifest_is_versioned_and_owns_only_explicit_payload_paths(self) -> None:
        manifest = yaml.safe_load((LEO / "distribution.yaml").read_text(encoding="utf-8"))
        self.assertEqual("leo", manifest["name"])
        self.assertEqual("0.1.0", str(manifest["version"]))
        owned = set(manifest["distribution_owned"])
        self.assertNotIn("skills", owned)
        self.assertNotIn("skills/", owned)
        for name in EXPECTED_SKILLS:
            self.assertIn(f"skills/{name}/", owned)
        for requirement in manifest.get("env_requires", []):
            self.assertFalse(requirement.get("required", False), requirement)

    def test_skill_frontmatter_is_valid_and_names_match_directories(self) -> None:
        names: list[str] = []
        for path in sorted(SKILLS.glob("*/SKILL.md")):
            metadata = frontmatter(path.read_text(encoding="utf-8"))
            self.assertEqual(path.parent.name, metadata.get("name"), path)
            self.assertTrue(metadata.get("description"), path)
            self.assertRegex(str(metadata.get("version", "")), r"^\d+\.\d+\.\d+$", path)
            names.append(metadata["name"])
        self.assertEqual(len(names), len(set(names)))

    def test_sourcing_contract_is_generic_approval_gated_and_non_contacting(self) -> None:
        text = (SKILLS / "leo-flexible-sourcing" / "SKILL.md").read_text(encoding="utf-8").lower()
        for phrase in (
            "sector",
            "zone",
            "target_count",
            "target notion database",
            "official site",
            "normalize",
            "deduplic",
            "provenance",
            "mission approval",
            "read back",
            "never contact",
            "free tools first",
            "capped approval",
        ):
            self.assertIn(phrase, text)
        for fixed_term in ("google maps", "apify", "actor id", "campaign id"):
            self.assertNotIn(fixed_term, text)

    def test_notion_and_instantly_are_separate_optional_onboarding_flows(self) -> None:
        notion = (SKILLS / "leo-notion-pipeline" / "SKILL.md").read_text(encoding="utf-8").lower()
        instantly = (SKILLS / "leo-instantly-operations" / "SKILL.md").read_text(encoding="utf-8").lower()
        onboarding = (SKILLS / "leo-onboarding" / "SKILL.md").read_text(encoding="utf-8").lower()
        for phrase in (
            "separate oauth",
            "read-only",
            "workspace",
            "database identity",
            "existing database",
            "adapt",
            "read back",
        ):
            self.assertIn(phrase, notion)
        for phrase in (
            "optional",
            "read-only",
            "profile-local authorization",
            "explicit approval",
            "activate",
            "send",
            "read back",
        ):
            self.assertIn(phrase, instantly)
        self.assertIn("sourcing works without instantly", onboarding)
        self.assertIn("no credentials", onboarding)

    def test_leo_payload_is_sanitized(self) -> None:
        violations: list[str] = []
        for path in LEO.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            lowered = text.lower()
            for term in FORBIDDEN_CLIENT_TERMS:
                if term in lowered:
                    violations.append(f"{path.relative_to(ROOT)}: forbidden client term {term!r}")
            for pattern in PERSONAL_PATHS + SECRET_SHAPES:
                if pattern.search(text):
                    violations.append(f"{path.relative_to(ROOT)}: sensitive value or personal path")
            if UUID.search(text):
                violations.append(f"{path.relative_to(ROOT)}: embedded identifier")
            if "notion.so/" in lowered or "notion.site/" in lowered:
                violations.append(f"{path.relative_to(ROOT)}: embedded Notion URL")
        self.assertEqual([], violations)

    def test_readme_documents_optional_local_installer_without_external_connections(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Léo v0.1.0", text)
        self.assertIn("./install.sh leo", text)
        self.assertIn("python3 -m unittest discover -s tests -p 'test_leo_*.py' -v", text)
        lowered = text.lower()
        leo_section = lowered[lowered.index("léo v0.1.0") :]
        self.assertIn("optionnelle", leo_section)
        self.assertIn("n’écrit pas dans notion", leo_section)
        self.assertIn("ne contacte pas instantly", leo_section)
        self.assertIn("ne lance aucune campagne", leo_section)
        self.assertIn("idempotente", leo_section)
        self.assertIn("mise à jour de version est refusée", leo_section)


if __name__ == "__main__":
    unittest.main()
