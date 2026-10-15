#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DWIGHT_SOURCE="${DWIGHT_SOURCE:-$SCRIPT_DIR/distributions/dwight}"
DWIGHT_PROFILE="${DWIGHT_PROFILE:-dwight}"
CLAUDE_SEO_INTEGRATION_SOURCE="${CLAUDE_SEO_INTEGRATION_SOURCE:-$SCRIPT_DIR/integrations/claude-seo}"

fail() {
  printf 'Erreur : %s\n' "$1" >&2
  return 1
}

command -v hermes >/dev/null 2>&1 || fail 'la commande hermes est introuvable.'

# Refuser un HERMES_HOME traversant un lien symbolique avant le premier appel
# Hermes : certaines versions peuvent initialiser des fichiers lors de la
# résolution du profil, ce qui écrirait sinon hors de la racine attendue.
if [[ -n "${HERMES_HOME:-}" ]]; then
  python3 - "$HERMES_HOME" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
if path != path.resolve():
    raise SystemExit(f"HERMES_HOME traversant un ancêtre symbolique : {path}")
PY
fi

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
"$PYTHON_BIN" - "$TARGET_HOME" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
if path != path.resolve():
    raise SystemExit(f"Racine default traversant un ancêtre symbolique : {path}")
PY
[[ ! -L "$DEFAULT_CONFIG" && ! -L "$TARGET_HOME" ]] || fail 'profil default symbolique non autorisé.'
if [[ -e "$TARGET_HOME/local" ]]; then
  [[ -d "$TARGET_HOME/local" && ! -L "$TARGET_HOME/local" ]] || fail 'dossier local default non sûr.'
fi
if [[ -e "$TARGET_HOME/skills" ]]; then
  [[ -d "$TARGET_HOME/skills" && ! -L "$TARGET_HOME/skills" ]] || fail 'dossier skills default non sûr.'
fi
for CANONICAL_FILE in "$TARGET_HOME/local/CLIENT.md" "$TARGET_HOME/local/onboarding.yaml"; do
  if [[ -e "$CANONICAL_FILE" || -L "$CANONICAL_FILE" ]]; then
    [[ -f "$CANONICAL_FILE" && ! -L "$CANONICAL_FILE" ]] || fail "fichier canonique non sûr : $CANONICAL_FILE"
  fi
done

PROFILES_ROOT="$TARGET_HOME/profiles"
EXPECTED_DWIGHT_HOME="$PROFILES_ROOT/$DWIGHT_PROFILE"
if [[ -e "$PROFILES_ROOT" || -L "$PROFILES_ROOT" ]]; then
  [[ -d "$PROFILES_ROOT" && ! -L "$PROFILES_ROOT" ]] || fail 'racine profiles non sûre ou symbolique.'
fi
if [[ -e "$EXPECTED_DWIGHT_HOME" || -L "$EXPECTED_DWIGHT_HOME" ]]; then
  [[ -d "$EXPECTED_DWIGHT_HOME" && ! -L "$EXPECTED_DWIGHT_HOME" ]] \
    || fail 'racine du profil Dwight non sûre ou symbolique.'
fi
BACKUP_DIR="$(mktemp -d)"
CREATED_DWIGHT=0
DEFAULT_MUTATED=0
SOUL_EXISTED=0
SKILL_EXISTED=0
CLIENT_CREATED=0
ONBOARDING_CREATED=0
ONBOARDING_EXISTED=0
DWIGHT_CLIENT_LINK_CREATED=0
DWIGHT_ONBOARDING_LINK_CREATED=0
DWIGHT_UPDATE_STARTED=0
DWIGHT_UPDATE_PATH_VERIFIED=0
DWIGHT_UPDATE_HOME=''
DWIGHT_UPDATE_BACKUP=''
DWIGHT_ROLLBACK_BACKUP=''

cleanup() {
  "$PYTHON_BIN" - "$BACKUP_DIR" <<'PY'
import shutil, sys
shutil.rmtree(sys.argv[1], ignore_errors=True)
PY
}

