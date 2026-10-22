---
name: probe-session
version: "0.3.1"
description: "Validate whether Chrome Profile cookie injection works for a target URL. Runs Playwright twice — anonymous vs injected Chrome session — compares title and body to determine if injection succeeded. Triggers: test Chrome cookie injection, verify login state for a URL, debug extract-url authentication issues."
user_invocable: true
---

# probe-session

验证 Chrome Profile cookie 注入机制是否对目标 URL 生效。

底层机制说明见 `docs/explanation/chrome-profile-cookie-injection.md`。

---

## 路径变量

```
ScriptDir: SKILL_DIR/scripts
```

---

## 执行流程

### 步骤 1：从用户消息中提取 URL

从用户消息中提取目标 URL，做净化：

```python
import re
url_safe = re.sub(r'[\x00-\x1f\x7f]', '', url).strip()[:2048]
```

### 步骤 2：列出 Chrome Profile，让用户选择

运行 `python3 SKILL_DIR/scripts/list_profiles.py`（超时 30 秒），解析 stdout 的 JSON，格式化成编号列表展示给用户。

向用户展示如下格式，**等待用户回复编号**：

```
请选择要使用的 Chrome Profile：

[1] Default  (harvey@gmail.com)          ★ X.com 已登录  ← 推荐
[2] Profile 1  (other@gmail.com)           · 无 X.com 登录态
[3] Profile 9  (dev@gmail.com)            ★ X.com 已登录
```

格式规则：
- `has_xcom_auth: true` → 显示 `★ X.com 已登录`，列表中第一个标注「← 推荐」
- `has_xcom_auth: false` → 显示 `· 无 X.com 登录态`
- `error` 非空 → 显示 `⚠ 读取失败: {error}`

根据用户输入的编号取对应条目的 `path` 字段，作为 `selected_profile`。

### 步骤 3：运行探针脚本

运行 `python3 SKILL_DIR/scripts/probe.py "<url_safe>" "<selected_profile>"`（超时 120 秒），取 stdout；退出码非 0 时一并展示 stderr。

### 步骤 4：向用户报告

将脚本输出原样展示，并解读"结论"一行：

- `Cookie 注入有效 ✓` → 机制正常，登录态成功注入
- `Title 相同` → cookie 未生效或页面无需登录，需进一步排查
- `未提取到任何 cookie` → 该 Profile 尚未在 Chrome 中登录目标网站

---

## 前提条件

```bash
pip install pycookiecheat playwright
playwright install chromium
```
