#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_BASE="$(python3 -c 'import os,tempfile; print(os.path.realpath(tempfile.gettempdir()))')"
TMP="$(mktemp -d "$TMP_BASE/dwight-v013-upgrade.XXXXXX")"
cleanup() {
  python3 -c 'import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)' "$TMP"
}
trap cleanup EXIT

WORKING="$TMP/working"
HOME_DIR="$TMP/home"
mkdir -p "$HOME_DIR"

git clone --quiet --no-hardlinks "$ROOT" "$WORKING"
git -C "$WORKING" checkout --quiet v0.1.2
cp "$WORKING/distributions/dwight/config.yaml" "$HOME_DIR/config.yaml"

HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >/dev/null

python3 - "$HOME_DIR/config.yaml" <<'PY'
import sys, yaml
path = sys.argv[1]
with open(path, encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
sensitive_key = 'api' + '_key'
data['model'] = {
    'default': 'synthetic-model',
    'provider': 'synthetic-provider',
    'base_url': 'https://model.invalid/v1',
    sensitive_key: 'synthetic-sensitive-value',
}
data['providers'] = {'synthetic-provider': {sensitive_key: 'synthetic-sensitive-value'}}
data['credential_pool_strategies'] = {'synthetic-provider': 'synthetic-strategy'}
with open(path, 'w', encoding='utf-8') as fh:
    yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)
PY

CLIENT_SKILL="$HOME_DIR/profiles/dwight/skills/client-demo-test"
mkdir -p "$CLIENT_SKILL"
printf '%s\n' \
  '---' \
  'name: client-demo-test' \
  'description: "Synthetic client skill preservation probe."' \
  'version: 0.0.1' \
  '---' \
  '' \
  '# Synthetic probe' > "$CLIENT_SKILL/SKILL.md"

NEW_CORE_COLLISION="$HOME_DIR/profiles/dwight/skills/dwight-claude-seo"
mkdir -p "$NEW_CORE_COLLISION"
printf '%s\n' \
  '---' \
  'name: dwight-claude-seo' \
  'description: "Synthetic pre-existing client collision probe."' \
  'version: 0.0.1' \
  '---' > "$NEW_CORE_COLLISION/SKILL.md"

python3 - "$ROOT" "$WORKING" <<'PY'
from pathlib import Path
import shutil, sys
src, dst = map(Path, sys.argv[1:])
for entry in src.iterdir():
    if entry.name == '.git':
        continue
    target = dst / entry.name
    if entry.is_dir():
        shutil.copytree(entry, target, dirs_exist_ok=True)
    else:
        shutil.copy2(entry, target)
PY

python3 - "$WORKING/distributions/dwight/distribution.yaml" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
assert str(data.get('version')) == '0.1.3', data
PY

COLLISION_LOG="$TMP/new-core-collision.log"
if HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >"$COLLISION_LOG" 2>&1; then
  printf 'expected collision with a newly introduced Core skill to block update\n' >&2
  exit 1
fi
grep -q 'new Core name collision' "$COLLISION_LOG"
grep -q 'Synthetic pre-existing client collision probe' "$NEW_CORE_COLLISION/SKILL.md"
rm -rf "$NEW_CORE_COLLISION"

HERMES_HOME="$HOME_DIR" "$WORKING/install.sh"

test -f "$CLIENT_SKILL/SKILL.md"
grep -q 'Synthetic probe' "$CLIENT_SKILL/SKILL.md"
test -x "$HOME_DIR/profiles/dwight/bin/dwight-claude-seo"
test -x "$HOME_DIR/profiles/dwight/bin/dwight-schema-org-hook"
test -f "$HOME_DIR/profiles/dwight/local/.starter-managed/claude-seo-state.json"
CLAUDE_RUNTIME_SENTINEL="$HOME_DIR/profiles/dwight/local/claude-seo-data/preserve-me.txt"
mkdir -p "$(dirname "$CLAUDE_RUNTIME_SENTINEL")"
printf '%s\n' 'runtime data survives upgrades' > "$CLAUDE_RUNTIME_SENTINEL"
# A successful repeat install must be idempotent and preserve runtime data.
HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >/dev/null
grep -q '^runtime data survives upgrades$' "$CLAUDE_RUNTIME_SENTINEL"
python3 - "$HOME_DIR/profiles/dwight/distribution.yaml" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
assert str(data.get('version')) == '0.1.3', data
PY
python3 - "$HOME_DIR/profiles/dwight/config.yaml" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
text = repr(data).lower()
assert 'synthetic-sensitive-value' not in text, data
assert 'synthetic-strategy' not in text, data
assert 'providers' not in data, data
assert 'credential_pool_strategies' not in data, data
assert set(data.get('model', {})) <= {'default', 'provider', 'base_url'}, data
assert data.get('model', {}).get('default') == 'synthetic-model', data
PY
test -d "$HOME_DIR/profiles/dwight/local/migration-backups"
python3 - "$HOME_DIR/profiles/dwight/local/migration-backups" <<'PY'
from pathlib import Path
import stat, sys
root = Path(sys.argv[1])
backups = [p for p in root.iterdir() if p.is_dir()]
assert backups, root
for path in backups:
    assert stat.S_IMODE(path.stat().st_mode) & 0o077 == 0, path