dwight_parent_is_safe() {
  default_tree_is_safe || return 1
  [[ -d "$PROFILES_ROOT" && ! -L "$PROFILES_ROOT" \
     && "$(dirname "$EXPECTED_DWIGHT_HOME")" == "$PROFILES_ROOT" ]]
}

dwight_root_is_safe() {
  [[ -d "$PROFILES_ROOT" && ! -L "$PROFILES_ROOT" \
     && -n "$DWIGHT_UPDATE_HOME" \
     && "$DWIGHT_UPDATE_HOME" == "$EXPECTED_DWIGHT_HOME" \
     && -d "$DWIGHT_UPDATE_HOME" \
     && ! -L "$DWIGHT_UPDATE_HOME" ]]
}

default_tree_is_safe() {
  "$PYTHON_BIN" - "$TARGET_HOME" >/dev/null 2>&1 <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
raise SystemExit(0 if path == path.resolve() else 1)
PY
  [[ -d "$TARGET_HOME" && ! -L "$TARGET_HOME" \
     && -f "$DEFAULT_CONFIG" && ! -L "$DEFAULT_CONFIG" ]] || return 1
  for path in "$TARGET_HOME/local" "$TARGET_HOME/skills" "$PROFILES_ROOT"; do
    if [[ -e "$path" || -L "$path" ]]; then
      [[ -d "$path" && ! -L "$path" ]] || return 1
    fi
  done
  for path in "$TARGET_HOME/local/CLIENT.md" "$TARGET_HOME/local/onboarding.yaml"; do
    if [[ -e "$path" || -L "$path" ]]; then
      [[ -f "$path" && ! -L "$path" ]] || return 1
    fi
  done
  return 0
}

rollback() {
  rc=$?
  trap - ERR INT TERM
  set +e
  if [[ "$DWIGHT_UPDATE_STARTED" == 1 \
        && "$DWIGHT_UPDATE_PATH_VERIFIED" == 1 \
        && -n "$DWIGHT_ROLLBACK_BACKUP" \
        && -d "$DWIGHT_ROLLBACK_BACKUP" ]]; then
    if dwight_parent_is_safe; then
      if [[ -L "$EXPECTED_DWIGHT_HOME" ]]; then
        rm -f "$EXPECTED_DWIGHT_HOME"
      elif [[ -e "$EXPECTED_DWIGHT_HOME" ]]; then
        rm -rf "$EXPECTED_DWIGHT_HOME"
      fi
      cp -Rp "$DWIGHT_ROLLBACK_BACKUP" "$EXPECTED_DWIGHT_HOME"
      DWIGHT_UPDATE_HOME="$EXPECTED_DWIGHT_HOME"
    else
      printf 'Rollback Dwight ignoré : parent profiles devenu non sûr. Backup temporaire : %s\n' \
        "$DWIGHT_ROLLBACK_BACKUP" >&2
    fi
  fi
  if default_tree_is_safe; then
    if [[ "$DEFAULT_MUTATED" == 1 ]]; then
      if [[ "$SOUL_EXISTED" == 1 ]]; then
        cp -p "$BACKUP_DIR/SOUL.md" "$TARGET_HOME/SOUL.md"
      else
        rm -f "$TARGET_HOME/SOUL.md"
      fi
      rm -rf "$TARGET_HOME/skills/client-agent-onboarding"
      if [[ "$SKILL_EXISTED" == 1 ]]; then
        cp -Rp "$BACKUP_DIR/client-agent-onboarding" "$TARGET_HOME/skills/client-agent-onboarding"
      fi
    fi
    [[ "$CLIENT_CREATED" == 1 ]] && rm -f "$TARGET_HOME/local/CLIENT.md"
    if [[ "$ONBOARDING_EXISTED" == 1 ]]; then
      cp -p "$BACKUP_DIR/onboarding.yaml" "$TARGET_HOME/local/onboarding.yaml"
    elif [[ "$ONBOARDING_CREATED" == 1 ]]; then
      rm -f "$TARGET_HOME/local/onboarding.yaml"
    fi
  else
    printf 'Rollback default ignoré : arbre devenu non sûr.\n' >&2
  fi
  if [[ "$DWIGHT_UPDATE_PATH_VERIFIED" == 1 ]] && dwight_root_is_safe; then
    [[ "$DWIGHT_CLIENT_LINK_CREATED" == 1 ]] && rm -f "$DWIGHT_UPDATE_HOME/local/CLIENT.md"
    [[ "$DWIGHT_ONBOARDING_LINK_CREATED" == 1 ]] && rm -f "$DWIGHT_UPDATE_HOME/local/onboarding.yaml"
  fi
  if [[ "$CREATED_DWIGHT" == 1 ]]; then
    hermes profile delete "$DWIGHT_PROFILE" --yes >/dev/null 2>&1 || true
  fi
  cleanup
  printf 'Installation annulée ; les mutations du profil principal ont été restaurées.\n' >&2
  exit "$rc"
}

