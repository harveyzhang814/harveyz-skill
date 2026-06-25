# fix-skill 设计文档

## 概述

当 skill 执行出现错误时，自动诊断根因、尝试修复，修复成功后写入问题记录并通知调用方重试，修复失败则回滚并报告原因。

## 背景

extract-url 执行时调用多个 Python 脚本（playwright_xcom.py、playwright_web.py 等）。脚本出错或 SKILL.md 调度逻辑有误时，当前只能向用户报错，无法自动恢复。fix-skill 填补这一空白，并可复用于其他含脚本的 skill。

## 用户故事

任意 skill 的执行步骤失败后，主 session 捕获错误并自动调用 fix-skill，传入出错文件和错误信息。fix-skill 诊断根因、修复、验证，成功后写入修复记录并通知主 session 是否可自动重试。用户无感知。

**示例**：extract-url 的 Subagent 1 抓取失败，fix-skill 诊断出 playwright_xcom.py 的 CSS selector 过期，备份脚本、更新 selector、重跑验证通过，主 session 自动重试。

## Skill 定位

- **名称**：`fix-skill`
- **Bundle**：`meta`（通用工具类，任何 skill 均可调用）
- **路径**：`skills/meta/fix-skill/`
- **注意**：动词 `fix` 当前不在 publish-skill 的规范词表中，需在注册前将其加入词表

## 调用接口

任意 skill 在步骤失败后，由主 session 以以下上下文调用 fix-skill：

```
skill:           <调用方 skill 名称>
skill_dir:       <调用方 skill 的绝对路径>
fix_target_hint: script | skill_logic   # 调用方可选提示，fix-skill 以诊断结果为准
file:            <出错文件的绝对路径>
error:           <stderr 原文 + returncode>
call_args:       [<脚本被调用时的参数>]  # 用于重跑验证；skill_logic 类型可为空
```

调用方只需提供上下文，fix-skill 自行判断 fix_target 并执行完整流程。

## 内部流程

```
输入：skill_name + error_output + file + call_args

Step 1  备份
        cp <file> ~/.hskill/fix-skill/backups/<basename>.<YYYYMMDDTHHMMSS>.bak

Step 2  诊断根因
        读取 file 全文 + error_output
        判断 fix_target：
          script      → 错误定位在 Python 脚本内部
          skill_logic → 错误定位在 SKILL.md 调度逻辑
          external    → 外部依赖 / 网络 / 权限问题 → 直接 FAILURE，不修复

        ⚠️  external 类型示例（不尝试修复）：
            - Playwright 未安装 / Chrome 找不到
            - 网络超时 / DNS 失败
            - 文件权限不足

Step 3  修复
        对 file 做最小化改动，只修复已定位的根因
        禁止绕过问题（如 catch 后 pass、降级 fallback）

Step 4  验证
        script      → 用相同 call_args 重跑脚本，returncode == 0 为通过
        skill_logic → 逻辑自洽检查（无法重跑，检查改动是否与上下文步骤一致）

Step 5a SUCCESS
        写 fix record（见下方 template）
        返回：
          script 通过      → AUTO_RETRY
          skill_logic 通过 → NEEDS_MANUAL_RETRY

Step 5b FAILURE
        cp backup → file（还原）
        写 fix record（diff 留空，记录失败原因）
        返回：FAILURE + reason
```

**单次修复原则**：不循环重试。第一次验证失败即回滚，避免脚本被多次部分修改后状态不可预期。

## 调用方响应

extract-url 收到 fix-skill 返回值后：

| 返回值 | extract-url 行为 |
|--------|-----------------|
| `AUTO_RETRY` | 自动重试失败的步骤，继续执行 |
| `NEEDS_MANUAL_RETRY` | 报告用户："已修复 SKILL.md，请重新触发 skill" |
| `FAILURE` | 报告用户：原始错误 + fix 尝试失败原因 |

## Fix Record Template

**路径**：`~/.hskill/fix-skill/<YYYYMMDDTHHMMSS>--<skill-name>-<fix_target>.md`  
**备份路径**：`~/.hskill/fix-skill/backups/<basename>.<YYYYMMDDTHHMMSS>.bak`

```markdown
---
date: <YYYYMMDDTHHMMSS>
skill: <skill_name>
fix_target: script | skill_logic
file: <修复文件的相对路径>
status: AUTO_RETRY | NEEDS_MANUAL_RETRY | FAILURE
---

## 触发错误

\```
<error_output 原文>
\```

## 根因

<一句话定位：在哪个文件、哪一行、什么逻辑导致了错误>

## 修复内容

\```diff
<改动 diff，FAILURE 时留空>
\```

## 验证

- fix_target: script → 重跑结果：returncode <N>
- fix_target: skill_logic → 逻辑检查：<说明>
- fix_target: external / FAILURE → <失败原因>

## 备份路径

~/.hskill/fix-skill/backups/<basename>.<timestamp>.bak
```

## 数据目录结构

```
~/.hskill/fix-skill/
├── backups/
│   └── playwright_xcom.py.20260624T153000.bak
└── 20260624T153012--extract-url-script.md
```

## 风险和缓解

| 风险 | 缓解 |
|------|------|
| fix 改动引入新 bug | 验证步骤强制重跑；失败立即回滚 |
| skill_logic fix 无法自动验证 | 返回 NEEDS_MANUAL_RETRY，不自动重试 |
| 外部原因误判为可修复 | Step 2 明确列出 external 类型，优先排除 |
| 备份目录积累过多文件 | 超出范围，由用户手动清理或未来加 retention 策略 |
