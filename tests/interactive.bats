#!/usr/bin/env bats
# Tests for hskill interactive mode (TTY / fzf flow).
#
# ## How interactive testing works
#
# hskill's interactive mode requires a TTY (isTTY check) and uses fzf for all
# prompts. Real TTYs are unavailable in CI, so we use two mechanisms:
#
#   1. HSKILL_TEST_INTERACTIVE=1  — env var that bypasses the process.stdout.isTTY
#      guard in cli.js, letting the interactive loop run without a real TTY.
#
#   2. Mock fzf (tests/helpers/mock-fzf.sh) — placed first on PATH so all
#      `spawnSync('fzf', ...)` calls hit the mock instead of the real binary.
#      The mock reads responses from HSKILL_FZF_RESPONSES_FILE one per call,
#      and tracks progress in HSKILL_FZF_COUNTER_FILE.
#      --version probes (requireFzf) are intercepted and do NOT count.
#
# ## fzf call order for interactive install
#
# Skill-only selection (one full install round):
#   Call 1  skill selector   → tab-separated line (see _skill_line helper)
#   Call 2  scope selector   → "user ..." or "project ..."
#   Call 3  target selector  → "claude ..." (first word = target name)
#   Call N  (loop-back)      → empty line = Esc → loop exits
#
# Tool-only selection (no scope/target step):
#   Call 1  skill selector   → tool line (see _tool_line helper)
#   Call 2  (loop-back)      → empty = Esc → loop exits
#
# Mixed skill+tool in one round:
#   Call 1  skill selector   → skill<NL>tool lines
#   Call 2  scope selector   → "user ..."
#   Call 3  target selector  → "claude ..."
#   Call 4  (loop-back)      → empty = Esc
#
# ## Writing new interactive tests
#
#   1. Use _write_responses to build a response file describing the fzf session.
#      Use <NL> in a response line to produce multi-line output (multi-select).
#   2. Run the CLI with _run_interactive (sets all required env vars).
#   3. Assert on $output, $status, and the counter value via _fzf_call_count.
#
# Requires: bats-core (brew install bats-core)

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
CLI="${REPO_ROOT}/bin/cli.js"
MOCK_FZF="${REPO_ROOT}/tests/helpers/mock-fzf.sh"

SKILL1_NAME="skill-analyzer"
SKILL1_SRC="${REPO_ROOT}/skills/analysis/skill-analyzer"
SKILL1_VER="1.0.0"
SKILL1_BUNDLE="analysis"

SKILL2_NAME="diataxis-docs"
SKILL2_SRC="${REPO_ROOT}/skills/harness/diataxis-docs"
SKILL2_VER="1.0.0"
SKILL2_BUNDLE="document"

TOOL_NAME="p-launch"
TOOL_SRC="${REPO_ROOT}/tools/p-launch"
TOOL_VER="1.0.0"

HOOK_NAME_INTERACTIVE="check-similar-branch"
HOOK_SRC_INTERACTIVE="${REPO_ROOT}/hooks/check-similar-branch/check-similar-branch.sh"
HOOK_VER_INTERACTIVE="1.0.0"

