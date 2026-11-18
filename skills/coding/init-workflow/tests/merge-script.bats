#!/usr/bin/env bats
# 端到端：用 deploy_artifacts.py 把标准合并脚本部署进临时 hub 仓库（staging 检出在 hub），
# 在链接 worktree 里运行脚本，核对退出码、目标分支引用与提交标记（Spec 5.4 c、第 6 节）。

bats_require_minimum_version 1.5.0

DEPLOY="${BATS_TEST_DIRNAME}/../references/deploy_artifacts.py"

setup() {
  TMP="$(mktemp -d)"; cd "$TMP" || exit 1; TMP="$(pwd -P)"
  HUB="$TMP/hub"; WT="$TMP/wt"
  git init -q -b main "$HUB"
  git -C "$HUB" config user.email t@example.com
  git -C "$HUB" config user.name t
  echo base > "$HUB/a.txt"
  git -C "$HUB" add a.txt && git -C "$HUB" commit -qm seed
  git -C "$HUB" checkout -q -b staging
}
teardown() { [[ -n "${TMP:-}" && "$TMP" == /*/* ]] && rm -rf "$TMP"; }

# deploy_with <pre_checks 的 YAML 行，可为空> [merge 节里追加的 YAML 行，如 post_steps 块]：
# 写规则文件、部署、提交，并建链接 worktree
deploy_with() {
  cat > "$HUB/workflow-config.yml" <<YML
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
branch_naming:
  enforce: true
  allowed_patterns:
    - "^feature/.+"
  exempt:
    - main
    - staging
merge:
  pre_checks: [$1]
${2:-}
YML
  python3 "$DEPLOY" "$HUB" >/dev/null
  git -C "$HUB" add -A && git -C "$HUB" commit -qm deploy
  git -C "$HUB" worktree add -q -b feature/x "$WT" staging
  git -C "$WT" config user.email t@example.com
  git -C "$WT" config user.name t
}

@test "clean merge exits 0 and target carries the trailer" {
  deploy_with ""
  echo feat > "$WT/b.txt" && git -C "$WT" add b.txt && git -C "$WT" commit -qm feat
  cd "$WT"
  run bash scripts/merge-to-staging.sh
  [ "$status" -eq 0 ]
  [ "$(git -C "$HUB" rev-list --parents -n1 staging | wc -w)" -eq 3 ]
  git -C "$HUB" log -1 --format=%B staging | grep -qx 'Merge-Via: merge-to-staging.sh'
  # hub 检出着 staging：脚本应把它的工作树同步到新提交
  [ -f "$HUB/b.txt" ]
  [ -z "$(git -C "$HUB" status --porcelain)" ]
  [ "$(git -C "$HUB" symbolic-ref --short HEAD)" = "staging" ]
}

@test "already merged exits 0 without new commit" {
  deploy_with ""
  echo feat > "$WT/b.txt" && git -C "$WT" add b.txt && git -C "$WT" commit -qm feat
  cd "$WT"
  run bash scripts/merge-to-staging.sh
  [ "$status" -eq 0 ]
  before="$(git -C "$HUB" rev-parse staging)"
  run bash scripts/merge-to-staging.sh
  [ "$status" -eq 0 ]
  [ "$(git -C "$HUB" rev-parse staging)" = "$before" ]
}

@test "real conflict exits 2 and target ref unchanged" {
  deploy_with ""
  echo theirs > "$HUB/a.txt" && git -C "$HUB" commit -qam staging-side
  echo ours > "$WT/a.txt" && git -C "$WT" commit -qam feature-side
  before="$(git -C "$HUB" rev-parse staging)"
  cd "$WT"
  run bash scripts/merge-to-staging.sh
  [ "$status" -eq 2 ]
  [ "$(git -C "$HUB" rev-parse staging)" = "$before" ]
  grep -q '^<<<<<<<' "$WT/a.txt"
}

@test "failing pre_check exits 1 and target ref unchanged" {
  deploy_with "\"echo one >> $TMP/order\", \"test {target} = nope\", \"echo three >> $TMP/order\""
  echo feat > "$WT/b.txt" && git -C "$WT" add b.txt && git -C "$WT" commit -qm feat
  before="$(git -C "$HUB" rev-parse staging)"
  cd "$WT"
  run bash scripts/merge-to-staging.sh
  [ "$status" -eq 1 ]
  [ "$(git -C "$HUB" rev-parse staging)" = "$before" ]
  [[ "$output" == *"test staging = nope"* ]] || false
  # 按顺序执行、失败即停：只有第一条跑过
  [ "$(cat "$TMP/order")" = "one" ]
}

@test "passing pre_checks run in the worktree root and merge proceeds" {
  deploy_with "\"test -f b.txt\", \"test {target} = staging\""
  echo feat > "$WT/b.txt" && git -C "$WT" add b.txt && git -C "$WT" commit -qm feat
  mkdir "$WT/sub" && cd "$WT/sub"
  run bash ../scripts/merge-to-staging.sh
  [ "$status" -eq 0 ]
  [ "$(git -C "$HUB" rev-list --parents -n1 staging | wc -w)" -eq 3 ]
}

# helper_next_to_script：在 hub 的 scripts/ 放一个辅助脚本，被调用时把参数写进 $TMP/marker
helper_next_to_script() {
  mkdir -p "$HUB/scripts"
  printf '#!/bin/sh\necho "$1" > "%s/marker"\n' "$TMP" > "$HUB/scripts/helper.sh"
}

@test "{script_dir} pre_check runs a helper next to the merge script" {
  helper_next_to_script
  deploy_with "\"sh {script_dir}/helper.sh {target}\""
  echo feat > "$WT/b.txt" && git -C "$WT" add b.txt && git -C "$WT" commit -qm feat
  cd "$WT"
  run bash scripts/merge-to-staging.sh
  [ "$status" -eq 0 ]
  [ "$(cat "$TMP/marker")" = "staging" ]
}

@test "{script_dir} resolves when invoked by a relative path from a subdirectory" {
  helper_next_to_script
  deploy_with "\"sh {script_dir}/helper.sh {target}\""
  echo feat > "$WT/b.txt" && git -C "$WT" add b.txt && git -C "$WT" commit -qm feat
  mkdir "$WT/sub" && cd "$WT/sub"
  run bash ../scripts/merge-to-staging.sh
  [ "$status" -eq 0 ]
  [ "$(cat "$TMP/marker")" = "staging" ]
}

@test "{script_dir} survives a repository path with spaces" {
  mv "$TMP/hub" "$TMP/with space"
  HUB="$TMP/with space"; WT="$TMP/with space wt"
  helper_next_to_script
  deploy_with "\"sh {script_dir}/helper.sh {target}\""
  echo feat > "$WT/b.txt" && git -C "$WT" add b.txt && git -C "$WT" commit -qm feat
  cd "$WT"
  run bash scripts/merge-to-staging.sh
  [ "$status" -eq 0 ]
  [ "$(cat "$TMP/marker")" = "staging" ]
}

@test "refuses to run on any integration branch" {
  deploy_with ""
  git -C "$HUB" worktree add -q "$TMP/mainwt" main
  before="$(git -C "$HUB" rev-parse staging)"
  # staging：hub 检出着它，脚本随 staging 提交存在
  cd "$HUB"
  run bash scripts/merge-to-staging.sh
  [ "$status" -eq 1 ]
  [[ "$output" == *"当前在 staging"* ]] || false
  # main：在 main 的工作树里运行同一份脚本
  cd "$TMP/mainwt"
  [ "$(git rev-parse --abbrev-ref HEAD)" = "main" ]
  run bash "$HUB/scripts/merge-to-staging.sh"
  [ "$status" -eq 1 ]
  [[ "$output" == *"当前在 main"* ]] || false
  [ "$(git -C "$HUB" rev-parse staging)" = "$before" ]
}

# ── merge.post_steps（J5）：合并成功后在后台执行，不阻塞、不改变退出码与 stdout ──

now_ms() { python3 -c 'import time; print(int(time.time() * 1000))'; }

# wait_for <文件> <最长秒数>：等文件出现且非空
wait_for() {
  local f="$1" i
  for i in $(seq 1 $(( $2 * 10 ))); do
    [ -s "$f" ] && return 0
    sleep 0.1
  done
  return 1
}

commit_feature() {
  echo feat > "$WT/b.txt" && git -C "$WT" add b.txt && git -C "$WT" commit -qm feat
}

@test "J5a empty post_steps renders a merge script identical to fd60ab4 apart from the version line" {
  git -C "$BATS_TEST_DIRNAME" cat-file -e fd60ab4 2>/dev/null || skip "fd60ab4 不在本仓库历史里（浅克隆？）"
  ROOT="$(git -C "$BATS_TEST_DIRNAME" rev-parse --show-toplevel)"
  mkdir "$TMP/old"
  git -C "$ROOT" archive fd60ab4 skills/coding/init-workflow/references | tar -x -C "$TMP/old"
  OLD_DEPLOY="$TMP/old/skills/coding/init-workflow/references/deploy_artifacts.py"
  for side in old new; do
    mkdir "$TMP/$side-repo"
    git init -q -b main "$TMP/$side-repo"
    # 同一份不含 post_steps 的配置（含一条 pre_checks，保证走过 MANAGED 块渲染）
    cat > "$TMP/$side-repo/workflow-config.yml" <<'YML'
branches:
  protected:
    - name: main
      allow_direct_commit: false
      merge_from:
        - staging
    - name: staging
      allow_direct_commit: false
      merge_from:
        - "feature/*"
branch_naming:
  enforce: true
  allowed_patterns:
    - "^feature/.+"
  exempt:
    - main
    - staging
merge:
  pre_checks:
    - test {target} = staging
YML
  done
  python3 "$OLD_DEPLOY" "$TMP/old-repo" >/dev/null
  python3 "$DEPLOY" "$TMP/new-repo" >/dev/null
  OLD_SCRIPT="$TMP/old-repo/scripts/merge-to-staging.sh"
  NEW_SCRIPT="$TMP/new-repo/scripts/merge-to-staging.sh"
  [ -s "$OLD_SCRIPT" ]
  # 只有第 2 行（带版本号的生成标记）不同
  [ "$(diff "$OLD_SCRIPT" "$NEW_SCRIPT" | grep -c '^[<>]')" -eq 2 ]
  diff <(sed 2d "$OLD_SCRIPT") <(sed 2d "$NEW_SCRIPT")
  sed -n 2p "$OLD_SCRIPT" | grep -q '^# Generated by init-workflow '
  sed -n 2p "$NEW_SCRIPT" | grep -q '^# Generated by init-workflow '
}

@test "J5b background step sleep 30 then touch: merge returns within 2s with exit 0, marker appears ~30s later" {
  deploy_with "" "  post_steps:
    - sleep 30; touch $TMP/marker"
  commit_feature
  cd "$WT"
  start="$(now_ms)"
  # 3>&-：别让后台步骤继承 bats 的 fd 3，否则 bats 会等它退出
  run bash scripts/merge-to-staging.sh 3>&-
  elapsed=$(( $(now_ms) - start ))
  [ "$status" -eq 0 ]
  [ "$elapsed" -lt 2000 ]
  [ ! -e "$TMP/marker" ]
  for i in $(seq 1 80); do [ -e "$TMP/marker" ] && break; sleep 0.5; done
  [ -e "$TMP/marker" ]
}

@test "J5c a failing background step leaves exit code and stdout unchanged" {
  deploy_with "" "  post_steps:
    - exit 7"
  commit_feature
  cd "$WT"
  run --separate-stderr bash -c 'exec 3>&-; exec bash scripts/merge-to-staging.sh'
  [ "$status" -eq 0 ]
  # stdout 与无步骤时一致：只有那一行合并成功提示
  [ "$output" = "✅ 已将 feature/x 合并进本地 staging（$(git -C "$HUB" rev-parse staging)）" ]
  [ -z "$stderr" ]
}

@test "J5d placeholders and MERGE_* env vars reach the background step; already-merged skips it" {
  deploy_with "" '  post_steps:
    - printf "%s\n" "{merge_commit}" "{base_commit}" "{feature_branch}" "{target}" "$MERGE_COMMIT" "$MERGE_BASE_COMMIT" "$MERGE_FEATURE_BRANCH" "$MERGE_TARGET" "$PWD" > '"$TMP"'/out
    - echo run >> '"$TMP"'/count'
  commit_feature
  base="$(git -C "$HUB" rev-parse staging)"
  cd "$WT"
  run bash scripts/merge-to-staging.sh 3>&-
  [ "$status" -eq 0 ]
  merged="$(git -C "$HUB" rev-parse staging)"
  wait_for "$TMP/out" 10
  wait_for "$TMP/count" 10
  got() { sed -n "$(( $1 + 1 ))p" "$TMP/out"; }
  [ "$(got 0)" = "$merged" ]
  [ "$(got 1)" = "$base" ]
  [ "$(got 2)" = "feature/x" ]
  [ "$(got 3)" = "staging" ]
  [ "$(got 4)" = "$merged" ]
  [ "$(got 5)" = "$base" ]
  [ "$(got 6)" = "feature/x" ]
  [ "$(got 7)" = "staging" ]
  # 步骤在本次合并的 worktree 根目录下执行
  [ "$(got 8)" = "$WT" ]
  # 已经包含在 target 里、无需合并：不执行步骤
  rm -f "$TMP/count"
  run bash scripts/merge-to-staging.sh 3>&-
  [ "$status" -eq 0 ]
  [[ "$output" == *"无需合并"* ]] || false
  sleep 2
  [ ! -e "$TMP/count" ]
}

@test "J5e a real conflict does not run background steps" {
  deploy_with "" "  post_steps:
    - echo run >> $TMP/count"
  echo theirs > "$HUB/a.txt" && git -C "$HUB" commit -qam staging-side
  echo ours > "$WT/a.txt" && git -C "$WT" commit -qam feature-side
  cd "$WT"
  run bash scripts/merge-to-staging.sh 3>&-
  [ "$status" -eq 2 ]
  sleep 2
  [ ! -e "$TMP/count" ]
}
