#!/usr/bin/env bats
# 端到端：从“还不是 git 仓库”的目录出发，用默认配置部署、装上从 hook-templates.md 提取的 hooks，
# 经起步引导做出根提交与 staging，再走一轮 worktree → 合并脚本 → 首次推送。
# 复现 5.0.2 的卡点：hooks 生效后全新仓库做不出第一个提交、staging 不存在。

REFS="${BATS_TEST_DIRNAME}/../references"
TEMPLATE="$REFS/hook-templates.md"

extract_block() {
  local out
  out="$(awk -v id="$1" '
    index($0, "# --- BEGIN MANAGED: " id " ") == 1 { on = 1 }
    on { print }
    index($0, "# --- END MANAGED: " id) == 1 { on = 0 }
  ' "$TEMPLATE")"
  [ -n "$out" ] || { echo "template has no block: $1" >&2; return 1; }
  printf '%s\n' "$out" | sed \
    -e 's|<merge_target>|staging|g' \
    -e 's|<merge_trailer>|Merge-Via: merge-to-staging.sh|g' \
    -e 's|<merge_script>|scripts/merge-to-staging.sh|g'
}

# 按模板装 hooks 到仓库自己的 .githooks（与真实部署同位置，会进根提交）
install_hooks() {
  mkdir -p .githooks
  {
    printf '%s\n' '#!/bin/sh' 'BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)' '[ -z "$BRANCH" ] && exit 0' \
      'IS_MERGE=0' '[ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] && IS_MERGE=1'
    extract_block 'branches.protected/main'
    extract_block 'branches.protected/<merge_target>'
    printf '%s\n' 'exit 0'
  } > .githooks/pre-commit
  {
    printf '%s\n' '#!/bin/sh' 'SUBJECT=$(head -1 "$1")'
    extract_block 'commit-msg/merge-via'
    printf '%s\n' 'exit 0'
  } > .githooks/commit-msg
  {
    printf '%s\n' '#!/bin/sh' 'while IFS=" " read -r local_ref local_sha remote_ref remote_sha; do'
    extract_block 'pre-push/merge-via'
    printf '%s\n' 'done' 'exit 0'
  } > .githooks/pre-push
  chmod +x .githooks/*
  git config core.hooksPath .githooks
}

setup() {
  TMP="$(mktemp -d)"; cd "$TMP" || exit 1; TMP="$(pwd -P)"
  mkdir proj && cd proj
  echo hello > README.md
  git init -q   # 不带 -b：分支名由起步引导决定
  git config user.email t@example.com && git config user.name t
  mkdir -p .hskill/init-workflow
  cp "$REFS/workflow-config.yml" .hskill/init-workflow/workflow-config.yml
  python3 "$REFS/deploy_artifacts.py" . >/dev/null
  install_hooks
}
teardown() { [[ -n "${TMP:-}" && "$TMP" == /*/* ]] && rm -rf "$TMP"; }

@test "fresh repo: bootstrap commits everything on main, creates staging and rests on it" {
  run python3 "$REFS/bootstrap_branches.py" .
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "ROOT-COMMIT main" ]
  [[ "$output" == *"FILE README.md"* ]] || false
  [ "${lines[${#lines[@]}-2]}" = "CREATE staging main" ]
  [ "${lines[${#lines[@]}-1]}" = "SWITCH staging" ]
  [ "$(git symbolic-ref --short HEAD)" = "staging" ]
  [ "$(git rev-parse staging)" = "$(git rev-parse main)" ]
  git ls-tree -r --name-only main | grep -qx '.githooks/pre-commit'
  git ls-tree -r --name-only main | grep -qx 'README.md'
  [ -z "$(git status --porcelain)" ]
  # hooks 依旧生效：常驻的 staging 上直接提交被拒
  echo more >> README.md && git add README.md
  run git commit -qm "docs: readme"
  [ "$status" -ne 0 ]
}

@test "fresh repo: worktree from staging, script merge and first publish all work" {
  python3 "$REFS/bootstrap_branches.py" . >/dev/null
  git worktree add -q .worktrees/feature+x -b feature/x staging
  ( cd .worktrees/feature+x && echo x > x.txt && git add x.txt && git commit -qm "feat: x" )
  ( cd .worktrees/feature+x && bash scripts/merge-to-staging.sh >/dev/null )
  git log -1 --format=%B staging | grep -qx 'Merge-Via: merge-to-staging.sh'
  git init -q --bare "$TMP/remote.git"
  git remote add origin "$TMP/remote.git"
  run git push -q -u origin main staging
  [ "$status" -eq 0 ]
  run python3 "$REFS/bootstrap_branches.py" .
  [ "$output" = "$(printf 'EXISTS main\nEXISTS staging')" ]
}

@test "first publish of an untouched staging is flagged before the push is rejected" {
  python3 "$REFS/bootstrap_branches.py" . >/dev/null
  git init -q --bare "$TMP/remote.git"
  git remote add origin "$TMP/remote.git"
  run python3 "$REFS/bootstrap_branches.py" .
  [[ "$output" == *"WARN first-publish staging"* ]] || false
  run git push -q origin staging
  [ "$status" -ne 0 ]
}

@test "naming loop with quoted patterns is valid sh" {
  awk '/BEGIN MANAGED: post-checkout\/branch-naming/,/END MANAGED: post-checkout\/branch-naming/' "$TEMPLATE" \
    | sed -e 's/<exempt-branch-1>|<exempt-branch-2>/main|staging/' \
          -e "s/'<pattern 1>' '<pattern 2>' \.\.\./'^feature\/.+' '^release\/[0-9]+\\\\.[0-9]+\\\\.[0-9]+(-.+)?\$'/" \
    > "$TMP/naming.sh"
  grep -q "'^release/" "$TMP/naming.sh"
  run sh -n "$TMP/naming.sh"
  [ "$status" -eq 0 ]
  BRANCH=release/1.2.3 run sh -c ". '$TMP/naming.sh'"
  [ "$status" -eq 0 ]
  [[ "$output" != *"⚠️"* ]] || false
  BRANCH=bad-name run sh -c ". '$TMP/naming.sh'"
  [[ "$output" == *"⚠️"* ]] || false
}
