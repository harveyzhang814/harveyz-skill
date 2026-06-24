---
name: fix-skill
version: "1.1.0"
description: "Diagnose and fix errors in skill scripts or SKILL.md dispatch logic. Called automatically by other skills on failure. Backs up the affected file, identifies root cause (skips external causes), applies a minimal fix, verifies, then writes a fix record or restores the backup on failure. Returns AUTO_RETRY, NEEDS_MANUAL_RETRY, or FAILURE."
user_invocable: false
---

# fix-skill

## 输入上下文

| 字段 | 必填 | 说明 |
|------|------|------|
| `skill` | 是 | 调用方 skill 名称 |
| `skill_dir` | 是 | 调用方 skill 的绝对路径 |
| `file` | 是 | 出错文件的绝对路径（脚本或 SKILL.md） |
| `error` | 是 | stderr 原文 + returncode |
| `call_args` | 条件 | 脚本被调用时的参数列表，`script` 类型必填 |
| `fix_target_hint` | 否 | `script` 或 `skill_logic`，调用方可选提示，以诊断结果为准 |

---

## 数据目录

```
~/.hskill/fix-skill/
├── backups/    # 修复前的文件备份
└── *.md        # fix records
```

---

## Step 1：备份

将 `file` 复制到 `~/.hskill/fix-skill/backups/<文件名>.<YYYYMMDDTHHMMSS>.bak`，记录路径为 `backup_path`。

---

## Step 2：诊断根因

读取 `file` 全文，结合 `error` 分析。

**判断原则：fix_target 取决于「修改 `file` 内容能否解决错误」**

- **external** — 无法通过修改文件解决（环境缺失、网络、权限等）→ 跳至 Step 5b，无需回滚（文件未改动）
- **script** — 错误可追溯到脚本内具体行/逻辑
- **skill_logic** — 错误源于 SKILL.md 某步骤的调度指令

记录：`fix_target`、根因一句话、涉及行号或段落。

---

## Step 3：修复 + 生成 diff

对 `file` 做最小化改动，只修复已定位的根因。禁止用异常捕获吞掉错误、添加 fallback 绕过问题、修改无关代码。

修复完成后运行：

```bash
diff -u <backup_path> <file>
```

记录输出为 `diff_content`。

---

## Step 4：验证

- **script** — 用相同 `call_args` 重跑脚本，returncode 为 0 则通过
- **skill_logic** — 检查改动与 SKILL.md 上下步骤逻辑是否自洽

记录结论为 `verify_detail`。

---

## Step 5a：成功 → 写 fix record 并返回

读取 `references/fix-record-template.md`，填充所有字段（含 `diff_content`），写入：

```
~/.hskill/fix-skill/<YYYYMMDDTHHMMSS>--<skill>-<fix_target>.md
```

输出：

```
FIX_RESULT: AUTO_RETRY          # fix_target = script
FIX_RESULT: NEEDS_MANUAL_RETRY  # fix_target = skill_logic
RECORD_PATH: <record 路径>
```

---

## Step 5b：失败 → 回滚并返回

若文件已改动（非 external 类型），将 `backup_path` 还原到 `file` 原路径。

写入 fix record（`diff_content` 留空，status 为 FAILURE），输出：

```
FIX_RESULT: FAILURE
FAILURE_REASON: <原因>
RECORD_PATH: <record 路径>
```

---

## 调用方响应约定

| FIX_RESULT | 调用方行为 |
|------------|-----------|
| `AUTO_RETRY` | 自动重试原失败步骤（仅一次） |
| `NEEDS_MANUAL_RETRY` | 向用户报告"已修复，请重新触发" |
| `FAILURE` | 向用户报告原始错误 + FAILURE_REASON |
