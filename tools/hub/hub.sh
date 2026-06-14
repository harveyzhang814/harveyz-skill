#!/usr/bin/env bash
set -e

# DEV mode: HSKILL_HUB_DEV points to the source repo root (tools/hub/).
# hub runs directly from source via editable install in a dev venv.
if [ -n "${HSKILL_HUB_DEV}" ] && [ -d "${HSKILL_HUB_DEV}" ]; then
  DEV_VENV="${HSKILL_HUB_DEV}/.venv"
  if [ ! -x "${DEV_VENV}/bin/hub" ]; then
    python3 -m venv "${DEV_VENV}"
    "${DEV_VENV}/bin/pip" install -q -e "${HSKILL_HUB_DEV}"
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
