#!/usr/bin/env bash
# leave-worktree.sh —「离开」在宿主离开之后的部分：画布节点内释放本节点对被离开 worktree 的占用，
# 再经 App 做删除检查（agent-canvas-ctl remove-worktree）。删不删全由 App 判定，本脚本只做调用前的
# 本地守卫并原样报告结果。
#
# 用法：leave-worktree.sh [--path <离开前所在工作区的绝对路径>]
#   在宿主离开之后运行。不给 --path 时按身份查本节点持有的 worktree，恰好一个才处理。
#
# stdout：先一行 canvas=yes|no；之后最多一个 worktree 一组：
#   worktree=<绝对路径>
#   released=yes|no|error|skipped   exit-worktree 的 released；skipped 表示没释放（started-here、cwd-inside）
#   removed=yes|no
#   reason=<原因>        removed=no 时：started-here、cwd-inside、app-too-old、no-merge-target、
#                        inspect-worktree.sh 的 reason（如 workflow-not-deployed），或 remove-worktree 的 code
#                        （held-by-others、not-merged、dirty、locked、open-window、trapped-session、
#                        session-scan-failed、already-removed、lease-service-unavailable、not-ready …）；
#                        remove-worktree 失败但取不到 code 时为 remove-failed
#   branch_kept=<分支>   删成时保留的分支
#   detail=<原文>        失败原文（单行；多处失败用 " | " 连接）
# 不处理时（不出 worktree 组）：
#   lookup=none                   没给 --path，本节点没有持有任何 worktree
#   lookup=ambiguous + candidate= 没给 --path，本节点持有多个，逐行列出候选路径，请带 --path 重来
#   lookup=error + detail=        查身份或租约失败（给了 --path 时前面有 worktree= 行）
# 画布外（AGENT_CANVAS_NODE_TOKEN 为空，或没有 agent-canvas-ctl）只输出 canvas=no，不调用任何 ctl。
#
# 判定顺序：画布 → 确定 W → started-here / cwd-inside（不释放、不删）→ exit-worktree（失败只记录）
#   → App 版本（help remove-worktree 须列出 trapped-session 与 open-window，否则 app-too-old）
#   → merge_target（同目录 inspect-worktree.sh --path W）→ remove-worktree --path W --merged-into <目标>
#
# 退出码：0 正常（含所有「不删」）；2 用法错误（--path 缺参数或不是绝对路径、未知参数）。
#
# 不自己删 worktree、不删分支、不加 --force：删除只经 agent-canvas-ctl remove-worktree。
# bash + jq，兼容 macOS 自带的 bash 3.2。

set -uo pipefail

usage() {
  echo "用法：leave-worktree.sh [--path <绝对路径>]${1:+（$1）}" >&2
  exit 2
}

