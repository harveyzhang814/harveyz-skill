#!/usr/bin/env bash
# validate-handoff.sh — 校验一份交接文档的 frontmatter 与必备正文结构。
#
# 用法：validate-handoff.sh <交接文档.md>
# 退出码：0 通过（可能带 WARN）/ 1 校验失败（ERROR 一次全列出）/ 2 用法错误
#
# 只对单份文档跑（author 的完整性门禁、verify 开头各一次），刻意不批量扫目录：
# 存量的旧交接文档没有 frontmatter，不该被这条规则追认；而新文档漏写 frontmatter
# 会被硬拦（若改成"没有 frontmatter 就跳过"，忘写的新文档反而静默放行）。
#
# 纯 bash + coreutils，无外部依赖——这个 skill 要在任意仓库里能跑。

set -uo pipefail

LEGAL_STATUSES=(待执行 执行中 待验收 已验收 打回)
LEGAL_ACCEPTANCE=(hard soft)
REQUIRED_FIELDS=(status date acceptance)
UUID_RE='^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'

errors=()
warns=()
err() { errors+=("ERROR: $1"); }
warn() { warns+=("WARN: $1"); }

file="${1:-}"
if [[ -z "$file" ]]; then
  echo "用法：validate-handoff.sh <交接文档.md>" >&2
  exit 2
fi
if [[ ! -f "$file" ]]; then
  echo "用法：validate-handoff.sh <交接文档.md>（文件不存在：${file}）" >&2
  exit 2
fi

base="$(basename "$file")"
dir="$(cd "$(dirname "$file")" && pwd)"
toplevel="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null || true)"

# ── frontmatter 抽取：首行必须是 ---，到下一个 --- 为止 ─────────────────────
fm="$(awk 'NR==1{if($0!="---") exit; next} /^---[[:space:]]*$/{exit} {print}' "$file")"

has_field() { printf '%s\n' "$fm" | grep -qE "^$1:"; }
field() {
  printf '%s\n' "$fm" \
    | grep -E "^$1:" | head -1 \
    | sed -E "s/^$1:[[:space:]]*//" \
    | sed -E 's/[[:space:]]+#.*$//' \
    | sed -E 's/[[:space:]]+$//' \
    | tr -d '"'"'"
}
join_by() { local IFS='|'; echo "$*"; }

if [[ -z "$fm" ]]; then
  err "缺 frontmatter：文档首行须是 --- 开启的 YAML frontmatter 块"
