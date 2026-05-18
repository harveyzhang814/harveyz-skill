#!/usr/bin/env bash
# run-skill-tests.sh
# Discover and run custom tests under skills/.
#
# Patterns discovered:
#   skills/*/*/tests/*.bats  → run with bats
#   skills/*/*/tests/*.py    → run with python3
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

_run_python() {
  local file="$1"
  found=$((found + 1))
  echo "── python3: ${file#"${REPO_ROOT}/"}"
  if python3 "${file}"; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
  fi
}

# Discover skill custom tests (two levels deep: skills/<category>/<skill>/tests/)
while IFS= read -r -d '' bats_file; do
  _run_bats "${bats_file}"
done < <(find "${REPO_ROOT}/skills" -path "*/tests/*.bats" -print0 2>/dev/null | sort -z)

while IFS= read -r -d '' py_file; do
  _run_python "${py_file}"
done < <(find "${REPO_ROOT}/skills" -path "*/tests/*.py" -print0 2>/dev/null | sort -z)

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
