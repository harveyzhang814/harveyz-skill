# 全栈调试环境参考

## 日志目录

```
/tmp/fsd-test-node-spa/tmp/logs/
├── backend.log    — Express 进程 stdout/stderr（含 ISO 8601 时间戳）
└── browser.log    — Vite SPA 浏览器 console（通过 Vite plugin 捕获）
```

## 来源接入方式

### backend.log — Express 裸进程

```bash
# 启动并重定向输出（带时间戳注入）
node server.js 2>&1 | awk '{ print strftime("%Y-%m-%dT%H:%M:%S.000Z"), $0; fflush() }' \
  >> tmp/logs/backend.log &
echo $! > tmp/logs/backend.pid
```

停止：`kill $(cat tmp/logs/backend.pid)`

### browser.log — React SPA (Vite)

在 `vite.config.js` 中添加 console 捕获 plugin，或在 `src/main.jsx` 中注入：

```js
// src/main.jsx 顶部注入（仅开发模式）
if (import.meta.env.DEV) {
  const orig = { log: console.log, warn: console.warn, error: console.error };
  const send = (level, args) => {
    const msg = `${new Date().toISOString()} [${level}] ${args.join(' ')}`;
    fetch('/api/__log', { method: 'POST', body: JSON.stringify({ msg }) });
  };
  ['log', 'warn', 'error'].forEach(l => {
    console[l] = (...a) => { orig[l](...a); send(l, a.map(String)); };
  });
}
```

后端新增 `/api/__log` 端点写入 `tmp/logs/browser.log`。

## 验证脚本

```bash
bash harness/debug/verify-logs.sh
```

全部 OK 才继续测试场景。

## 启动方式（模式 A — 独立启动）

```bash
# 1. 启动日志捕获
mkdir -p tmp/logs
node server.js 2>&1 | awk '{ print strftime("%Y-%m-%dT%H:%M:%S.000Z"), $0; fflush() }' >> tmp/logs/backend.log &

# 2. 启动 Vite（带 browser.log 注入）
npm run dev

# 3. 验证环境
bash harness/debug/verify-logs.sh
```

## 查询方式

```bash
# 查看 Express 最新错误
grep -E "ERROR|error|Error" tmp/logs/backend.log | tail -20

# 查看浏览器 console 错误
grep "\[error\]" tmp/logs/browser.log | tail -20

# 跨层时序合并（按 ISO 时间戳排序）
sort -m <(grep "^2" tmp/logs/backend.log) <(grep "^2" tmp/logs/browser.log) | tail -50
```

## 清理

```bash
kill $(cat tmp/logs/backend.pid) 2>/dev/null || true
rm -rf tmp/logs/
```
