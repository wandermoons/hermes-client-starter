#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DWIGHT_SOURCE="${DWIGHT_SOURCE:-$SCRIPT_DIR/distributions/dwight}"
DWIGHT_PROFILE="${DWIGHT_PROFILE:-dwight}"

fail() {
  printf 'Erreur : %s\n' "$1" >&2
  exit 1
}

command -v hermes >/dev/null 2>&1 || fail 'la commande hermes est introuvable.'

# Utiliser l’interpréteur de l’installation Hermes, qui possède PyYAML, plutôt
# que le python3 système dont les dépendances varient selon l’hôte.
HERMES_INSTALL_DIR=''
while IFS= read -r line; do
  case "$line" in
    'Install directory: '*) HERMES_INSTALL_DIR="${line#Install directory: }" ;;
  esac
done < <(hermes --version)

PYTHON_BIN=''
for candidate in \
  "${HERMES_PYTHON:-}" \
  "$HERMES_INSTALL_DIR/.venv/bin/python" \
  "$HERMES_INSTALL_DIR/venv/bin/python" \
  "$(command -v python3 2>/dev/null || true)"; do
  if [[ -n "$candidate" && -x "$candidate" ]] && "$candidate" -c 'import yaml' >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done
[[ -n "$PYTHON_BIN" ]] || fail 'aucun interpréteur Python avec PyYAML n’a été trouvé.'

