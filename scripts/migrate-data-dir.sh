#!/usr/bin/env bash
# migrate-data-dir.sh — one-time migration from legacy hskill data paths to $HOME/.hskill/
#
# Run after upgrading hskill to move old data to the new layout:
#   ~/.local/share/hskill/tools/       → ~/.hskill/tools/
#   ~/.local/share/hskill/p-launch-venv/ → (removed; recreated on next p-launch run)
#
# Usage: bash scripts/migrate-data-dir.sh

set -euo pipefail

OLD_TOOLS="$HOME/.local/share/hskill/tools"
NEW_TOOLS="$HOME/.hskill/tools"
OLD_VENV="$HOME/.local/share/hskill/p-launch-venv"

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
info() { printf "\033[2m· %s\033[0m\n"  "$*"; }
warn() { printf "\033[33m⚠\033[0m %s\n" "$*"; }

echo ""
echo "hskill data dir migration"
echo "─────────────────────────"

# ── tools metadata ────────────────────────────────────────────────────────────
if [[ -d "$OLD_TOOLS" && ! -d "$NEW_TOOLS" ]]; then
  mkdir -p "$(dirname "$NEW_TOOLS")"
  mv "$OLD_TOOLS" "$NEW_TOOLS"
  ok "Moved $OLD_TOOLS → $NEW_TOOLS"
elif [[ -d "$OLD_TOOLS" && -d "$NEW_TOOLS" ]]; then
  warn "$NEW_TOOLS already exists — skipping tools migration (remove manually if needed)"
  info "Old: $OLD_TOOLS"
elif [[ ! -d "$OLD_TOOLS" ]]; then
  info "No legacy tools dir found — nothing to migrate"
fi

# ── p-launch venv ─────────────────────────────────────────────────────────────
if [[ -d "$OLD_VENV" ]]; then
  rm -rf "$OLD_VENV"
  ok "Removed legacy venv $OLD_VENV"
  info "p-launch will recreate its venv at \$HOME/.hskill/p-launch/venv on next run"
else
  info "No legacy venv found — nothing to clean up"
fi

# ── cleanup empty parent ──────────────────────────────────────────────────────
OLD_PARENT="$HOME/.local/share/hskill"
if [[ -d "$OLD_PARENT" ]]; then
  remaining=$(find "$OLD_PARENT" -mindepth 1 | head -1)
  if [[ -z "$remaining" ]]; then
    rmdir "$OLD_PARENT"
    ok "Removed empty dir $OLD_PARENT"
  else
    info "$OLD_PARENT not empty — kept (remaining files inside)"
  fi
fi

echo ""