trap rollback ERR INT TERM
trap cleanup EXIT

if [[ -f "$TARGET_HOME/local/onboarding.yaml" ]]; then
  cp -p "$TARGET_HOME/local/onboarding.yaml" "$BACKUP_DIR/onboarding.yaml"
  ONBOARDING_EXISTED=1
fi

# Installer ou mettre à jour Dwight AVANT de modifier le profil principal.
if hermes profile show "$DWIGHT_PROFILE" >/dev/null 2>&1; then
  DWIGHT_CONFIG_BEFORE="$(hermes -p "$DWIGHT_PROFILE" config path)"
  DWIGHT_HOME_BEFORE="$(dirname "$DWIGHT_CONFIG_BEFORE")"
  "$PYTHON_BIN" - "$EXPECTED_DWIGHT_HOME" "$DWIGHT_HOME_BEFORE" <<'PY'
from pathlib import Path
import sys
expected = Path(sys.argv[1]).resolve()
actual = Path(sys.argv[2]).resolve()
if expected != actual:
    raise SystemExit(f"Chemin Dwight incohérent avant update : attendu {expected}, obtenu {actual}")
PY
  DWIGHT_UPDATE_PATH_VERIFIED=1
  [[ -f "$DWIGHT_CONFIG_BEFORE" && ! -L "$DWIGHT_CONFIG_BEFORE" ]] \
    || fail 'configuration Dwight installée absente ou symbolique.'
  if [[ -e "$DWIGHT_HOME_BEFORE/local" ]]; then
    [[ -d "$DWIGHT_HOME_BEFORE/local" && ! -L "$DWIGHT_HOME_BEFORE/local" ]] \
      || fail 'dossier local Dwight non sûr.'
  fi
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
  [[ -d "$MANIFEST_SOURCE" && -d "$DWIGHT_SOURCE" ]] \
    || fail "source Dwight locale introuvable : ${MANIFEST_SOURCE:-absente}."
  MANIFEST_SOURCE_CANON="$(cd "$MANIFEST_SOURCE" && pwd -P)"
  DWIGHT_SOURCE_CANON="$(cd "$DWIGHT_SOURCE" && pwd -P)"
  [[ "$MANIFEST_SOURCE_CANON" == "$DWIGHT_SOURCE_CANON" ]] \
    || fail "collision de source Dwight : ${MANIFEST_SOURCE:-absente}."
  DWIGHT_SOURCE="$DWIGHT_SOURCE_CANON"

  INSTALLED_DWIGHT_VERSION="$("$PYTHON_BIN" - "$MANIFEST" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
print(data.get('version', ''))
PY
)"
  [[ -n "$INSTALLED_DWIGHT_VERSION" ]] || fail 'version Dwight installée absente.'

  SOURCE_DWIGHT_VERSION="$("$PYTHON_BIN" - "$DWIGHT_SOURCE/distribution.yaml" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
