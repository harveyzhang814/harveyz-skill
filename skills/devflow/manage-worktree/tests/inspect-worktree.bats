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
  [ "$status" -eq 3 ]; [[ "$output" == *"verdict=n/a"* ]] || false
}

@test "02 main worktree on a feature branch is not linked -> exit 1" {
  git -C "$REPO" checkout -q -b feature/x
  run bash "$SCRIPT" --path "$REPO"
  [ "$status" -eq 1 ]; [[ "$output" == *"linked=no"* ]] || false; [[ "$output" == *"reason=not-linked"* ]] || false
}

@test "03 linked worktree on feature branch without rules or hooks -> pass" {
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 0 ]; [[ "$output" == *"verdict=pass"* ]] || false; [[ "$output" == *"hooks=n/a"* ]] || false
  [[ "$output" == *"rule_file=none"* ]] || false; [[ "$output" == *"base=main"* ]] || false
}

@test "04 detached linked worktree -> exit 1, detached" {
  git -C "$REPO" worktree add -q --detach "$TMP/wt" HEAD
  run bash "$SCRIPT" --path "$TMP/wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"detached=yes"* ]] || false; [[ "$output" == *"reason=detached"* ]] || false
}

@test "05 without rules the default branch counts as integration" {
  git -C "$REPO" checkout -q -b feature/park
  git -C "$REPO" worktree add -q "$TMP/wt" main
  run bash "$SCRIPT" --path "$TMP/wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"is_integration=yes"* ]] || false; [[ "$output" == *"reason=integration-branch"* ]] || false
}

@test "06 primary rule file gives integration branches and staging base for feature" {
  rule_file .hskill/init-workflow/workflow-config.yml
  git -C "$REPO" branch staging
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt" --type feature
  [ "$status" -eq 0 ]
  [[ "$output" == *"rule_file=.hskill/init-workflow/workflow-config.yml"* ]] || false
  [[ "$output" == *"integration=main staging"* ]] || false; [[ "$output" == *"base=staging"* ]] || false
}

@test "07 linked worktree on a protected branch from rules -> integration-branch" {
  rule_file .hskill/init-workflow/workflow-config.yml
  git -C "$REPO" branch staging
  git -C "$REPO" worktree add -q "$TMP/wt" staging
  run bash "$SCRIPT" --path "$TMP/wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"reason=integration-branch"* ]] || false
}

@test "08 legacy .claude rule file is found when primary is absent" {
  rule_file .claude/workflow-config.yml
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [[ "$output" == *"rule_file=.claude/workflow-config.yml"* ]] || false; [[ "$output" == *"base=staging"* ]] || false
}

@test "09 primary rule file wins over legacy .claude file" {
  rule_file .claude/workflow-config.yml
  rule_file .hskill/init-workflow/workflow-config.yml
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [[ "$output" == *"rule_file=.hskill/init-workflow/workflow-config.yml"* ]] || false
}

@test "10 type not listed in any merge_from falls back to default branch" {
  rule_file .hskill/init-workflow/workflow-config.yml
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt" --type chore
  [[ "$output" == *"base=main"* ]] || false
}

@test "11 .githooks present but hooksPath unset -> hooks-missing; set -> pass" {
  mkdir "$REPO/.githooks" && touch "$REPO/.githooks/pre-commit"
  git -C "$REPO" add -A && git -C "$REPO" commit -qm hooks
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"hooks=missing"* ]] || false; [[ "$output" == *"reason=hooks-missing"* ]] || false
  git -C "$REPO" config core.hooksPath .githooks
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 0 ]; [[ "$output" == *"hooks=ok"* ]] || false
}

@test "12 subdirectory of a worktree is not root -> exit 1" {
  wt="$(linked feature/x)"; mkdir "$wt/sub"
  run bash "$SCRIPT" --path "$wt/sub"
  [ "$status" -eq 1 ]; [[ "$output" == *"reason=not-root"* ]] || false
}

@test "13 this repository's real rule file yields staging as feature base" {
  cp "$REPO_ROOT/.claude/workflow-config.yml" "$REPO/workflow-config.yml"
  git -C "$REPO" add -A && git -C "$REPO" commit -qm real
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt" --type feature
  [[ "$output" == *"base=staging"* ]] || false; [[ "$output" == *"integration=main staging"* ]] || false
}

@test "14 unknown option -> exit 2" {
  run bash "$SCRIPT" --bogus
  [ "$status" -eq 2 ]
}

# ── hooksPath 的等价写法，以及受保护分支条目下更深层的 name: ────────────────
with_githooks() {
  mkdir "$REPO/.githooks" && touch "$REPO/.githooks/pre-commit"
  git -C "$REPO" add -A && git -C "$REPO" commit -qm hooks
}

@test "15 hooksPath written as ./.githooks/ counts as configured" {
  with_githooks
  wt="$(linked feature/x)"
  git -C "$REPO" config core.hooksPath ./.githooks/
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 0 ]; [[ "$output" == *"hooks=ok"* ]] || false
}

@test "16 absolute hooksPath to the main worktree's .githooks counts as configured" {
  with_githooks
  wt="$(linked feature/x)"
  git -C "$REPO" config core.hooksPath "$REPO/.githooks"
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 0 ]; [[ "$output" == *"hooks=ok"* ]] || false
}

@test "17 hooksPath pointing elsewhere is still hooks-missing" {
  with_githooks
  mkdir "$TMP/elsewhere"
  wt="$(linked feature/x)"
  git -C "$REPO" config core.hooksPath "$TMP/elsewhere"
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"reason=hooks-missing"* ]] || false
}

@test "18 nested name: keys inside a protected entry are not branch names" {
  mkdir -p "$REPO/.hskill/init-workflow"
  cat > "$REPO/.hskill/init-workflow/workflow-config.yml" <<'YML'
branches:
  protected:
    - name: main
      reviewers:
        - name: alice
      merge_from:
        - staging
    - name: staging
      merge_from:
        - "feature/*"
YML
  git -C "$REPO" add -A && git -C "$REPO" commit -qm rules
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [[ "$output" == *"integration=main staging"* ]] || false; [[ "$output" == *"base=staging"* ]] || false
}
