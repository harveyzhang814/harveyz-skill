#!/usr/bin/env bash
# create-worktree.sh —「准备」的新建一步。分支名、基线、路径由调用方按 manage-worktree 的规则推断后传入，
# 本脚本不推断、不检测，只负责建：
#   画布节点内：agent-canvas-ctl create-worktree，新建与登记占用（来源 create）一步完成；
#               失败按返回的 code 报告并停下，不退回 git worktree add（退回会产生未登记的 worktree）。
#   画布外：    git -C <repo> worktree add <path> <branch>，或带 --base 时 git -C <repo> worktree add <path> -b <branch> <base>。
#
# 用法：create-worktree.sh --branch <分支> [--base <基线>] --path <绝对路径> --repo <绝对路径>
#   期望分支已存在且没被 checkout → 不给 --base；其他新建情况 → 给 --base。
#
# stdout（每行一个 key=value）：
#   成功：created=yes、path=<绝对路径>、branch=<分支>；画布内另有 leased=yes|no（no 时 detail= 登记失败原文，
#         「进入」后补调的 claim-worktree 会补登记）
#   失败：created=no、reason=<code>、detail=<原文（单行）>
#     画布内 code 取 App 返回的 code（no-node-identity、not-a-repo、path-exists、branch-in-use、branch-exists、
#     base-required、base-not-found、git-failed、not-ready、lease-service-unavailable …），
#     取不到结构化 code（HTTP 等纯文本错误）时为 create-failed；画布外 git 失败为 git-failed。
#
# 画布判定：AGENT_CANVAS_NODE_TOKEN 非空且 command -v agent-canvas-ctl 有结果；画布外不调用任何 ctl。
# 退出码：0 已建好；1 没建成；2 用法错误。
# bash + jq，兼容 macOS 自带的 bash 3.2。

set -uo pipefail

usage() {
  echo "用法：create-worktree.sh --branch <分支> [--base <基线>] --path <绝对路径> --repo <绝对路径>${1:+（$1）}" >&2
  exit 2
}

branch=""; base=""; path=""; repo=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch|--base|--path|--repo)
      [[ $# -ge 2 && -n "$2" ]] || usage "$1 缺少参数"
      case "$1" in
        --branch) branch="$2" ;;
        --base) base="$2" ;;
        --path) [[ "$2" == /* ]] || usage "--path 须为绝对路径：$2"; path="$2" ;;
        --repo) [[ "$2" == /* ]] || usage "--repo 须为绝对路径：$2"; repo="$2" ;;
      esac
      shift 2 ;;
    *) usage "未知参数：$1" ;;
  esac
done
[[ -n "$branch" ]] || usage "缺少 --branch"
[[ -n "$path" ]] || usage "缺少 --path"
[[ -n "$repo" ]] || usage "缺少 --repo"

one_line() { printf '%s' "$1" | tr '\r\n' '  '; }
fail() { # fail <reason> <原文>
  echo "created=no"
  echo "reason=$1"
  [[ -n "$2" ]] && echo "detail=$(one_line "$2")"
  exit 1
}

errf="$(mktemp "${TMPDIR:-/tmp}/create-worktree.XXXXXX")" || errf="/dev/null"
trap '[[ "$errf" != /dev/null ]] && rm -f "$errf"' EXIT

# ── 画布外：照旧 git worktree add ─────────────────────────────────────────────
if [[ -z "${AGENT_CANVAS_NODE_TOKEN:-}" ]] || ! command -v agent-canvas-ctl >/dev/null 2>&1; then
  if [[ -n "$base" ]]; then
    git -C "$repo" worktree add "$path" -b "$branch" "$base" >/dev/null 2>"$errf"
  else
    git -C "$repo" worktree add "$path" "$branch" >/dev/null 2>"$errf"
  fi
  rc=$?
  [[ "$rc" -eq 0 ]] || fail git-failed "$(cat "$errf" 2>/dev/null)"
  echo "created=yes"
  echo "path=$path"
  echo "branch=$branch"
  exit 0
fi

# ── 画布内：经 App 新建并登记 ─────────────────────────────────────────────────
args=(create-worktree --branch "$branch")
[[ -n "$base" ]] && args+=(--base "$base")
args+=(--path "$path" --repo "$repo")
out="$(agent-canvas-ctl "${args[@]}" 2>"$errf")"; rc=$?

if [[ "$rc" -ne 0 ]]; then
  # 租约能力失败时 CLI 把 { ok:false, code, message } 写到 stderr 并退出非零；HTTP 等错误则是纯文本
  err="$(cat "$errf" 2>/dev/null)"
  code="$(printf '%s' "$err" | jq -r '.code // empty' 2>/dev/null)"
  msg="$(printf '%s' "$err" | jq -r '.message // empty' 2>/dev/null)"
  [[ -z "$msg" ]] && msg="$err"
  [[ -z "$msg" ]] && msg="agent-canvas-ctl create-worktree 退出码 $rc"
  fail "${code:-create-failed}" "$msg"
fi

got_path="$(printf '%s' "$out" | jq -r '.path // empty' 2>/dev/null)"
got_branch="$(printf '%s' "$out" | jq -r '.branch // empty' 2>/dev/null)"
leased="$(printf '%s' "$out" | jq -r 'if .leased == false then "no" else "yes" end' 2>/dev/null)"
echo "created=yes"
echo "path=${got_path:-$path}"
echo "branch=${got_branch:-$branch}"
echo "leased=${leased:-yes}"
if [[ "$leased" == "no" ]]; then
  lease_err="$(printf '%s' "$out" | jq -r '.leaseError // empty' 2>/dev/null)"
  echo "detail=$(one_line "${lease_err:-已建好但登记占用失败}")"
fi
exit 0
