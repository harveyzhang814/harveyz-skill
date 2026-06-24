---
name: fix-skill
version: "1.0.0"
description: "Diagnose and fix errors in skill scripts or SKILL.md dispatch logic. Called automatically by other skills on failure. Backs up the affected file, identifies root cause (skips external causes), applies a minimal fix, verifies, then writes a fix record or restores the backup on failure. Returns AUTO_RETRY, NEEDS_MANUAL_RETRY, or FAILURE."
user_invocable: false
---

# fix-skill

## 输入上下文

调用方（主 session）在传递控制权给 fix-skill 前，须在上下文中提供以下字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `skill` | 是 | 调用方 skill 名称（如 `extract-url`） |
| `skill_dir` | 是 | 调用方 skill 的绝对路径 |
| `file` | 是 | 出错文件的绝对路径（脚本或 SKILL.md） |
| `error` | 是 | stderr 原文 + returncode |
| `call_args` | 条件 | 脚本被调用时的参数列表，`script` 类型必填，`skill_logic` 可为空 |
| `fix_target_hint` | 否 | `script` 或 `skill_logic`，调用方可选提示，fix-skill 以诊断结果为准 |

---

## 数据目录

```
~/.hskill/fix-skill/
├── backups/          # 修复前的文件备份
└── <record>.md       # fix records
```

---

## Step 1：备份

```python
import shutil, datetime
from pathlib import Path

backup_dir = Path.home() / '.hskill' / 'fix-skill' / 'backups'
backup_dir.mkdir(parents=True, exist_ok=True)

src = Path(file)  # 来自输入上下文
ts  = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
dst = backup_dir / f'{src.name}.{ts}.bak'
shutil.copy2(src, dst)
print(f'备份已保存：{dst}')
```

记录 `backup_path = dst`，Step 5b 回滚时使用。

---

## Step 2：诊断根因

读取 `file` 全文，结合 `error` 分析。

**判断 fix_target（以诊断结果为准，忽略 fix_target_hint）：**

**→ external（直接跳至 Step 5b FAILURE，不修复）：**
- Playwright / Chrome 未安装或路径找不到
- 网络超时 / DNS 失败 / HTTP 错误
- 文件权限不足
- 根因无法定位到 `file` 内部代码

**→ script：** 错误可追溯到 Python 脚本内的具体行/逻辑

**→ skill_logic：** 错误源于 SKILL.md 中某步骤的调度指令（如参数拼装、路径引用、步骤顺序）

记录诊断结论：`fix_target`、根因描述（一句话）、涉及的具体行号或段落。

---

## Step 3：修复

对 `file` 做**最小化改动**，只修复已定位的根因。

**禁止：**
- 用 `except: pass` 吞掉异常
- 添加 fallback 绕过问题
- 修改与根因无关的代码

直接编辑 `file`，保留 `backup_path` 不变。

---

## Step 4：验证

**fix_target = script：**
```python
import subprocess
result = subprocess.run(
    ['python3', file] + call_args,
    capture_output=True, text=True, timeout=120
)
verified = (result.returncode == 0)
verify_detail = f'returncode={result.returncode}'
```

**fix_target = skill_logic：**
逐段检查改动是否与 SKILL.md 上下步骤逻辑自洽（无法重跑）。
`verified = True` 当且仅当改动语义完整、无明显矛盾。
`verify_detail = '逻辑检查：<简要说明>'`

---

## Step 5a：成功 → 写 fix record

读取 `references/fix-record-template.md`（相对于 fix-skill 目录），填充所有字段，写入：

```
~/.hskill/fix-skill/<YYYYMMDDTHHMMSS>--<skill>-<fix_target>.md
```

写入完成后输出：

```
FIX_RESULT: AUTO_RETRY
RECORD_PATH: <record 绝对路径>
```

（`fix_target = skill_logic` 时输出 `FIX_RESULT: NEEDS_MANUAL_RETRY`）

---

## Step 5b：失败 → 回滚

```python
import shutil
shutil.copy2(backup_path, file)
print(f'已回滚：{file}')
```

写入 fix record（diff 字段留空，status 为 FAILURE），然后输出：

```
FIX_RESULT: FAILURE
FAILURE_REASON: <external 类型描述 或 验证失败原因>
RECORD_PATH: <record 绝对路径>
```

---

## 调用方响应约定

调用方（主 session）解析 `FIX_RESULT:` 行：

| 值 | 调用方行为 |
|----|-----------|
| `AUTO_RETRY` | 自动重试原失败步骤，继续执行 |
| `NEEDS_MANUAL_RETRY` | 向用户报告："已修复 SKILL.md，请重新触发 skill" |
| `FAILURE` | 向用户报告：原始错误 + `FAILURE_REASON` |
