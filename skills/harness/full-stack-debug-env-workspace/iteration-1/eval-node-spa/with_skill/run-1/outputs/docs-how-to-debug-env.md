# 如何启动全栈调试环境

## 概述

本环境为 my-app（Node.js Express + React SPA）搭建了两层独立日志捕获：

- **backend.log** — Express 进程的所有 stdout/stderr，包括请求日志、错误堆栈、自定义 console.log
- **browser.log** — 前端 Vite 开发服务器中 SPA 的 console 输出（需注入 hook）

每层独立文件，互不干扰；所有行首均有 ISO 8601 时间戳，支持跨层时序对比。

## 前提条件

- Node.js 已安装
- `npm install` 已完成
- `tmp/` 已加入 `.gitignore`

## 启动步骤

### 1. 创建日志目录

```bash
mkdir -p tmp/logs
```

### 2. 启动后端（带日志捕获）

```bash
node server.js 2>&1 \
  | awk '{ print strftime("%Y-%m-%dT%H:%M:%S.000Z"), $0; fflush() }' \
  >> tmp/logs/backend.log &
echo $! > tmp/logs/backend.pid
echo "后端已启动，日志 -> tmp/logs/backend.log"
```

### 3. 注入浏览器 console hook

在 `src/main.jsx` 顶部加入以下代码（见 `harness/debug/README.md` 完整实现），然后启动 Vite：

```bash
npm run dev
```

### 4. 验证环境就绪

```bash
bash harness/debug/verify-logs.sh
```

看到 `所有常驻来源 OK` 才继续。

## 排查问题

**backend.log 为空**
- 检查 Express 是否在运行：`lsof -i:3001`
- 确认 PID 文件存在：`cat tmp/logs/backend.pid`

**browser.log 为空**
- 确认 `src/main.jsx` 中已加入 console hook
- 在浏览器中执行一次操作，触发 console 输出
- 检查 `/api/__log` 端点是否已在 server.js 中注册

**如何新增来源**
1. 在 `harness/debug/README.md` 的来源列表中添加新行
2. 在 `verify-logs.sh` 中添加对应 `check_source` 调用
3. 重新运行验证脚本确认 OK

## 关闭环境

```bash
# 停止后端捕获进程
kill $(cat tmp/logs/backend.pid) 2>/dev/null || true

# 按需清理日志（不强制）
rm -rf tmp/logs/
```

## 验证频率建议

- 每次开始新的 Agent 测试会话前运行一次
- 修改日志捕获配置后运行一次
- CI 中可跳过（CI 有独立日志收集）
