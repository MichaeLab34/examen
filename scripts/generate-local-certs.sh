#!/usr/bin/env bash
#
# Génère les certificats TLS de développement attendus par Caddy.
#
# Pourquoi ce script existe : le `Caddyfile` exige des certificats explicites
# (`tls /etc/caddy/certs/localhost.crt ...`) que le `compose.yaml` monte depuis
# `./caddy-certs`. Ce répertoire est volontairement absent du dépôt — une clé
# privée ne se versionne pas (`.gitignore`). Sans ce script, un clone frais
# produit un Caddy qui refuse de démarrer sur :
#
#     Error: loading initial config: ... open /etc/caddy/certs/localhost.crt:
#     no such file or directory
#
# Usage :
#   bash scripts/generate-local-certs.sh            # ne fait rien si déjà présents
#   bash scripts/generate-local-certs.sh --force    # régénère
#
# Fonctionne sur macOS, Linux et Windows (Git Bash).
#
# ATTENTION : certificat auto-signé, réservé au développement local. Une mise en
# service réelle utilise un certificat émis par une autorité reconnue — Caddy
# sait l'obtenir automatiquement via ACME dès que le domaine est public.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="${REPO_ROOT}/caddy-certs"
CRT="${CERT_DIR}/localhost.crt"
KEY="${CERT_DIR}/localhost.key"

# 825 jours : limite au-delà de laquelle les navigateurs rejettent un certificat.
VALIDITY_DAYS=825
SUBJECT="/CN=localhost/O=Decrochage L1 (developpement local)"
# `api` et `mlflow` sont les noms de service du réseau Compose, joignables depuis
# les autres conteneurs.
SAN="subjectAltName=DNS:localhost,DNS:api,DNS:mlflow,IP:127.0.0.1"

usage() {
  sed -n '3,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Argument inconnu : $arg (utiliser --force ou --help)" >&2
      exit 2
      ;;
  esac
done

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl est introuvable." >&2
  echo "  macOS   : préinstallé, sinon 'brew install openssl'" >&2
  echo "  Linux   : 'apt install openssl' ou équivalent" >&2
  echo "  Windows : fourni avec Git for Windows (lancer depuis Git Bash)" >&2
  exit 1
fi

if [[ -f "$CRT" && -f "$KEY" && "$FORCE" -eq 0 ]]; then
  echo "Certificats déjà présents, rien à faire :"
  echo "  $CRT"
  echo "  $KEY"
  openssl x509 -in "$CRT" -noout -subject -dates 2>/dev/null | sed 's/^/  /' || true
  echo
  echo "Utiliser --force pour les régénérer (par exemple s'ils sont expirés)."
  exit 0
fi

mkdir -p "$CERT_DIR"

echo "Génération d'une paire auto-signée pour le développement local..."

# Sur Git Bash, MSYS convertit tout argument ressemblant à un chemin Unix en
# chemin Windows. Il faut l'empêcher pour `-subj` (`/CN=...` n'est pas un
# chemin) **sans** désactiver la conversion globalement : l'openssl de Git for
# Windows est un binaire natif qui ne sait pas lire `/c/Users/...` et échouerait
# sur « Can't open ... for writing, No such file or directory ».
# `MSYS2_ARG_CONV_EXCL` cible le seul argument concerné, et la variable est
# simplement ignorée sur macOS et Linux.
MSYS2_ARG_CONV_EXCL='/CN=' openssl req -x509 \
  -newkey rsa:2048 \
  -sha256 \
  -days "$VALIDITY_DAYS" \
  -nodes \
  -keyout "$KEY" \
  -out "$CRT" \
  -subj "$SUBJECT" \
  -addext "$SAN" \
  2>/dev/null

# Ne pas se contenter du code de sortie : openssl peut échouer en écriture tout
# en laissant un fichier partiel, et un certificat vide ferait échouer Caddy
# bien plus loin, avec un message beaucoup moins clair.
if [[ ! -s "$CRT" || ! -s "$KEY" ]]; then
  echo "Échec : les fichiers attendus n'ont pas été produits." >&2
  echo "  $CRT" >&2
  echo "  $KEY" >&2
  exit 1
fi
if ! openssl x509 -in "$CRT" -noout >/dev/null 2>&1; then
  echo "Échec : $CRT n'est pas un certificat X.509 valide." >&2
  exit 1
fi

# Sans effet sur Windows, mais correct sur macOS et Linux.
chmod 600 "$KEY" 2>/dev/null || true
chmod 644 "$CRT" 2>/dev/null || true

echo "Terminé :"
echo "  $CRT"
echo "  $KEY"
openssl x509 -in "$CRT" -noout -subject -dates -ext subjectAltName 2>/dev/null | sed 's/^/  /' || true
echo
echo "Ces fichiers sont ignorés par git (.gitignore : caddy-certs/) et ne doivent"
echo "jamais être committés ni partagés."
echo
echo "Lancer ensuite la pile complète :"
echo "  docker compose --profile run up -d"
echo
echo "Le navigateur signalera un certificat non approuvé : c'est attendu pour un"
echo "certificat auto-signé. Accepter l'exception une fois, de préférence avant"
echo "une démonstration en direct."
