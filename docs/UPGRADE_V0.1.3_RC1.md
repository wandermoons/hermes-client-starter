# Runbook — Dwight v0.1.3-rc1 avec Claude SEO

## Statut

- Release candidate publique pour pilote contrôlé : `v0.1.3-rc1`.
- Distribution interne : `0.1.3`.
- Upstream : `AgriciDaniel/claude-seo` `v2.2.4`, commit `6b63c8bb7b2e8e4480060604555e3af629b54c2c`, licence MIT.
- Cette procédure s'applique uniquement au tag publié et vérifié `v0.1.3-rc1`.
- Ne jamais copier un profil Dwight personnel vers un client.

## Portée

Cette mise à jour ajoute le socle Claude SEO générique :

- 25 méthodologies portées comme skills Hermes ;
- 18 spécialistes Hermes ;
- fan-out/fan-in en six vagues de trois spécialistes maximum ;
- runtime Python/Chromium isolé ;
- validation post-render Schema.org ;
- contrôles d'intégrité du payload et préservation des données runtime.

Elle ne contient ni contexte, mémoire, session, credential, chemin personnel ni procédure propre à un autre client. Le contexte client reste sous `local/CLIENT.md` et les secrets restent dans le mécanisme privé de credentials du VPS.

## Règles absolues

1. Créer un snapshot Hostinger avant la mutation.
2. Exécuter les commandes Hermes comme utilisateur Linux `hermes`, jamais comme `root`.
3. Arrêter si le clone Git n'est pas propre, si un fichier Core a divergé, si un chemin est symbolique ou si des fichiers sont illisibles.
4. Ne jamais utiliser `git reset --hard` pour contourner un échec.
5. Ne jamais lancer directement `hermes profile update dwight` ; utiliser `./install.sh`.
6. Aucune publication, mutation externe ou requête payante pendant la validation.
7. Ne pas redémarrer le VPS dans la même fenêtre de changement : la WebUI historique peut nécessiter un redémarrage manuel distinct.

## 1. Préflight depuis l'hôte VPS — lecture seule

```bash
export HERMES_CONTAINER="<conteneur-hermes>"

docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker exec "$HERMES_CONTAINER" hermes --version
docker exec "$HERMES_CONTAINER" hermes -p default config path

docker exec --user hermes "$HERMES_CONTAINER" bash -lc '
  set -e
  cd /opt/data/hermes-client-starter

  echo "=== DÉPÔT ==="
  git remote get-url origin
  git branch --show-current
  git status --short
  echo "Starter : $(cat VERSION)"

  echo "=== DWIGHT INSTALLÉ ==="
  grep "^version:" /opt/data/profiles/dwight/distribution.yaml

  echo "=== PYTHON ==="
  python3 -c "import sys; print(sys.version); raise SystemExit(0 if sys.version_info >= (3,10) else 1)"

  echo "=== ESPACE ==="
  df -h /opt/data

  echo "=== LISIBILITÉ ==="
  unreadable="$(find /opt/data/profiles/dwight -not -readable -print -quit)"
  test -z "$unreadable" || { echo "Illisible : $unreadable"; exit 1; }
'
```

Critères de passage :

- profil `default` sous `/opt/data/config.yaml` ;
- clone sous `/opt/data/hermes-client-starter` ;
- aucune sortie de `git status --short` ;
- Dwight actuellement en `0.1.2` ou version explicitement auditée ;
- Python `>= 3.10` ;
- au moins 3 Go disponibles pour le runtime, la venv et Chromium ;
- aucun chemin Dwight illisible par `hermes`.

## 2. Snapshot

Créer un snapshot du VPS dans Hostinger. Noter son identifiant et son heure hors du dépôt public. Ne continuer qu'après confirmation de sa disponibilité.

## 3. Récupérer la release — après publication du tag

```bash
docker exec --user hermes -it "$HERMES_CONTAINER" bash -lc '
  set -e
  cd /opt/data/hermes-client-starter
  test -z "$(git status --porcelain)"
  git fetch --tags --prune origin
  git checkout --detach v0.1.3-rc1
  test "$(cat VERSION)" = "0.1.3"
  bash -n install.sh
'
```

Le mode détaché évite de suivre silencieusement une branche plus récente pendant le pilote.

## 4. Installer

```bash
docker exec --user hermes -it "$HERMES_CONTAINER" bash -lc '
  set -e
  cd /opt/data/hermes-client-starter
  ./install.sh
'
```

