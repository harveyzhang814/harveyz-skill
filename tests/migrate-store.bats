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
  # Without this the script falls back to the real ~/.hskill/sync-xtimeline
  # and the test reads the developer's own data.
  export HSKILL_LEGACY_XTIMELINE="${TEST_DIR}/legacy-xtimeline"
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

_write_legacy_xtimeline() {
  # Old layout with no config.json: products sit in the skill dir itself.
  mkdir -p "${HSKILL_LEGACY_XTIMELINE}/digests" "${HSKILL_LEGACY_XTIMELINE}/tweets"
  echo "old digest" > "${HSKILL_LEGACY_XTIMELINE}/digests/20260817T192449--digest.md"
  echo '[]' > "${HSKILL_LEGACY_XTIMELINE}/tweets/trq212.json"
}

_write_legacy_xtimeline_with_data_dir() {
  # The real old layout: config.json's DATA_DIR points somewhere else
  # entirely (a vault subdir), and that is where the products live.
  LEGACY_DATA="${TEST_DIR}/legacy-vault-twitter"
  mkdir -p "${HSKILL_LEGACY_XTIMELINE}" "${LEGACY_DATA}/digests" "${LEGACY_DATA}/tweets"
  cat > "${HSKILL_LEGACY_XTIMELINE}/config.json" <<CFG
{"DATA_DIR": "${LEGACY_DATA}"}
CFG
  echo "vault digest" > "${LEGACY_DATA}/digests/20260822T064553--digest.md"
  echo '[]' > "${LEGACY_DATA}/tweets/trq212.json"
}

@test "dry-run: hash8 dir with meta.json listed under copied, non-hash dir under skipped" {
  _write_vault_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"
  mkdir -p "${VAULT}/我的笔记"
  echo "hi" > "${VAULT}/我的笔记/note.md"

  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"将复制：deadbeef"* ]]
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

@test "--apply: copies matching hash8 dirs into ROOT/articles, leaves the source in place" {
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
  # Copy, never move: the migration must be reversible by changing config
  # alone, which only holds if the original is still sitting there.
  [ -d "${VAULT}/deadbeef" ]
  [ -f "${VAULT}/deadbeef/meta.json" ]
}

@test "--apply: copies DATA_DIR/tweets and DATA_DIR/youtube into ROOT/feeds" {
  _write_roster_config
  mkdir -p "${DATA_DIR}/tweets/creators" "${DATA_DIR}/youtube/creators"
  echo '[]' > "${DATA_DIR}/tweets/creators/alice.json"

  run bash "$SCRIPT" --apply
  [ "$status" -eq 0 ]
  [ -f "${ROOT}/feeds/tweets/creators/alice.json" ]
  [ -d "${ROOT}/feeds/youtube" ]
  [ -f "${DATA_DIR}/tweets/creators/alice.json" ]
  [ -d "${DATA_DIR}/youtube" ]
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

@test "dry-run: hash8 dir missing meta.json is skipped, hash8 dir with meta.json is copied" {
  _write_vault_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"
  mkdir -p "${VAULT}/abcdef12"
  echo "hi" > "${VAULT}/abcdef12/other.txt"

  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"将复制：deadbeef"* ]]
  [[ "$output" == *"跳过：abcdef12"* ]]
}

@test "--apply: pre-existing destination is left untouched, source left in place" {
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

@test "--apply: Origin/ and Image/ go to articles/_orphans without a meta.json" {
  _write_vault_config
  mkdir -p "${VAULT}/Origin" "${VAULT}/Image"
  echo "orphan article" > "${VAULT}/Origin/old.md"
  echo "orphan image" > "${VAULT}/Image/31e1d2a2_img_1.jpg"

  run bash "$SCRIPT" --apply
  [ "$status" -eq 0 ]
  [ -f "${ROOT}/articles/_orphans/Origin/old.md" ]
  [ -f "${ROOT}/articles/_orphans/Image/31e1d2a2_img_1.jpg" ]
  # No source_url is recoverable for these, so fabricating one would put a
  # lie into the `find -name meta.json` index.
  [ ! -e "${ROOT}/articles/_orphans/Origin/meta.json" ]
  [ ! -e "${ROOT}/articles/_orphans/meta.json" ]
  [ -d "${VAULT}/Origin" ]
  [ -d "${VAULT}/Image" ]
}

@test "--verify: exits non-zero before migration, zero after" {
  _write_vault_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"

  run bash "$SCRIPT" --verify
  [ "$status" -ne 0 ]

  bash "$SCRIPT" --apply
  run bash "$SCRIPT" --verify
  [ "$status" -eq 0 ]
  [[ "$output" == *"全部通过"* ]]
}

@test "--verify: writes nothing" {
  _write_vault_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"

  run bash "$SCRIPT" --verify
  [ ! -e "${ROOT}" ]
}

@test "--verify: a truncated copy fails" {
  _write_roster_config
  mkdir -p "${DATA_DIR}/tweets/creators"
  echo '[{"id": "1"}]' > "${DATA_DIR}/tweets/creators/alice.json"
  bash "$SCRIPT" --apply

  printf '' > "${ROOT}/feeds/tweets/creators/alice.json"

  run bash "$SCRIPT" --verify
  [ "$status" -ne 0 ]
  [[ "$output" == *"比源还小"* ]]
}

@test "--verify: a target that grew past its source passes" {
  # What live use looks like: the skills start appending to the migrated
  # feed archive. Only shrinkage means a broken copy.
  _write_roster_config
  mkdir -p "${DATA_DIR}/tweets/creators"
  echo '[{"id": "1"}]' > "${DATA_DIR}/tweets/creators/alice.json"
  bash "$SCRIPT" --apply

  echo '[{"id": "1"}, {"id": "2"}]' > "${ROOT}/feeds/tweets/creators/alice.json"

  run bash "$SCRIPT" --verify
  [ "$status" -eq 0 ]
  [[ "$output" == *"已比源更大"* ]]
}

@test "unknown flag exits 2" {
  run bash "$SCRIPT" --nope
  [ "$status" -eq 2 ]
}

@test "--apply: legacy sync-xtimeline layout merges into feeds/tweets" {
  _write_legacy_xtimeline

  run bash "$SCRIPT" --apply
  [ "$status" -eq 0 ]
  # digests/ (plural) -> digest/, flat tweets/*.json -> creators/
  [ -f "${ROOT}/feeds/tweets/digest/20260817T192449--digest.md" ]
  [ -f "${ROOT}/feeds/tweets/creators/trq212.json" ]
  [ -f "${HSKILL_LEGACY_XTIMELINE}/digests/20260817T192449--digest.md" ]
}

@test "--apply: legacy source comes from its config.json DATA_DIR, not the skill dir" {
  _write_legacy_xtimeline_with_data_dir

  run bash "$SCRIPT" --apply
  [ "$status" -eq 0 ]
  [[ "$output" == *"${LEGACY_DATA}"* ]]
  [ -f "${ROOT}/feeds/tweets/digest/20260822T064553--digest.md" ]
  [ -f "${ROOT}/feeds/tweets/creators/trq212.json" ]
  [ -f "${LEGACY_DATA}/digests/20260822T064553--digest.md" ]
}
