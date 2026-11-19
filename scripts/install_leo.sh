#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEO_SOURCE="${LEO_SOURCE:-$SCRIPT_DIR/distributions/leo}"
LEO_PROFILE="${LEO_PROFILE:-leo}"
CREATING_LEO=0
PROFILES_ROOT_PREEXISTED=0

fail() {
  printf 'Erreur Léo : %s\n' "$1" >&2
  return 1
}

command -v hermes >/dev/null 2>&1 || fail 'la commande hermes est introuvable.'
command -v python3 >/dev/null 2>&1 || fail 'python3 est introuvable.'

safe_real_path() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
if not path.is_absolute():
    raise SystemExit(f"chemin non absolu : {path}")
resolved = path.resolve()
if path != resolved:
    raise SystemExit(f"chemin traversant un lien symbolique : {path}")
print(resolved)
PY
}

manifest_value() {
  python3 - "$1" "$2" <<'PY'
from pathlib import Path
import sys
path, key = Path(sys.argv[1]), sys.argv[2]
lines = path.read_text(encoding="utf-8").splitlines()
for index, raw in enumerate(lines):
    if raw[:1].isspace() or ":" not in raw:
        continue
    candidate, value = raw.split(":", 1)
    if candidate.strip() != key:
        continue
    value = value.split(" #", 1)[0].strip()
    if not value:
        continuation = []
        for following in lines[index + 1:]:
            if not following.strip() or following.lstrip().startswith("#"):
                continue
            if not following[:1].isspace():
                break
            continuation.append(following.strip())
        value = " ".join(continuation)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    if not value:
        raise SystemExit(1)
    print(value)
    raise SystemExit(0)
raise SystemExit(1)
PY
}

[[ "$LEO_PROFILE" =~ ^[a-z0-9][a-z0-9_-]{0,31}$ ]] \
  || fail "nom de profil invalide : $LEO_PROFILE"
[[ -d "$LEO_SOURCE" && ! -L "$LEO_SOURCE" ]] || fail "source absente ou symbolique : $LEO_SOURCE"
LEO_SOURCE="$(safe_real_path "$LEO_SOURCE")" || fail 'source Léo non sûre.'
SOURCE_MANIFEST="$LEO_SOURCE/distribution.yaml"
[[ -f "$SOURCE_MANIFEST" && ! -L "$SOURCE_MANIFEST" ]] || fail 'manifest source absent ou symbolique.'
for required in SOUL.md config.yaml distribution.yaml; do
  [[ -f "$LEO_SOURCE/$required" && ! -L "$LEO_SOURCE/$required" ]] \
    || fail "fichier source requis absent ou symbolique : $required"
done
[[ -d "$LEO_SOURCE/skills" && ! -L "$LEO_SOURCE/skills" ]] || fail 'dossier skills source absent ou symbolique.'

