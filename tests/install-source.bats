#!/usr/bin/env bats
# Tests for lib/install-source.js and the source-tracking `update` / `version` flows.
# See docs/superpowers/specs/2026-09-15-hskill-install-source-design.md
# Requires: bats-core (brew install bats-core)

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
CLI="${REPO_ROOT}/bin/cli.js"

setup() {
  TEST_DIR="$(mktemp -d)"
  GLOBAL_ROOT="${TEST_DIR}/global"
  mkdir -p "${GLOBAL_ROOT}/harveyz-skill"
  printf '{"name":"harveyz-skill","version":"1.0.0"}\n' > "${GLOBAL_ROOT}/harveyz-skill/package.json"

  NPM_LOG="${TEST_DIR}/npm.log"
  MOCK_BIN="${TEST_DIR}/bin"
  mkdir -p "${MOCK_BIN}"
  cp "${BATS_TEST_DIRNAME}/helpers/mock-npm.sh" "${MOCK_BIN}/npm"
  chmod +x "${MOCK_BIN}/npm"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

_make_repo() {
  local repo="$1"
  mkdir -p "$repo"
  (cd "$repo" \
    && git init -q -b main \
    && git config user.email t@t.com \
    && git config user.name t \
    && printf '{"name":"harveyz-skill","version":"9.9.9"}\n' > package.json \
    && git add package.json \
    && git commit -q -m init)
}

_write_source() {
  local repo="$1" branch="$2" commit="$3" dirty="$4"
  cat > "${GLOBAL_ROOT}/harveyz-skill/.hskill-source.json" <<EOF
{"repo":"${repo}","branch":"${branch}","commit":"${commit}","dirty":${dirty},"version":"9.9.9","installedAt":"2020-01-01T00:00:00Z"}
EOF
}

# ── readSource() ──────────────────────────────────────────────────────────────

@test "readSource: missing file returns null" {
  run env HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" node --input-type=module -e "
import { readSource } from '${REPO_ROOT}/lib/install-source.js'
console.log(JSON.stringify(readSource()))
"
  [ "$status" -eq 0 ]
  [ "$output" = "null" ]
}

@test "readSource: corrupt JSON returns null without throwing" {
  echo '{ not json' > "${GLOBAL_ROOT}/harveyz-skill/.hskill-source.json"
  run env HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" node --input-type=module -e "
import { readSource } from '${REPO_ROOT}/lib/install-source.js'
console.log(JSON.stringify(readSource()))
"
  [ "$status" -eq 0 ]
  [ "$output" = "null" ]
}

# ── update sticky branching ───────────────────────────────────────────────────

@test "update: no trace file installs from npm" {
  run env HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" HSKILL_TEST_NPM_LOG="${NPM_LOG}" PATH="${MOCK_BIN}:${PATH}" \
    node "${CLI}" update
  [ "$status" -eq 0 ]
  grep -q "install -g harveyz-skill@latest" "${NPM_LOG}"
  ! grep -q "pack" "${NPM_LOG}"
}

@test "update: trace file present installs from the recorded local repo" {
  local repo="${TEST_DIR}/repo"
  _make_repo "$repo"
  local commit
  commit="$(cd "$repo" && git rev-parse --short HEAD)"
  _write_source "$repo" main "$commit" false

  run env HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" HSKILL_TEST_NPM_LOG="${NPM_LOG}" PATH="${MOCK_BIN}:${PATH}" \
    node "${CLI}" update
  [ "$status" -eq 0 ]
  grep -q "pack --pack-destination" "${NPM_LOG}"
  ! grep -q "harveyz-skill@latest" "${NPM_LOG}"
  grep -q "\"repo\": \"${repo}\"" "${GLOBAL_ROOT}/harveyz-skill/.hskill-source.json"
  grep -q '"version": "9.9.9+local"' "${GLOBAL_ROOT}/harveyz-skill/package.json"
}

# ── flag misuse ────────────────────────────────────────────────────────────────

@test "update --local and --npm together errors" {
  run env HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" node "${CLI}" update --local /tmp/does-not-matter --npm
  [ "$status" -eq 1 ]
  [[ "$output" == *"mutually exclusive"* ]]
}

@test "update --local without a path errors" {
  run env HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" node "${CLI}" update --local
  [ "$status" -eq 1 ]
  [[ "$output" == *"requires a path"* ]]
}

# ── repo.info invalidated ─────────────────────────────────────────────────────

@test "update --local: nonexistent repo exits non-zero without invoking npm" {
  run env HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" HSKILL_TEST_NPM_LOG="${NPM_LOG}" PATH="${MOCK_BIN}:${PATH}" \
    node "${CLI}" update --local "${TEST_DIR}/does-not-exist"
  [ "$status" -eq 1 ]
  [[ "$output" == *"不存在"* ]]
  [ ! -f "${NPM_LOG}" ]
}

# ── compareVersions build metadata ────────────────────────────────────────────

@test "compareVersions: +local build metadata does not affect ordering" {
  run node --input-type=module -e "
import { compareVersions } from '${REPO_ROOT}/lib/version-check.js'
console.log(compareVersions('0.33.0+local', '0.33.0') === 0)
console.log(compareVersions('0.33.0+local', '0.34.0') < 0)
console.log(compareVersions('0.33.0+local', '0.32.0') > 0)
"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | sed -n '1p')" = "true" ]
  [ "$(echo "$output" | sed -n '2p')" = "true" ]
  [ "$(echo "$output" | sed -n '3p')" = "true" ]
}

# ── version --check: local branch ─────────────────────────────────────────────

@test "version --check: local source, commit matches and clean reports up to date" {
  local repo="${TEST_DIR}/repo"
  _make_repo "$repo"
  local commit
  commit="$(cd "$repo" && git rev-parse --short HEAD)"
  _write_source "$repo" main "$commit" false

  run env HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" node "${CLI}" version --check
  [ "$status" -eq 0 ]
  [[ "$output" == *"up to date"* ]]
}

@test "version --check: local source, new commits reports outdated" {
  local repo="${TEST_DIR}/repo"
  _make_repo "$repo"
  local old_commit
  old_commit="$(cd "$repo" && git rev-parse --short HEAD)"
  (cd "$repo" && echo more >> package.json && git commit -qam more)
  _write_source "$repo" main "$old_commit" false

  run env HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" node "${CLI}" version --check
  [ "$status" -eq 0 ]
  [[ "$output" == *"new commits"* ]]
}

@test "version --check: local source, same commit but dirty reports uncommitted changes" {
  local repo="${TEST_DIR}/repo"
  _make_repo "$repo"
  local commit
  commit="$(cd "$repo" && git rev-parse --short HEAD)"
  echo dirty > "${repo}/untracked.txt"
  _write_source "$repo" main "$commit" false

  run env HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" node "${CLI}" version --check
  [ "$status" -eq 0 ]
  [[ "$output" == *"uncommitted changes"* ]]
}

# ── version output: npm source unchanged ──────────────────────────────────────

@test "version: npm source output is unchanged (single line, no source lines)" {
  local expected
  expected="$(node -e "console.log(require('${REPO_ROOT}/package.json').version)")"

  run env HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" node "${CLI}" version
  [ "$status" -eq 0 ]
  [ "$output" = "$expected" ]
}
