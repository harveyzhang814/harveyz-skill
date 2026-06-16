---
name: probe-chrome-session
version: "0.1.0"
description: "验证 Chrome Profile cookie 注入机制是否生效。对同一 URL 跑两次 Playwright：匿名访问 vs 注入 Chrome 登录态，对比 title 和 body 判断注入是否有效。触发场景：用户想测试 Chrome cookie 注入、验证某网站能否用 Chrome 登录态访问、调试 extract-url 的登录态问题。"
user_invocable: true
---

# probe-chrome-session

验证 Chrome Profile cookie 注入机制是否对目标 URL 生效。

底层机制说明见 `docs/explanation/chrome-profile-cookie-injection.md`。

---

## 路径变量

```
ChromeProfile: CHROME_PROFILE
ScriptDir:     SKILL_DIR/scripts
```

---

## 执行流程

### 步骤 1：从用户消息中提取 URL

从用户消息中提取目标 URL，对其做净化：

```python
import re
url_safe = re.sub(r'[\x00-\x1f\x7f]', '', url).strip()[:2048]
```

### 步骤 2：运行探针脚本

用 subprocess list 调用脚本（禁止字符串拼接）：

```python
import subprocess, os, sys
result = subprocess.run(
    ['python3', 'SKILL_DIR/scripts/probe.py', url_safe, 'CHROME_PROFILE'],
    capture_output=True, text=True, timeout=120
)
print(result.stdout)
if result.returncode != 0:
    print(result.stderr, file=sys.stderr)
```

### 步骤 3：向用户报告

将脚本输出原样展示给用户，并解读"结论"一行：

- `Cookie 注入有效 ✓` → 机制正常，登录态成功注入
- `Title 相同` → cookie 未生效或页面无需登录，需进一步排查
- `未提取到任何 cookie` → 用户尚未在 Chrome 中登录目标网站

---

## 前提条件

```bash
pip install pycookiecheat playwright
playwright install chromium
```

目标网站需在 Chrome 中已登录（cookie 存在于 CHROME_PROFILE/Cookies）。
