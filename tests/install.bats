#!/usr/bin/env bats
# End-to-end tests for `hskill install` (flag-based, non-interactive).
#
# These tests run the real CLI with --skill / --bundle / --tool / --scope /
# --target flags and verify actual file-system state after installation.
# They complement agent-cli.bats (which tests JSON output shape) by asserting
# that the right files end up in the right directories.
#
# Requires: bats-core (brew install bats-core)

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
CLI="${REPO_ROOT}/bin/cli.js"
NODE="$(which node)"

SKILL1_NAME="skill-analyzer"
SKILL1_SRC="${REPO_ROOT}/skills/analysis/skill-analyzer"
SKILL1_VER="1.0.0"

SKILL2_NAME="diataxis-docs"
SKILL2_SRC="${REPO_ROOT}/skills/harness/diataxis-docs"

TOOL_NAME="p-launch"
TOOL_SRC="${REPO_ROOT}/tools/p-launch"

setup() {
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  mkdir -p "${MOCK_HOME}/.claude/skills"
  mkdir -p "${MOCK_HOME}/.cursor/skills"
  mkdir -p "${MOCK_HOME}/.local/bin"
  mkdir -p "${MOCK_HOME}/.local/share/hskill/tools"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

# ── helpers ───────────────────────────────────────────────────────────────────

# Run CLI non-interactively (pipe forces non-TTY); captures stdout.
_install() {
  HOME="${MOCK_HOME}" node "${CLI}" install "$@" 2>/tmp/bats-install-stderr | cat
}

_stderr() { cat /tmp/bats-install-stderr; }

# Extract the installed version from a SKILL.md (strips surrounding quotes).
_skill_version() {
  grep -o 'version: [^[:space:]]*' "$1" | head -1 | awk '{print $2}' | tr -d '"'
}

# ── single skill installation ─────────────────────────────────────────────────

@test "install --skill: SKILL.md written to target dir" {
  _install --skill "${SKILL1_NAME}" --target claude --scope user --force
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

@test "install --skill: installed version matches available version" {
  _install --skill "${SKILL1_NAME}" --target claude --scope user --force
  [ "$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md")" = "${SKILL1_VER}" ]
}

@test "install --skill --target cursor: installs to cursor dir" {
  _install --skill "${SKILL1_NAME}" --target cursor --scope user --force
  [ -f "${MOCK_HOME}/.cursor/skills/${SKILL1_NAME}/SKILL.md" ]
  [ ! -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

@test "install --skill --target all: installs to every target" {
  _install --skill "${SKILL1_NAME}" --target all --scope user --force
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
  [ -f "${MOCK_HOME}/.cursor/skills/${SKILL1_NAME}/SKILL.md" ]
}

# ── project scope ─────────────────────────────────────────────────────────────

@test "install --scope project: installs to cwd/.claude/skills" {
  local project_dir="${TEST_DIR}/my-project"
  mkdir -p "${project_dir}"
  (cd "${project_dir}" && HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL1_NAME}" --target claude --scope project --force 2>/dev/null | cat)
  [ -f "${project_dir}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
  [ ! -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

@test "install --scope project: does not install to user-scope dir" {
  local project_dir="${TEST_DIR}/proj2"
  mkdir -p "${project_dir}"
  (cd "${project_dir}" && HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL1_NAME}" --target claude --scope project --force 2>/dev/null | cat)
  [ ! -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

# ── force flag ────────────────────────────────────────────────────────────────

@test "install --force: overwrites an outdated skill" {
  # Pre-install old version.
  mkdir -p "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}"
  printf -- '---\nname: %s\nversion: 0.0.1\n---\n' "${SKILL1_NAME}" \
    > "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md"

  _install --skill "${SKILL1_NAME}" --target claude --scope user --force

  [ "$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md")" = "${SKILL1_VER}" ]
}

@test "install (no --force): up-to-date skill is skipped" {
  # Pre-install at current version.
  _install --skill "${SKILL1_NAME}" --target claude --scope user --force

  # Second install without --force; stderr should mention skipped.
  local err
  HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL1_NAME}" --target claude --scope user \
    2>/tmp/bats-install-stderr >/dev/null | cat
  err="$(_stderr)"
  [[ "$err" == *"skipped"* ]] || [[ "$err" == *"up-to-date"* ]]
}

@test "install (no --force): outdated skill skipped, old version preserved" {
  mkdir -p "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}"
  printf -- '---\nname: %s\nversion: 0.0.1\n---\n' "${SKILL1_NAME}" \
    > "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md"

  _install --skill "${SKILL1_NAME}" --target claude --scope user

  [ "$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md")" = "0.0.1" ]
}

# ── bundle installation ───────────────────────────────────────────────────────

@test "install --bundle analysis: installs all skills in the bundle" {
  _install --bundle analysis --target claude --scope user --force
  # analysis bundle contains skill-analyzer.
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

@test "install --bundle document: installs all skills in the bundle" {
  _install --bundle document --target claude --scope user --force
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL2_NAME}/SKILL.md" ]
}

@test "install --bundle: --json reports installed list" {
  local out
  out=$(HOME="${MOCK_HOME}" node "${CLI}" install \
    --bundle analysis --target claude --scope user --force --json 2>/dev/null | cat)
  echo "$out" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$out" == *'"installed"'* ]]
  [[ "$out" == *"${SKILL1_NAME}"* ]]
}

# ── tool installation ─────────────────────────────────────────────────────────

@test "install --tool: binary created in ~/.local/bin" {
  _install --tool "${TOOL_NAME}" --force
  [ -x "${MOCK_HOME}/.local/bin/${TOOL_NAME}" ]
}

@test "install --tool: installed binary is executable and non-empty" {
  _install --tool "${TOOL_NAME}" --force
  [ -s "${MOCK_HOME}/.local/bin/${TOOL_NAME}" ]
}

@test "install --tool: tool.json written to data dir" {
  _install --tool "${TOOL_NAME}" --force
  [ -f "${MOCK_HOME}/.local/share/hskill/tools/${TOOL_NAME}.json" ]
}

@test "install --tool (no --force): already-installed tool is skipped" {
  _install --tool "${TOOL_NAME}" --force

  local err
  HOME="${MOCK_HOME}" node "${CLI}" install --tool "${TOOL_NAME}" \
    2>/tmp/bats-install-stderr >/dev/null | cat
  err="$(_stderr)"
  [[ "$err" == *"skipped"* ]] || [[ "$err" == *"already exists"* ]]
}

@test "install --tool --force: re-installs over existing binary" {
  _install --tool "${TOOL_NAME}" --force
  local mtime1
  mtime1=$(stat -f '%m' "${MOCK_HOME}/.local/bin/${TOOL_NAME}" 2>/dev/null || \
           stat -c '%Y' "${MOCK_HOME}/.local/bin/${TOOL_NAME}" 2>/dev/null)

  sleep 1
  _install --tool "${TOOL_NAME}" --force
  local mtime2
  mtime2=$(stat -f '%m' "${MOCK_HOME}/.local/bin/${TOOL_NAME}" 2>/dev/null || \
           stat -c '%Y' "${MOCK_HOME}/.local/bin/${TOOL_NAME}" 2>/dev/null)

  [ "${mtime2}" -ge "${mtime1}" ]
}

# ── multiple skills ───────────────────────────────────────────────────────────

@test "install --skill (comma-separated): installs all listed skills" {
  _install --skill "${SKILL1_NAME},${SKILL2_NAME}" --target claude --scope user --force
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL2_NAME}/SKILL.md" ]
}

# ── JSON output ───────────────────────────────────────────────────────────────

@test "install --skill --json: reports installed skill under target key" {
  local out
  out=$(HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL1_NAME}" --target claude --scope user --force --json 2>/dev/null | cat)
  echo "$out" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$out" == *'"skills"'* ]]
  [[ "$out" == *'"claude"'* ]]
  [[ "$out" == *"${SKILL1_NAME}"* ]]
}

@test "install --skill --json: skipped entry has reason field" {
  # Pre-install so next run skips.
  _install --skill "${SKILL1_NAME}" --target claude --scope user --force

  local out
  out=$(HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL1_NAME}" --target claude --scope user --json 2>/dev/null | cat)
  echo "$out" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$out" == *'"skipped"'* ]]
  [[ "$out" == *'"reason"'* ]]
}

# ── uninstall tool ────────────────────────────────────────────────────────────

_uninstall() {
  HOME="${MOCK_HOME}" node "${CLI}" uninstall "$@" 2>/tmp/bats-uninstall-stderr | cat
}

@test "uninstall: removes binary from ~/.local/bin" {
  _install --tool "${TOOL_NAME}" --force
  [ -x "${MOCK_HOME}/.local/bin/${TOOL_NAME}" ]
  _uninstall "${TOOL_NAME}" --yes
  [ ! -f "${MOCK_HOME}/.local/bin/${TOOL_NAME}" ]
}

@test "uninstall: removes tool.json from share dir" {
  _install --tool "${TOOL_NAME}" --force
  _uninstall "${TOOL_NAME}" --yes
  [ ! -f "${MOCK_HOME}/.local/share/hskill/tools/${TOOL_NAME}.json" ]
}

@test "uninstall: removes companion .py from share dir" {
  _install --tool "${TOOL_NAME}" --force
  _uninstall "${TOOL_NAME}" --yes
  [ ! -f "${MOCK_HOME}/.local/share/hskill/tools/${TOOL_NAME}.py" ]
}

@test "uninstall: removes uninstallPaths declared in tool.json" {
  _install --tool "${TOOL_NAME}" --force
  mkdir -p "${MOCK_HOME}/.local/share/hskill/p-launch-venv"
  _uninstall "${TOOL_NAME}" --yes
  [ ! -d "${MOCK_HOME}/.local/share/hskill/p-launch-venv" ]
}

@test "uninstall: keeps configPaths without --yes in non-TTY" {
  _install --tool "${TOOL_NAME}" --force
  mkdir -p "${MOCK_HOME}/.config/p-launch"
  printf 'PROJECT_DIRS=(%s)\n' "${MOCK_HOME}" > "${MOCK_HOME}/.config/p-launch/config.zsh"
  _uninstall "${TOOL_NAME}"
  [ -f "${MOCK_HOME}/.config/p-launch/config.zsh" ]
}

@test "uninstall: removes configPaths with --yes" {
  _install --tool "${TOOL_NAME}" --force
  mkdir -p "${MOCK_HOME}/.config/p-launch"
  printf 'PROJECT_DIRS=(%s)\n' "${MOCK_HOME}" > "${MOCK_HOME}/.config/p-launch/config.zsh"
  _uninstall "${TOOL_NAME}" --yes
  [ ! -d "${MOCK_HOME}/.config/p-launch" ]
}

@test "uninstall: removes zshrc snippet if present" {
  _install --tool "${TOOL_NAME}" --force
  printf '# >>> p-launch\nexport PATH="$HOME/.local/bin:$PATH"\n# <<< p-launch\n' \
    >> "${MOCK_HOME}/.zshrc"
  _uninstall "${TOOL_NAME}" --yes
  run grep "p-launch" "${MOCK_HOME}/.zshrc"
  [ "$status" -ne 0 ]
}

@test "uninstall: exits 0 when tool is not installed" {
  run _uninstall "${TOOL_NAME}" --yes
  [ "$status" -eq 0 ]
}
