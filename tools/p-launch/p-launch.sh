#!/usr/bin/env zsh
# p-launch — launcher (sets up isolated venv, delegates to Python + Textual)

_die() { printf "\033[31merror:\033[0m %s\n" "$*" >&2; exit 1 }

# ── Dependency checks ──────────────────────────────────────────────────────
command -v python3 &>/dev/null \
  || _die "python3 not found — install Python 3.11+ first"

# ── Isolated venv ─────────────────────────────────────────────────────────
VENV="$HOME/.local/share/hskill/p-launch-venv"

if [[ ! -d "$VENV" ]]; then
  printf "\033[2mSetting up p-launch environment (first run)...\033[0m\n" >&2
  python3 -m venv "$VENV" \
    || _die "Failed to create venv at $VENV"
  "$VENV/bin/pip" install textual -q \
    || _die "Failed to install textual — check your network and try again"
  printf "\033[32m✓\033[0m p-launch environment ready\n" >&2
fi

# ── Locate the Python entry point ─────────────────────────────────────────
# Installed path (via hskill installer)
PYFILE="$HOME/.local/share/hskill/tools/p-launch.py"

# Dev fallback: run from source tree alongside this script
if [[ ! -f "$PYFILE" ]]; then
  PYFILE="${0:A:h}/p-launch.py"
fi

[[ -f "$PYFILE" ]] \
  || _die "p-launch.py not found (tried $HOME/.local/share/hskill/tools/p-launch.py) — reinstall p-launch"

exec "$VENV/bin/python" "$PYFILE" "$@"
