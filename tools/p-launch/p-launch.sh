#!/usr/bin/env zsh
# p-launch — launcher (checks deps, delegates to Python + Textual)

_die() { printf "\033[31merror:\033[0m %s\n" "$*" >&2; exit 1 }

# ── Dependency checks ──────────────────────────────────────────────────────
command -v python3 &>/dev/null \
  || _die "python3 not found — install Python 3.11+ first"

python3 -c "import textual" 2>/dev/null \
  || _die "textual not installed — fix with: pip install textual"

# ── Locate the Python entry point ─────────────────────────────────────────
# Installed path (via hskill installer)
PYFILE="$HOME/.local/share/hskill/tools/p-launch.py"

# Dev fallback: run from source tree alongside this script
if [[ ! -f "$PYFILE" ]]; then
  PYFILE="${0:A:h}/p-launch.py"
fi

[[ -f "$PYFILE" ]] \
  || _die "p-launch.py not found (tried $HOME/.local/share/hskill/tools/p-launch.py) — reinstall p-launch"

exec python3 "$PYFILE" "$@"
