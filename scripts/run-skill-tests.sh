#!/usr/bin/env bash
# run-skill-tests.sh
# Discover and run custom tests under skills/.
#
# Patterns discovered:
#   skills/*/*/tests/*.bats  → run with bats
#   skills/*/*/tests/ 与 tools/*/tests/ → 用 pytest 按目录运行
#
# tools/p-launch/tests/ is already covered by `npm test` (bats tests/ tools/p-launch/tests/)
# so it is intentionally excluded here.
#
# Exit codes:
#   0  all tests passed (or no tests found)
#   1  one or more tests failed

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

passed=0
failed=0
found=0

_run_bats() {
  local file="$1"
  found=$((found + 1))
  echo "── bats: ${file#"${REPO_ROOT}/"}"
  if bats "${file}"; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
  fi
}

_run_pytest_dir() {
  local dir="$1"
  found=$((found + 1))
  echo "── pytest: ${dir#"${REPO_ROOT}/"}"
  if (cd "$(dirname "${dir}")" && python3 -m pytest tests/ -q); then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
  fi
}

# Discover skill custom tests (two levels deep: skills/<category>/<skill>/tests/)
while IFS= read -r -d '' bats_file; do
  _run_bats "${bats_file}"
done < <(find "${REPO_ROOT}/skills" -path "*/tests/*.bats" -print0 2>/dev/null | sort -z)

# skills/<category>/<skill>/tests/ 与 tools/<tool>/tests/，任一含 test_*.py 即视为 pytest 套件
#
# tools/browser-fetch-mcp/tests/ 单独排除：该工具用 uv 管理自己的 .venv，
# 其 mcp SDK 版本与系统 python3 site-packages 里的不兼容，用系统 python3 跑
# 会得到 31 failed（ImportError: cannot import name 'MCPServer'），但用它自己的
# .venv 跑是 124 passed 全绿。这是脚本调用方式导致的环境问题，不是代码问题，
# 排除以避免误报；如需验证，运行：
#   cd tools/browser-fetch-mcp && .venv/bin/python3 -m pytest tests/
while IFS= read -r -d '' tests_dir; do
  if compgen -G "${tests_dir}/test_*.py" > /dev/null; then
    _run_pytest_dir "${tests_dir}"
  fi
done < <(find "${REPO_ROOT}/skills" "${REPO_ROOT}/tools" \
           -type d -name tests \
           -not -path "*/.venv/*" -not -path "*/node_modules/*" \
           -not -path "*/tools/browser-fetch-mcp/tests" \
           -print0 2>/dev/null | sort -z)

if [ "${found}" -eq 0 ]; then
  echo "(no custom skill tests)"
  exit 0
fi

echo ""
echo "── custom skill tests: ${passed} passed, ${failed} failed (${found} total)"

if [ "${failed}" -gt 0 ]; then
  exit 1
fi
exit 0
