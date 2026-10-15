from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DWIGHT = ROOT / "distributions" / "dwight"
SKILLS = DWIGHT / "skills"
INTEGRATION = ROOT / "integrations" / "claude-seo"
UPSTREAM_RELEASE = "v2.2.4"
UPSTREAM_COMMIT = "6b63c8bb7b2e8e4480060604555e3af629b54c2c"
FORBIDDEN_CLIENT_TERMS = (
    "wander" + "moons",
    "wander" + "labs.fr",
    "next" + "rise",
    "/users/" + "elliot",
    "nathan" + " demo",
)
CLIENT_SAFETY_OVERLAY = """
## Hermes client-safety overlay

This vendored methodology is subordinate to `dwight-seo-core`, `dwight-claude-seo`, the active profile `SOUL.md`, and the authorized client context in `local/CLIENT.md`.

- Load `dwight-claude-seo` before applying this workflow.
- Treat upstream slash commands as documentation; use only the profile-isolated `dwight-claude-seo` and `dwight-schema-org-hook` launchers.
- Do not run upstream installers, `sudo`, package-manager commands, optional-extension setup, credential setup, or global/user package installation unless the user explicitly approves that exact environment change.
- Do not make a paid API call without a current capped budget preauthorization or exact explicit approval.
- Do not publish, submit indexing, change a CMS, generate a paid asset, message anyone, or perform another external persistent mutation without exact explicit approval.
- Keep audit fan-out read-only; parent Dwight owns network acquisition and final artifact writes. Report unavailable integrations instead of improvising.

"""


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    value = yaml.safe_load(text[4:end])
    return value if isinstance(value, dict) else {}


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _upstream_source_tree_hash(root: Path) -> str:
    """Hash vendored skills after removing only the audited safety overlay."""
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
        content = path.read_bytes()
        if path.name == "SKILL.md":
            text = content.decode("utf-8")
            if text.count(CLIENT_SAFETY_OVERLAY) != 1:
                raise AssertionError(f"unexpected client-safety overlay count: {path}")
            content = text.replace(CLIENT_SAFETY_OVERLAY, "", 1).encode("utf-8")
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def _upstream_runtime_tree_hash(root: Path) -> str:
    """Hash the selected runtime as upstream, before the RC dependency lock."""
    digest = hashlib.sha256()
    upstream_requirements = (root / "requirements.upstream.txt").read_bytes()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
        relative = path.relative_to(root).as_posix()
        if relative == "requirements.upstream.txt":
            continue
        content = upstream_requirements if relative == "requirements.txt" else path.read_bytes()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


