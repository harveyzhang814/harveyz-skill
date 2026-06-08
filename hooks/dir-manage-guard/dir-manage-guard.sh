#!/bin/bash
# dir-manage-guard.sh
# version: 1.0.0
# PreToolUse hook: 检测目标文件是否在受方法论管理的目录中
# 触发条件: Edit / Write 工具调用

set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')

case "$TOOL_NAME" in
  Edit|Write) ;;
  *) exit 0 ;;
esac

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
[ -z "$FILE_PATH" ] && exit 0

# 解析为绝对路径
if [[ "$FILE_PATH" != /* ]]; then
  FILE_PATH="$(pwd)/$FILE_PATH"
fi
DIR=$(dirname "$FILE_PATH")

GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || GIT_ROOT=""

# 向上遍历，查找受方法论管理的目录（含 DIR_METHOD.md 或含 methodology 字段的 INDEX.md）
GOVERNED_DIR=""
CURRENT="$DIR"
DEPTH=0

while [ "$DEPTH" -lt 8 ]; do
  if [ -f "$CURRENT/DIR_METHOD.md" ]; then
    GOVERNED_DIR="$CURRENT"
    break
  fi

  if [ -f "$CURRENT/INDEX.md" ] && grep -q "^methodology:" "$CURRENT/INDEX.md" 2>/dev/null; then
    GOVERNED_DIR="$CURRENT"
    break
  fi

  if [ -n "$GIT_ROOT" ] && [ "$CURRENT" = "$GIT_ROOT" ]; then
    break
  fi
  [ "$CURRENT" = "/" ] && break

  CURRENT=$(dirname "$CURRENT")
  DEPTH=$((DEPTH + 1))
done

[ -z "$GOVERNED_DIR" ] && exit 0

# 构造相对路径用于显示
if [ -n "$GIT_ROOT" ]; then
  REL_DIR="${GOVERNED_DIR#$GIT_ROOT/}"
else
  REL_DIR="$GOVERNED_DIR"
fi

MSG="DIR_MANAGE_GUARD: 文件 \"$(basename "$FILE_PATH")\" 位于受方法论管理的目录 \`$REL_DIR\`。

在继续此次文件操作前，请先调用 \`dir-manage\` skill，由它主导分类、命名和索引更新。"

jq -n --arg msg "$MSG" \
  '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","additionalContext":$msg}}'

exit 0
