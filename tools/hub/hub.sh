#!/usr/bin/env bash
set -e

VENV_DIR="${HOME}/.hskill/tools/hub/venv"
INSTALL_DIR="${HOME}/.hskill/tools/hub"

if [ ! -x "${VENV_DIR}/bin/hub" ]; then
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install -q "${INSTALL_DIR}"
fi

exec "${VENV_DIR}/bin/hub" "$@"