print(data.get('version', ''))
PY
)"
  [[ -n "$SOURCE_DWIGHT_VERSION" ]] || fail 'version Dwight source absente.'
  [[ -f "$DWIGHT_HOME_BEFORE/SOUL.md" && ! -L "$DWIGHT_HOME_BEFORE/SOUL.md" ]] \
    || fail 'SOUL Dwight installé absent ou symbolique.'
  [[ -f "$DWIGHT_HOME_BEFORE/distribution.yaml" && ! -L "$DWIGHT_HOME_BEFORE/distribution.yaml" ]] \
    || fail 'manifest Dwight installé absent ou symbolique.'
  [[ -d "$DWIGHT_HOME_BEFORE/skills" && ! -L "$DWIGHT_HOME_BEFORE/skills" ]] \
    || fail 'dossier skills Dwight absent ou symbolique.'

  STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
  mkdir -p "$DWIGHT_HOME_BEFORE/local/migration-backups"
  [[ -d "$DWIGHT_HOME_BEFORE/local/migration-backups" \
      && ! -L "$DWIGHT_HOME_BEFORE/local/migration-backups" ]] \
    || fail 'dossier de backup Dwight non sûr.'
  PREVIOUS_UMASK="$(umask)"
  umask 077
  DWIGHT_UPDATE_BACKUP="$(mktemp -d "$DWIGHT_HOME_BEFORE/local/migration-backups/pre-v${SOURCE_DWIGHT_VERSION}-${STAMP}.XXXXXX")"
  cp -p "$DWIGHT_HOME_BEFORE/SOUL.md" "$DWIGHT_UPDATE_BACKUP/SOUL.md"
  cp -p "$DWIGHT_HOME_BEFORE/distribution.yaml" "$DWIGHT_UPDATE_BACKUP/distribution.yaml"
  cp -p "$DWIGHT_CONFIG_BEFORE" "$DWIGHT_UPDATE_BACKUP/config.yaml"
  cp -Rp "$DWIGHT_HOME_BEFORE/skills" "$DWIGHT_UPDATE_BACKUP/skills"
  chmod 700 "$DWIGHT_UPDATE_BACKUP"
  umask "$PREVIOUS_UMASK"
  DWIGHT_ROLLBACK_BACKUP="$BACKUP_DIR/dwight-profile"
  cp -Rp "$DWIGHT_HOME_BEFORE" "$DWIGHT_ROLLBACK_BACKUP"

  REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)" \
    || fail 'clone Git requis pour vérifier le baseline Dwight avant update.'
  "$PYTHON_BIN" "$SCRIPT_DIR/scripts/dwight_update_guard.py" \
    --repo-root "$REPO_ROOT" \
    --source "$DWIGHT_SOURCE" \
    --installed "$DWIGHT_HOME_BEFORE" \
    --installed-version "$INSTALLED_DWIGHT_VERSION" \
    || fail "fichiers Core Dwight modifiés ; backup conservé dans $DWIGHT_UPDATE_BACKUP."

  CORE_SKILL_NAMES="$("$PYTHON_BIN" - "$DWIGHT_SOURCE/distribution.yaml" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
for path in data.get('distribution_owned') or []:
    parts = str(path).strip('/').split('/')
    if len(parts) >= 2 and parts[0] == 'skills':
        print(parts[1])
