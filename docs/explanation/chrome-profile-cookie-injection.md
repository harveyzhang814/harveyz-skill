# Chrome Profile Cookie 提取与 Playwright 注入（通用机制）

让无头浏览器（Playwright）继承用户已有 Chrome 登录态的通用模式。

X.com 的具体应用见 [xcom-playwright-auth.md](xcom-playwright-auth.md)。

---

## 问题

LLM agent 需要抓取登录态才能访问的页面，但：

- 无法在 headless 浏览器里交互式登录
- 不能将账号密码硬编码进 skill
- 用户已经在 Chrome 里登录了，session 数据就在本地磁盘

**核心思路**：读取用户 Chrome Profile 里已有的加密 cookie，解密后注入 Playwright browser context，让无头浏览器"假装"是那个已登录的 Chrome。

---

## 流程

```
~/Library/Application Support/Google/Chrome/<Profile>/Cookies
         │
         │ 1. 复制到 /tmp（绕开 Chrome 运行时文件锁）
         ↓
pycookiecheat.chrome_cookies(url, cookie_file=tmp_path)
         │ 2. 从 macOS Keychain 读取 "Chrome Safe Storage" 密钥
         │    PBKDF2 派生 AES-128 密钥 → 解密每条 cookie 值
         ↓
{cookie_name: plaintext_value, ...}
         │
         │ 3. 格式化为 Playwright cookie 列表
         ↓
browser_context.add_cookies([...])
         │
         │ 4. 无头浏览器携带 session 发请求，服务器认为是已登录用户
         ↓
page.goto("https://example.com/protected")
```

---

## 实现

### 为什么要复制到 /tmp

Chrome 运行时会对 `Cookies` 文件加排他锁。直接 `sqlite3.connect()` 会报 `database is locked`。复制到临时路径后操作，用完删除：

```python
import shutil, tempfile, os
from pathlib import Path

cookies_src = Path(chrome_profile) / 'Cookies'
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    tmp_path = f.name
shutil.copy2(cookies_src, tmp_path)
try:
    # ... 操作 tmp_path ...
finally:
    os.unlink(tmp_path)
```

### pycookiecheat 解密

Chrome 在 macOS 上用 AES-128-CBC 加密所有 cookie 值，密钥存在系统 Keychain（item 名称："Chrome Safe Storage"）。`pycookiecheat` 封装了这个流程，返回明文 dict：

```python
import pycookiecheat

cookies_dict = pycookiecheat.chrome_cookies(
    'https://target-site.com',   # 只提取匹配此域的 cookie
    cookie_file=tmp_path         # 指向临时副本，不是原始文件
)
# → {'session_id': 'abc123', 'csrf_token': 'xyz', ...}
```

`cookie_file` 参数必须指向临时副本，不能是原始路径（会被文件锁拒绝）。

首次运行时 macOS 会弹 Keychain 授权弹窗，用户选「始终允许」后不再重复。

### 注入 Playwright Context

将明文 cookie 转为 Playwright 格式，注入 browser context：

```python
from playwright.sync_api import sync_playwright

pw_cookies = [
    {
        'name': k,
        'value': v,
        'domain': '.target-site.com',  # 注意前缀点号（匹配所有子域）
        'path': '/',
        'secure': True,
    }
    for k, v in cookies_dict.items()
]

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--disable-blink-features=AutomationControlled'],
    )
    ctx = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/136.0.0.0 Safari/537.36',
    )
    ctx.add_cookies(pw_cookies)   # 必须在 new_page() 之前注入
    page = ctx.new_page()
    page.goto('https://target-site.com/protected')
    # ...
    browser.close()
```

**反检测要点**：
- `--disable-blink-features=AutomationControlled`：隐藏 `navigator.webdriver = true` 标志，阻止网站用 JS 检测到这是自动化浏览器
- 真实 macOS Chrome User-Agent：与注入的 Chrome cookie 来源一致，避免 UA 与 session 不匹配被拒

---

## 最小复用模板

在其他 skill 里复用此方案的最小代码：

```python
import shutil, tempfile, os, pycookiecheat
from pathlib import Path
from playwright.sync_api import sync_playwright

TARGET_URL   = 'https://example.com/protected'
TARGET_DOMAIN = '.example.com'
CHROME_PROFILE = '/path/to/Chrome/Profile'   # 从 vars.json 注入

# 1. 提取并解密 cookie
cookies_src = Path(CHROME_PROFILE) / 'Cookies'
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    tmp = f.name
shutil.copy2(cookies_src, tmp)
try:
    cookies = pycookiecheat.chrome_cookies(TARGET_URL, cookie_file=tmp)
finally:
    os.unlink(tmp)

# 2. 注入并访问
pw_cookies = [
    {'name': k, 'value': v, 'domain': TARGET_DOMAIN, 'path': '/', 'secure': True}
    for k, v in cookies.items()
]
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--disable-blink-features=AutomationControlled'],
    )
    ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; ...) Chrome/136.0.0.0 Safari/537.36')
    ctx.add_cookies(pw_cookies)
    page = ctx.new_page()
    page.goto(TARGET_URL)
    # ... 提取内容 ...
    browser.close()
```

**vars.json 配置项**（让用户在安装时选择 Profile）：

```json
{
  "name": "CHROME_PROFILE",
  "type": "chrome_profile_select",
  "description": "Chrome 用户配置目录",
  "default": "{{HOME}}/Library/Application Support/Google/Chrome/Default"
}
```

`type: chrome_profile_select` 触发交互式 Profile 扫描，写入 skill 变量配置，后续运行直接使用。

---

## 依赖

```
pip install pycookiecheat playwright
playwright install chromium
```

---

## 安全边界

| 边界 | 处理方式 |
|------|---------|
| URL scheme | 脚本入口处验证，只允许 `http/https` |
| 图片下载 SSRF | `_is_safe_image_url()` 过滤私有 IP、loopback、非 HTTP scheme |
| Shell 注入 | `subprocess.run(list)` 而非字符串拼接；含特殊字符的参数通过 env var 传递 |
| Cookie 不落盘 | 解密后只写入 Playwright context 内存，不打印、不持久化 |

---

## 限制

| 限制 | 说明 |
|------|------|
| 仅支持 macOS | 依赖 Keychain 解密；Linux 需换 `browser-cookie3`，Windows 用 DPAPI |
| Chrome 必须已运行过 | `Cookies` DB 由 Chrome 首次启动时建立 |
| 无自动续期 | Session cookie 过期后需用户在 Chrome 里手动重新登录 |
| 单 Profile 绑定 | 一个 skill 实例对应一个 Profile；多账号需多实例 |
| Chrome 大版本升级 | 极少情况下加密方案变化，需升级 `pycookiecheat` |
