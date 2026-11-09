#!/usr/bin/env bats

SCRIPT="${BATS_TEST_DIRNAME}/../scripts/inspect-worktree.sh"
REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/../../../.." && pwd)"

setup() {
  TMP="$(mktemp -d)"; cd "$TMP" || exit 1; TMP="$(pwd -P)"
  git init -q -b main repo && cd repo
  git config user.email t@example.com && git config user.name t
  echo x > seed.txt && git add seed.txt && git commit -qm seed
  REPO="$TMP/repo"
}
teardown() { [[ -n "${TMP:-}" && "$TMP" == /*/* ]] && rm -rf "$TMP"; }

rule_file() { # rule_file <相对路径>
  mkdir -p "$(dirname "$REPO/$1")"
  cat > "$REPO/$1" <<'YML'
branches:
  protected:
    - name: main
      allow_direct_commit: false
      merge_from:
        - staging
        - "release/*"
    - name: staging
      allow_direct_commit: false
      merge_from:
        - "feature/*"
        - "fix/*"
branch_naming:
  enforce: true
YML
  git -C "$REPO" add -A && git -C "$REPO" commit -qm rules
}
linked() { git -C "$REPO" worktree add -q -b "$1" "$TMP/wt" HEAD >/dev/null; echo "$TMP/wt"; }

@test "01 non-git directory -> exit 3, verdict n/a" {
  mkdir "$TMP/plain"
  run bash "$SCRIPT" --path "$TMP/plain"
  [ "$status" -eq 3 ]; [[ "$output" == *"verdict=n/a"* ]]
}

@test "02 main worktree on a feature branch is not linked -> exit 1" {
  git -C "$REPO" checkout -q -b feature/x
  run bash "$SCRIPT" --path "$REPO"
  [ "$status" -eq 1 ]; [[ "$output" == *"linked=no"* ]]; [[ "$output" == *"reason=not-linked"* ]]
}

@test "03 linked worktree on feature branch without rules or hooks -> pass" {
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 0 ]; [[ "$output" == *"verdict=pass"* ]]; [[ "$output" == *"hooks=n/a"* ]]
  [[ "$output" == *"rule_file=none"* ]]; [[ "$output" == *"base=main"* ]]
}

@test "04 detached linked worktree -> exit 1, detached" {
  git -C "$REPO" worktree add -q --detach "$TMP/wt" HEAD
  run bash "$SCRIPT" --path "$TMP/wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"detached=yes"* ]]; [[ "$output" == *"reason=detached"* ]]
}

@test "05 without rules the default branch counts as integration" {
  git -C "$REPO" checkout -q -b feature/park
  git -C "$REPO" worktree add -q "$TMP/wt" main
  run bash "$SCRIPT" --path "$TMP/wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"is_integration=yes"* ]]; [[ "$output" == *"reason=integration-branch"* ]]
}

@test "06 primary rule file gives integration branches and staging base for feature" {
  rule_file .hskill/init-workflow/workflow-config.yml
  git -C "$REPO" branch staging
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt" --type feature
  [ "$status" -eq 0 ]
  [[ "$output" == *"rule_file=.hskill/init-workflow/workflow-config.yml"* ]]
  [[ "$output" == *"integration=main staging"* ]]; [[ "$output" == *"base=staging"* ]]
}

@test "07 linked worktree on a protected branch from rules -> integration-branch" {
  rule_file .hskill/init-workflow/workflow-config.yml
  git -C "$REPO" branch staging
  git -C "$REPO" worktree add -q "$TMP/wt" staging
  run bash "$SCRIPT" --path "$TMP/wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"reason=integration-branch"* ]]
}

@test "08 legacy .claude rule file is found when primary is absent" {
  rule_file .claude/workflow-config.yml
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [[ "$output" == *"rule_file=.claude/workflow-config.yml"* ]]; [[ "$output" == *"base=staging"* ]]
}

@test "09 primary rule file wins over legacy .claude file" {
  rule_file .claude/workflow-config.yml
  rule_file .hskill/init-workflow/workflow-config.yml
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [[ "$output" == *"rule_file=.hskill/init-workflow/workflow-config.yml"* ]]
}

@test "10 type not listed in any merge_from falls back to default branch" {
  rule_file .hskill/init-workflow/workflow-config.yml
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt" --type chore
  [[ "$output" == *"base=main"* ]]
}

@test "11 .githooks present but hooksPath unset -> hooks-missing; set -> pass" {
  mkdir "$REPO/.githooks" && touch "$REPO/.githooks/pre-commit"
  git -C "$REPO" add -A && git -C "$REPO" commit -qm hooks
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"hooks=missing"* ]]; [[ "$output" == *"reason=hooks-missing"* ]]
  git -C "$REPO" config core.hooksPath .githooks
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 0 ]; [[ "$output" == *"hooks=ok"* ]]
}

@test "12 subdirectory of a worktree is not root -> exit 1" {
  wt="$(linked feature/x)"; mkdir "$wt/sub"
  run bash "$SCRIPT" --path "$wt/sub"
  [ "$status" -eq 1 ]; [[ "$output" == *"reason=not-root"* ]]
}

@test "13 this repository's real rule file yields staging as feature base" {
  cp "$REPO_ROOT/.claude/workflow-config.yml" "$REPO/workflow-config.yml"
  git -C "$REPO" add -A && git -C "$REPO" commit -qm real
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt" --type feature
  [[ "$output" == *"base=staging"* ]]; [[ "$output" == *"integration=main staging"* ]]
}

@test "14 unknown option -> exit 2" {
  run bash "$SCRIPT" --bogus
  [ "$status" -eq 2 ]
}
