# X.com 登录态抓取（extract-url 的具体应用）

本文描述 extract-url skill 如何识别 X.com 登录态、选择 Chrome Profile、以及用无头浏览器抓取需要登录才能访问的推文内容。

底层 cookie 提取与注入的通用机制见 [chrome-profile-cookie-injection.md](chrome-profile-cookie-injection.md)。

---

## 为什么 X.com 需要特殊处理

X.com 的大部分内容依赖客户端 JS 渲染，且需要登录态：

- 普通网站可由 LLM 平台工具（`web_fetch`）预取 HTML 再交给 Playwright 渲染，无需登录
- X.com 未登录时只渲染登录墙，`web_fetch` 取回的 HTML 没有推文内容
- 因此必须用携带 X.com session cookie 的 Playwright 直接访问

---

## X.com 的身份标识 Cookie

X.com 使用三个 cookie 标识已登录用户：

| Cookie 名 | 作用 |
|-----------|------|
| `auth_token` | 主 session 令牌，标识用户身份 |
| `ct0` | CSRF token，每次写操作携带 |
| `twid` | Twitter 用户 ID |

三者同时存在 → 该 Profile 已登录 X.com。

---

## Profile 扫描（`detect_chrome_profile.py`）

扫描本机所有 Chrome Profile，找出已登录 X.com 的那个：

```python
CHROME_BASE = Path.home() / "Library/Application Support/Google/Chrome"
XCOM_HOSTS  = [".twitter.com", ".x.com"]
AUTH_COOKIES = {"auth_token", "ct0", "twid"}

for profile_dir in profiles:           # Default 优先，再 Profile 1, 2, ...
    # 读取 Google 账号 email，帮用户辨别是哪个账号
    prefs = json.loads((profile_dir / "Preferences").read_text(errors="ignore"))
    email = prefs.get("account_info", [{}])[0].get("email", "") \
            or prefs.get("user_name", "")

    # 复制 Cookies DB 到 /tmp（绕开 Chrome 文件锁），只读 cookie 名称
    shutil.copy2(profile_dir / "Cookies", tmp_path)
    conn = sqlite3.connect(tmp_path)
    cur.execute(
        "SELECT name FROM cookies WHERE host_key IN (?, ?)", XCOM_HOSTS
    )
    found = {row["name"] for row in cur.fetchall()}

    if AUTH_COOKIES & found:
        print(f"{profile_dir.name}  {email}  <-- 推荐")
```

关键点：
- 只检查 cookie **名称**是否存在，不解密值 — 避免在扫描阶段触发 Keychain 授权弹窗
- 读 `Preferences` 取 Google email — 多 Profile 环境下靠账号名识别，而不是靠 `Profile 1` 这类无意义目录名

脚本输出供用户选择，选定后路径写入 `CHROME_PROFILE` 变量。

---

## 抓取流程（`playwright_xcom.py`）

拿到 `CHROME_PROFILE` 后，用通用机制提取 X.com cookie，注入无头浏览器：

```python
# 提取（通用步骤，详见 chrome-profile-cookie-injection.md）
cookies_dict = pycookiecheat.chrome_cookies('https://x.com', cookie_file=tmp_path)

pw_cookies = [
    {'name': k, 'value': v, 'domain': '.x.com', 'path': '/', 'secure': True}
    for k, v in cookies_dict.items()
]

# 注入并访问
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--disable-blink-features=AutomationControlled'],
    )
    ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; ...) Chrome/136.0.0.0 Safari/537.36')
    ctx.add_cookies(pw_cookies)
    page = ctx.new_page()
    page.goto(url, timeout=60000, wait_until='domcontentloaded')

    # 等待推文 article 出现 —— 同时作为隐式鉴权验证：
    #   cookie 有效 → X.com 渲染出推文，selector 命中，继续执行
    #   cookie 失效 → 页面停在登录墙，20s 内 selector 不出现，超时报错
    page.wait_for_selector('article[data-testid="tweet"]', timeout=20000)
```

`wait_for_selector` 是唯一的鉴权验证点。没有额外的"是否已登录"检查——selector 本身就是答案。

---

## 配置：CHROME_PROFILE 变量

`vars.json` 中的定义：

```json
{
  "name": "CHROME_PROFILE",
  "description": "Chrome 用户配置目录（X.com 登录态所需）",
  "type": "chrome_profile_select",
  "default": "{{HOME}}/Library/Application Support/Google/Chrome/Default"
}
```

`type: chrome_profile_select` 在 `hskill install` 时触发交互式选择器，调用 `detect_chrome_profile.py` 列出各 Profile 的账号和 X.com cookie 状态，用户选择后写入配置，后续运行直接读取。

---

## 与普通网站路径的对比

| | X.com | 普通网站 |
|---|---|---|
| 抓取脚本 | `playwright_xcom.py` | `playwright_web.py` |
| 需要 Chrome cookie | 是 | 否 |
| HTML 来源 | Playwright 直接访问（携带 cookie）| 平台工具 `web_fetch` 预取，存 `/tmp/fetched_page.html` |
| 渲染方式 | 在线渲染（JS 执行，需登录态） | 本地渲染（加载静态 HTML） |

普通网站走的路径完全不涉及 Chrome Profile，两条路径在 `playwright_xcom.py` 与 `playwright_web.py` 处分叉。

---

## 相关文件

| 文件 | 用途 |
|------|------|
| `skills/research/extract-url/scripts/detect_chrome_profile.py` | 扫描所有 Profile，识别 X.com 登录态，输出推荐 Profile |
| `skills/research/extract-url/scripts/playwright_xcom.py` | X.com 抓取脚本：cookie 注入 + 推文 DOM 提取 |
| `skills/research/extract-url/vars.json` | `CHROME_PROFILE` 变量定义 |
| [chrome-profile-cookie-injection.md](chrome-profile-cookie-injection.md) | 底层 cookie 提取与注入的通用机制 |