PY

snapshot_dwight_modes() {
  python3 - "$HOME_DIR/profiles/dwight" <<'PY'
from pathlib import Path
import stat, sys
root = Path(sys.argv[1])
paths = [root / 'config.yaml', root / 'SOUL.md', root / 'distribution.yaml', root / 'skills']
paths.extend(sorted((root / 'skills').rglob('*')))
for path in paths:
    print(f"{path.relative_to(root)}|{stat.S_IMODE(path.lstat().st_mode):04o}")
PY
}
assert_dwight_modes() {
  snapshot_dwight_modes > "$TMP/modes-current.txt"
  if ! cmp -s "$TMP/modes-baseline.txt" "$TMP/modes-current.txt"; then
    diff -u "$TMP/modes-baseline.txt" "$TMP/modes-current.txt" >&2 || true
    printf 'rollback changed Dwight permissions\n' >&2
    exit 1
  fi
}
snapshot_dwight_modes > "$TMP/modes-baseline.txt"

snapshot_default_modes() {
  python3 - "$HOME_DIR" <<'PY'
from pathlib import Path
import stat, sys
root = Path(sys.argv[1])
paths = [root / 'config.yaml', root / 'SOUL.md', root / 'local', root / 'skills', root / 'skills' / 'client-agent-onboarding']
paths.extend(sorted((root / 'skills' / 'client-agent-onboarding').rglob('*')))
for path in paths:
    if path.exists() or path.is_symlink():
        print(f"{path.relative_to(root)}|{stat.S_IMODE(path.lstat().st_mode):04o}")
PY
}
assert_default_modes() {
  snapshot_default_modes > "$TMP/default-modes-current.txt"
  if ! cmp -s "$TMP/default-modes-baseline.txt" "$TMP/default-modes-current.txt"; then
    diff -u "$TMP/default-modes-baseline.txt" "$TMP/default-modes-current.txt" >&2 || true
    printf 'rollback changed default permissions\n' >&2
    exit 1
  fi
}
snapshot_default_modes > "$TMP/default-modes-baseline.txt"

cp "$HOME_DIR/profiles/dwight/config.yaml" "$TMP/config-before-query-secret.yaml"
python3 - "$HOME_DIR/config.yaml" <<'PY'
import sys, yaml
path = sys.argv[1]
with open(path, encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
model = data.setdefault('model', {})
query_key = 'api' + '_key'
model['base_url'] = 'https://model.invalid/v1?' + query_key + '=synthetic-sensitive-value'
with open(path, 'w', encoding='utf-8') as fh:
    yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)
PY
QUERY_LOG="$TMP/query-secret.log"
if HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >"$QUERY_LOG" 2>&1; then
  printf 'expected model.base_url query to block update\n' >&2
  exit 1
fi
grep -q 'Query ou fragment interdit' "$QUERY_LOG"
cmp -s "$TMP/config-before-query-secret.yaml" "$HOME_DIR/profiles/dwight/config.yaml" \
  || { printf 'query-secret failure did not restore Dwight config\n' >&2; exit 1; }
assert_dwight_modes
python3 - "$HOME_DIR/config.yaml" <<'PY'
import sys, yaml
path = sys.argv[1]
with open(path, encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
data['model']['base_url'] = 'https://model.invalid/v1'
with open(path, 'w', encoding='utf-8') as fh:
    yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)
PY

