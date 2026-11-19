from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"
LEO_INSTALLER = ROOT / "scripts" / "install_leo.sh"
LEO_SOURCE = ROOT / "distributions" / "leo"


def prepare_fake_environment(tmp: Path) -> tuple[dict[str, str], Path, Path, Path]:
    home = tmp / "hermes-home"
    home.mkdir()
    (home / "config.yaml").write_text("model: test\n", encoding="utf-8")
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    log = tmp / "hermes-calls.log"
    external = tmp / "external-profiles"
    fake = bin_dir / "hermes"
    fake.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import os
            import shutil
            import sys
            from pathlib import Path

            args = sys.argv[1:]
            home = Path(os.environ["FAKE_HERMES_HOME"])
            log = Path(os.environ["FAKE_HERMES_LOG"])
            with log.open("a", encoding="utf-8") as fh:
                fh.write(" ".join(args) + "\\n")

            if args == ["-p", "default", "config", "path"]:
                print(home / "config.yaml")
                raise SystemExit(0)
            if len(args) == 3 and args[:2] == ["profile", "show"]:
                profile = args[2]
                raise SystemExit(0 if (home / "profiles" / profile / "config.yaml").is_file() else 1)
            if len(args) >= 3 and args[:2] == ["profile", "install"]:
                source = Path(args[2]).resolve()
                profile = args[args.index("--name") + 1]
                if os.environ.get("FAKE_INSTALL_MODE") == "profiles-symlink":
                    profiles = home / "profiles"
                    if profiles.is_symlink():
                        profiles.unlink()
                    elif profiles.exists():
                        shutil.rmtree(profiles)
                    external = Path(os.environ["FAKE_EXTERNAL_PROFILES"])
                    external.mkdir(parents=True, exist_ok=True)
                    profiles.symlink_to(external, target_is_directory=True)
                target = home / "profiles" / profile
                shutil.copytree(source, target)
                manifest = target / "distribution.yaml"
                if os.environ.get("FAKE_WRAP_SOURCE") == "1":
                    source_entry = f"\\nsource:\\n  {source}\\n"
                else:
                    source_entry = f"\\nsource: {source}\\n"
                manifest.write_text(
                    manifest.read_text(encoding="utf-8") + source_entry,
                    encoding="utf-8",
                )
                if os.environ.get("FAKE_INSTALL_MODE") == "missing-config":
                    (target / "config.yaml").unlink()
                raise SystemExit(0)
            if len(args) == 4 and args[0:2] == ["-p", "leo"] and args[2:] == ["config", "path"]:
                print(home / "profiles" / "leo" / "config.yaml")
                raise SystemExit(0)
            if len(args) == 4 and args[:2] == ["profile", "delete"] and args[3] == "--yes":
                target = home / "profiles" / args[2]
                if target.is_symlink():
                    target.unlink()
                elif target.exists():
                    shutil.rmtree(target)
                raise SystemExit(0)
            print(f"unexpected fake hermes args: {args}", file=sys.stderr)
            raise SystemExit(2)
            """
        ),
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    env = os.environ.copy()
    env.update(
        PATH=f"{bin_dir}:{env['PATH']}",
        FAKE_HERMES_HOME=str(home),
        FAKE_HERMES_LOG=str(log),
        FAKE_EXTERNAL_PROFILES=str(external),
        HERMES_HOME=str(home),
        LEO_SOURCE=str(LEO_SOURCE),
    )
    return env, home, log, external


def run_installer(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(INSTALLER), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class LeoInstallerTests(unittest.TestCase):
    def test_main_installer_routes_leo_without_changing_dwight_default(self) -> None:
        text = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("HERMES_CLIENT_DISTRIBUTION", text)
        self.assertIn("scripts/install_leo.sh", text)
        self.assertIn("dwight", text)
        self.assertIn("leo", text)

    def test_leo_installer_is_client_safe_and_has_no_external_connector_actions(self) -> None:
        text = LEO_INSTALLER.read_text(encoding="utf-8").lower()
        for forbidden in (
            "curl ",
            "wget ",
            "git clone",
            "notion.so",
            "instantly.ai",
            "api key",
            "bearer ",
        ):
            self.assertNotIn(forbidden, text)
        self.assertNotIn("dwight", text)
        self.assertIn("hermes profile install", text)
        self.assertIn("already installed", text)
        self.assertIn("update refused", text)

    def test_clean_install_and_realistic_wrapped_source_rerun_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            env, home, log, _ = prepare_fake_environment(Path(raw_tmp).resolve())
            env["FAKE_WRAP_SOURCE"] = "1"

            first = run_installer(env, "leo")
            self.assertEqual(0, first.returncode, first.stderr)
            installed = home / "profiles" / "leo"
            self.assertTrue((installed / "SOUL.md").is_file())
            self.assertTrue(
                (installed / "skills" / "leo-flexible-sourcing" / "SKILL.md").is_file()
            )

            second = run_installer(env, "--distribution", "leo")
            self.assertEqual(0, second.returncode, second.stderr)
            self.assertIn("already installed", second.stdout.lower())
            calls = log.read_text(encoding="utf-8").splitlines()
            install_calls = [line for line in calls if line.startswith("profile install ")]
            self.assertEqual(1, len(install_calls), calls)

    def test_fresh_install_rolls_back_when_post_install_config_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            env, home, log, _ = prepare_fake_environment(Path(raw_tmp).resolve())
            env["FAKE_INSTALL_MODE"] = "missing-config"

            result = run_installer(env, "leo")

            self.assertNotEqual(0, result.returncode)
            self.assertFalse((home / "profiles" / "leo").exists())
            self.assertIn(
                "profile delete leo --yes",
                log.read_text(encoding="utf-8").splitlines(),
            )

    def test_fresh_install_rolls_back_profiles_root_symlink_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            env, home, log, external = prepare_fake_environment(Path(raw_tmp).resolve())
            env["FAKE_INSTALL_MODE"] = "profiles-symlink"

            result = run_installer(env, "leo")

            self.assertNotEqual(0, result.returncode)
            self.assertFalse((home / "profiles").is_symlink())
            self.assertFalse((external / "leo").exists())
            self.assertIn(
                "profile delete leo --yes",
                log.read_text(encoding="utf-8").splitlines(),
            )


if __name__ == "__main__":
    unittest.main()