setup() {
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  MOCK_BIN="${TEST_DIR}/bin"
  COUNTER_FILE="${TEST_DIR}/fzf-call-count"
  RESPONSES_FILE="${TEST_DIR}/fzf-responses.txt"

  mkdir -p "${MOCK_HOME}/.claude/skills"
  mkdir -p "${MOCK_HOME}/.cursor/skills"
  mkdir -p "${MOCK_HOME}/.local/bin"
  mkdir -p "${MOCK_BIN}"

  cp "${MOCK_FZF}" "${MOCK_BIN}/fzf"
  chmod +x "${MOCK_BIN}/fzf"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

# ── helpers ───────────────────────────────────────────────────────────────────

# fzf output line for a skill.
# Format: display<TAB>name<TAB>ver<TAB>bundle<TAB>kind<TAB>srcPath
_skill_line() {
  local name="$1" ver="$2" bundle="$3" src="$4"
  printf 'display\t%s\t%s\t%s\tskill\t%s' "$name" "$ver" "$bundle" "$src"
}

# fzf output line for a tool.
_tool_line() {
  local name="$1" ver="$2" src="$3"
  printf 'display\t%s\t%s\tshell-tool\ttool\t%s' "$name" "$ver" "$src"
}

# fzf output line for a hook (mirrors fzfSelect format)
_hook_line() {
  local name="$1" ver="$2" src="$3"
  printf 'display\t%s\t%s\thook\thook\t%s' "$name" "$ver" "$src"
}

# Write one fzf response per argument into the responses file.
# Empty string "" writes a blank line → simulates Esc/cancel.
# Use <NL> within a response to produce multi-line output (multi-select).
_write_responses() {
  > "${RESPONSES_FILE}"
  for r in "$@"; do
    printf '%s\n' "$r" >> "${RESPONSES_FILE}"
  done
}

# Number of times mock fzf was called (--version probes excluded).
_fzf_call_count() {
  cat "${COUNTER_FILE}" 2>/dev/null || echo 0
}

# Run the CLI in interactive test mode; captures combined stdout+stderr.
# Pass any extra flags (e.g. --force) as arguments.
_run_interactive() {
  HSKILL_TEST_INTERACTIVE=1 \
  HSKILL_FZF_COUNTER_FILE="${COUNTER_FILE}" \
  HSKILL_FZF_RESPONSES_FILE="${RESPONSES_FILE}" \
  HOME="${MOCK_HOME}" \
  PATH="${MOCK_BIN}:${PATH}" \
  NO_COLOR=1 \
  node "${CLI}" "$@" 2>&1
}

# Extract the installed version from a SKILL.md file (strips surrounding quotes).
_skill_version() {
  grep -o 'version: [^[:space:]]*' "$1" | head -1 | awk '{print $2}' | tr -d '"'
}

# ── loop-back behavior ────────────────────────────────────────────────────────

@test "interactive loop: shows success message then returns to skill selector" {
  _write_responses \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")" \
    "install" \
    "user" \
    "claude" \
    ""  # Esc on loop-back

  run _run_interactive --force

  [[ "$output" == *"Skills installed"* ]]
  [[ "$output" == *"${SKILL1_NAME}"* ]]
  [[ "$output" == *"Nothing selected, exiting"* ]]
  [ "$(_fzf_call_count)" -eq 5 ]   # skill + action + scope + target + loop-back
  [ "$status" -eq 0 ]
}

@test "interactive loop: skill is actually written to target directory" {
  _write_responses \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")" \
    "install" \
    "user" \
    "claude" \
    ""

  run _run_interactive --force

  [ -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

@test "interactive loop: two installs in one session, then exit" {
  _write_responses \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")" \
    "install" "user" "claude" \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")" \
    "install" "user" "claude" \
    ""  # Esc on third round

  run _run_interactive --force

  local count
  count=$(echo "$output" | grep -c "Skills installed")
  [ "$count" -eq 2 ]
  [ "$(_fzf_call_count)" -eq 9 ]   # (skill+action+scope+target)×2 + loop-back
  [ "$status" -eq 0 ]
}

@test "interactive loop: cancel on scope selection exits loop cleanly" {
  _write_responses \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")" \
    "install" \
    ""  # Esc on scope

  run _run_interactive --force

  [ "$status" -eq 0 ]
  [[ "$output" == *"Cancelled"* ]]
  [[ "$output" != *"Skills installed"* ]]
  [ "$(_fzf_call_count)" -eq 3 ]   # skill + action + scope(Esc)
}

@test "interactive loop: cancel on target selection exits loop cleanly" {
  _write_responses \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")" \
    "install" \
    "user" \
    ""  # Esc on target

  run _run_interactive --force

  [ "$status" -eq 0 ]
  [[ "$output" == *"Cancelled"* ]]
  [[ "$output" != *"Skills installed"* ]]
  [ "$(_fzf_call_count)" -eq 4 ]   # skill + action + scope + target(Esc)
}

@test "interactive loop: immediate Esc on first skill select exits cleanly" {
  _write_responses ""

  run _run_interactive --force

  [ "$status" -eq 0 ]
  [[ "$output" == *"Nothing selected, exiting"* ]]
  [[ "$output" != *"Skills installed"* ]]
  [ "$(_fzf_call_count)" -eq 1 ]
}

@test "interactive loop: requires TTY without HSKILL_TEST_INTERACTIVE" {
  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" NO_COLOR=1 \
    node "${CLI}" 2>&1
  [ "$status" -eq 1 ]
  [[ "$output" == *"requires a TTY"* ]]
}

# ── multi-select ──────────────────────────────────────────────────────────────

@test "interactive multi-select: two skills installed in one round" {
  local two_skills
  two_skills="$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")<NL>$(_skill_line "${SKILL2_NAME}" "${SKILL2_VER}" "${SKILL2_BUNDLE}" "${SKILL2_SRC}")"

  _write_responses \
    "$two_skills" \
    "install" \
    "user" \
    "claude" \
    ""

  run _run_interactive --force

  [ "$status" -eq 0 ]
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL2_NAME}/SKILL.md" ]
  [ "$(_fzf_call_count)" -eq 5 ]   # skill-select(2 items) + action + scope + target + loop-back
}

@test "interactive multi-select: both skill names appear in success output" {
  local two_skills
  two_skills="$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")<NL>$(_skill_line "${SKILL2_NAME}" "${SKILL2_VER}" "${SKILL2_BUNDLE}" "${SKILL2_SRC}")"

  _write_responses "$two_skills" "install" "user" "claude" ""

  run _run_interactive --force

  [[ "$output" == *"${SKILL1_NAME}"* ]]
  [[ "$output" == *"${SKILL2_NAME}"* ]]
}

