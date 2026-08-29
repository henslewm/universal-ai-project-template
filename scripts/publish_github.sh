#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-henslewm}"
REPO="${2:-$(basename "$PWD")}"
VISIBILITY="${3:-private}"

gh auth status
gh repo create "$OWNER/$REPO" "--$VISIBILITY" --source . --remote origin --push