REAL_HERMES="$(command -v hermes)"
FAKE_BIN="$TMP/fake-bin"
mkdir -p "$FAKE_BIN"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [[ "$1" == profile && "$2" == update ]]; then' \
  '  printf "\n# simulated partial update\n" >> "$HERMES_HOME/profiles/dwight/SOUL.md"' \
  '  rm -rf "$HERMES_HOME/profiles/dwight/skills/client-demo-test"' \
  '  exit 42' \
  'fi' \
  "exec \"$REAL_HERMES\" \"\$@\"" > "$FAKE_BIN/hermes"
chmod 700 "$FAKE_BIN/hermes"
if PATH="$FAKE_BIN:$PATH" HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >/dev/null 2>&1; then
  printf 'expected simulated profile update failure\n' >&2
  exit 1
fi
test -f "$CLIENT_SKILL/SKILL.md"
if grep -q 'simulated partial update' "$HOME_DIR/profiles/dwight/SOUL.md"; then
  printf 'rollback did not restore Dwight SOUL\n' >&2
  exit 1
fi
assert_dwight_modes

OUTSIDE_SKILLS="$TMP/outside-skills"
FAKE_SYMLINK_BIN="$TMP/fake-symlink-bin"
mkdir -p "$OUTSIDE_SKILLS" "$FAKE_SYMLINK_BIN"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [[ "$1" == profile && "$2" == update ]]; then' \
  '  rm -rf "$HERMES_HOME/profiles/dwight/skills"' \
  "  ln -s \"$OUTSIDE_SKILLS\" \"\$HERMES_HOME/profiles/dwight/skills\"" \
  '  exit 0' \
  'fi' \
  "exec \"$REAL_HERMES\" \"\$@\"" > "$FAKE_SYMLINK_BIN/hermes"
chmod 700 "$FAKE_SYMLINK_BIN/hermes"
SYMLINK_UPDATE_LOG="$TMP/symlink-after-update.log"
if PATH="$FAKE_SYMLINK_BIN:$PATH" HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >"$SYMLINK_UPDATE_LOG" 2>&1; then
  printf 'expected post-update skills symlink to block installation\n' >&2
  exit 1
fi
grep -q 'dossier skills Dwight devenu non sûr après update' "$SYMLINK_UPDATE_LOG"
test -d "$HOME_DIR/profiles/dwight/skills"
test ! -L "$HOME_DIR/profiles/dwight/skills"
test -f "$CLIENT_SKILL/SKILL.md"
test ! -e "$OUTSIDE_SKILLS/client-demo-test"
assert_dwight_modes

OUTSIDE_DWIGHT_ROOT="$TMP/outside-dwight-root"
DISPLACED_DWIGHT_ROOT="$TMP/displaced-dwight-root"
FAKE_ROOT_SYMLINK_BIN="$TMP/fake-root-symlink-bin"
mkdir -p "$OUTSIDE_DWIGHT_ROOT" "$FAKE_ROOT_SYMLINK_BIN"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [[ "$1" == profile && "$2" == update ]]; then' \
  "  mv \"\$HERMES_HOME/profiles/dwight\" \"$DISPLACED_DWIGHT_ROOT\"" \
  "  ln -s \"$OUTSIDE_DWIGHT_ROOT\" \"\$HERMES_HOME/profiles/dwight\"" \
  '  exit 0' \
  'fi' \
  "exec \"$REAL_HERMES\" \"\$@\"" > "$FAKE_ROOT_SYMLINK_BIN/hermes"
chmod 700 "$FAKE_ROOT_SYMLINK_BIN/hermes"
ROOT_SYMLINK_LOG="$TMP/root-symlink-after-update.log"
if PATH="$FAKE_ROOT_SYMLINK_BIN:$PATH" HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >"$ROOT_SYMLINK_LOG" 2>&1; then
  printf 'expected post-update Dwight root symlink to block installation\n' >&2
  exit 1
fi
grep -q 'racine Dwight devenue non sûre après update' "$ROOT_SYMLINK_LOG"
test -d "$HOME_DIR/profiles/dwight"
test ! -L "$HOME_DIR/profiles/dwight"
test -f "$CLIENT_SKILL/SKILL.md"
test ! -e "$OUTSIDE_DWIGHT_ROOT/SOUL.md"
assert_dwight_modes