SOURCE_NAME="$(manifest_value "$SOURCE_MANIFEST" name)" || fail 'nom de distribution source absent.'
SOURCE_VERSION="$(manifest_value "$SOURCE_MANIFEST" version)" || fail 'version de distribution source absente.'
[[ "$SOURCE_NAME" == leo ]] || fail "distribution source inattendue : $SOURCE_NAME"
[[ "$SOURCE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "version source invalide : $SOURCE_VERSION"

if [[ -n "${HERMES_HOME:-}" ]]; then
  safe_real_path "$HERMES_HOME" >/dev/null || fail 'HERMES_HOME non sûr.'
fi

DEFAULT_CONFIG="$(hermes -p default config path)"
[[ "$DEFAULT_CONFIG" = /* && -f "$DEFAULT_CONFIG" && ! -L "$DEFAULT_CONFIG" ]] \
  || fail "configuration default invalide : $DEFAULT_CONFIG"
DEFAULT_HOME="$(dirname "$DEFAULT_CONFIG")"
DEFAULT_HOME="$(safe_real_path "$DEFAULT_HOME")" || fail 'racine default non sûre.'
[[ "$DEFAULT_HOME" != / && "$DEFAULT_HOME" != */profiles/* ]] || fail "racine default dangereuse : $DEFAULT_HOME"
PROFILES_ROOT="$DEFAULT_HOME/profiles"
EXPECTED_LEO_HOME="$PROFILES_ROOT/$LEO_PROFILE"
if [[ -e "$PROFILES_ROOT" || -L "$PROFILES_ROOT" ]]; then
  PROFILES_ROOT_PREEXISTED=1
  [[ -d "$PROFILES_ROOT" && ! -L "$PROFILES_ROOT" ]] || fail 'racine profiles non sûre ou symbolique.'
  safe_real_path "$PROFILES_ROOT" >/dev/null || fail 'racine profiles traversant un lien symbolique.'
fi
if [[ -e "$EXPECTED_LEO_HOME" || -L "$EXPECTED_LEO_HOME" ]]; then
  [[ -d "$EXPECTED_LEO_HOME" && ! -L "$EXPECTED_LEO_HOME" ]] || fail 'racine Léo non sûre ou symbolique.'
  safe_real_path "$EXPECTED_LEO_HOME" >/dev/null || fail 'racine Léo traversant un lien symbolique.'
fi

rollback() {
  rc=$?
  trap - ERR INT TERM
  if [[ "$CREATING_LEO" == 1 ]]; then
    hermes profile delete "$LEO_PROFILE" --yes >/dev/null 2>&1 || true
    if [[ -L "$PROFILES_ROOT" ]]; then
      rm -f -- "$PROFILES_ROOT" || true
    elif [[ -d "$PROFILES_ROOT" ]]; then
      python3 - "$PROFILES_ROOT" "$EXPECTED_LEO_HOME" <<'PY' || true
from pathlib import Path
import shutil
import sys

root, target = Path(sys.argv[1]), Path(sys.argv[2])
if root.is_symlink() or root.resolve() != root or target.parent != root:
    raise SystemExit(1)
if target.is_symlink():
    target.unlink()
elif target.exists():
    shutil.rmtree(target)
PY
      if [[ "$PROFILES_ROOT_PREEXISTED" == 0 ]]; then
        rmdir "$PROFILES_ROOT" >/dev/null 2>&1 || true
      fi
    fi
  fi
  printf 'Installation Léo annulée ; aucune connexion Notion ou Instantly n’a été créée.\n' >&2
  exit "$rc"
}
trap rollback ERR INT TERM

if hermes profile show "$LEO_PROFILE" >/dev/null 2>&1; then
  LEO_CONFIG="$(hermes -p "$LEO_PROFILE" config path)"
  [[ "$LEO_CONFIG" = /* && -f "$LEO_CONFIG" && ! -L "$LEO_CONFIG" ]] \
    || fail "configuration Léo invalide : $LEO_CONFIG"
  LEO_HOME="$(dirname "$LEO_CONFIG")"
  LEO_HOME_REAL="$(safe_real_path "$LEO_HOME")" || fail 'racine Léo installée non sûre.'
  [[ "$LEO_HOME_REAL" == "$EXPECTED_LEO_HOME" ]] \
    || fail "collision de profil : attendu $EXPECTED_LEO_HOME, obtenu $LEO_HOME_REAL"
  INSTALLED_MANIFEST="$LEO_HOME/distribution.yaml"
  [[ -f "$INSTALLED_MANIFEST" && ! -L "$INSTALLED_MANIFEST" ]] \
    || fail "collision : le profil $LEO_PROFILE n’est pas une distribution Léo."
  INSTALLED_NAME="$(manifest_value "$INSTALLED_MANIFEST" name)" || fail 'nom installé absent.'
  INSTALLED_VERSION="$(manifest_value "$INSTALLED_MANIFEST" version)" || fail 'version installée absente.'
  INSTALLED_SOURCE="$(manifest_value "$INSTALLED_MANIFEST" source)" || fail 'source installée absente.'
  [[ "$INSTALLED_NAME" == leo ]] || fail "collision de distribution : $INSTALLED_NAME"
  [[ -d "$INSTALLED_SOURCE" && ! -L "$INSTALLED_SOURCE" ]] || fail "source installée introuvable : $INSTALLED_SOURCE"
  INSTALLED_SOURCE="$(safe_real_path "$INSTALLED_SOURCE")" || fail 'source installée non sûre.'
  [[ "$INSTALLED_SOURCE" == "$LEO_SOURCE" ]] || fail "collision de source : $INSTALLED_SOURCE"
  [[ "$INSTALLED_VERSION" == "$SOURCE_VERSION" ]] \
    || fail "update refused: installed v$INSTALLED_VERSION, source v$SOURCE_VERSION. Use a reviewed migration before updating Léo."
  printf 'Léo v%s is already installed from the expected source.\n' "$INSTALLED_VERSION"
else
  CREATING_LEO=1
  hermes profile install "$LEO_SOURCE" --name "$LEO_PROFILE" --alias --yes
fi

LEO_CONFIG="$(hermes -p "$LEO_PROFILE" config path)"
[[ "$LEO_CONFIG" = /* && -f "$LEO_CONFIG" && ! -L "$LEO_CONFIG" ]] \
  || fail "configuration Léo absente après installation : $LEO_CONFIG"
LEO_HOME="$(dirname "$LEO_CONFIG")"
LEO_HOME_REAL="$(safe_real_path "$LEO_HOME")" || fail 'racine Léo finale non sûre.'
[[ "$LEO_HOME_REAL" == "$EXPECTED_LEO_HOME" ]] \
  || fail "chemin Léo final incohérent : $LEO_HOME_REAL"
for required in SOUL.md config.yaml distribution.yaml; do
  [[ -f "$LEO_HOME/$required" && ! -L "$LEO_HOME/$required" ]] \
    || fail "fichier Léo installé absent ou symbolique : $required"
done
[[ -d "$LEO_HOME/skills" && ! -L "$LEO_HOME/skills" ]] || fail 'skills Léo installés absents ou symboliques.'

CREATING_LEO=0
trap - ERR INT TERM
printf '\nInstallation Léo terminée.\n'
printf 'Profil : %s\n' "$LEO_HOME"
printf 'Distribution : v%s\n' "$SOURCE_VERSION"
printf 'Connexions : aucune ; Notion et Instantly restent à configurer séparément pendant l’onboarding.\n'
printf 'Étape suivante : ouvrir une nouvelle session Léo et commencer par le skill leo-onboarding.\n'
