#!/bin/sh
# install-git-hooks.sh
# 独立激活脚本：在已有 .githooks/ 目录的项目中重新设置 core.hooksPath。
# 适用场景：克隆仓库后首次激活，或 git config 被重置后修复。
#
# 完整的 hook 生成请通过 /git-workflow-init skill 完成（读取 workflow-config.yml）。

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/.githooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo "❌ 未找到 .githooks/ 目录。请先运行 /git-workflow-init skill 完成完整初始化。"
    exit 1
fi

git config core.hooksPath .githooks
echo "✅ core.hooksPath 已设置为 .githooks"

INSTALLED=$(find "$HOOKS_DIR" -maxdepth 1 -type f | sort | xargs -I{} basename {} 2>/dev/null | tr '\n' ' ')
echo "   已激活的 hooks：${INSTALLED:-（无）}"
