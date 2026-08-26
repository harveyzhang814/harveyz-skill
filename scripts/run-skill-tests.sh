#!/usr/bin/env bash
# run-skill-tests.sh
# Discover and run custom tests under skills/.
#
# Patterns discovered:
#   skills/*/*/tests/*.bats  → run with bats
#   skills/*/*/tests/ 与 tools/*/tests/ → 用 pytest 按目录运行
#
# */archived/* 整体排除（bats 与 pytest 两条扫描都排除）：archived 下的代码
# 已退役，不在 shipping 集合里（例如 tools/archived/todo-tool 不在
# skills-index.json 注册，且带一个没人维护的真实语法错误）。让已退役代码
# 挡住 npm test 没有意义，所以在发现阶段就直接排除，不是「跑了但放过」。
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

# 每个 tool/skill 目录优先用自己的 .venv 解释器（若存在），否则退回系统
# python3。原因：工具会用 uv/venv 钉住自己的依赖版本，这些版本可能与系统
# site-packages 不兼容（实例：tools/browser-fetch-mcp 的 mcp SDK 版本与系统
# python3 装的 mcp 不兼容，直接用系统 python3 跑会得到一堆和代码无关的
# ImportError；用它自己的 .venv 跑是 124 passed 全绿）。优先用 .venv 能让
# 这类套件按其真实状态被评估，而不是被解释器不匹配误报成失败。
_run_pytest_dir() {
  local dir="$1"
  local tool_dir
  tool_dir="$(dirname "${dir}")"
  local rel="${tool_dir#"${REPO_ROOT}/"}"
  local python_bin="python3"
  local label=""
  if [ -x "${tool_dir}/.venv/bin/python" ]; then
    python_bin="${tool_dir}/.venv/bin/python"
    label=" (.venv)"
  fi
  found=$((found + 1))
  echo "── pytest: ${rel}${label}"
  if (cd "${tool_dir}" && "${python_bin}" -m pytest tests/ -q); then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
  fi
}

# Discover skill custom tests (two levels deep: skills/<category>/<skill>/tests/)
while IFS= read -r -d '' bats_file; do
  _run_bats "${bats_file}"
done < <(find "${REPO_ROOT}/skills" -path "*/tests/*.bats" \
           -not -path "*/archived/*" \
           -print0 2>/dev/null | sort -z)

# skills/<category>/<skill>/tests/ 与 tools/<tool>/tests/，任一含 test_*.py 即视为 pytest 套件
while IFS= read -r -d '' tests_dir; do
  if compgen -G "${tests_dir}/test_*.py" > /dev/null; then
    _run_pytest_dir "${tests_dir}"
  fi
done < <(find "${REPO_ROOT}/skills" "${REPO_ROOT}/tools" \
           -type d -name tests \
           -not -path "*/.venv/*" -not -path "*/node_modules/*" \
           -not -path "*/archived/*" \
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
