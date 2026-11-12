#!/usr/bin/env bats
# merge-worktree.sh 端到端：临时 hub 仓库用 deploy_artifacts.py 部署并提交到基线分支 staging，
# 在链接 worktree 里跑「合并」，核对退出码、提示与合并目标分支的引用（Spec 5.5、第 6 节）。

SCRIPT="${BATS_TEST_DIRNAME}/../scripts/merge-worktree.sh"
DEPLOY="${BATS_TEST_DIRNAME}/../../../coding/init-workflow/references/deploy_artifacts.py"

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

# 写规则文件 → 部署 → 提交到 staging。$1 为 pre_checks 的 YAML 内容（可为空）
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
}
# 在 staging 上建链接 worktree feature/x
add_wt() {
  git -C "$HUB" worktree add -q -b feature/x "$WT" staging
  git -C "$WT" config user.email t@example.com
  git -C "$WT" config user.name t
}
commit_in_wt() { echo feat > "$WT/b.txt" && git -C "$WT" add b.txt && git -C "$WT" commit -qm feat; }

@test "not deployed -> exit 4" {
  add_wt
  cd "$WT"
  run bash "$SCRIPT"
  [ "$status" -eq 4 ]
  [[ "$output" == *"init-workflow"* ]] || false
}

@test "resolved.env without integration_branches -> exit 4 naming resolved-invalid" {
  deploy_with ""
  sed -e '/^integration_branches=/d' "$HUB/.hskill/init-workflow/resolved.env" > "$TMP/e.env"
  cp "$TMP/e.env" "$HUB/.hskill/init-workflow/resolved.env"
  git -C "$HUB" add -A && git -C "$HUB" commit -qm broken
  add_wt
  cd "$WT"
  before="$(git -C "$HUB" rev-parse staging)"
  run bash "$SCRIPT"
  [ "$status" -eq 4 ]
  [[ "$output" == *"resolved-invalid"* ]] || false
  [ "$(git -C "$HUB" rev-parse staging)" = "$before" ]
}

@test "on integration branch -> exit 5" {
  deploy_with ""
  git -C "$HUB" worktree add -q "$TMP/mainwt" main
  cd "$TMP/mainwt"
  [ "$(git rev-parse --abbrev-ref HEAD)" = "main" ]
  before="$(git -C "$HUB" rev-parse staging)"
  run bash "$SCRIPT"
  [ "$status" -eq 5 ]
  [[ "$output" == *"integration-branch"* ]] || false
  [ "$(git -C "$HUB" rev-parse staging)" = "$before" ]
}

@test "detached -> exit 5" {
  deploy_with ""
  git -C "$HUB" worktree add -q --detach "$WT" staging
  cd "$WT"
  run bash "$SCRIPT"
  [ "$status" -eq 5 ]
  [[ "$output" == *"detached"* ]] || false
}

@test "worktree subdirectory -> exit 5" {
  deploy_with ""
  add_wt
  commit_in_wt
  mkdir "$WT/sub"
  before="$(git -C "$HUB" rev-parse staging)"
  cd "$WT/sub"
  run bash "$SCRIPT"
  [ "$status" -eq 5 ]
  [[ "$output" == *"not-root"* ]] || false
  [ "$(git -C "$HUB" rev-parse staging)" = "$before" ]
}

@test "no merge target configured -> exit 6" {
  # 配置无 base.feature：不写合并目标，基线回落到默认分支 main，部署提交在 main 上
  git -C "$HUB" checkout -q main
  cat > "$HUB/workflow-config.yml" <<'YML'
branches:
  protected:
    - name: main
      allow_direct_commit: false
      merge_from:
        - "fix/*"
branch_naming:
  enforce: true
  allowed_patterns:
    - "^fix/.+"
  exempt:
    - main
YML
  python3 "$DEPLOY" "$HUB" >/dev/null
  git -C "$HUB" add -A && git -C "$HUB" commit -qm deploy
  git -C "$HUB" worktree add -q -b fix/x "$WT" main
  cd "$WT"
  run bash "$SCRIPT"
  [ "$status" -eq 6 ]
  [[ "$output" == *"本仓库未配置合并目标"* ]] || false
}

@test "branch created before deployment lacks script -> exit 7 and hint names the target" {
  # 先建分支，再在 staging 上提交部署：分支里没有合并脚本
  add_wt
  deploy_with ""
  [ ! -e "$WT/scripts/merge-to-staging.sh" ]
  commit_in_wt
  before="$(git -C "$HUB" rev-parse staging)"
  cd "$WT"
  run bash "$SCRIPT"
  [ "$status" -eq 7 ]
  [[ "$output" == *"先把 staging 并入本分支再「合并」"* ]] || false
  [ "$(git -C "$HUB" rev-parse staging)" = "$before" ]
}

@test "clean merge passes through exit 0" {
  deploy_with ""
  add_wt
  commit_in_wt
  cd "$WT"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"合并进本地 staging"* ]] || false
  [ "$(git -C "$HUB" rev-list --parents -n1 staging | wc -w)" -eq 3 ]
  git -C "$HUB" log -1 --format=%B staging | grep -qx 'Merge-Via: merge-to-staging.sh'
}

@test "conflict passes through exit 2" {
  deploy_with ""
  add_wt
  echo theirs > "$HUB/a.txt" && git -C "$HUB" commit -qam staging-side
  echo ours > "$WT/a.txt" && git -C "$WT" commit -qam feature-side
  before="$(git -C "$HUB" rev-parse staging)"
  cd "$WT"
  run bash "$SCRIPT"
  [ "$status" -eq 2 ]
  [ "$(git -C "$HUB" rev-parse staging)" = "$before" ]
  grep -q '^<<<<<<<' "$WT/a.txt"
}

@test "failing pre_check passes through exit 1" {
  deploy_with "\"test {target} = nope\""
  add_wt
  commit_in_wt
  before="$(git -C "$HUB" rev-parse staging)"
  cd "$WT"
  run bash "$SCRIPT"
  [ "$status" -eq 1 ]
  [[ "$output" == *"test staging = nope"* ]] || false
  [ "$(git -C "$HUB" rev-parse staging)" = "$before" ]
}
