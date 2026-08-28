#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 一次性数据目录迁移：browser-fetch-mcp -> browser-fetch。
# contexts/ 下是 Playwright persistent context，站点登录态实际落盘在这里；
# 不迁移的表现是静默退回未登录，不报错。新目录已存在时不动老目录。
_migrate_data_dir() {
  local old="${HOME}/.hskill/browser-fetch-mcp"
  local new="${HOME}/.hskill/browser-fetch"
  if [ -d "${old}" ] && [ ! -d "${new}" ]; then
    mv "${old}" "${new}"
    echo "browser-fetch: 已迁移数据目录 ${old} -> ${new}" >&2
  fi
}

_migrate_data_dir

# 测试钩子：只跑迁移，不进安装分支
if [ "$1" = "--migrate-only" ]; then
  return 0 2>/dev/null || exit 0
fi

# venv 必须由满足 pyproject requires-python (>=3.11) 的解释器创建。macOS 自带的
# python3 是 3.9，PATH 上它排在 homebrew 前面时建出的 venv 装不上任何包；而
# `python3 -m venv` 不带 --clear 不会替换已存在的解释器，坏 venv 永远修不好，
# 且后续报错是 "No module named playwright"，指不到真原因。
# --clear 保证可恢复，前置校验保证第一次就报对。
_require_python() {
  if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    echo "browser-fetch: 需要 Python >= 3.11，当前是 $(python3 -V 2>&1)（$(command -v python3)）" >&2
    exit 1
  fi
}

# Dev 模式：从源码树运行
if [ -d "${SCRIPT_DIR}/browser_fetch" ] && [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
  DEV_VENV="${SCRIPT_DIR}/.venv"
  if [ ! -x "${DEV_VENV}/bin/browser-fetch" ]; then
    _require_python
    python3 -m venv --clear "${DEV_VENV}" >&2
    "${DEV_VENV}/bin/pip" install -q -e "${SCRIPT_DIR}" >&2
    "${DEV_VENV}/bin/python3" -m playwright install chromium >&2
  fi
  exec "${DEV_VENV}/bin/browser-fetch" "$@"
fi

VENV_DIR="${HOME}/.hskill/tools/browser-fetch/venv"
INSTALL_DIR="${HOME}/.hskill/tools/browser-fetch"
HASH_FILE="${VENV_DIR}/.installed_hash"

_hash_source() {
  find "${INSTALL_DIR}" -type f \( -name "*.py" -o -name "*.toml" -o -name "*.json" \) \
    ! -path "*/__pycache__/*" ! -path "*/venv/*" \
    | sort | xargs sha256sum 2>/dev/null | sha256sum | awk '{print $1}'
}

CURRENT_HASH=$(_hash_source)

if [ ! -x "${VENV_DIR}/bin/browser-fetch" ] || [ "$(cat "${HASH_FILE}" 2>/dev/null)" != "${CURRENT_HASH}" ]; then
  _require_python
  python3 -m venv --clear "${VENV_DIR}" >&2
  "${VENV_DIR}/bin/pip" install -q --upgrade "${INSTALL_DIR}" >&2
  "${VENV_DIR}/bin/python3" -m playwright install chromium >&2
  echo "${CURRENT_HASH}" > "${HASH_FILE}"
fi

exec "${VENV_DIR}/bin/browser-fetch" "$@"
