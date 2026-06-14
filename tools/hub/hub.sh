#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Auto-detect dev mode: script is running from the source tree
if [ -d "${SCRIPT_DIR}/hub" ] && [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
  DEV_VENV="${SCRIPT_DIR}/.venv"
  if [ ! -x "${DEV_VENV}/bin/hub" ]; then
    python3 -m venv "${DEV_VENV}"
    "${DEV_VENV}/bin/pip" install -q -e "${SCRIPT_DIR}"
  fi
  exec "${DEV_VENV}/bin/hub" "$@"
fi

VENV_DIR="${HOME}/.hskill/tools/hub/venv"
INSTALL_DIR="${HOME}/.hskill/tools/hub"

if [ ! -x "${VENV_DIR}/bin/hub" ]; then
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install -q "${INSTALL_DIR}"
fi

exec "${VENV_DIR}/bin/hub" "$@"
