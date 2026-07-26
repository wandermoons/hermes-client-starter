#!/usr/bin/env python3
"""Verify that installed Dwight managed files still match their baseline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


MANAGED_ROOTS = ("SOUL.md", "skills")


def load_version(manifest: Path) -> str:
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    version = str(data.get("version") or "").strip()
    if not version:
        raise ValueError(f"missing version in {manifest}")
    return version


def load_core_skill_names(manifest: Path) -> set[str]:
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    names: set[str] = set()
    for owned_path in data.get("distribution_owned") or []:
        parts = str(owned_path).strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "skills":
            names.add(parts[1])
    if not names:
        raise ValueError(f"no explicit Core skill paths in {manifest}")
    return names


def current_baseline(source: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    soul = source / "SOUL.md"
    if soul.is_file():
        files["SOUL.md"] = soul.read_bytes()
    skills = source / "skills"
    if skills.is_dir():
        for path in sorted(skills.rglob("*")):
            if path.is_file() and not path.is_symlink():
                files[path.relative_to(source).as_posix()] = path.read_bytes()
    return files


def git_baseline(repo: Path, source: Path, version: str) -> dict[str, bytes]:
    tag = f"v{version}"
    subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", f"{tag}^{{commit}}"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    source_rel = source.resolve().relative_to(repo.resolve()).as_posix()
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", tag, "--", source_rel],
        check=True,
        capture_output=True,
        text=True,
    )
    files: dict[str, bytes] = {}
    prefix = f"{source_rel}/"
    for repo_path in result.stdout.splitlines():
        if not repo_path.startswith(prefix):
            continue
        rel = repo_path[len(prefix) :]
        if not (rel == "SOUL.md" or rel.startswith("skills/")):
            continue
        blob = subprocess.run(
            ["git", "-C", str(repo), "show", f"{tag}:{repo_path}"],
            check=True,
            capture_output=True,
        ).stdout
        files[rel] = blob
    return files


def verify(repo: Path, source: Path, installed: Path, installed_version: str) -> list[str]:
    source_version = load_version(source / "distribution.yaml")
    if installed_version == source_version:
        baseline = current_baseline(source)
    else:
        baseline = git_baseline(repo, source, installed_version)
    if not baseline:
        raise RuntimeError("managed baseline is empty")

    divergent: list[str] = []
    for rel, expected in baseline.items():
        actual_path = installed / rel
        if not actual_path.is_file() or actual_path.is_symlink():
            divergent.append(rel)
            continue
        if actual_path.read_bytes() != expected:
            divergent.append(rel)

    baseline_paths = set(baseline)
    core_skill_names: set[str] = set()
    for rel in baseline_paths:
        parts = Path(rel).parts
        if len(parts) >= 3 and parts[0] == "skills":
            core_skill_names.add(parts[1])

    incoming_core_skill_names = load_core_skill_names(source / "distribution.yaml")
    for skill_name in sorted(incoming_core_skill_names - core_skill_names):
        collision = installed / "skills" / skill_name
        if collision.exists() or collision.is_symlink():
            divergent.append(f"skills/{skill_name} (new Core name collision)")

    for skill_name in sorted(core_skill_names):
        skill_root = installed / "skills" / skill_name
        if not skill_root.is_dir() or skill_root.is_symlink():
            marker = f"skills/{skill_name}"
            if marker not in divergent:
                divergent.append(marker)
            continue
        for path in skill_root.rglob("*"):
            if not (path.is_file() or path.is_symlink()):
                continue
            rel = path.relative_to(installed).as_posix()
            if path.is_symlink() or rel not in baseline_paths:
                divergent.append(rel)
    return divergent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--installed", required=True, type=Path)
    parser.add_argument("--installed-version", required=True)
    args = parser.parse_args()

    try:
        divergent = verify(
            args.repo_root,
            args.source,
            args.installed,
            args.installed_version,
        )
    except Exception as exc:
        print(f"baseline verification unavailable: {exc}", file=sys.stderr)
        return 2

    if divergent:
        print("managed Dwight files diverged:", file=sys.stderr)
        for rel in divergent:
            print(f"  - {rel}", file=sys.stderr)
        return 3
    print("DWIGHT_MANAGED_BASELINE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