Marqueurs attendus :

```text
DWIGHT_MANAGED_BASELINE_OK
✓ Updated 'dwight' → v0.1.3
CLAUDE_SEO_PAYLOAD_OK release=v2.2.4 commit=6b63c8bb7b2e8e4480060604555e3af629b54c2c
Installation terminée.
```

L'installateur bloque les dérives et collisions avant écrasement, crée un backup privé sous `profiles/dwight/local/migration-backups/`, installe le payload de façon atomique et restaure automatiquement le profil si une étape critique échoue.

## 5. Initialiser le runtime

Cette étape télécharge et installe environ 1,3 Go de runtime sur l'environnement de référence. La taille réelle du VPS peut varier.

```bash
docker exec --user hermes -it "$HERMES_CONTAINER" bash -lc '
  set -e
  export PATH="/opt/data/profiles/dwight/bin:$PATH"
  dwight-claude-seo doctor --json || true
  dwight-claude-seo setup
  dwight-claude-seo doctor --json
'
```

Critères :

```json
{
  "ready": true,
  "browser_ready": true,
  "plugin_version": "2.2.4",
  "reasons": []
}
```

Si `setup` indique que le cœur est prêt mais que Chromium est indisponible, arrêter la validation de rendu. Ne pas installer de paquets système en root sans diagnostic et validation séparés.

## 6. Vérifications post-installation

```bash
docker exec --user hermes -it "$HERMES_CONTAINER" bash -lc '
  set -e
  export PATH="/opt/data/profiles/dwight/bin:$PATH"

  grep -q "^version: 0.1.3$" /opt/data/profiles/dwight/distribution.yaml
  test "$(readlink /opt/data/profiles/dwight/local/CLIENT.md)" = "/opt/data/local/CLIENT.md"
  test "$(readlink /opt/data/profiles/dwight/local/onboarding.yaml)" = "/opt/data/local/onboarding.yaml"
  test -x /opt/data/profiles/dwight/bin/dwight-claude-seo
  test -x /opt/data/profiles/dwight/bin/dwight-schema-org-hook

  hermes -p dwight chat \
    -q "Réponds uniquement : OK" \
    --toolsets safe \
    --quiet
'
```

Puis, sans appel réseau ni mutation, tester le routage :

```bash
docker exec --user hermes -it "$HERMES_CONTAINER" bash -lc '
  hermes -p dwight \
    -s dwight-seo-core,dwight-claude-seo,dwight-claude-seo-fanout \
    chat --toolsets safe --quiet \
    -q "Résume en cinq lignes la version Claude SEO, les 18 spécialistes, les vagues d audit, la règle de coût et la règle de mutation. N effectue aucune action externe."
'
```

La réponse doit mentionner `2.2.4`, 18 spécialistes, l'orchestration, l'autorisation/budget des appels payants et l'approbation des mutations.

## 7. WebUI

Créer une nouvelle conversation : le SOUL et les skills sont chargés au démarrage d'une session. Demander :

```text
Présente les capacités actuelles de Dwight, l'état des intégrations et les actions qui nécessitent mon approbation. Ne lance aucun audit et ne modifie rien.
```

Ne pas utiliser une ancienne conversation comme preuve de chargement de la nouvelle distribution.

## 8. Rollback

### Échec pendant `./install.sh`

Ne rien forcer. L'installateur restaure automatiquement Dwight et le profil principal. Conserver le message d'erreur et le chemin du backup indiqué.

### Échec après installation réussie

Le rollback privilégié du pilote est la restauration du snapshot Hostinger. Cela restaure ensemble le Core, le runtime, les permissions, l'orchestrateur et le volume persistant.

Si le snapshot n'est pas utilisable, ne pas improviser un `git checkout` suivi de `hermes profile update` : les nouveaux skills pourraient être préservés comme skills locaux. Utiliser le backup `pre-v0.1.3-*` sous supervision, après avoir inventorié les éventuelles écritures faites depuis le déploiement.

## Go / No-Go

**GO** si : snapshot disponible, préflight propre, installation sans erreur, `doctor` prêt avec Chromium, appel modèle `OK`, routage correct et nouvelle session WebUI conforme.

**NO-GO** si : clone modifié, Core divergent, permissions incorrectes, Python trop ancien, espace insuffisant, runtime ou Chromium incomplet, modèle en échec, contexte client absent, ou comportement demandant une mutation/une dépense sans approbation.
