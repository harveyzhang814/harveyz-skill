#!/bin/bash
# check-similar-branch.sh
# PreToolUse command hook: 用 LLM 语义分析检测相似分支
# 触发条件: git checkout -b 或 git switch -c

set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# 只拦截分支创建命令
if ! echo "$CMD" | grep -qE 'git (checkout -b|switch -c)'; then
  exit 0
fi

# 提取新分支名
NEW_BRANCH=$(echo "$CMD" | grep -oE '(checkout -b|switch -c)\s+\S+' | awk '{print $NF}' | tr -d "'\"")
[ -z "$NEW_BRANCH" ] && exit 0

# 确保在 git 仓库中
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0

# 获取现有分支列表（排除新分支本身和 HEAD）
BRANCHES=$(git -C "$GIT_ROOT" branch 2>/dev/null \
  | sed 's|[ *]*||' \
  | grep -v "^${NEW_BRANCH}$" \
  | grep -v 'HEAD' \
  || true)

[ -z "$BRANCHES" ] && exit 0

# 用 claude -p 做语义相似度分析
BRANCH_LIST=$(echo "$BRANCHES" | head -40)  # 最多传 40 条，避免 token 过多

LLM_RESULT=$(claude -p "You are a git branch similarity checker. Determine if the new branch semantically overlaps with any existing branches.

New branch: $NEW_BRANCH

Existing branches:
$BRANCH_LIST

Rules:
- SIMILAR: same type prefix (feature/, fix/, etc.) AND same feature/module/topic (even if worded differently)
- NOT similar: different type prefix, or completely unrelated topics
- Ignore generic words: add, update, fix, improve, cleanup

Respond with ONLY valid JSON, no explanation:
- If similar branches found: {\"similar\": true, \"matches\": [\"branch-name-1\", \"branch-name-2\"]}
- If none found: {\"similar\": false}" 2>/dev/null)

# 解析 LLM 结果
IS_SIMILAR=$(echo "$LLM_RESULT" | jq -r '.similar // false' 2>/dev/null || echo "false")

if [ "$IS_SIMILAR" = "true" ]; then
  # 格式化相似分支列表
  MATCH_LIST=$(echo "$LLM_RESULT" | jq -r '.matches[]' 2>/dev/null | sed 's/^/  • /' | tr '\n' '|' | sed 's/|$//' | tr '|' '\n')

  MSG="⚠️ BRANCH_GUARD: 发现语义相似的已有分支，建议复用而非新建。

新分支: $NEW_BRANCH
相似分支:
$MATCH_LIST

请询问用户：是否复用已有分支？
若选择复用，将同步 staging 最新代码：
  git checkout <branch>
  git fetch origin
  git merge origin/staging"

  jq -n --arg msg "$MSG" \
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","additionalContext":$msg}}'
fi

exit 0
