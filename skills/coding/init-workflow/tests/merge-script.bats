#!/usr/bin/env bats
# 端到端：用 deploy_artifacts.py 把标准合并脚本部署进临时 hub 仓库（staging 检出在 hub），
# 在链接 worktree 里运行脚本，核对退出码、目标分支引用与提交标记（Spec 5.4 c、第 6 节）。

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

# deploy_with <pre_checks 的 YAML 行，可为空>：写规则文件、部署、提交，并建链接 worktree
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