class ClaudeSeoDistributionTests(unittest.TestCase):
    def test_upstream_provenance_is_pinned(self) -> None:
        provenance = yaml.safe_load((INTEGRATION / "upstream.yaml").read_text(encoding="utf-8"))
        self.assertEqual("https://github.com/AgriciDaniel/claude-seo", provenance["repository"])
        self.assertEqual(UPSTREAM_RELEASE, provenance["release"])
        self.assertEqual(UPSTREAM_COMMIT, provenance["commit"])
        self.assertEqual("MIT", provenance["license"])
        self.assertEqual(provenance["runtime_tree_sha256"], _tree_hash(INTEGRATION / "runtime"))
        self.assertEqual(
            provenance["upstream_runtime_tree_sha256"],
            _upstream_runtime_tree_hash(INTEGRATION / "runtime"),
        )
        self.assertEqual(provenance["hermes_port_tree_sha256"], _tree_hash(INTEGRATION / "hermes-port"))
        self.assertEqual(provenance["wrappers_tree_sha256"], _tree_hash(INTEGRATION / "wrappers"))
        self.assertEqual(
            provenance["runtime_policy_sha256"],
            hashlib.sha256((INTEGRATION / "runtime-policy.yaml").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            provenance["upstream_skills_tree_sha256"],
            _tree_hash(SKILLS / "claude-seo-upstream"),
        )
        self.assertEqual(
            "c2eacf189795935b9045cef14e5ea8c25d2dda8b824d2d59d4aecf1ecc26f2b7",
            provenance["upstream_source_skills_tree_sha256"],
        )
        self.assertEqual(
            provenance["upstream_source_skills_tree_sha256"],
            _upstream_source_tree_hash(SKILLS / "claude-seo-upstream"),
        )

    def test_all_ported_skills_exist_and_names_are_unique(self) -> None:
        upstream = sorted((SKILLS / "claude-seo-upstream").glob("*/SKILL.md"))
        specialists = sorted((SKILLS / "dwight-claude-seo-agents").glob("*/SKILL.md"))
        self.assertEqual(25, len(upstream))
        self.assertEqual(18, len(specialists))
        self.assertTrue((SKILLS / "dwight-claude-seo" / "SKILL.md").is_file())
        self.assertTrue((SKILLS / "dwight-claude-seo-fanout" / "SKILL.md").is_file())
        names = [_frontmatter(path).get("name") for path in SKILLS.rglob("SKILL.md")]
        self.assertNotIn(None, names)
        self.assertEqual(len(names), len(set(names)))
        for path in upstream:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(1, text.count("## Hermes client-safety overlay"), path)
            self.assertIn("Load `dwight-claude-seo` before applying this workflow.", text, path)
            self.assertIn("Do not make a paid API call", text, path)
            self.assertIn("external persistent mutation", text, path)
        for path in specialists:
            text = path.read_text(encoding="utf-8")
            self.assertIn("`./bin/dwight-claude-seo run <script> ...`", text, path)

    def test_client_safe_adapter_has_no_profile_contamination(self) -> None:
        paths = [
            SKILLS / "dwight-claude-seo" / "SKILL.md",
            SKILLS / "dwight-claude-seo-fanout" / "SKILL.md",
            *sorted((SKILLS / "dwight-claude-seo-agents").glob("*/SKILL.md")),
            *sorted((SKILLS / "dwight-claude-seo-fanout" / "references").glob("*")),
        ]
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in paths
            if path.is_file()
        ).lower()
        for term in FORBIDDEN_CLIENT_TERMS:
            self.assertNotIn(term, text)
        self.assertNotIn("/users/", text)
        self.assertIn("local/client.md", text)
        self.assertIn("validation explicite", text)
        self.assertIn("budget préautorisé", text)
        adapter = (SKILLS / "dwight-claude-seo" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("./bin/dwight-claude-seo doctor --json", adapter)
        self.assertIn("./bin/dwight-schema-org-hook", adapter)

    def test_runtime_snapshot_is_minimal_and_complete(self) -> None:
        runtime = INTEGRATION / "runtime"
        for relative in (
            "LICENSE",
            "requirements.txt",
            "pyproject.toml",
            ".claude-plugin/plugin.json",
            "bin/claude-seo",
            "scripts/runtime.py",
            "scripts/render_page.py",
        ):
            self.assertTrue((runtime / relative).is_file(), relative)
        for forbidden in (".git", ".github", "screenshots", "tests", "agents", "hooks", "extensions"):
            self.assertFalse((runtime / forbidden).exists(), forbidden)

    def test_runtime_policy_classifies_every_bundled_script_exactly_once(self) -> None:
        policy = yaml.safe_load((INTEGRATION / "runtime-policy.yaml").read_text(encoding="utf-8"))
        allowed = set(policy["allowed_scripts"])
        disabled = set(policy["disabled_scripts"])
        actual = {path.name for path in (INTEGRATION / "runtime" / "scripts").glob("*.py")}
        self.assertFalse(allowed & disabled)
        self.assertEqual(actual, allowed | disabled)
        self.assertEqual("disabled", policy["extensions"])
        self.assertEqual("paid_api", policy["disabled_scripts"]["dataforseo_merchant.py"])
        self.assertEqual("external_mutation", policy["disabled_scripts"]["indexing_notify.py"])
        self.assertEqual("unpinned_remote_update", policy["disabled_scripts"]["sync_flow.py"])

    def test_wrapper_templates_resolve_profile_home_dynamically(self) -> None:
        for name in ("dwight-claude-seo", "dwight-schema-org-hook"):
            text = (INTEGRATION / "wrappers" / name).read_text(encoding="utf-8")
            self.assertIn('${BASH_SOURCE[0]}', text)
            self.assertIn("dirname --", text)
            self.assertIn(".starter-managed/claude-seo", text)
            self.assertNotIn("/Users/", text)
            self.assertNotIn("/opt/data", text)

    def test_payload_installer_is_idempotent_preserves_runtime_data_and_blocks_drift(self) -> None:
        installer = ROOT / "scripts" / "install_claude_seo_payload.py"
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp).resolve() / "profiles" / "dwight"
            profile.mkdir(parents=True)
            command = [
                sys.executable,
                str(installer),
                "--integration-source",
                str(INTEGRATION),
                "--profile-home",
                str(profile),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            managed = profile / "local" / ".starter-managed" / "claude-seo"
            state_path = profile / "local" / ".starter-managed" / "claude-seo-state.json"
            runtime_data = profile / "local" / "claude-seo-data" / "sentinel.txt"
            runtime_data.parent.mkdir(parents=True, exist_ok=True)
            runtime_data.write_text("preserve me\n", encoding="utf-8")
            first_hash = _tree_hash(managed)

            subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertEqual(first_hash, _tree_hash(managed))
            self.assertEqual("preserve me\n", runtime_data.read_text(encoding="utf-8"))
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(UPSTREAM_COMMIT, state["upstream_commit"])
            self.assertEqual(first_hash, state["tree_sha256"])
            self.assertEqual(0o600, state_path.stat().st_mode & 0o777)
            self.assertEqual(0o755, (profile / "bin" / "dwight-claude-seo").stat().st_mode & 0o777)

            drifted = managed / "upstream" / "requirements.txt"
            drifted.write_text(drifted.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
            result = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("managed Claude SEO payload diverged", result.stderr)
            self.assertTrue(drifted.read_text(encoding="utf-8").endswith("# drift\n"))

    def test_payload_installer_rejects_tampered_source(self) -> None:
        installer = ROOT / "scripts" / "install_claude_seo_payload.py"
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp).resolve()
            source = temp_root / "integration"
            profile = temp_root / "profile"
            shutil.copytree(INTEGRATION, source)
            profile.mkdir()
            requirements = source / "runtime" / "requirements.txt"
            requirements.write_text(
                requirements.read_text(encoding="utf-8") + "# tampered\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(installer),
                    "--integration-source",
                    str(source),
                    "--profile-home",
                    str(profile),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("source integrity check failed", result.stderr)
            self.assertFalse((profile / "local").exists())

    def test_payload_installer_rejects_symlinked_roots_trees_and_unsafe_bin(self) -> None:
        installer = ROOT / "scripts" / "install_claude_seo_payload.py"
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp).resolve()
            outside_profile = temp_root / "outside-profile"
            outside_profile.mkdir()
            profile_link = temp_root / "profile-link"
            profile_link.symlink_to(outside_profile, target_is_directory=True)
            result = subprocess.run(
                [sys.executable, str(installer), "--integration-source", str(INTEGRATION), "--profile-home", str(profile_link)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("symbolic link forbidden", result.stderr)
            self.assertFalse((outside_profile / "local").exists())

            source = temp_root / "integration"
            shutil.copytree(INTEGRATION, source)
            outside_file = temp_root / "outside.txt"
            outside_file.write_text("outside\n", encoding="utf-8")
            (source / "runtime" / "scripts" / "outside-link.py").symlink_to(outside_file)
            safe_profile = temp_root / "safe-profile"
            safe_profile.mkdir()
            result = subprocess.run(
                [sys.executable, str(installer), "--integration-source", str(source), "--profile-home", str(safe_profile)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("symbolic link forbidden", result.stderr)
            self.assertFalse((safe_profile / "local").exists())

            unsafe_profile = temp_root / "unsafe-profile"
            (unsafe_profile / "bin").mkdir(parents=True)
            (unsafe_profile / "bin").chmod(0o777)
            result = subprocess.run(
                [sys.executable, str(installer), "--integration-source", str(INTEGRATION), "--profile-home", str(unsafe_profile)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("group/world-writable profile bin directory", result.stderr)

    def test_installed_wrapper_blocks_disabled_unknown_and_extension_scripts(self) -> None:
        installer = ROOT / "scripts" / "install_claude_seo_payload.py"
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp).resolve() / "profile"
            profile.mkdir()
            subprocess.run(
                [sys.executable, str(installer), "--integration-source", str(INTEGRATION), "--profile-home", str(profile)],
                check=True,
                capture_output=True,
                text=True,
            )
            wrapper = profile / "bin" / "dwight-claude-seo"
            for args, expected in (
                (("run", "indexnow_submit.py"), "disabled by the client runtime policy"),
                (("run", "unknown.py"), "not classified by the client runtime policy"),
                (("run", "--extension", "dataforseo", "tool.py"), "optional extension execution is disabled"),
            ):
                result = subprocess.run([str(wrapper), *args], check=False, capture_output=True, text=True)
                self.assertEqual(4, result.returncode)
                self.assertIn(expected, result.stderr)

    def test_distribution_config_enables_one_orchestrator_level(self) -> None:
        config = yaml.safe_load((DWIGHT / "config.yaml").read_text(encoding="utf-8"))
        delegation = config["delegation"]
        self.assertEqual(3, delegation["max_concurrent_children"])
        self.assertEqual(2, delegation["max_spawn_depth"])
        self.assertTrue(delegation["orchestrator_enabled"])
        self.assertFalse(delegation["subagent_auto_approve"])
        self.assertFalse(delegation["inherit_mcp_toolsets"])
        self.assertEqual(30, delegation["max_iterations"])
        self.assertEqual(1200, delegation["child_timeout_seconds"])


if __name__ == "__main__":
    unittest.main()
