#!/usr/bin/env bash
# verify-logs.sh — 验证 docker-app 全栈调试环境
# 运行方式: bash harness/debug/verify-logs.sh
# 前提: docker compose up -d 已运行，日志捕获已启动

set -euo pipefail

LOG_DIR="$(cd "$(dirname "$0")/../.." && pwd)/tmp/logs"
PASS=0
FAIL=0
SKIP=0

ISO8601_PATTERN='^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'

check_source() {
  local name="$1"
  local file="$LOG_DIR/$2"
  local type="${3:-常驻}"

  echo -n "  [$name] ... "

  if [ ! -f "$file" ]; then
    if [ "$type" = "任务驱动型" ]; then
      echo "SKIP (文件不存在，需先入队任务)"
      ((SKIP++)) || true
      return
    else
      echo "MISSING"
      ((FAIL++)) || true
      return
    fi
  fi

  if [ ! -s "$file" ]; then
    if [ "$type" = "任务驱动型" ]; then
      echo "SKIP (文件为空，暂无任务输出)"
      ((SKIP++)) || true
      return
    else
      echo "NO_NEW_OUTPUT (文件为空)"
      ((FAIL++)) || true
      return
    fi
  fi

  local now
  now=$(date +%s)
  local mtime
  mtime=$(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file" 2>/dev/null)
  local age=$((now - mtime))

  if [ $age -gt 60 ]; then
    if [ "$type" = "任务驱动型" ]; then
      echo "SKIP (最后写入 ${age}s 前，暂无活跃任务)"
      ((SKIP++)) || true
      return
    else
      echo "NO_NEW_OUTPUT (最后写入 ${age}s 前)"
      ((FAIL++)) || true
      return
    fi
  fi

  local first_line
  first_line=$(head -1 "$file")
  if ! echo "$first_line" | grep -qE "$ISO8601_PATTERN"; then
    echo "FAIL (行首缺少 ISO 8601 时间戳)"
    ((FAIL++)) || true
    return
  fi

  echo "OK"
  ((PASS++)) || true
}

trigger_requests() {
  echo "--- 触发 API 请求 ---"
  if command -v curl &>/dev/null; then
    curl -sf http://localhost:3000/health -o /dev/null && echo "  GET /health -> OK" || echo "  GET /health -> 跳过（服务未运行）"
  fi
  # worker 是任务驱动型，此处不触发队列任务
  echo ""
}

echo "=============================="
echo " docker-app 日志环境验证"
echo " 日志目录: $LOG_DIR"
echo "=============================="
echo ""

trigger_requests

echo "--- 检查日志来源 ---"
check_source "api.log (Node.js API 容器)" "api.log" "常驻"
check_source "worker.log (Celery Worker)" "worker.log" "任务驱动型"
check_source "db.log (PostgreSQL)" "db.log" "常驻"
echo ""

echo "=============================="
echo " 结果: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo " 说明: SKIP 为任务驱动型来源，暂无活跃任务属正常"
echo "=============================="

if [ $FAIL -gt 0 ]; then
  echo "有来源未就绪，请检查后重试。"
  exit 1
fi

echo "所有常驻来源 OK（任务驱动型 SKIP 正常），可以开始运行测试场景。"
exit 0
