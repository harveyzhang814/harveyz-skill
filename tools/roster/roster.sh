#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# venv 必须由满足 pyproject requires-python (>=3.11) 的解释器创建。macOS 自带的
# python3 是 3.9，PATH 上它排在 homebrew 前面时建出的 venv 装不上任何包；而
# `python3 -m venv` 不带 --clear 不会替换已存在的解释器，坏 venv 永远修不好。
# --clear 保证可恢复，前置校验保证第一次就报对。
_require_python() {
  if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    echo "roster: 需要 Python >= 3.11，当前是 $(python3 -V 2>&1)（$(command -v python3)）" >&2
    exit 1
  fi
}

# Auto-detect dev mode: script is running from the source tree
if [ -d "${SCRIPT_DIR}/roster" ] && [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
  DEV_VENV="${SCRIPT_DIR}/.venv"
  if [ ! -x "${DEV_VENV}/bin/roster" ]; then
    _require_python
    python3 -m venv --clear "${DEV_VENV}" >&2
    "${DEV_VENV}/bin/pip" install -q -e "${SCRIPT_DIR}" >&2
  fi
  exec "${DEV_VENV}/bin/roster" "$@"
fi

VENV_DIR="${HOME}/.hskill/tools/roster/venv"
INSTALL_DIR="${HOME}/.hskill/tools/roster"
HASH_FILE="${VENV_DIR}/.installed_hash"

_hash_source() {
  find "${INSTALL_DIR}" -type f \( -name "*.py" -o -name "*.toml" -o -name "*.json" \) \
    ! -path "*/__pycache__/*" ! -path "*/venv/*" \
    | sort | xargs sha256sum 2>/dev/null | sha256sum | awk '{print $1}'
}

CURRENT_HASH=$(_hash_source)

if [ ! -x "${VENV_DIR}/bin/roster" ] || [ "$(cat "${HASH_FILE}" 2>/dev/null)" != "${CURRENT_HASH}" ]; then
  _require_python
  python3 -m venv --clear "${VENV_DIR}" >&2
  "${VENV_DIR}/bin/pip" install -q --upgrade "${INSTALL_DIR}" >&2
  echo "${CURRENT_HASH}" > "${HASH_FILE}"
fi

exec "${VENV_DIR}/bin/roster" "$@"