DISPLACED_DEFAULT_ROOT="$TMP/displaced-default-root"
OUTSIDE_DEFAULT_ROOT="$TMP/outside-default-root"
OUTSIDE_DEFAULT_BASELINE="$TMP/outside-default-baseline"
FAKE_DEFAULT_ROOT_BIN="$TMP/fake-default-root-bin"
mkdir -p "$FAKE_DEFAULT_ROOT_BIN"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [[ "$1" == profile && "$2" == update ]]; then' \
  "  \"$REAL_HERMES\" \"\$@\" || exit \$?" \
  "  mv \"\$HERMES_HOME\" \"$DISPLACED_DEFAULT_ROOT\"" \
  "  mkdir -p \"$OUTSIDE_DEFAULT_ROOT\"" \
  "  cp -Rp \"$DISPLACED_DEFAULT_ROOT/.\" \"$OUTSIDE_DEFAULT_ROOT/\"" \
  "  cp -Rp \"$OUTSIDE_DEFAULT_ROOT\" \"$OUTSIDE_DEFAULT_BASELINE\"" \
  "  ln -s \"$OUTSIDE_DEFAULT_ROOT\" \"\$HERMES_HOME\"" \
  '  exit 0' \
  'fi' \
  "exec \"$REAL_HERMES\" \"\$@\"" > "$FAKE_DEFAULT_ROOT_BIN/hermes"
chmod 700 "$FAKE_DEFAULT_ROOT_BIN/hermes"
DEFAULT_ROOT_LOG="$TMP/default-root-after-update.log"
if PATH="$FAKE_DEFAULT_ROOT_BIN:$PATH" HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >"$DEFAULT_ROOT_LOG" 2>&1; then
  printf 'expected post-update default root substitution to block installation\n' >&2
  exit 1
fi
grep -q 'arbre default devenu non sûr après update' "$DEFAULT_ROOT_LOG"
test -L "$HOME_DIR"
diff -qr "$OUTSIDE_DEFAULT_BASELINE" "$OUTSIDE_DEFAULT_ROOT" >/dev/null
rm "$HOME_DIR"
mv "$DISPLACED_DEFAULT_ROOT" "$HOME_DIR"
assert_dwight_modes
assert_default_modes

OUTSIDE_DEFAULT_SKILLS="$TMP/outside-default-skills"
SAVED_DEFAULT_SKILLS="$TMP/saved-default-skills"
FAKE_DEFAULT_SYMLINK_BIN="$TMP/fake-default-symlink-bin"
mkdir -p "$OUTSIDE_DEFAULT_SKILLS" "$FAKE_DEFAULT_SYMLINK_BIN"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [[ "$1" == profile && "$2" == update ]]; then' \
  "  mv \"\$HERMES_HOME/skills\" \"$SAVED_DEFAULT_SKILLS\"" \
  "  ln -s \"$OUTSIDE_DEFAULT_SKILLS\" \"\$HERMES_HOME/skills\"" \
  '  exit 0' \
  'fi' \
  "exec \"$REAL_HERMES\" \"\$@\"" > "$FAKE_DEFAULT_SYMLINK_BIN/hermes"
chmod 700 "$FAKE_DEFAULT_SYMLINK_BIN/hermes"
DEFAULT_SYMLINK_LOG="$TMP/default-symlink-after-update.log"
if PATH="$FAKE_DEFAULT_SYMLINK_BIN:$PATH" HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >"$DEFAULT_SYMLINK_LOG" 2>&1; then
  printf 'expected post-update default skills symlink to block installation\n' >&2
  exit 1
fi
grep -q 'arbre default devenu non sûr après update' "$DEFAULT_SYMLINK_LOG"
test -L "$HOME_DIR/skills"
test ! -e "$OUTSIDE_DEFAULT_SKILLS/client-agent-onboarding"
rm "$HOME_DIR/skills"
mv "$SAVED_DEFAULT_SKILLS" "$HOME_DIR/skills"
test -f "$HOME_DIR/skills/client-agent-onboarding/SKILL.md"
assert_dwight_modes
assert_default_modes

DOWNGRADE_HELPER="$TMP/downgrade-manifest.py"
printf '%s\n' \
  'import sys, yaml' \
  'path = sys.argv[1]' \
  'with open(path, encoding="utf-8") as fh: data = yaml.safe_load(fh) or {}' \
  'data["version"] = "0.0.0"' \
  'with open(path, "w", encoding="utf-8") as fh: yaml.safe_dump(data, fh, sort_keys=False)' \
  > "$DOWNGRADE_HELPER"
