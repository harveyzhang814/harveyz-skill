# Hotfix 生命周期参考

Skill 安装到各平台后有时需要直接热修（hotfix），绕过"源仓库→发布→重装"的完整流程。本文档定义追踪这些差异的格式规范与合并回源的工作流。

---

## HOTFIXES.md 格式

**文件位置：** `<skill_install_dir>/references/HOTFIXES.md`（仅存在于安装版，源仓库无此文件）

```markdown
# HOTFIXES

## HF-001
- platform: claude
- date: 2026-07-01
- file: SKILL.md
- section: "## ② 网页内容获取"
- change: "原：调用 web_fetch 后将 HTML 写入 /tmp/fetched_page.html，再传路径给脚本。改后：web_fetch 直接返回 HTML 字符串，不再写临时文件，直接传字符串给脚本。"
- reason: "Claude Code 新版本 web_fetch 返回值结构变更，原写法抛异常"
- merged_back: false
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `platform` | 是 | 热修发生的平台（`claude`、`codex`、`unknown` 等），用于判断补丁是否需同步到其他平台 |
| `date` | 是 | 热修日期（YYYY-MM-DD） |
| `file` | 是 | 被修改的文件名 |
| `section` | 是 | 被修改章节的标题，用于 sync-hotfix 定位 |
| `change` | 是 | 改前/改后状态的完整描述，供人工理解和 sync-hotfix 应用 |
| `reason` | 是 | 热修原因，为合并时的语义裁决提供上下文 |
| `merged_back` | 是 | `false`（待合并）/ `true`（已合并或已作废） |

### 编号规则

条目编号格式为 `HF-NNN`，按已有条目数自增。fix-skill 自动修复时自动生成；手动热修时手动递增。

---

## 条目创建方式

### 自动创建（fix-skill）

当 fix-skill 在 Step 3a（成功路径）完成修复后，自动 append 一条条目到 `skill_dir/references/HOTFIXES.md`。若文件不存在则先创建并写入 `# HOTFIXES` 头部。

### 手动创建

用户在安装版 SKILL.md 中手动改动后，直接手写条目到 HOTFIXES.md，无需调用任何 skill。

---

## sync-hotfix 工作流

`sync-hotfix` skill 将安装版的 hotfix 合并回源仓库。

**调用方式：** `/sync-hotfix <skill_name>`（如 `/sync-hotfix extract-url`）

**首次运行：** 引导输入源仓库根目录路径和 skill 所在 category，写入 `~/.hskill/sync-hotfix/config.json`，后续自动读取。

**每条条目的处理选项：**

| 选项 | 行为 |
|------|------|
| 应用 | 根据 `change` 描述修改源文件，展示结果后用户确认写入，标记 `merged_back: true` |
| 跳过 | 本次不处理，`merged_back` 保持 `false`，下次 sync 继续出现 |
| 作废 | 源仓库已有相同改动或热修不再适用，直接标记 `merged_back: true` |

处理完成后输出摘要：已应用 N 条、跳过 N 条、作废 N 条，并提示在源仓库提交变更。
