# Node.js 进程日志最佳实践

适用场景：裸 Node.js 进程（Express、Fastify、Koa、NestJS、自定义 HTTP 服务等）

## 日志产生方式

Node.js 进程的日志通常来自三条路径：
1. `console.log/warn/error` → stdout/stderr
2. 写日志库（winston、pino、bunyan）→ 文件或 stdout
3. 未捕获异常 / unhandledRejection → stderr

## 时间戳处理

**pino / winston（JSON 格式）**：默认输出包含 ISO 8601 时间戳字段（`time` 或 `timestamp`），格式已符合要求，不需要额外处理。

**console.log 直接输出（无时间戳）**：capture 层注入（python3 方案，跨平台兼容）：
```bash
node server.js 2>&1 | python3 -u -c '
import sys, datetime
for line in iter(sys.stdin.readline, ""):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(ts, line.rstrip(), flush=True)
' >> backend.log
```

**注意：`awk strftime` 仅 Linux（gawk）可用，macOS BSD awk 不支持。统一用 python3 方案可避免平台差异。**

**winston plain text 格式**（形如 `2024-01-15 14:30:01 info message`）：非 ISO 格式，capture 层替换：
```bash
node server.js 2>&1 | sed 's/^\([0-9-]* [0-9:]*\)/\1Z/' >> backend.log
# 或直接注入新时间戳，忽略原有格式（macOS 用上方 python3 方案）
```

## 捕获原则

**优先捕获 stdout + stderr，而不是只捕获文件。**
即使进程同时写文件，文件可能有缓冲延迟；stdout/stderr 是实时的。

**如果进程写 JSON 日志（pino/winston JSON 格式），保留原始格式，不要提前 parse。**
在查询阶段用 `jq` 按需过滤，比提前展开更灵活。

## 接入方式

启动时包裹，注入时间戳写入独立文件：

```bash
# 无时间戳的进程（python3，跨平台）
node server.js 2>&1 \
  | python3 -u -c 'import sys,datetime; [print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), l.rstrip(), flush=True) for l in iter(sys.stdin.readline,"")]' \
  >> /tmp/myproject-logs/backend.log &

# 已有 ISO 8601 时间戳的进程（pino/winston JSON）
node server.js >> /tmp/myproject-logs/backend.log 2>&1 &
```

已在运行的进程无法重定向 stdout，只能读其写入的日志文件（确认该文件有 ISO 时间戳，否则另行处理）。

## 未捕获异常

确保进程注册了全局异常处理，否则崩溃时没有日志：

```js
process.on('uncaughtException', err => {
  console.error('[fatal]', err.stack);
  process.exit(1);
});
process.on('unhandledRejection', (reason) => {
  console.error('[unhandled-rejection]', reason);
});
```

## 常见陷阱

- pino 默认异步写，进程崩溃时最后几行可能丢失 → 生产调试时用 `sync: true` 或 pino-pretty
- winston 的 `transports.File` 有写缓冲，tail 时可能看到延迟 → 设置 `maxsize` 触发 flush 或直接 tail stdout
- `NODE_ENV=production` 时部分框架会关闭 debug 日志 → 调试时显式设置 `DEBUG=*` 或对应变量