# Toujours résoudre le vrai profil default via Hermes. Ne jamais traiter un
# HERMES_HOME éventuellement positionné sur un profil nommé comme la racine.
DEFAULT_CONFIG="$(hermes -p default config path)"
[[ "$DEFAULT_CONFIG" = /* ]] || fail "chemin de configuration default non absolu : $DEFAULT_CONFIG"
[[ "$(basename "$DEFAULT_CONFIG")" == config.yaml ]] || fail "configuration default inattendue : $DEFAULT_CONFIG"
[[ -f "$DEFAULT_CONFIG" ]] || fail "configuration default absente : $DEFAULT_CONFIG"
TARGET_HOME="$(dirname "$DEFAULT_CONFIG")"
[[ -n "$TARGET_HOME" && "$TARGET_HOME" != / ]] || fail "racine default dangereuse : $TARGET_HOME"
[[ "$TARGET_HOME" != */profiles/* ]] || fail "le profil default résolu se trouve sous profiles/ : $TARGET_HOME"

EXPECTED_DWIGHT_HOME="$TARGET_HOME/profiles/$DWIGHT_PROFILE"
BACKUP_DIR="$(mktemp -d)"
CREATED_DWIGHT=0
DEFAULT_MUTATED=0
SOUL_EXISTED=0
SKILL_EXISTED=0
CLIENT_CREATED=0
ONBOARDING_CREATED=0

cleanup() {
  "$PYTHON_BIN" - "$BACKUP_DIR" <<'PY'
import shutil, sys
shutil.rmtree(sys.argv[1], ignore_errors=True)
PY
}

rollback() {
  rc=$?
  trap - ERR INT TERM
  set +e
  if [[ "$DEFAULT_MUTATED" == 1 ]]; then
    if [[ "$SOUL_EXISTED" == 1 ]]; then
      cp -p "$BACKUP_DIR/SOUL.md" "$TARGET_HOME/SOUL.md"
    else
      rm -f "$TARGET_HOME/SOUL.md"
    fi
    rm -rf "$TARGET_HOME/skills/client-agent-onboarding"
    if [[ "$SKILL_EXISTED" == 1 ]]; then
      mkdir -p "$TARGET_HOME/skills/client-agent-onboarding"
      cp -R "$BACKUP_DIR/client-agent-onboarding/." "$TARGET_HOME/skills/client-agent-onboarding/"
    fi
  fi
  [[ "$CLIENT_CREATED" == 1 ]] && rm -f "$TARGET_HOME/local/CLIENT.md"
  [[ "$ONBOARDING_CREATED" == 1 ]] && rm -f "$TARGET_HOME/local/onboarding.yaml"
  if [[ "$CREATED_DWIGHT" == 1 ]]; then
    hermes profile delete "$DWIGHT_PROFILE" --yes >/dev/null 2>&1 || true
  fi
  cleanup
  printf 'Installation annulée ; les mutations du profil principal ont été restaurées.\n' >&2
  exit "$rc"
}

trap rollback ERR INT TERM
trap cleanup EXIT

# Installer ou mettre à jour Dwight AVANT de modifier le profil principal.
if hermes profile show "$DWIGHT_PROFILE" >/dev/null 2>&1; then
  DWIGHT_CONFIG_BEFORE="$(hermes -p "$DWIGHT_PROFILE" config path)"
  DWIGHT_HOME_BEFORE="$(dirname "$DWIGHT_CONFIG_BEFORE")"
  MANIFEST="$DWIGHT_HOME_BEFORE/distribution.yaml"
  [[ -f "$MANIFEST" ]] || fail "collision : le profil $DWIGHT_PROFILE existe mais n’est pas une distribution."

  MANIFEST_NAME="$("$PYTHON_BIN" - "$MANIFEST" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
print(data.get('name', ''))
PY
)"
  MANIFEST_SOURCE="$("$PYTHON_BIN" - "$MANIFEST" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
print(data.get('source', ''))
PY
)"
  [[ "$MANIFEST_NAME" == "$DWIGHT_PROFILE" ]] || fail "collision de distribution : nom ${MANIFEST_NAME:-absent}."
  [[ "$MANIFEST_SOURCE" == "$DWIGHT_SOURCE" ]] || fail "collision de source Dwight : ${MANIFEST_SOURCE:-absente}."
  hermes profile update "$DWIGHT_PROFILE"
else
  hermes profile install "$DWIGHT_SOURCE" --name "$DWIGHT_PROFILE" --alias --yes
  CREATED_DWIGHT=1
fi

DWIGHT_CONFIG="$(hermes -p "$DWIGHT_PROFILE" config path)"
[[ "$DWIGHT_CONFIG" = /* && -f "$DWIGHT_CONFIG" ]] || fail "configuration Dwight invalide : $DWIGHT_CONFIG"
DWIGHT_HOME="$(dirname "$DWIGHT_CONFIG")"

"$PYTHON_BIN" - "$EXPECTED_DWIGHT_HOME" "$DWIGHT_HOME" <<'PY'
from pathlib import Path
import sys
expected = Path(sys.argv[1]).resolve()
actual = Path(sys.argv[2]).resolve()
if expected != actual:
    raise SystemExit(f"Chemin Dwight incohérent : attendu {expected}, obtenu {actual}")
PY

DWIGHT_MANIFEST="$DWIGHT_HOME/distribution.yaml"
[[ -f "$DWIGHT_MANIFEST" ]] || fail 'manifest Dwight absent après installation.'
DWIGHT_VERSION="$("$PYTHON_BIN" - "$DWIGHT_MANIFEST" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
print(data.get('version', 'unknown'))
PY
)"

# Adapter le modèle au profil default sans copier de credential, puis fixer un
# cwd absolu et prévisible dans le périmètre du client.
"$PYTHON_BIN" - "$DEFAULT_CONFIG" "$DWIGHT_CONFIG" "$DWIGHT_HOME" <<'PY'
import sys, yaml
src_path, dst_path, dwight_home = sys.argv[1:]
with open(src_path, encoding='utf-8') as fh:
    src = yaml.safe_load(fh) or {}
with open(dst_path, encoding='utf-8') as fh:
    dst = yaml.safe_load(fh) or {}
for key in ('model', 'providers', 'fallback_providers', 'credential_pool_strategies'):
    if key in src:
        dst[key] = src[key]
dst.setdefault('terminal', {})['cwd'] = dwight_home
with open(dst_path, 'w', encoding='utf-8') as fh:
    yaml.safe_dump(dst, fh, allow_unicode=True, sort_keys=False)
PY

# Le contexte du profil principal est la source canonique. Dwight y accède via
# des liens symboliques locaux afin d’éviter deux copies divergentes.
mkdir -p "$TARGET_HOME/local" "$TARGET_HOME/skills" "$DWIGHT_HOME/local"
if [[ ! -f "$TARGET_HOME/local/CLIENT.md" ]]; then
  install -m 600 "$SCRIPT_DIR/templates/CLIENT.md" "$TARGET_HOME/local/CLIENT.md"
  CLIENT_CREATED=1
fi
if [[ ! -f "$TARGET_HOME/local/onboarding.yaml" ]]; then
  install -m 600 "$SCRIPT_DIR/templates/onboarding.yaml" "$TARGET_HOME/local/onboarding.yaml"
  ONBOARDING_CREATED=1
fi

ensure_canonical_link() {
  canonical="$1"
  link="$2"
  if [[ -L "$link" ]]; then
    [[ "$(readlink "$link")" == "$canonical" ]] || fail "lien local divergent : $link"
    return
  fi
  if [[ -e "$link" ]]; then
    cmp -s "$canonical" "$link" || fail "contexte local divergent à fusionner manuellement : $link"
    rm -f "$link"
  fi
  ln -s "$canonical" "$link"
}

ensure_canonical_link "$TARGET_HOME/local/CLIENT.md" "$DWIGHT_HOME/local/CLIENT.md"
ensure_canonical_link "$TARGET_HOME/local/onboarding.yaml" "$DWIGHT_HOME/local/onboarding.yaml"

"$PYTHON_BIN" - "$TARGET_HOME/local/onboarding.yaml" "$DWIGHT_VERSION" <<'PY'
import sys, yaml
path, version = sys.argv[1:]
with open(path, encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
profiles = data.setdefault('managed_profiles', {})
dwight = profiles.setdefault('dwight', {})
dwight.update(status='installed', distribution='hermes-dwight-seo', version=version)
with open(path, 'w', encoding='utf-8') as fh:
    yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)
PY

# Sauvegarder puis muter le profil principal en dernier.
if [[ -f "$TARGET_HOME/SOUL.md" ]]; then
  cp -p "$TARGET_HOME/SOUL.md" "$BACKUP_DIR/SOUL.md"
  SOUL_EXISTED=1
fi
if [[ -d "$TARGET_HOME/skills/client-agent-onboarding" ]]; then
  mkdir -p "$BACKUP_DIR/client-agent-onboarding"
  cp -R "$TARGET_HOME/skills/client-agent-onboarding/." "$BACKUP_DIR/client-agent-onboarding/"
  SKILL_EXISTED=1
fi
DEFAULT_MUTATED=1
install -m 600 "$SCRIPT_DIR/SOUL.md" "$TARGET_HOME/SOUL.md"
rm -rf "$TARGET_HOME/skills/client-agent-onboarding"
mkdir -p "$TARGET_HOME/skills/client-agent-onboarding"
cp -R "$SCRIPT_DIR/skills/client-agent-onboarding/." "$TARGET_HOME/skills/client-agent-onboarding/"

# Toutes les opérations critiques sont terminées.
trap - ERR INT TERM
DEFAULT_MUTATED=0
CREATED_DWIGHT=0
cleanup
trap - EXIT

printf '\nInstallation terminée.\n'
printf 'Profil principal : %s\n' "$TARGET_HOME"
printf 'Profil Dwight : %s\n' "$DWIGHT_HOME"
printf 'Distribution Dwight : v%s\n' "$DWIGHT_VERSION"
printf 'Contexte canonique : %s\n' "$TARGET_HOME/local/CLIENT.md"
printf 'Étape suivante : ouvrir une nouvelle session et vérifier l’accès au modèle depuis Dwight.\n'
