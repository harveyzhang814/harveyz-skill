#!/usr/bin/env bats
# create-worktree.sh：「准备」的新建一步（worktree-remove-on-leave spec §4.6、D14，判据 J8）。
# 画布内经 agent-canvas-ctl create-worktree 新建并登记，失败不退回 git worktree add；画布外照旧 git worktree add。
# agent-canvas-ctl 用桩：PATH 前置 $TMP/bin/agent-canvas-ctl，按子命令读 $FX/<子命令>.{out,err,rc}
# 夹具作答（成功 JSON 进 stdout；ok:false 的 JSON 进 stderr、退出 1），每次调用把参数追加到 $TMP/ctl.log。
# git 用包装：PATH 前置 $TMP/bin/git，把参数追加到 $TMP/git.log 后交给真实 git。

SCRIPT="${BATS_TEST_DIRNAME}/../scripts/create-worktree.sh"

setup() {
  TMP="$(mktemp -d)"; cd "$TMP" || exit 1; TMP="$(pwd -P)"
  REPO="$TMP/repo"; W="$TMP/repo/.worktrees/feature+x"
  git init -q -b main "$REPO"
  git -C "$REPO" config user.email t@example.com
  git -C "$REPO" config user.name t
  echo x > "$REPO/seed.txt"
  git -C "$REPO" add seed.txt && git -C "$REPO" commit -qm seed
  git -C "$REPO" branch staging main

  FX="$TMP/fx"; CTL_LOG="$TMP/ctl.log"; GIT_LOG="$TMP/git.log"; export FX CTL_LOG GIT_LOG
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
  REAL_GIT="$(command -v git)"
  printf '#!/usr/bin/env bash\necho "$*" >> "$GIT_LOG"\nexec "%s" "$@"\n' "$REAL_GIT" > "$TMP/bin/git"
  chmod +x "$TMP/bin/agent-canvas-ctl" "$TMP/bin/git"
  export PATH="$TMP/bin:$PATH"
  export AGENT_CANVAS_NODE_TOKEN="tok-test"
  cd "$REPO" || exit 1
}
teardown() { [[ -n "${TMP:-}" && "$TMP" == /*/* ]] && rm -rf "$TMP"; }

create_ok() { # create_ok <branch>
  printf '{"ok":true,"path":"%s","branch":"%s","reused":false,"leased":true}\n' "$W" "$1" > "$FX/create-worktree.out"
}

has_line() { printf '%s\n' "$output" | grep -qxF -- "$1"; }
logged() { [[ -f "$CTL_LOG" ]] && grep -qF -- "$1" "$CTL_LOG"; }
not_logged() { ! logged "$1"; }
no_git_worktree_add() { ! { [[ -f "$GIT_LOG" ]] && grep -q 'worktree add' "$GIT_LOG"; }; }

@test "J8 in canvas, new branch -> ctl create-worktree with --base" {
  create_ok feature/x
  run bash "$SCRIPT" --branch feature/x --base staging --path "$W" --repo "$REPO"
  [ "$status" -eq 0 ]
  has_line "created=yes"
  has_line "path=$W"
  has_line "branch=feature/x"
  logged "create-worktree --branch feature/x --base staging --path $W --repo $REPO"
  no_git_worktree_add
}

@test "J8 in canvas, existing branch -> no --base" {
  git -C "$REPO" branch feature/x main
  create_ok feature/x
  run bash "$SCRIPT" --branch feature/x --path "$W" --repo "$REPO"
  [ "$status" -eq 0 ]
  has_line "created=yes"
  has_line "branch=feature/x"
  logged "create-worktree --branch feature/x --path $W --repo $REPO"
  not_logged "--base"
  no_git_worktree_add
}

@test "J8 ctl fails -> created=no, exit 1, no git worktree add" {
  printf '{"ok":false,"code":"branch-in-use","message":"分支已被 /x 占用"}\n' > "$FX/create-worktree.err"
  echo 1 > "$FX/create-worktree.rc"
  run bash "$SCRIPT" --branch feature/x --base staging --path "$W" --repo "$REPO"
  [ "$status" -eq 1 ]
  has_line "created=no"
  has_line "reason=branch-in-use"
  has_line "detail=分支已被 /x 占用"
  no_git_worktree_add
  [ ! -e "$W" ]
  # 拿不到结构化 code（HTTP 等纯文本错误）也不退回
  printf 'connect ECONNREFUSED\n' > "$FX/create-worktree.err"
  run bash "$SCRIPT" --branch feature/x --base staging --path "$W" --repo "$REPO"
  [ "$status" -eq 1 ]
  has_line "created=no"
  has_line "reason=create-failed"
  has_line "detail=connect ECONNREFUSED"
  no_git_worktree_add
  [ ! -e "$W" ]
}

@test "J8 outside canvas -> git worktree add, no ctl" {
  export AGENT_CANVAS_NODE_TOKEN=""
  run bash "$SCRIPT" --branch feature/x --base staging --path "$W" --repo "$REPO"
  [ "$status" -eq 0 ]
  has_line "created=yes"
  has_line "path=$W"
  has_line "branch=feature/x"
  [ ! -e "$CTL_LOG" ]
  grep -qF -- "-C $REPO worktree add $W -b feature/x staging" "$GIT_LOG"
  [ "$(git -C "$W" rev-parse --abbrev-ref HEAD)" = "feature/x" ]
  # 已存在的分支：不带 -b，直接挂上
  W2="$TMP/repo/.worktrees/feature+y"
  git -C "$REPO" branch feature/y main
  run bash "$SCRIPT" --branch feature/y --path "$W2" --repo "$REPO"
  [ "$status" -eq 0 ]
  has_line "created=yes"
  grep -qF -- "-C $REPO worktree add $W2 feature/y" "$GIT_LOG"
  [ "$(git -C "$W2" rev-parse --abbrev-ref HEAD)" = "feature/y" ]
}
