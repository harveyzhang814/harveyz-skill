#!/usr/bin/env zsh
# todo-tool — task manager CLI (sets up isolated venv, delegates to `todo`)

_die() { printf "\033[31merror:\033[0m %s\n" "$*" >&2; exit 1 }

# ── Dependency checks ──────────────────────────────────────────────────────
command -v python3 &>/dev/null \
  || _die "python3 not found — install Python 3.11+ first"

# ── Isolated venv ─────────────────────────────────────────────────────────
VENV="$HOME/.hskill/todo-tool/venv"
PKG="$HOME/.hskill/tools/todo-tool"

if [[ ! -d "$VENV" ]]; then
  printf "\033[2mSetting up todo environment (first run)...\033[0m\n" >&2
  python3 -m venv "$VENV" \
    || _die "Failed to create venv at $VENV"
  "$VENV/bin/pip" install -q -e "$PKG" \
    || _die "Failed to install todo-tool — check your network and try again"
  printf "\033[32m✓\033[0m todo environment ready\n" >&2
fi

exec "$VENV/bin/todo" "$@"
