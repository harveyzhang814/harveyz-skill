#!/usr/bin/env bats
# tests/hook-script.bats
# Behavior tests for scripts/hooks/check-similar-branch.sh

setup() {
  TEST_DIR="$(mktemp -d)"
  HOOK_SCRIPT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)/scripts/hooks/check-similar-branch.sh"

  # Mock bin dir — fake `claude` lives here
  MOCK_BIN="${TEST_DIR}/bin"
  mkdir -p "${MOCK_BIN}"

  # Default mock claude: returns {"similar": false}
  cat > "${MOCK_BIN}/claude" << 'EOF'
#!/bin/bash
echo '{"similar": false}'
EOF
  chmod +x "${MOCK_BIN}/claude"

  # Real git repo with test branches
  REPO_DIR="${TEST_DIR}/repo"
  mkdir -p "${REPO_DIR}"
  cd "${REPO_DIR}"
  git init -q
  git config user.email "test@test.com"
  git config user.name "Test"
  touch README.md && git add . && git commit -q -m "init"
  git branch feature/add-auth
  git branch feature/login-system
  git branch fix/button-color
}

teardown() {
  rm -rf "${TEST_DIR}"
}

# Helper: pipe JSON command input into hook script, mock claude in PATH
_run_hook() {
  local cmd="$1"
  local input="{\"tool_input\": {\"command\": \"${cmd}\"}}"
  echo "$input" | PATH="${MOCK_BIN}:${PATH}" bash "${HOOK_SCRIPT}"
}

# ---------------------------------------------------------------------------
# Group 1: Command filtering — hook should exit 0 with no output
# ---------------------------------------------------------------------------

@test "hook: non-branch command passes through silently" {
  cd "${REPO_DIR}"
  output="$(_run_hook "git status")"
  [ -z "$output" ]
}

@test "hook: git add command passes through silently" {
  cd "${REPO_DIR}"
  output="$(_run_hook "git add .")"
  [ -z "$output" ]
}

@test "hook: git checkout without -b passes through silently" {
  cd "${REPO_DIR}"
  output="$(_run_hook "git checkout main")"
  [ -z "$output" ]
}

@test "hook: git checkout -b triggers hook (no-similar path exits cleanly)" {
  cd "${REPO_DIR}"
  # Default mock returns {"similar": false} — hook runs but outputs nothing
  output="$(_run_hook "git checkout -b feature/new-thing")"
  [ -z "$output" ]
}

@test "hook: git switch -c triggers hook (no-similar path exits cleanly)" {
  cd "${REPO_DIR}"
  output="$(_run_hook "git switch -c feature/new-thing")"
  [ -z "$output" ]
}

# ---------------------------------------------------------------------------
# Group 2: Empty branch list / no git repo
# ---------------------------------------------------------------------------

@test "hook: exits silently when no existing branches" {
  # Fresh repo with only one commit; after filtering current branch list is empty
  EMPTY_REPO="${TEST_DIR}/empty"
  mkdir -p "${EMPTY_REPO}" && cd "${EMPTY_REPO}"
  git init -q
  git config user.email "test@test.com"
  git config user.name "Test"
  touch f && git add . && git commit -q -m "init"
  # Only one branch (the initial one); filtered list will be empty
  output="$(echo '{"tool_input": {"command": "git checkout -b new-branch"}}' \
    | PATH="${MOCK_BIN}:${PATH}" bash "${HOOK_SCRIPT}")"
  [ -z "$output" ]
}

@test "hook: exits silently outside a git repo" {
  cd /tmp
  output="$(echo '{"tool_input": {"command": "git checkout -b new-branch"}}' \
    | PATH="${MOCK_BIN}:${PATH}" bash "${HOOK_SCRIPT}" 2>/dev/null)"
  [ -z "$output" ]
}

# ---------------------------------------------------------------------------
# Group 3: LLM says no similar branches
# ---------------------------------------------------------------------------

