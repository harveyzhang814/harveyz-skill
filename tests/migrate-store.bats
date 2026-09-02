#!/usr/bin/env bats
# Tests for scripts/migrate-store.sh — the one-time migration into the
# unified storage root. Every test runs against a temp fixture, never the
# real ~/.hskill/ configs or a real Obsidian vault.

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/migrate-store.sh"

setup() {
  TEST_DIR="$(mktemp -d)"
  export HSKILL_CONFIG="${TEST_DIR}/hskill-config.json"
  export HSKILL_EXTRACT_URL_CONFIG="${TEST_DIR}/vault-config.json"
  export HSKILL_ROSTER_CONFIG="${TEST_DIR}/roster-config.json"
  ROOT="${TEST_DIR}/knowledge"
  VAULT="${TEST_DIR}/vault"
  DATA_DIR="${TEST_DIR}/roster-data"
  cat > "$HSKILL_CONFIG" <<CFG
{"knowledgeRoot": "${ROOT}"}
CFG
}

teardown() {
  rm -rf "${TEST_DIR}"
}

_write_vault_config() {
  cat > "$HSKILL_EXTRACT_URL_CONFIG" <<CFG
{"VAULT_PATH": "${VAULT}"}
CFG
}

_write_roster_config() {
  cat > "$HSKILL_ROSTER_CONFIG" <<CFG
{"DATA_DIR": "${DATA_DIR}"}
CFG
}

@test "dry-run: hash8 dir with meta.json listed under moved, non-hash dir under skipped" {
  _write_vault_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"
  mkdir -p "${VAULT}/我的笔记"
  echo "hi" > "${VAULT}/我的笔记/note.md"

  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"将搬：deadbeef"* ]]
  [[ "$output" == *"跳过：我的笔记"* ]]
}

@test "dry-run: produces no filesystem side effects" {
  _write_vault_config
  _write_roster_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"
  mkdir -p "${DATA_DIR}/tweets" "${DATA_DIR}/youtube"

  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [ ! -e "${ROOT}" ]
  [ -d "${VAULT}/deadbeef" ]
  [ -d "${DATA_DIR}/tweets" ]
  [ -d "${DATA_DIR}/youtube" ]
}

@test "--apply: moves matching hash8 dirs into ROOT/articles, leaves non-matching alone" {
  _write_vault_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"
  mkdir -p "${VAULT}/我的笔记"
  echo "hi" > "${VAULT}/我的笔记/note.md"

  run bash "$SCRIPT" --apply
  [ "$status" -eq 0 ]
  [ -d "${ROOT}/articles/deadbeef" ]
  [ -f "${ROOT}/articles/deadbeef/meta.json" ]
  [ -d "${VAULT}/我的笔记" ]
  [ ! -e "${VAULT}/deadbeef" ]
}

@test "--apply: moves DATA_DIR/tweets and DATA_DIR/youtube into ROOT/feeds" {
  _write_roster_config
  mkdir -p "${DATA_DIR}/tweets/creators" "${DATA_DIR}/youtube/creators"
  echo '[]' > "${DATA_DIR}/tweets/creators/alice.json"

  run bash "$SCRIPT" --apply
  [ "$status" -eq 0 ]
  [ -f "${ROOT}/feeds/tweets/creators/alice.json" ]
  [ -d "${ROOT}/feeds/youtube" ]
  [ ! -e "${DATA_DIR}/tweets" ]
  [ ! -e "${DATA_DIR}/youtube" ]
}

@test "--apply: rerunning is idempotent" {
  _write_vault_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"

  bash "$SCRIPT" --apply
  run bash "$SCRIPT" --apply
  [ "$status" -eq 0 ]
  [ -d "${ROOT}/articles/deadbeef" ]
}

@test "dry-run: tilde-prefixed knowledgeRoot is expanded, not printed literally" {
  cat > "$HSKILL_CONFIG" <<CFG
{"knowledgeRoot": "~/some-subdir-under-home-that-doesnt-exist-yet"}
CFG

  HOME="${TEST_DIR}" run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" != *'~'* ]]
}

@test "dry-run: hash8 dir missing meta.json is skipped, hash8 dir with meta.json is moved" {
  _write_vault_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"
  mkdir -p "${VAULT}/abcdef12"
  echo "hi" > "${VAULT}/abcdef12/other.txt"

  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"将搬：deadbeef"* ]]
  [[ "$output" == *"跳过：abcdef12"* ]]
}

@test "--apply: pre-existing destination is left untouched, source dir not moved" {
  _write_vault_config
  mkdir -p "${ROOT}/articles/deadbeef"
  echo '{"sentinel": "dest-original"}' > "${ROOT}/articles/deadbeef/meta.json"
  mkdir -p "${VAULT}/deadbeef"
  echo '{"sentinel": "source-new"}' > "${VAULT}/deadbeef/meta.json"

  run bash "$SCRIPT" --apply
  [ "$status" -eq 0 ]
  [[ "$output" == *"跳过：deadbeef（目标已存在：${ROOT}/articles/deadbeef）"* ]]
  [ -d "${VAULT}/deadbeef" ]
  [ -f "${VAULT}/deadbeef/meta.json" ]
  grep -q "source-new" "${VAULT}/deadbeef/meta.json"
  grep -q "dest-original" "${ROOT}/articles/deadbeef/meta.json"
}
