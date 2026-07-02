---
migrated: 2026-07-02
docs:
  - reference/hotfix-lifecycle.md  # HOTFIXES.md 格式、fix-skill 自动写入行为、sync-hotfix 合并回源工作流
implemented_in:
  - skills/meta/fix-skill/SKILL.md
---

# fix-skill v2 设计文档

## 概述

当 skill 执行出现错误时，AI 自主诊断根因、最多尝试 3 轮修复任意类型文件，每轮结果实时追加到 fix session 文档。修复成功后通知调用方自动重试，3 轮全失败则回滚并保留完整诊断记录。

## 背景

v1 设计存在两个根本问题：一是将修复对象限定为 script 和 SKILL.md 两类，实际上任意文件（配置、模板、数据文件）都可能需要修复；二是只有一次修复机会，失败即放弃，缺乏递进尝试能力。v2 重新设计以解决这两个问题。

## 用户故事

extract-url 的 Subagent 1 因脚本错误失败，主 session 自动调用 fix-skill。fix-skill 备份脚本，第 1 轮诊断出 CSS selector 过期并修复，验证通过后通知主 session 重试。用户收到一条通知："已自动修复 playwright_xcom.py，共尝试 1 轮，记录见 ~/.hskill/fix-skill/…"，无需介入。

## Skill 定位

- **名称**：`fix-skill`
- **Bundle**：`meta`（通用工具，任意 skill 可调用）
- **路径**：`skills/meta/fix-skill/`
- **user_invocable**：false

## 接口

### 输入

| 字段 | 必填 | 说明 |
|------|------|------|
| `skill` | 是 | 调用方 skill 名称 |
| `skill_dir` | 是 | 调用方 skill 绝对路径 |
| `file` | 是 | 出错文件绝对路径（任意类型） |
| `error` | 是 | stderr 原文 + returncode |
| `call_args` | 否 | 验证时重跑脚本所需参数；无则仅做内容自洽检查（适用于非脚本文件） |

### 输出

```
FIX_RESULT: AUTO_RETRY | FAILURE | FAILURE+RESTORE_FAILED
SESSION_PATH: <fix session 文档绝对路径>
ATTEMPTS: <实际尝试轮数>
```

### 调用方响应

| FIX_RESULT | 行为 |
|------------|------|
| `AUTO_RETRY` | 重试原失败步骤（仅一次）；通知用户「已自动修复，共尝试 N 轮，记录见 SESSION_PATH」 |
| `FAILURE` | 向用户报告原始错误 + 「已尝试 3 轮均失败，已回滚，诊断记录见 SESSION_PATH」 |
| `FAILURE+RESTORE_FAILED` | 立即告警用户：「修复失败且还原异常，file 状态不可知，backup 保留在 SESSION_PATH 中，请手动处理」 |

## 内部流程

```
Step 1: 备份 + 创建 fix session 文档
  将 file 复制到 ~/.hskill/fix-skill/backups/<文件名>.<YYYYMMDDTHHMMSS>.bak
  创建 fix session 文档，写入 header（时间、skill、file、原始错误）

Step 2: 尝试修复（最多 3 轮，每轮从干净 backup 状态出发）

  轮次 N:
    读取 fix session 文档（获取前 N-1 轮的假设与失败原因）
    提出新假设（必须与前几轮不同，说明为何）
    修改 file
    验证：
      有 call_args → 在真实环境中重跑脚本，returncode 为 0 则通过
      无 call_args → 检查改动内容是否语义完整、逻辑自洽（非脚本文件）
    立即 append 本轮结果到 fix session 文档
    成功 → Step 3a
    失败 → 还原 file 到 backup（不是上一轮状态），进入下一轮

  3 轮全失败 → Step 3b

Step 3a: 成功
  最终状态校验：确认 file 可读、内容与本轮修复一致
    → 校验失败：降级为 Step 3b（视为修复失败，触发还原流程）
  在 fix session 文档末尾追加「最终结果：成功（第 N 轮）」
  删除 backup_path
  输出 FIX_RESULT: AUTO_RETRY

Step 3b: 全部失败
  还原 file：将 backup_path 内容写回 file
  最终状态校验：逐字节确认 file 与 backup_path 完全一致
    → 校验失败：不删除 backup，在 session 文档标注「还原异常，backup 已保留」
               输出 FIX_RESULT: FAILURE + RESTORE_FAILED
    → 校验通过：删除 backup_path
  在 fix session 文档末尾追加「最终结果：失败，已回滚」
  输出 FIX_RESULT: FAILURE
```

**关键约束：每轮失败后还原到原始 backup，不是上一轮修改后的状态。避免多轮错误叠加，确保每轮从同一基线出发。**

## Fix Session 文档格式

**路径：** `~/.hskill/fix-skill/<YYYYMMDDTHHMMSS>--<skill>--<filename>.md`

```markdown
---
date: <YYYYMMDDTHHMMSS>
skill: <skill>
file: <file 相对路径>
backup: <backup 绝对路径>
status: in_progress | success | failure
---

## 原始错误

<error 原文>

---

## 第 1 轮

**假设：** <本轮对根因的假设>

**改动：**
\```diff
<diff -u backup file 输出>
\```

**验证结果：** 通过 / 失败 — <verify_detail>

**失败原因：** <若失败，说明为何假设不成立，为下一轮提供方向>

---

## 第 N 轮

（格式同上，假设字段需说明与前几轮的区别）

---

## 最终结果

状态：成功（第 N 轮）/ 失败（3 轮均未解决）
```

**注：** frontmatter `status` 字段在每轮完成后更新，便于外部扫描未完成的 session。

## 数据目录结构

```
~/.hskill/fix-skill/
├── backups/                                            # 暂存，session 结束自动清空
│   └── playwright_xcom.py.20260624T153000.bak
└── 20260624T153012--extract-url--playwright_xcom.py.md  # 永久保留
```

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 3 轮假设耗尽但根因是 external | 第 1 轮诊断时若判定为 external（改文件无法解决），立即输出 FAILURE，不消耗轮次 |
| 同一文件并发修复 | 超出范围，调用方应避免并发触发 |