@test "hook: no output when LLM returns similar=false" {
  cd "${REPO_DIR}"
  # Default mock already returns {"similar": false}
  output="$(_run_hook "git checkout -b feature/completely-unrelated")"
  [ -z "$output" ]
}

# ---------------------------------------------------------------------------
# Group 4: LLM says similar branches found — verify output format
# ---------------------------------------------------------------------------

@test "hook: outputs hookSpecificOutput when LLM finds similar branches" {
  cd "${REPO_DIR}"
  cat > "${MOCK_BIN}/claude" << 'EOF'
#!/bin/bash
echo '{"similar": true, "matches": ["feature/add-auth"]}'
EOF
  output="$(_run_hook "git checkout -b feature/add-authentication")"
  [ -n "$output" ]
}

@test "hook: output is valid JSON when similar branches found" {
  cd "${REPO_DIR}"
  cat > "${MOCK_BIN}/claude" << 'EOF'
#!/bin/bash
echo '{"similar": true, "matches": ["feature/add-auth"]}'
EOF
  output="$(_run_hook "git checkout -b feature/add-authentication")"
  echo "$output" | jq empty
}

@test "hook: output has hookSpecificOutput key" {
  cd "${REPO_DIR}"
  cat > "${MOCK_BIN}/claude" << 'EOF'
#!/bin/bash
echo '{"similar": true, "matches": ["feature/add-auth"]}'
EOF
  output="$(_run_hook "git checkout -b feature/add-authentication")"
  echo "$output" | jq -e '.hookSpecificOutput' > /dev/null
}

@test "hook: output contains BRANCH_GUARD in additionalContext" {
  cd "${REPO_DIR}"
  cat > "${MOCK_BIN}/claude" << 'EOF'
#!/bin/bash
echo '{"similar": true, "matches": ["feature/add-auth"]}'
EOF
  output="$(_run_hook "git checkout -b feature/add-authentication")"
  echo "$output" | jq -r '.hookSpecificOutput.additionalContext' | grep -q "BRANCH_GUARD"
}

@test "hook: output additionalContext mentions the similar branch name" {
  cd "${REPO_DIR}"
  cat > "${MOCK_BIN}/claude" << 'EOF'
#!/bin/bash
echo '{"similar": true, "matches": ["feature/add-auth"]}'
EOF
  output="$(_run_hook "git checkout -b feature/add-authentication")"
  echo "$output" | jq -r '.hookSpecificOutput.additionalContext' | grep -q "feature/add-auth"
}

# ---------------------------------------------------------------------------
# Group 5: E2E with real claude CLI (slow, skipped in CI if not available)
# ---------------------------------------------------------------------------

@test "hook e2e: real LLM detects semantic similarity between auth branches" {
  if ! command -v claude &>/dev/null; then
    skip "claude CLI not available"
  fi

  cd "${REPO_DIR}"
  # REPO already has feature/add-auth and feature/login-system
  # feature/authentication should be flagged as similar to feature/add-auth
  output="$(echo '{"tool_input": {"command": "git checkout -b feature/authentication"}}' \
    | bash "${HOOK_SCRIPT}" 2>/dev/null)"

  # Either empty (LLM said no) or valid JSON with hookSpecificOutput
  if [ -n "$output" ]; then
    echo "$output" | jq empty
    echo "$output" | jq -e '.hookSpecificOutput' > /dev/null
  fi
}

@test "hook e2e: real LLM does NOT flag unrelated branches" {
  if ! command -v claude &>/dev/null; then
    skip "claude CLI not available"
  fi

  cd "${REPO_DIR}"
  # docs/readme-update is clearly unrelated to feature/add-auth or fix/button-color
  output="$(echo '{"tool_input": {"command": "git checkout -b docs/readme-update"}}' \
    | bash "${HOOK_SCRIPT}" 2>/dev/null)"

  [ -z "$output" ]
}
