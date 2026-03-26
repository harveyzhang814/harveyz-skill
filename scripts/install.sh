#!/bin/bash
# Harvey Skills — 依赖安装脚本
# 目前 harvey-plain 无外部依赖，预留扩展用

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$(dirname "$SCRIPT_DIR")/skills"

echo "Harvey Skills — 检查依赖..."

# harvey-card 依赖检查（预留）
CARD_DIR="$SKILLS_DIR/harvey-card"
if [ -d "$CARD_DIR" ] && [ -f "$CARD_DIR/package.json" ]; then
    echo "→ 发现 harvey-card，安装 Playwright 依赖..."
    cd "$CARD_DIR"
    npm install
    npx playwright install chromium
    echo "✓ harvey-card 依赖安装完成"
else
    echo "→ 无 harvey-card，跳过"
fi

echo "✓ 依赖检查完成"
