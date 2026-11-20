#!/usr/bin/env bats
# leave-worktree.sh：「离开」在宿主离开之后的部分（worktree-remove-on-leave spec §3.1、§4.1、判据 J1）。
# 真实 git 仓库（inspect-worktree.sh 要从基线分支读 resolved.env 取 merge_target），
# agent-canvas-ctl 用桩：PATH 前置 $TMP/bin/agent-canvas-ctl，按子命令读 $FX/<子命令>.{out,err,rc}
# 夹具作答（返回形状照 App 的租约能力：成功 JSON 进 stdout；ok:false 的 JSON 进 stderr、退出 1），
# 每次调用把参数追加到 $TMP/ctl.log。

SCRIPT="${BATS_TEST_DIRNAME}/../scripts/leave-worktree.sh"

setup() {
  TMP="$(mktemp -d)"; cd "$TMP" || exit 1; TMP="$(pwd -P)"
  REPO="$TMP/repo"; W="$TMP/repo/.worktrees/feature+x"; W2="$TMP/repo/.worktrees/feature+y"
  git init -q -b main "$REPO"
  git -C "$REPO" config user.email t@example.com
  git -C "$REPO" config user.name t
  echo x > "$REPO/seed.txt"
  git -C "$REPO" add seed.txt && git -C "$REPO" commit -qm seed

  FX="$TMP/fx"; CTL_LOG="$TMP/ctl.log"; export FX CTL_LOG
  mkdir -p "$TMP/bin" "$FX"
  cat > "$TMP/bin/agent-canvas-ctl" <<'STUB'
#!/usr/bin/env bash
echo "$*" >> "$CTL_LOG"
sub="$1"
if [[ ! -f "$FX/$sub.out" && ! -f "$FX/$sub.err" ]]; then echo "stub: no fixture for $sub" >&2; exit 1; fi
[[ -f "$FX/$sub.out" ]] && cat "$FX/$sub.out"
[[ -f "$FX/$sub.err" ]] && cat "$FX/$sub.err" >&2
exit "$(cat "$FX/$sub.rc" 2>/dev/null || echo 0)"
STUB
  chmod +x "$TMP/bin/agent-canvas-ctl"
  export PATH="$TMP/bin:$PATH"
  export AGENT_CANVAS_NODE_TOKEN="tok-test"
  default_fixtures
  cd "$REPO" || exit 1
}
teardown() { [[ -n "${TMP:-}" && "$TMP" == /*/* ]] && rm -rf "$TMP"; }

# 部署 resolved.env 到 staging（带不带 merge_target 由 $1 决定），再建 W（feature/x）与 W2（feature/y）
deploy() { # deploy [no-merge-target]
  mkdir -p "$REPO/.hskill/init-workflow"
  {
    echo "schema=1"
    echo "integration_branches=main staging"
    echo "base.feature=staging"
    [[ "${1:-}" == "no-merge-target" ]] || echo "merge_target=staging"
    [[ "${1:-}" == "no-merge-target" ]] || echo "merge_script=scripts/merge-to-staging.sh"
    echo "worktree_dir=.worktrees"
  } > "$REPO/.hskill/init-workflow/resolved.env"
  git -C "$REPO" add -A && git -C "$REPO" commit -qm deploy
  git -C "$REPO" branch -f staging main
  git -C "$REPO" worktree add -q -b feature/x "$W" staging
  git -C "$REPO" worktree add -q -b feature/y "$W2" staging
}

# holder <nodeId> <first.source> <last.source> [validity]
holder() {
  printf '{"nodeId":"%s","runId":"r-%s","first":{"source":"%s","at":1},"last":{"source":"%s","at":2},"validity":"%s"}' \
    "$1" "$1" "$2" "$3" "${4:-valid}"
}
# lease_view <path> <holder JSON,...>
lease_view() {
  printf '{"path":"%s","gitDir":"%s/.git/worktrees/x","state":"claimed","holders":[%s],"ready":true}' "$1" "$REPO" "$2"
}
set_lease() { printf '{"ok":true,"lease":%s}\n' "$(lease_view "$W" "$1")" > "$FX/get-worktree-lease.out"; }
fail_with() { # fail_with <子命令> <code> <message>
  printf '{"ok":false,"code":"%s","message":"%s"}\n' "$2" "$3" > "$FX/$1.err"
  echo 1 > "$FX/$1.rc"; rm -f "$FX/$1.out"
}

default_fixtures() {
  echo '{"id":"n1","kind":"pty","title":"me"}' > "$FX/whoami.out"
  set_lease "$(holder n1 claude:EnterWorktree explicit)"
  printf '{"ok":true,"path":"%s","released":true}\n' "$W" > "$FX/exit-worktree.out"
  cat > "$FX/help.out" <<'HELP'
remove-worktree --path <dir> --merged-into <ref>
  code 取 not-linked-worktree、already-removed、held-by-others、open-window、trapped-session、session-scan-failed、locked、dirty、not-merged
HELP
  printf '{"ok":true,"path":"%s","removed":true,"branchKept":"feature/x"}\n' "$W" > "$FX/remove-worktree.out"
}

has_line() { printf '%s\n' "$output" | grep -qxF -- "$1"; }
logged() { [[ -f "$CTL_LOG" ]] && grep -qF -- "$1" "$CTL_LOG"; }
not_logged() { ! logged "$1"; }

@test "outside canvas -> canvas=no, no ctl call" {
  deploy
  export AGENT_CANVAS_NODE_TOKEN=""
  run bash "$SCRIPT" --path "$W"
  [ "$status" -eq 0 ]
  [ "$output" = "canvas=no" ]
  [ ! -e "$CTL_LOG" ]
  # 有令牌但 PATH 上没有 agent-canvas-ctl 也算画布外
  export AGENT_CANVAS_NODE_TOKEN="tok-test"
  saved_path="$PATH"; export PATH="/usr/bin:/bin"
  run /bin/bash "$SCRIPT" --path "$W"
  export PATH="$saved_path"
  [ "$status" -eq 0 ]
  [ "$output" = "canvas=no" ]
  [ ! -e "$CTL_LOG" ]
}

@test "S1 merged and alone -> released=yes removed=yes branch_kept=feature/x" {
  deploy
  run bash "$SCRIPT" --path "$W"
  [ "$status" -eq 0 ]
  has_line "canvas=yes"
  has_line "worktree=$W"
  has_line "released=yes"
  has_line "removed=yes"
  has_line "branch_kept=feature/x"
  logged "exit-worktree --path $W"
  logged "help remove-worktree"
  logged "remove-worktree --path $W --merged-into staging"
  # 脚本自己不删分支、不删 worktree（桩不删，目录与分支都还在）
  git -C "$REPO" rev-parse --verify -q feature/x >/dev/null
}

@test "S2 held by others -> removed=no reason=held-by-others" {
  deploy
  set_lease "$(holder n1 claude:EnterWorktree explicit),$(holder n2 spawn-cwd explicit)"
  fail_with remove-worktree held-by-others "还有其他持有者"
  run bash "$SCRIPT" --path "$W"
  [ "$status" -eq 0 ]
  has_line "worktree=$W"
  has_line "released=yes"
  has_line "removed=no"
  has_line "reason=held-by-others"
  has_line "detail=还有其他持有者"
  logged "remove-worktree --path $W --merged-into staging"
}

@test "S4 started-here (spawn-cwd) even when run from repo root -> no exit-worktree, no remove-worktree" {
  deploy
  set_lease "$(holder n2 explicit explicit),$(holder n1 spawn-cwd explicit)"
  [ "$(pwd -P)" = "$REPO" ]
  run bash "$SCRIPT" --path "$W"
  [ "$status" -eq 0 ]
  has_line "worktree=$W"
  has_line "released=skipped"
  has_line "removed=no"
  has_line "reason=started-here"
  logged "get-worktree-lease --path $W"
  not_logged "exit-worktree"
  not_logged "remove-worktree --path"
}

@test "cwd inside W -> reason=cwd-inside, no exit-worktree" {
  deploy
  mkdir -p "$W/sub"; cd "$W/sub"
  run bash "$SCRIPT" --path "$W"
  [ "$status" -eq 0 ]
  has_line "worktree=$W"
  has_line "released=skipped"
  has_line "removed=no"
  has_line "reason=cwd-inside"
  not_logged "exit-worktree"
  not_logged "remove-worktree --path"
}

@test "S7 not merged -> reason=not-merged" {
  deploy
  fail_with remove-worktree not-merged "HEAD 未合入 staging"
  run bash "$SCRIPT" --path "$W"
  [ "$status" -eq 0 ]
  has_line "released=yes"
  has_line "removed=no"
  has_line "reason=not-merged"
  [[ "$output" != *"branch_kept="* ]] || false
}

@test "S9 no --path, exactly one held -> processes it" {
  deploy
  printf '{"ok":true,"commonDir":"%s/.git","ready":true,"worktrees":[%s,%s,%s]}\n' "$REPO" \
    "$(lease_view "$W" "$(holder n1 explicit explicit)")" \
    "$(lease_view "$W2" "$(holder n2 explicit explicit)")" \
    "$(lease_view "$TMP/old" "$(holder n1 explicit explicit invalid)")" > "$FX/list-worktree-leases.out"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  has_line "canvas=yes"
  has_line "worktree=$W"
  has_line "released=yes"
  has_line "removed=yes"
  logged "list-worktree-leases --repo $REPO"
  logged "exit-worktree --path $W"
  logged "remove-worktree --path $W --merged-into staging"
  [[ "$output" != *"worktree=$W2"* ]] || false
}

@test "no --path, two held -> lookup=ambiguous, nothing processed" {
  deploy
  printf '{"ok":true,"commonDir":"%s/.git","ready":true,"worktrees":[%s,%s]}\n' "$REPO" \
    "$(lease_view "$W" "$(holder n1 explicit explicit)")" \
    "$(lease_view "$W2" "$(holder n1 create create pending)")" > "$FX/list-worktree-leases.out"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  has_line "lookup=ambiguous"
  has_line "candidate=$W"
  has_line "candidate=$W2"
  [[ "$output" != *"worktree="* ]] || false
  not_logged "exit-worktree"
  not_logged "remove-worktree --path"
  # 一个都没有 → lookup=none；查询失败 → lookup=error 带 detail
  printf '{"ok":true,"commonDir":"%s/.git","ready":true,"worktrees":[]}\n' "$REPO" > "$FX/list-worktree-leases.out"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  has_line "lookup=none"
  fail_with list-worktree-leases lease-service-unavailable "租约服务不可用"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  has_line "lookup=error"
  has_line "detail=租约服务不可用"
  not_logged "exit-worktree"
}

@test "S10 --path W1 while also holding W2 -> only W1 processed" {
  deploy
  printf '{"ok":true,"commonDir":"%s/.git","ready":true,"worktrees":[%s,%s]}\n' "$REPO" \
    "$(lease_view "$W" "$(holder n1 claude:EnterWorktree explicit)")" \
    "$(lease_view "$W2" "$(holder n1 create create)")" > "$FX/list-worktree-leases.out"
  run bash "$SCRIPT" --path "$W"
  [ "$status" -eq 0 ]
  has_line "worktree=$W"
  has_line "removed=yes"
  [ "$(printf '%s\n' "$output" | grep -c '^worktree=')" -eq 1 ]
  not_logged "$W2"
  not_logged "list-worktree-leases"
}

@test "old app help lacks trapped-session -> released=yes removed=no reason=app-too-old, no remove-worktree" {
  deploy
  echo 'remove-worktree --path <dir> --merged-into <ref>  code 取 held-by-others、open-window、locked、dirty、not-merged' > "$FX/help.out"
  run bash "$SCRIPT" --path "$W"
  [ "$status" -eq 0 ]
  has_line "released=yes"
  has_line "removed=no"
  has_line "reason=app-too-old"
  logged "exit-worktree --path $W"
  logged "help remove-worktree"
  not_logged "remove-worktree --path"
}

@test "exit-worktree fails -> released=error, still exit 0" {
  deploy
  fail_with exit-worktree lease-service-unavailable "租约服务不可用"
  fail_with remove-worktree held-by-others "还有其他持有者"
  run bash "$SCRIPT" --path "$W"
  [ "$status" -eq 0 ]
  has_line "worktree=$W"
  has_line "released=error"
  has_line "removed=no"
  has_line "reason=held-by-others"
  [[ "$output" == *"detail="*"租约服务不可用"* ]] || false
}

@test "no merge_target -> reason=no-merge-target" {
  deploy no-merge-target
  run bash "$SCRIPT" --path "$W"
  [ "$status" -eq 0 ]
  has_line "released=yes"
  has_line "removed=no"
  has_line "reason=no-merge-target"
  not_logged "remove-worktree --path"
}

@test "relative --path -> exit 2" {
  run bash "$SCRIPT" --path .worktrees/feature+x
  [ "$status" -eq 2 ]
  run bash "$SCRIPT" --bogus
  [ "$status" -eq 2 ]
  run bash "$SCRIPT" --path
  [ "$status" -eq 2 ]
  [ ! -e "$CTL_LOG" ]
}