path=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --path)
      [[ $# -ge 2 && -n "$2" ]] || usage "--path 缺少参数"
      [[ "$2" == /* ]] || usage "--path 须为绝对路径：$2"
      path="$2"; shift 2 ;;
    *) usage "未知参数：$1" ;;
  esac
done

if [[ -z "${AGENT_CANVAS_NODE_TOKEN:-}" ]] || ! command -v agent-canvas-ctl >/dev/null 2>&1; then
  echo "canvas=no"
  exit 0
fi
echo "canvas=yes"

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
errf="$(mktemp "${TMPDIR:-/tmp}/leave-worktree.XXXXXX")" || errf="/dev/null"
trap '[[ "$errf" != /dev/null ]] && rm -f "$errf"' EXIT

# ── ctl <子命令…>：stdout 进 CTL_OUT，退出码进 CTL_RC；失败时 CTL_CODE / CTL_MSG 取自 stderr ──
# 租约能力失败时 CLI 把 { ok:false, code, message } 写到 stderr 并退出 1；HTTP 等错误则是纯文本。
CTL_OUT=""; CTL_RC=0; CTL_CODE=""; CTL_MSG=""
ctl() {
  local err
  CTL_OUT="$(agent-canvas-ctl "$@" 2>"$errf")"; CTL_RC=$?
  CTL_CODE=""; CTL_MSG=""
  [[ "$CTL_RC" -eq 0 ]] && return 0
  err="$(cat "$errf" 2>/dev/null)"
  CTL_CODE="$(printf '%s' "$err" | jq -r '.code // empty' 2>/dev/null)"
  CTL_MSG="$(printf '%s' "$err" | jq -r '.message // empty' 2>/dev/null)"
  [[ -z "$CTL_MSG" ]] && CTL_MSG="$err"
  [[ -z "$CTL_MSG" ]] && CTL_MSG="agent-canvas-ctl $1 退出码 $CTL_RC"
  CTL_MSG="$(printf '%s' "$CTL_MSG" | tr '\r\n' '  ')"
  return 1
}

lookup_error() { # lookup_error <原文>
  echo "lookup=error"
  echo "detail=$(printf '%s' "$1" | tr '\r\n' '  ')"
  exit 0
}

if ! command -v jq >/dev/null 2>&1; then
  [[ -n "$path" ]] && echo "worktree=$path"
  lookup_error "缺少 jq，无法解析 agent-canvas-ctl 的返回"
fi

# ── 身份 ────────────────────────────────────────────────────────────────────
if ! ctl whoami; then
  [[ -n "$path" ]] && echo "worktree=$path"
  lookup_error "whoami 失败：$CTL_MSG"
fi
me="$(printf '%s' "$CTL_OUT" | jq -r '.id // empty' 2>/dev/null)"
if [[ -z "$me" ]]; then
  [[ -n "$path" ]] && echo "worktree=$path"
  lookup_error "whoami 返回里没有 id"
fi

# ── 确定 W：给了 --path 用它；否则按身份查，本节点是有效或待定持有者的恰好一个才用 ──
if [[ -z "$path" ]]; then
  repo="$(pwd -P)"
  ctl list-worktree-leases --repo "$repo" || lookup_error "$CTL_MSG"
  held="$(printf '%s' "$CTL_OUT" | jq -r --arg id "$me" \
    '.worktrees[]? | select(any(.holders[]?; .nodeId == $id and (.validity == "valid" or .validity == "pending"))) | .path' 2>/dev/null)" \
    || lookup_error "list-worktree-leases 返回无法解析"
  count=0
  [[ -n "$held" ]] && count="$(printf '%s\n' "$held" | grep -c .)"
  if [[ "$count" -eq 0 ]]; then
    echo "lookup=none"
    exit 0
  fi
  if [[ "$count" -gt 1 ]]; then
    echo "lookup=ambiguous"
    printf '%s\n' "$held" | while IFS= read -r p; do echo "candidate=$p"; done
    exit 0
  fi
  path="$held"
fi

echo "worktree=$path"

details=""
add_detail() { if [[ -z "$details" ]]; then details="$1"; else details="$details | $1"; fi; }
finish() { # finish <released> <removed> [reason] [branch_kept]
  echo "released=$1"
  echo "removed=$2"
  [[ -n "${3:-}" ]] && echo "reason=$3"
  [[ -n "${4:-}" ]] && echo "branch_kept=$4"
  [[ -n "$details" ]] && echo "detail=$details"
  exit 0
}

# ── 节点没有真正离开：持有来源含 spawn-cwd（主判据），或脚本的 pwd 在 W 内（补充）──
# 查不到租约就判断不了是不是启动在 W 里，不释放也不删（释放会让停止后删除漏掉 W）。
ctl get-worktree-lease --path "$path" || lookup_error "get-worktree-lease 失败：$CTL_MSG"
started="$(printf '%s' "$CTL_OUT" | jq -r --arg id "$me" \
  '[.lease.holders[]? | select(.nodeId == $id) | select(.first.source == "spawn-cwd" or .last.source == "spawn-cwd")] | length' 2>/dev/null)" \
  || lookup_error "get-worktree-lease 返回无法解析"
[[ "${started:-0}" -gt 0 ]] && finish skipped no started-here

w_real="$(cd "$path" 2>/dev/null && pwd -P)" || w_real="$path"
cwd="$(pwd -P)"
if [[ "$cwd" == "$w_real" || "$cwd" == "$w_real"/* || "$cwd" == "$path" || "$cwd" == "$path"/* ]]; then
  finish skipped no cwd-inside
fi

# ── 释放占用：失败只记入报告，继续做删除检查 ──────────────────────────────────
if ctl exit-worktree --path "$path"; then
  case "$(printf '%s' "$CTL_OUT" | jq -r '.released' 2>/dev/null)" in
    true) released="yes" ;;
    false) released="no" ;;
    *) released="error"; add_detail "exit-worktree 返回无法解析" ;;
  esac
else
  released="error"
  add_detail "exit-worktree：$CTL_MSG"
fi

# ── App 版本：旧 remove-worktree 没有困住会话与窗口检查，自动删除不安全 ──────
if ! ctl help remove-worktree || [[ "$CTL_OUT" != *trapped-session* || "$CTL_OUT" != *open-window* ]]; then
  finish "$released" no app-too-old
fi

# ── merge_target：同目录 inspect-worktree.sh 从基线分支上的 resolved.env 取 ──
inspect_out="$(bash "$here/inspect-worktree.sh" --path "$path" 2>/dev/null)"
inspect_rc=$?
merge_target=""
case "$inspect_rc" in
  0|1) merge_target="$(printf '%s\n' "$inspect_out" | sed -n 's/^merge_target=//p' | head -n 1)" ;;
  4)
    inspect_reason="$(printf '%s\n' "$inspect_out" | sed -n 's/^reason=//p' | head -n 1)"
    finish "$released" no "${inspect_reason:-no-merge-target}"
    ;;
esac
[[ -z "$merge_target" ]] && finish "$released" no no-merge-target

# ── 删除检查：全部判定在 App 的 remove-worktree 里 ────────────────────────────
if ctl remove-worktree --path "$path" --merged-into "$merge_target"; then
  branch_kept="$(printf '%s' "$CTL_OUT" | jq -r '.branchKept // empty' 2>/dev/null)"
  finish "$released" yes "" "$branch_kept"
fi
add_detail "$CTL_MSG"
finish "$released" no "${CTL_CODE:-remove-failed}"