FAKE_VERSION_BIN="$TMP/fake-version-bin"
mkdir -p "$FAKE_VERSION_BIN"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [[ "$1" == profile && "$2" == update ]]; then' \
  "  \"$REAL_HERMES\" \"\$@\" || exit \$?" \
  "  python3 \"$DOWNGRADE_HELPER\" \"\$HERMES_HOME/profiles/dwight/distribution.yaml\"" \
  '  exit 0' \
  'fi' \
  "exec \"$REAL_HERMES\" \"\$@\"" > "$FAKE_VERSION_BIN/hermes"
chmod 700 "$FAKE_VERSION_BIN/hermes"
VERSION_LOG="$TMP/version-mismatch.log"
if PATH="$FAKE_VERSION_BIN:$PATH" HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >"$VERSION_LOG" 2>&1; then
  printf 'expected post-update version mismatch to block installation\n' >&2
  exit 1
fi
grep -q 'version Dwight incohérente après update' "$VERSION_LOG"
python3 - "$HOME_DIR/profiles/dwight/distribution.yaml" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
assert str(data.get('version')) == '0.1.3', data
PY
assert_dwight_modes

python3 - \
  "$HOME_DIR/profiles/dwight/config.yaml" \
  "$HOME_DIR/local/onboarding.yaml" <<'PY'
import sys, yaml
config_path, onboarding_path = sys.argv[1:]
with open(config_path, encoding='utf-8') as fh:
    config = yaml.safe_load(fh) or {}
config['model'] = {'default': 'pre-late-failure-model', 'provider': 'synthetic-provider'}
with open(config_path, 'w', encoding='utf-8') as fh:
    yaml.safe_dump(config, fh, allow_unicode=True, sort_keys=False)
with open(onboarding_path, encoding='utf-8') as fh:
    onboarding = yaml.safe_load(fh) or {}
onboarding.pop('managed_profiles', None)
with open(onboarding_path, 'w', encoding='utf-8') as fh:
    yaml.safe_dump(onboarding, fh, allow_unicode=True, sort_keys=False)
PY
cp "$HOME_DIR/profiles/dwight/config.yaml" "$TMP/config-before-late.yaml"
cp "$HOME_DIR/local/onboarding.yaml" "$TMP/onboarding-before-late.yaml"
cp "$HOME_DIR/SOUL.md" "$TMP/default-soul-before-late.md"
cp "$HOME_DIR/skills/client-agent-onboarding/SKILL.md" "$TMP/default-skill-before-late.md"

FAKE_LATE_BIN="$TMP/fake-late-bin"
mkdir -p "$FAKE_LATE_BIN"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  "if [[ \"\$*\" == *\"$WORKING/skills/client-agent-onboarding\"* ]]; then exit 43; fi" \
  'exec /bin/cp "$@"' > "$FAKE_LATE_BIN/cp"
chmod 700 "$FAKE_LATE_BIN/cp"
if PATH="$FAKE_LATE_BIN:$PATH" HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >/dev/null 2>&1; then
  printf 'expected simulated late installation failure\n' >&2
  exit 1
fi
cmp -s "$TMP/config-before-late.yaml" "$HOME_DIR/profiles/dwight/config.yaml" \
  || { printf 'late rollback did not restore Dwight config\n' >&2; exit 1; }
cmp -s "$TMP/onboarding-before-late.yaml" "$HOME_DIR/local/onboarding.yaml" \
  || { printf 'late rollback did not restore onboarding\n' >&2; exit 1; }
cmp -s "$TMP/default-soul-before-late.md" "$HOME_DIR/SOUL.md" \
  || { printf 'late rollback did not restore default SOUL\n' >&2; exit 1; }
cmp -s "$TMP/default-skill-before-late.md" "$HOME_DIR/skills/client-agent-onboarding/SKILL.md" \
  || { printf 'late rollback did not restore default onboarding skill\n' >&2; exit 1; }
assert_dwight_modes
assert_default_modes

PROFILE_ROOT="$HOME_DIR/profiles/dwight"
EXTERNAL_PROFILE="$TMP/external-dwight"
mv "$PROFILE_ROOT" "$EXTERNAL_PROFILE"
ln -s "$EXTERNAL_PROFILE" "$PROFILE_ROOT"
cp "$EXTERNAL_PROFILE/distribution.yaml" "$TMP/external-distribution-before.yaml"
PROFILE_LINK_LOG="$TMP/profile-root-symlink.log"
if HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >"$PROFILE_LINK_LOG" 2>&1; then
  printf 'expected symlinked Dwight profile root to block update\n' >&2
  exit 1
