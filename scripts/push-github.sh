#!/usr/bin/env bash
# Push to GitHub over HTTPS using a Personal Access Token (interactive).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

GITHUB_USER="${GITHUB_USER:-vaanni2811}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-main}"

echo "Clearing any cached GitHub HTTPS credentials..."
git credential reject <<EOF 2>/dev/null || true
protocol=https
host=github.com
EOF

echo ""
echo "GitHub push for: https://github.com/${GITHUB_USER}/release-dashboard-tv.git"
echo "Create a token at: https://github.com/settings/tokens (classic, scope: repo)"
echo ""
printf "GitHub username [%s]: " "$GITHUB_USER"
read -r input_user
GITHUB_USER="${input_user:-$GITHUB_USER}"

if [[ ! -t 0 ]]; then
  echo "Error: not a terminal. Run this script in your IDE terminal:" >&2
  echo "  bash scripts/push-github.sh" >&2
  exit 1
fi

printf "GitHub Personal Access Token (input hidden): "
read -rs GITHUB_TOKEN
echo ""

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "Error: empty token." >&2
  exit 1
fi

printf "protocol=https\nhost=github.com\nusername=%s\npassword=%s\n" \
  "$GITHUB_USER" "$GITHUB_TOKEN" | git credential approve

echo "Pushing ${BRANCH} to ${REMOTE}..."
git push -u "$REMOTE" "$BRANCH"

echo "Done."