PY
)"
  [[ -n "$CORE_SKILL_NAMES" ]] || fail 'aucun skill Core déclaré dans la distribution source.'

  DWIGHT_UPDATE_STARTED=1
  DWIGHT_UPDATE_HOME="$DWIGHT_HOME_BEFORE"
  hermes profile update "$DWIGHT_PROFILE" --yes

  default_tree_is_safe || fail 'arbre default devenu non sûr après update.'
  dwight_root_is_safe || fail 'racine Dwight devenue non sûre après update.'
  [[ -d "$DWIGHT_UPDATE_HOME/skills" && ! -L "$DWIGHT_UPDATE_HOME/skills" ]] \
    || fail 'dossier skills Dwight devenu non sûr après update.'
  for UPDATED_FILE in config.yaml SOUL.md distribution.yaml; do
    [[ -f "$DWIGHT_UPDATE_HOME/$UPDATED_FILE" && ! -L "$DWIGHT_UPDATE_HOME/$UPDATED_FILE" ]] \
      || fail "fichier Dwight devenu non sûr après update : $UPDATED_FILE"
  done
  POST_UPDATE_VERSION="$("$PYTHON_BIN" - "$DWIGHT_UPDATE_HOME/distribution.yaml" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
print(data.get('version', ''))
PY
)"
  [[ "$POST_UPDATE_VERSION" == "$SOURCE_DWIGHT_VERSION" ]] \
    || fail "version Dwight incohérente après update : ${POST_UPDATE_VERSION:-absente}, attendue $SOURCE_DWIGHT_VERSION."

  shopt -s nullglob
  for PRESERVED_SKILL in "$DWIGHT_UPDATE_BACKUP/skills"/*; do
    [[ -d "$PRESERVED_SKILL" && ! -L "$PRESERVED_SKILL" ]] \
      || fail "skill local non sûr dans le backup : $PRESERVED_SKILL"
    PRESERVED_NAME="$(basename "$PRESERVED_SKILL")"
    IS_CORE=0
    while IFS= read -r CORE_NAME; do
      if [[ "$PRESERVED_NAME" == "$CORE_NAME" ]]; then
        IS_CORE=1
        break
      fi
    done <<< "$CORE_SKILL_NAMES"
    if [[ "$IS_CORE" == 0 ]]; then
      rm -rf "$DWIGHT_HOME_BEFORE/skills/$PRESERVED_NAME"
      cp -Rp "$PRESERVED_SKILL" "$DWIGHT_HOME_BEFORE/skills/$PRESERVED_NAME"
    fi
  done
  shopt -u nullglob
else
  hermes profile install "$DWIGHT_SOURCE" --name "$DWIGHT_PROFILE" --alias --yes
  CREATED_DWIGHT=1
fi

DWIGHT_CONFIG="$(hermes -p "$DWIGHT_PROFILE" config path)"
[[ "$DWIGHT_CONFIG" = /* && -f "$DWIGHT_CONFIG" && ! -L "$DWIGHT_CONFIG" ]] \
  || fail "configuration Dwight invalide : $DWIGHT_CONFIG"
DWIGHT_HOME="$(dirname "$DWIGHT_CONFIG")"

"$PYTHON_BIN" - "$EXPECTED_DWIGHT_HOME" "$DWIGHT_HOME" <<'PY'
from pathlib import Path
import sys
expected = Path(sys.argv[1]).resolve()
actual = Path(sys.argv[2]).resolve()
if expected != actual:
    raise SystemExit(f"Chemin Dwight incohérent : attendu {expected}, obtenu {actual}")
PY
DWIGHT_UPDATE_HOME="$DWIGHT_HOME"
DWIGHT_UPDATE_PATH_VERIFIED=1

DWIGHT_MANIFEST="$DWIGHT_HOME/distribution.yaml"
[[ -f "$DWIGHT_MANIFEST" ]] || fail 'manifest Dwight absent après installation.'
DWIGHT_VERSION="$("$PYTHON_BIN" - "$DWIGHT_MANIFEST" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as fh:
    data = yaml.safe_load(fh) or {}
print(data.get('version', 'unknown'))
PY
)"

# Installer le runtime Claude SEO hors des chemins Core Hermes. Cette couche
# possède son propre baseline, bloque toute dérive locale et préserve
# local/claude-seo-data (venv, Chromium, caches et état runtime).
"$PYTHON_BIN" "$SCRIPT_DIR/scripts/install_claude_seo_payload.py" \
  --integration-source "$CLAUDE_SEO_INTEGRATION_SOURCE" \
  --profile-home "$DWIGHT_HOME"

# Adapter uniquement la sélection du modèle au profil default. Ne jamais copier
# les providers, credentials, tokens ou stratégies d’authentification.
"$PYTHON_BIN" - "$DEFAULT_CONFIG" "$DWIGHT_CONFIG" "$DWIGHT_HOME" <<'PY'
import copy
import sys
from urllib.parse import urlsplit

import yaml

src_path, dst_path, dwight_home = sys.argv[1:]
with open(src_path, encoding='utf-8') as fh:
    src = yaml.safe_load(fh) or {}
with open(dst_path, encoding='utf-8') as fh:
    dst = yaml.safe_load(fh) or {}

model = src.get('model')
if isinstance(model, str):
    dst['model'] = model
elif isinstance(model, dict):
    allowed = {'default', 'provider', 'base_url'}
    safe_model = {key: copy.deepcopy(value) for key, value in model.items() if key in allowed}
    for key, value in safe_model.items():
        if not isinstance(value, str):
            raise SystemExit(f"Champ model.{key} non textuel ; copie refusée")
    base_url = safe_model.get('base_url')
    if base_url:
        parsed = urlsplit(base_url)
        if parsed.username is not None or parsed.password is not None:
            raise SystemExit('Credentials intégrés à model.base_url ; copie refusée')
        if parsed.query or parsed.fragment:
            raise SystemExit('Query ou fragment interdit dans model.base_url ; copie refusée')
    if safe_model:
        dst['model'] = safe_model
elif model is not None:
    raise SystemExit('Format model default non pris en charge ; copie refusée')

dst.setdefault('terminal', {})['cwd'] = dwight_home
with open(dst_path, 'w', encoding='utf-8') as fh:
    yaml.safe_dump(dst, fh, allow_unicode=True, sort_keys=False)
PY

# Le profil principal reste la source de vérité du contexte client. Dwight reçoit
# des liens symboliques locaux afin d’éviter deux copies divergentes.
default_tree_is_safe || fail 'arbre default devenu non sûr après update.'
for LOCAL_DIR in "$TARGET_HOME/local" "$DWIGHT_HOME/local"; do
  if [[ -e "$LOCAL_DIR" || -L "$LOCAL_DIR" ]]; then
    [[ -d "$LOCAL_DIR" && ! -L "$LOCAL_DIR" ]] || fail "dossier local non sûr : $LOCAL_DIR"
  fi
done
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
    fail "fichier local existant à fusionner manuellement avant création du lien : $link"
  fi
  ln -s "$canonical" "$link"
  if [[ "$link" == "$DWIGHT_HOME/local/CLIENT.md" ]]; then
    DWIGHT_CLIENT_LINK_CREATED=1
  elif [[ "$link" == "$DWIGHT_HOME/local/onboarding.yaml" ]]; then
    DWIGHT_ONBOARDING_LINK_CREATED=1
  fi
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
  cp -Rp "$TARGET_HOME/skills/client-agent-onboarding" "$BACKUP_DIR/client-agent-onboarding"
  SKILL_EXISTED=1
fi
DEFAULT_MUTATED=1
install -m 600 "$SCRIPT_DIR/SOUL.md" "$TARGET_HOME/SOUL.md"
rm -rf "$TARGET_HOME/skills/client-agent-onboarding"
cp -Rp "$SCRIPT_DIR/skills/client-agent-onboarding" "$TARGET_HOME/skills/client-agent-onboarding"

# Toutes les opérations critiques sont terminées.
DWIGHT_UPDATE_STARTED=0
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
printf 'Runtime Claude SEO : exécuter `cd %s && ./bin/dwight-claude-seo doctor --json`, puis `./bin/dwight-claude-seo setup` si nécessaire.\n' "$DWIGHT_HOME"
printf 'Étape suivante : ouvrir une nouvelle session et vérifier l’accès au modèle depuis Dwight.\n'