fi
grep -q 'racine du profil Dwight non sûre ou symbolique' "$PROFILE_LINK_LOG"
cmp -s "$TMP/external-distribution-before.yaml" "$EXTERNAL_PROFILE/distribution.yaml" \
  || { printf 'external Dwight target was modified\n' >&2; exit 1; }
rm -f "$PROFILE_ROOT"
mv "$EXTERNAL_PROFILE" "$PROFILE_ROOT"

PARENT_HOME="$TMP/parent-symlink-home"
OUTSIDE_PROFILES="$TMP/outside-profiles"
mkdir -p "$PARENT_HOME" "$OUTSIDE_PROFILES"
cp "$WORKING/distributions/dwight/config.yaml" "$PARENT_HOME/config.yaml"
ln -s "$OUTSIDE_PROFILES" "$PARENT_HOME/profiles"
PARENT_LINK_LOG="$TMP/profiles-parent-symlink.log"
if HERMES_HOME="$PARENT_HOME" "$WORKING/install.sh" >"$PARENT_LINK_LOG" 2>&1; then
  printf 'expected symlinked profiles parent to block installation\n' >&2
  exit 1
fi
grep -q 'racine profiles non sûre ou symbolique' "$PARENT_LINK_LOG"
test ! -e "$OUTSIDE_PROFILES/dwight"

ANCESTOR_REAL="$TMP/ancestor-real"
ANCESTOR_LINK="$TMP/ancestor-link"
ANCESTOR_HOME_REAL="$ANCESTOR_REAL/default-root"
mkdir -p "$ANCESTOR_HOME_REAL"
cp "$WORKING/distributions/dwight/config.yaml" "$ANCESTOR_HOME_REAL/config.yaml"
ln -s "$ANCESTOR_REAL" "$ANCESTOR_LINK"
ANCESTOR_LOG="$TMP/ancestor-symlink.log"
if HERMES_HOME="$ANCESTOR_LINK/default-root" "$WORKING/install.sh" >"$ANCESTOR_LOG" 2>&1; then
  printf 'expected symlinked ancestor to block installation\n' >&2
  exit 1
fi
grep -q 'ancêtre symbolique' "$ANCESTOR_LOG"
test ! -e "$ANCESTOR_HOME_REAL/profiles/dwight"
test ! -e "$ANCESTOR_HOME_REAL/SOUL.md"

CORE_EXTRA="$HOME_DIR/profiles/dwight/skills/dwight-seo-core/local-override.md"
printf '%s\n' '# unmanaged Core override' > "$CORE_EXTRA"
if HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >/dev/null 2>&1; then
  printf 'expected extra file inside a Core skill to block update\n' >&2
  exit 1
fi
test -f "$CORE_EXTRA"
rm -f "$CORE_EXTRA"

mv "$HOME_DIR/local/onboarding.yaml" "$TMP/onboarding-regular.yaml"
printf '%s\n' 'external sentinel' > "$TMP/external-onboarding.yaml"
ln -s "$TMP/external-onboarding.yaml" "$HOME_DIR/local/onboarding.yaml"
if HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >/dev/null 2>&1; then
  printf 'expected canonical onboarding symlink to block update\n' >&2
  exit 1
fi
grep -q '^external sentinel$' "$TMP/external-onboarding.yaml"
rm -f "$HOME_DIR/local/onboarding.yaml"
mv "$TMP/onboarding-regular.yaml" "$HOME_DIR/local/onboarding.yaml"

printf '\n# unauthorized managed edit\n' >> "$HOME_DIR/profiles/dwight/SOUL.md"
if HERMES_HOME="$HOME_DIR" "$WORKING/install.sh" >/dev/null 2>&1; then
  printf 'expected modified managed SOUL to block update\n' >&2
  exit 1
fi
grep -q 'unauthorized managed edit' "$HOME_DIR/profiles/dwight/SOUL.md"
grep -q '^runtime data survives upgrades$' "$CLAUDE_RUNTIME_SENTINEL"

printf 'INSTALL_UPGRADE_GUARDS_OK\n'
