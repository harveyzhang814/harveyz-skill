# Electron 日志最佳实践

适用场景：Electron 桌面应用（含主进程、preload、renderer）

## 时间戳处理

- **主进程 stdout**：通常无时间戳，capture 层注入（python3，跨平台）：
  ```bash
  electron . 2>&1 | python3 -u -c 'import sys,datetime; [print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), l.rstrip(), flush=True) for l in iter(sys.stdin.readline,"")]' >> main.log &
  ```
- **renderer console hook**：在 hook 代码里直接用 `new Date().toISOString()` 生成，已是 ISO 8601，无需额外处理（下方示例已包含）。
- **electron-log 库**：默认格式含时间戳但非 ISO，建议配置 `log.transports.file.format = '[{iso}] [{level}] {text}'`。

## 三条日志路径

| 层 | 日志去向 | 捕获方式 |
|---|---|---|
| 主进程（main.js） | stdout/stderr（终端启动时可见） | 包裹启动命令（策略 B） |
| 内嵌子服务（spawn + pipe） | 主进程 stdout（前缀标识来源） | 同上，无独立文件 |
| preload 脚本 | renderer 的 DevTools console | renderer 层捕获 |
| renderer（页面 JS） | DevTools console（F12） | preload 拦截或 CDP |

**主进程 stdout 和 renderer console 是完全独立的两条路径，必须分别接入。内嵌子服务若通过 pipe 路由到主进程，则合并在主进程日志中，没有独立文件。**

## 主进程捕获

启动时包裹，写入独立文件，注入时间戳：

```bash
LOGS=/tmp/myproject-logs
mkdir -p "$LOGS"

# python3 方案（跨平台，Linux/macOS 均可用）
PY_TS='import sys,datetime; [print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), l.rstrip(), flush=True) for l in iter(sys.stdin.readline,"")]'

electron . 2>&1 | python3 -u -c "$PY_TS" >> "$LOGS/main.log" &
# 或通过 npm script:
npm start 2>&1 | python3 -u -c "$PY_TS" >> "$LOGS/main.log" &
```

如果已通过 GUI 启动（非终端），主进程日志可能写入系统日志：
- macOS：`~/Library/Logs/<AppName>/main.log`（如用 electron-log）
- Windows：`%APPDATA%\<AppName>\logs\`

## Renderer Console 捕获

**方案 A：preload 拦截（推荐，无需修改业务代码）**

在 preload.js 中拦截 console，写入独立的 renderer 日志文件：

```js
// preload.js
const fs = require('fs');
const RENDERER_LOG = process.env.RENDERER_LOG || '/tmp/myproject-logs/renderer.log';

['log', 'info', 'warn', 'error'].forEach(level => {
  const orig = console[level];
  console[level] = (...args) => {
    orig(...args);
    const line = `${new Date().toISOString()} ${level} ${args.map(a =>
      typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' ')}\n`;
    fs.appendFileSync(RENDERER_LOG, line);
  };
});

window.addEventListener('error', e => {
  fs.appendFileSync(RENDERER_LOG,
    `${new Date().toISOString()} uncaught ${e.message} ${e.filename}:${e.lineno}\n`);
});
window.addEventListener('unhandledrejection', e => {
  fs.appendFileSync(RENDERER_LOG,
    `${new Date().toISOString()} unhandledRejection ${e.reason}\n`);
});
```

主进程写自己的日志文件（`main.log`），renderer 写自己的（`renderer.log`），两者独立。

**方案 B：CDP（Chrome DevTools Protocol）**

用于测试框架（Playwright with Electron、Spectron 等），在测试 setup 中注册：

```js
const { _electron: electron } = require('playwright');
const RENDERER_LOG = '/tmp/myproject-logs/renderer.log';
const app = await electron.launch({ args: ['main.js'] });
const page = await app.firstWindow();
page.on('console', msg => {
  const ts = new Date().toISOString();
  fs.appendFileSync(RENDERER_LOG, `${ts} ${msg.type()} ${msg.text()}\n`);
});
```

## 嵌入式子服务（Electron 内嵌 HTTP/gRPC 服务）

Electron 应用常通过 `spawn` 在内部启动一个本地服务（HTTP、gRPC 等），并把子进程的 stdout/stderr pipe 到主进程的 console：

```js
// main-helpers.js 典型模式
httpProcess = spawn('node', ['services/http-server/index.js'], { stdio: ['ignore', 'pipe', 'pipe'] });
httpProcess.stdout.on('data', buf => console.log(`[service-name] ${buf.toString().trimEnd()}`));
httpProcess.stderr.on('data', buf => console.warn(`[service-name] ${buf.toString().trimEnd()}`));
```

**后果：子服务没有独立日志文件**，它的所有输出都以 `[service-name]` 前缀合并进 `main-process.log`。

**识别方法：** 若在第二阶段发现某个服务（如 HTTP API）有进程但找不到独立日志文件，检查 Electron 主进程的启动代码，看是否有 `spawn` + stdout pipe 的模式。

**查询方法：** 不要找独立的 `http.log`，直接在主进程日志里按前缀过滤：
```bash
grep '\[service-name\]' electron/main-process.log
```

**注意：** 这种模式下，子服务的 Bearer token、端口等运行时信息由主进程生成并保存在内存中，外部脚本无法直接读取——验证脚本需要使用主进程保存到文件的 token，而不能从子服务日志里提取。

---

## 常见陷阱

- renderer 的 `console.log` 只在 DevTools 可见，在终端里什么都看不到 → 必须主动挂钩
- contextIsolation=true 时，preload 无法直接 require fs → 需用 ipcRenderer 把日志发到主进程写文件
- Electron 的 `app.getPath('logs')` 返回系统日志目录，可用于固定日志路径
- 生产包里没有 DevTools → 提前在 preload 挂好钩，否则 renderer 日志永久丢失
- **内嵌子服务没有独立日志文件** → 不要找 `http.log`，去主进程日志里按前缀 grep
