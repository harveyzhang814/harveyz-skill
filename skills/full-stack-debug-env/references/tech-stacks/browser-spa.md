# 浏览器 SPA 日志最佳实践

适用场景：React、Vue、Angular、Svelte 等 Web 前端，运行在浏览器中

## 核心问题

浏览器 console 完全独立于服务端，不会自动流到任何文件。必须在以下某个层面主动捕获：

1. **测试框架层**（Playwright、Cypress、Puppeteer）— 推荐，无需改业务代码
2. **应用代码层**（全局 console 拦截 + 发到后端）— 适合需要生产日志的场景
3. **网络代理层**（mitmproxy）— 适合捕获网络请求，不捕获 console

## 时间戳处理

浏览器 console 原生没有时间戳。必须在 hook 代码里主动添加 `new Date().toISOString()`。下方所有示例均已包含。

## 方案一：Playwright（推荐用于自动化测试）

```js
// 在 test setup 或 beforeEach 中注册
page.on('console', msg => {
  const ts = new Date().toISOString();
  fs.appendFileSync(LOG, `${ts} ${msg.type()} ${msg.text()}\n`);
});

page.on('pageerror', err => {
  const ts = new Date().toISOString();
  fs.appendFileSync(LOG, `${ts} uncaught ${err.message}\n`);
});

page.on('requestfailed', req => {
  const ts = new Date().toISOString();
  fs.appendFileSync(LOG, `${ts} request-failed ${req.url()} ${req.failure().errorText}\n`);
});
```

`page.on('requestfailed')` 能捕获网络请求失败，这是服务端日志看不到的视角。

## 方案二：Cypress

```js
// cypress/support/commands.js 或 e2e.js
Cypress.on('window:console', (type, ...args) => {
  const ts = new Date().toISOString();
  cy.task('log', `${ts} ${type} ${args.join(' ')}`);
});

Cypress.on('uncaught:exception', (err) => {
  const ts = new Date().toISOString();
  cy.task('log', `${ts} uncaught ${err.message}`);
  return false; // 不让 Cypress 自动 fail
});
```

需在 `cypress.config.js` 定义 `log` task 写入独立的 `browser.log`。

## 方案三：应用代码全局拦截（适合非测试场景）

在应用入口（main.js / index.js / App.tsx 最顶部）注入：

```js
const LOG_ENDPOINT = '/api/client-logs'; // 后端提供接收接口

['log', 'warn', 'error'].forEach(level => {
  const orig = console[level];
  console[level] = (...args) => {
    orig(...args);
    // 发到后端（fire-and-forget）
    fetch(LOG_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level, args: args.map(String), ts: Date.now() })
    }).catch(() => {}); // 静默失败，不递归触发 console.error
  };
});

window.addEventListener('error', e =>
  fetch(LOG_ENDPOINT, { method: 'POST', body: JSON.stringify({
    level: 'uncaught', message: e.message, stack: e.error?.stack }) }));
```

后端接收后写入独立的 `browser.log` 文件。注意 body 里的 `ts` 字段已是 epoch ms，后端写文件时转为 ISO 8601。

## 常见陷阱

- `console.log` 里的对象在 Playwright 的 `msg.text()` 里是 `[object Object]` → 用 `msg.args()` 逐个 `jsonValue()` 展开
- Cypress 的 `uncaught:exception` 默认会让测试 fail → 根据需要 `return false` 决定是否忽略
- 应用代码拦截在生产环境发送日志会带来隐私和流量问题 → 仅在 dev/staging 启用
- `fetch` 失败时不要调用 `console.error`，否则递归死循环
