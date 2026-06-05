#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_SRC="$ROOT/colab-cli"

install_copy() {
  local dest="$1"
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  cp -a "$SKILL_SRC" "$dest"
}

install_copy "${CODEX_HOME:-$HOME/.codex}/skills/colab-cli"
install_copy "$HOME/.agents/skills/colab-cli"

if [ -d "$HOME/.config/opencode" ]; then
  install_copy "$HOME/.config/opencode/skills/colab-cli"
fi

if [ -d "$HOME/.hermes" ]; then
  install_copy "$HOME/.hermes/skills/data-science/colab-cli"
fi

echo "Installed colab-cli skill for Codex, shared agent skills, opencode, and Hermes where present."