# ── tool installation ─────────────────────────────────────────────────────────

@test "interactive tool install: tool binary written to ~/.local/bin" {
  # Tool install has no scope/target prompts — only skill-selector + action + loop-back.
  _write_responses \
    "$(_tool_line "${TOOL_NAME}" "${TOOL_VER}" "${TOOL_SRC}")" \
    "install" \
    ""  # Esc on loop-back

  run _run_interactive --force

  [ "$status" -eq 0 ]
  [ -x "${MOCK_HOME}/.local/bin/${TOOL_NAME}" ]
  [ "$(_fzf_call_count)" -eq 3 ]   # tool-select + action + loop-back (no scope/target)
}

@test "interactive tool install: success message shown" {
  _write_responses \
    "$(_tool_line "${TOOL_NAME}" "${TOOL_VER}" "${TOOL_SRC}")" \
    "install" \
    ""

  run _run_interactive --force

  [[ "$output" == *"Shell tools installed"* ]]
  [[ "$output" == *"${TOOL_NAME}"* ]]
}

# ── already-installed skill ───────────────────────────────────────────────────

@test "interactive: up-to-date skill is skipped without prompting" {
  # Pre-install at current version (no quotes — readVersion strips them anyway).
  mkdir -p "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}"
  printf -- '---\nname: %s\nversion: %s\n---\n' "${SKILL1_NAME}" "${SKILL1_VER}" \
    > "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md"

  _write_responses \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")" \
    "install" "user" "claude" ""

  # No --force: up-to-date skill must be skipped, no prompt.
  run _run_interactive

  [ "$status" -eq 0 ]
  [[ "$output" == *"skipped"* ]]
  [[ "$output" == *"up-to-date"* ]]
}

@test "interactive: outdated skill skipped in non-TTY (no overwrite prompt)" {
  # Pre-install at an older version.
  mkdir -p "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}"
  printf -- '---\nname: %s\nversion: 0.0.1\n---\n' "${SKILL1_NAME}" \
    > "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md"

  _write_responses \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")" \
    "install" "user" "claude" ""

  # No --force: outdated skill skipped without prompting (non-TTY path).
  run _run_interactive

  [ "$status" -eq 0 ]
  [[ "$output" == *"skipped"* ]]
  # Old version must still be in place.
  [ "$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md")" = "0.0.1" ]
}

@test "interactive --force: outdated skill is overwritten" {
  mkdir -p "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}"
  printf -- '---\nname: %s\nversion: 0.0.1\n---\n' "${SKILL1_NAME}" \
    > "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md"

  _write_responses \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")" \
    "install" "user" "claude" ""

  run _run_interactive --force

  [ "$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md")" = "${SKILL1_VER}" ]
}

# ── project scope ─────────────────────────────────────────────────────────────

