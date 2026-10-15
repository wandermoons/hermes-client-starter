#!/usr/bin/env python3
"""Install the pinned Claude SEO runtime into one Dwight profile safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import uuid
from pathlib import Path
from typing import NoReturn

WRAPPERS = ("dwight-claude-seo", "dwight-schema-org-hook")


def fail(message: str) -> NoReturn:
    raise RuntimeError(message)


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail(f"invalid managed Claude SEO state: {exc}")
    if not isinstance(parsed, dict):
        fail("invalid managed Claude SEO state")
    return parsed


def require_regular_directory(path: Path, label: str) -> None:
    if not path.is_dir() or path.is_symlink():
        fail(f"unsafe {label}: {path}")


def absolute_without_resolving(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def require_no_symlink_components(path: Path, label: str) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            fail(f"missing {label} component: {current}")
        if stat.S_ISLNK(mode):
            fail(f"symbolic link forbidden in {label}: {current}")


def require_safe_directory_permissions(path: Path, label: str) -> None:
    mode = stat.S_IMODE(path.lstat().st_mode)
    if mode & 0o022:
        fail(f"group/world-writable {label} is unsafe: {path}")


def require_regular_tree(root: Path, label: str) -> None:
    require_regular_directory(root, label)
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in [*directories, *files]:
            path = current_path / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                fail(f"symbolic link forbidden in {label}: {path}")
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                fail(f"special file forbidden in {label}: {path}")


def validate_mutation_roots(profile: Path, local_dir: Path, bin_dir: Path, managed_parent: Path) -> None:
    for path, label in (
        (profile, "profile home"),
        (local_dir, "profile local directory"),
        (bin_dir, "profile bin directory"),
        (managed_parent, "starter-managed directory"),
    ):
        require_no_symlink_components(path, label)
        require_regular_directory(path, label)
        require_safe_directory_permissions(path, label)


def cleanup_regular_tree(path: Path, parent: Path) -> None:
    """Remove a temporary tree only while its trusted parent is still safe."""
    try:
        require_no_symlink_components(parent, "cleanup parent")
        require_regular_directory(parent, "cleanup parent")
        if path.is_symlink():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path)
    except (OSError, RuntimeError):
        # Never follow a substituted parent merely to clean a temporary path.
        return


def restore_file_atomic(path: Path, backup: tuple[bytes, int] | None, token: str) -> None:
    if backup is None:
        if path.is_symlink() or path.exists():
            path.unlink()
        return
    data, mode = backup
    temp = path.parent / f".{path.name}.restore-{token}"
    temp.write_bytes(data)
    os.chmod(temp, mode)
    os.replace(temp, path)


def load_provenance(source: Path) -> dict:
    # Tiny fixed-format YAML subset, parsed without a new dependency.
    values: dict[str, str] = {}
    provenance_path = source / "upstream.yaml"
    if not provenance_path.is_file() or provenance_path.is_symlink():
        fail("invalid Claude SEO provenance file")
    for raw in provenance_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        values[key.strip()] = value.strip()
    required = {
        "repository", "release", "commit", "license", "author",
        "runtime_tree_sha256", "hermes_port_tree_sha256", "wrappers_tree_sha256",
        "runtime_policy_sha256",
    }
    missing = sorted(required - values.keys())
    if missing:
        fail(f"missing Claude SEO provenance fields: {', '.join(missing)}")
    if values["license"] != "MIT" or len(values["commit"]) != 40:
        fail("unexpected Claude SEO provenance")
    return values


def verify_existing(
    managed_root: Path,
    state_path: Path,
    bin_dir: Path,
) -> dict | None:
    exists = (
        managed_root.exists() or managed_root.is_symlink()
        or state_path.exists() or state_path.is_symlink()
        or any((bin_dir / name).exists() or (bin_dir / name).is_symlink() for name in WRAPPERS)
    )
    if not exists:
        return None
    if not managed_root.is_dir() or managed_root.is_symlink() or not state_path.is_file() or state_path.is_symlink():
        fail("managed Claude SEO payload is incomplete or unsafe")
    state = read_json(state_path)
    if tree_hash(managed_root) != state.get("tree_sha256"):
        fail("managed Claude SEO payload diverged; refusing to overwrite")
    expected_wrappers = state.get("wrappers")
    if not isinstance(expected_wrappers, dict):
        fail("managed Claude SEO wrapper state is missing")
    assert isinstance(expected_wrappers, dict)
    for name in WRAPPERS:
        path = bin_dir / name
        if not path.is_file() or path.is_symlink() or file_hash(path) != expected_wrappers.get(name):
            fail(f"managed Claude SEO wrapper diverged: {name}")
    return state


def install(integration_source: Path, profile_home: Path) -> dict:
    source = absolute_without_resolving(integration_source)
    profile = absolute_without_resolving(profile_home)
    require_no_symlink_components(source, "integration source")
    require_no_symlink_components(profile, "profile home")
    require_regular_tree(source, "integration source")
    require_regular_directory(profile, "profile home")
    require_safe_directory_permissions(profile, "profile home")
    for relative in ("runtime", "hermes-port", "wrappers"):
        require_regular_tree(source / relative, f"integration {relative}")

    provenance = load_provenance(source)
    for relative, field in (
        ("runtime", "runtime_tree_sha256"),
        ("hermes-port", "hermes_port_tree_sha256"),
        ("wrappers", "wrappers_tree_sha256"),
    ):
        actual_hash = tree_hash(source / relative)
        if actual_hash != provenance[field]:
            fail(f"Claude SEO source integrity check failed: {relative}")
    policy_source = source / "runtime-policy.yaml"
    if not policy_source.is_file() or policy_source.is_symlink():
        fail("invalid Claude SEO runtime policy")
    if file_hash(policy_source) != provenance["runtime_policy_sha256"]:
        fail("Claude SEO source integrity check failed: runtime-policy.yaml")
    local_dir = profile / "local"
    bin_dir = profile / "bin"
    local_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    bin_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    require_no_symlink_components(local_dir, "profile local directory")
    require_no_symlink_components(bin_dir, "profile bin directory")
    require_regular_directory(local_dir, "profile local directory")
    require_regular_directory(bin_dir, "profile bin directory")
    require_safe_directory_permissions(local_dir, "profile local directory")
    require_safe_directory_permissions(bin_dir, "profile bin directory")

    managed_parent = local_dir / ".starter-managed"
    managed_parent.mkdir(mode=0o700, exist_ok=True)
    require_no_symlink_components(managed_parent, "starter-managed directory")
    require_regular_directory(managed_parent, "starter-managed directory")
    os.chmod(managed_parent, 0o700)
    validate_mutation_roots(profile, local_dir, bin_dir, managed_parent)

    managed_root = managed_parent / "claude-seo"
    state_path = managed_parent / "claude-seo-state.json"
    previous_state = verify_existing(managed_root, state_path, bin_dir)

    token = uuid.uuid4().hex
    staged = managed_parent / f".claude-seo.next-{token}"
    previous = managed_parent / f".claude-seo.previous-{token}"
    wrapper_staged: dict[str, Path] = {}
    wrapper_backups: dict[str, tuple[bytes, int] | None] = {}
    old_state: tuple[bytes, int] | None = None

    try:
        staged.mkdir(mode=0o700)
        shutil.copytree(source / "runtime", staged / "upstream", symlinks=False)
        shutil.copytree(source / "hermes-port", staged / "hermes-port", symlinks=False)
        shutil.copy2(policy_source, staged / "runtime-policy.yaml")
        for path in staged.rglob("*"):
            if path.is_symlink():
                fail(f"symbolic link forbidden in managed Claude SEO payload: {path}")

        wrapper_hashes: dict[str, str] = {}
        for name in WRAPPERS:
            template = source / "wrappers" / name
            if not template.is_file() or template.is_symlink():
                fail(f"invalid Claude SEO wrapper template: {name}")
            target = bin_dir / name
            if (target.exists() or target.is_symlink()) and previous_state is None:
                fail(f"unmanaged command collision: {target}")
            wrapper_backups[name] = (
                (target.read_bytes(), stat.S_IMODE(target.stat().st_mode)) if target.exists() else None
            )
            temp = bin_dir / f".{name}.next-{token}"
            shutil.copy2(template, temp)
            os.chmod(temp, 0o755)
            wrapper_staged[name] = temp
            wrapper_hashes[name] = file_hash(temp)

        new_state = {
            "schema_version": 1,
            "upstream_repository": provenance["repository"],
            "upstream_release": provenance["release"],
            "upstream_commit": provenance["commit"],
            "tree_sha256": tree_hash(staged),
            "wrappers": wrapper_hashes,
        }
        state_temp = managed_parent / f".claude-seo-state.next-{token}.json"
        state_temp.write_text(json.dumps(new_state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(state_temp, 0o600)
        if state_path.exists():
            old_state = (state_path.read_bytes(), stat.S_IMODE(state_path.stat().st_mode))

        require_regular_tree(source, "integration source")
        validate_mutation_roots(profile, local_dir, bin_dir, managed_parent)
        for relative, field in (
            ("runtime", "runtime_tree_sha256"),
            ("hermes-port", "hermes_port_tree_sha256"),
            ("wrappers", "wrappers_tree_sha256"),
        ):
            if tree_hash(source / relative) != provenance[field]:
                fail(f"Claude SEO source changed during installation: {relative}")
        if file_hash(policy_source) != provenance["runtime_policy_sha256"]:
            fail("Claude SEO runtime policy changed during installation")
        if managed_root.exists():
            os.replace(managed_root, previous)
        os.replace(staged, managed_root)
        for name, temp in wrapper_staged.items():
            os.replace(temp, bin_dir / name)
        os.replace(state_temp, state_path)
        cleanup_regular_tree(previous, managed_parent)
        return new_state
    except Exception as original:
        try:
            validate_mutation_roots(profile, local_dir, bin_dir, managed_parent)
            if managed_root.exists() and previous.exists():
                cleanup_regular_tree(managed_root, managed_parent)
                os.replace(previous, managed_root)
            elif previous.exists():
                os.replace(previous, managed_root)
            elif managed_root.exists() and previous_state is None:
                cleanup_regular_tree(managed_root, managed_parent)
            for name, backup in wrapper_backups.items():
                restore_file_atomic(bin_dir / name, backup, token)
            restore_file_atomic(state_path, old_state, token)
        except (OSError, RuntimeError, ValueError) as rollback_error:
            fail(f"{original}; rollback halted safely: {rollback_error}")
        raise
    finally:
        cleanup_regular_tree(staged, managed_parent)
        cleanup_regular_tree(previous, managed_parent)
        try:
            validate_mutation_roots(profile, local_dir, bin_dir, managed_parent)
            for temp in wrapper_staged.values():
                if temp.is_symlink() or temp.exists():
                    temp.unlink()
            for temp in managed_parent.glob(f".claude-seo-state.next-{token}.json"):
                if temp.is_symlink() or temp.is_file():
                    temp.unlink()
        except (OSError, RuntimeError):
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--integration-source", required=True, type=Path)
    parser.add_argument("--profile-home", required=True, type=Path)
    args = parser.parse_args()
    try:
        state = install(args.integration_source, args.profile_home)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Claude SEO payload installation failed: {exc}", file=sys.stderr)
        return 1
    print(
        "CLAUDE_SEO_PAYLOAD_OK "
        f"release={state['upstream_release']} commit={state['upstream_commit']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