else
  for f in "${REQUIRED_FIELDS[@]}"; do
    has_field "$f" || err "缺必填字段 $f"
  done

  if has_field status; then
    v="$(field status)"
    printf '%s\n' "${LEGAL_STATUSES[@]}" | grep -qx -- "$v" \
      || err "status 非法值「${v}」，合法值：$(join_by "${LEGAL_STATUSES[@]}")"
  fi

  if has_field acceptance; then
    v="$(field acceptance)"
    printf '%s\n' "${LEGAL_ACCEPTANCE[@]}" | grep -qx -- "$v" \
      || err "acceptance 非法值「${v}」，合法值：$(join_by "${LEGAL_ACCEPTANCE[@]}")"
  fi

  if has_field date; then
    v="$(field date)"
    if [[ ! "$v" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
      err "date 格式须为 YYYY-MM-DD，实为「${v}」"
    elif [[ "$base" =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2})- ]]; then
      [[ "${BASH_REMATCH[1]}" != "$v" ]] \
        && err "date（${v}）与文件名日期段（${BASH_REMATCH[1]}）不一致"
    else
      err "文件名缺日期段，应形如 YYYY-MM-DD-<topic>-handoff.md，实为「${base}」"
    fi
  fi

  if has_field branch; then
    v="$(field branch)"
    if [[ -z "$v" ]]; then
      err "branch 字段为空——写了这个字段就得给出真实分支名，否则整行删掉"
    elif [[ -z "$toplevel" ]]; then
      warn "文档不在 git 仓库里，跳过 branch 存在性校验：$v"
    elif ! git -C "$dir" rev-parse --verify --quiet "refs/heads/$v" >/dev/null 2>&1; then
      err "branch 在本仓库不存在：${v}（接手方会照着它 git worktree add，写错就找不到活）"
    fi
  fi

  # worktree：author 在 author 阶段建好交接工作区后填的绝对路径，与 branch 成对。
  # 接手方照它进去开工，accept 方照它回来验收——由 author 建、也只有 author 一直知道
  # 它在哪，这是交接能闭环的前提。分级依据——**路径类问题一律 WARN，结构性
  # 写错才 ERROR**：ERROR 意味着"这份文档不合规，打回原 session"，而路径是有时效的
  # （accept 可能几天后、甚至换台机器跑），路径不在不等于文档写错。只有相对路径是
  # 无论何时都用不了的（accept 方的 cwd 与接手方不同），判 ERROR。
  if has_field worktree; then
    wt="$(field worktree)"
    if [[ -n "$wt" ]]; then
      if [[ "$wt" != /* ]]; then
        err "worktree 须是绝对路径，实为「${wt}」（accept 方的 cwd 与接手方不同，相对路径解析不出来）"
      elif [[ ! -d "$wt" ]]; then
        warn "worktree 路径不存在：${wt}（可能已被 remove；accept 方退回按 branch 自建 detached worktree）"
      else
        wt_top="$(git -C "$wt" rev-parse --show-toplevel 2>/dev/null || true)"
        wt_real="$(cd "$wt" && pwd -P)"
        if [[ -z "$wt_top" ]]; then
          warn "worktree 不是 git 工作区：${wt}"
        elif [[ "$wt_top" != "$wt_real" ]]; then
          warn "worktree 不是工作区根目录：${wt}（它所在的工作区根是 ${wt_top}）"
        else
          wt_branch="$(git -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
          if has_field branch && [[ -n "$(field branch)" ]]; then
            [[ "$wt_branch" != "$(field branch)" ]] \
              && warn "worktree 当前分支（${wt_branch}）与 branch 字段（$(field branch)）不一致：${wt}"
          else
            warn "填了 worktree 却没填 branch——两者成对；工作区一旦被误删，就没有兜底线索能重建了"
          fi
        fi
      fi
    fi
  fi

  # branch 填了、worktree 没填：说明接手方要去另一条分支上开工，而 author 没把工作区建好。
  # 判 WARN 不判 ERROR——「就地同分支续做」时两个字段都不该填，脚本分不出 author 是漏填了
  # 还是这次交接本就不需要独立工作区；只有「填了一半」才是确定可疑的。
  if has_field branch && [[ -n "$(field branch)" ]]; then
    if ! has_field worktree || [[ -z "$(field worktree)" ]]; then
      warn "填了 branch 却没填 worktree——author 应当建好交接工作区并填上，否则接手方不知道去哪开工"
    fi
  fi

  # 两个节点字段留空 = 视同未填：target_node 在模板里就是留给接手方回填的占位，
  # author 写完时它本来就该是空的。只有填了非法值才报错。
  for f in source_node target_node; do
    if has_field "$f"; then
      v="$(field "$f")"
      [[ -z "$v" ]] && continue
      [[ "$v" =~ $UUID_RE ]] || err "$f 不是合法的节点 uuid：「${v}」"
    fi
  done
fi

# ── 正文必备结构 ───────────────────────────────────────────────────────────
grep -qE '^##[[:space:]]*最小验收锚点' "$file" \
  || err "正文缺「## 最小验收锚点」一节——这是 accept 阶段唯一固定依据，任何情况下不能省"
grep -qE '\*\*交接目的\*\*' "$file" \
  || err "正文缺「**交接目的**」行——任何情况下不能省"

# ── 引用路径（只警告，不阻断：可能指向本次待创建的产物）────────────────────
while IFS= read -r link; do
  [[ -z "$link" ]] && continue
  [[ "$link" =~ ^(https?|mailto|ftp): ]] && continue
  [[ "$link" == \#* ]] && continue
  link="${link%%#*}"
  [[ -z "$link" || "$link" == *"<"* || "$link" == *">"* ]] && continue
  found=0
  for cand in "$dir/$link" "$link" ${toplevel:+"$toplevel/$link"}; do
    [[ -e "$cand" ]] && { found=1; break; }
  done
  [[ $found -eq 0 ]] && warn "引用路径不存在：$link"
done < <(grep -oE '\]\([^)]+\)' "$file" | sed -E 's/^\]\(//; s/\)$//')

# ── 报告 ───────────────────────────────────────────────────────────────────
for w in "${warns[@]:-}"; do [[ -n "$w" ]] && echo "$w"; done
for e in "${errors[@]:-}"; do [[ -n "$e" ]] && echo "$e"; done

if [[ ${#errors[@]} -gt 0 ]]; then
  echo "校验失败：${#errors[@]} 条 ERROR（补齐后重跑）"
  exit 1
fi
exit 0
