#!/usr/bin/env bats
# End-to-end tests for `hskill version --check`.
# Requires: bats-core (brew install bats-core)

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
CLI="${REPO_ROOT}/bin/cli.js"

setup() {
  TEST_DIR="$(mktemp -d)"
  STDERR_FILE="${TEST_DIR}/stderr"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

@test "version --check: unreachable registry exits non-zero with an error on stderr" {
  run env HSKILL_NPM_REGISTRY="http://127.0.0.1:1" node "${CLI}" version --check
  [ "$status" -eq 1 ]
  [[ "$output" == *"Could not check npm registry"* ]]
}