@test "interactive: hook install routes to hook flow (scope+target prompts)" {
  _write_responses \
    "$(_hook_line "${HOOK_NAME_INTERACTIVE}" "${HOOK_VER_INTERACTIVE}" "${HOOK_SRC_INTERACTIVE}")" \
    "install" \
    "user" \
    "claude" \
    ""

  run _run_interactive --force

  # 5 fzf calls: selector, action, scope, target, loop-back
  [ "$(_fzf_call_count)" -eq 5 ]
}

@test "interactive: hook install user+claude installs to ~/.claude/hooks/" {
  _write_responses \
    "$(_hook_line "${HOOK_NAME_INTERACTIVE}" "${HOOK_VER_INTERACTIVE}" "${HOOK_SRC_INTERACTIVE}")" \
    "install" \
    "user" \
    "claude" \
    ""

  run _run_interactive --force

  [ -f "${MOCK_HOME}/.claude/hooks/${HOOK_NAME_INTERACTIVE}.sh" ]
}

@test "interactive: hook install user+codex installs to ~/.codex/hooks/" {
  _write_responses \
    "$(_hook_line "${HOOK_NAME_INTERACTIVE}" "${HOOK_VER_INTERACTIVE}" "${HOOK_SRC_INTERACTIVE}")" \
    "install" \
    "user" \
    "codex" \
    ""

  run _run_interactive --force

  [ -f "${MOCK_HOME}/.codex/hooks/${HOOK_NAME_INTERACTIVE}.sh" ]
}

@test "interactive: hook install user+all installs to both claude and codex" {
  _write_responses \
    "$(_hook_line "${HOOK_NAME_INTERACTIVE}" "${HOOK_VER_INTERACTIVE}" "${HOOK_SRC_INTERACTIVE}")" \
    "install" \
    "user" \
    "all" \
    ""

  run _run_interactive --force

  [ -f "${MOCK_HOME}/.claude/hooks/${HOOK_NAME_INTERACTIVE}.sh" ]
  [ -f "${MOCK_HOME}/.codex/hooks/${HOOK_NAME_INTERACTIVE}.sh" ]
}

@test "interactive: hook+skill combined selection installs both" {
  _write_responses \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")<NL>$(_hook_line "${HOOK_NAME_INTERACTIVE}" "${HOOK_VER_INTERACTIVE}" "${HOOK_SRC_INTERACTIVE}")" \
    "install" \
    "user" \
    "claude" \
    "user" \
    "claude" \
    ""

  run _run_interactive --force

  [[ "$output" == *"${SKILL1_NAME}"* ]]
  [ -f "${MOCK_HOME}/.claude/hooks/${HOOK_NAME_INTERACTIVE}.sh" ]
}

@test "interactive project scope: skill written to .claude/skills in cwd" {
  local project_dir="${TEST_DIR}/my-project"
  mkdir -p "${project_dir}"

  _write_responses \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")" \
    "install" \
    "project" \
    "claude" \
    ""

  # Run from project_dir so process.cwd() points there.
  local out
  out=$(cd "${project_dir}" && \
    HSKILL_TEST_INTERACTIVE=1 \
    HSKILL_FZF_COUNTER_FILE="${COUNTER_FILE}" \
    HSKILL_FZF_RESPONSES_FILE="${RESPONSES_FILE}" \
    HOME="${MOCK_HOME}" \
    PATH="${MOCK_BIN}:${PATH}" \
    NO_COLOR=1 \
    node "${CLI}" --force 2>&1)

  [ -f "${project_dir}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
  # Must NOT appear in user-level skills.
  [ ! -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

# ── fzf action selection ──────────────────────────────────────────────────────

@test "interactive: HSKILL_TEST_ACTION=uninstall removes tool" {
  # Pre-install p-launch
  HOME="${MOCK_HOME}" node "${CLI}" install --tool p-launch --force 2>/dev/null
  [ -x "${MOCK_HOME}/.local/bin/p-launch" ]

  # HSKILL_TEST_ACTION=uninstall + HSKILL_TEST_TOOL=p-launch bypasses fzf
  run env HOME="${MOCK_HOME}" \
    HSKILL_TEST_INTERACTIVE=1 \
    HSKILL_TEST_TOOL="p-launch" \
    HSKILL_TEST_ACTION="uninstall" \
    HSKILL_TEST_YES="1" \
    node "${CLI}"
  [ "$status" -eq 0 ]
  [ ! -f "${MOCK_HOME}/.local/bin/p-launch" ]
}
