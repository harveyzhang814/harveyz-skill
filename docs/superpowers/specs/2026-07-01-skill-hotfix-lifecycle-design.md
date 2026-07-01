# Skill Hotfix 生命周期管理设计

**日期：** 2026-07-01  
**状态：** 待实现

---

## 背景

Skill 安装到各平台后（Claude Code、Codex、Hermes 等），有时会在安装版直接热修（hotfix）以快速恢复可用性，绕过"源仓库修改→发布→重新安装"的完整流程。这导致安装版与源仓库之间产生差异，需要一套机制追踪这些差异并将其合并回源仓库。

---

## 整体架构

三个组件，职责分离：

```
安装版 skill/
└── references/
    └── HOTFIXES.md   ← 单一记录源（fix-skill 自动写 + 用户手写）

fix-skill             ← 现有 skill，Step 3a 新增 append 动作

sync-hotfix           ← 新 skill，读 HOTFIXES.md，引导合并回源仓库
```

数据流：

```
热修发生
  ├── 脚本报错 → fix-skill 自动修复 → Step 3a → append HOTFIXES.md
  └── 手动改 SKILL.md → 用户手写 HOTFIXES.md 条目

合并回源
  └── 用户调用 sync-hotfix → 读 HOTFIXES.md → 定位源仓库对应章节
                           → 引导用户确认 → 写入 → 标记 merged_back: true
```

---

## HOTFIXES.md 格式

**文件位置：** `<skill_dir>/references/HOTFIXES.md`

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

**字段说明：**

| 字段 | 说明 |
|------|------|
| `platform` | 热修发生的平台，方便判断补丁是否适用于其他平台 |
| `date` | 热修日期 |
| `file` | 被修改的文件名（文件级指针） |
| `section` | 主 SKILL.md 的章节标题，定位修改位置 |
| `change` | 详细描述改前状态和改后状态，供 sync-hotfix 和人工理解完整差异 |
| `reason` | 热修原因，为合并时的语义裁决提供上下文 |
| `merged_back` | `false`（待合并）/ `true`（已合并或作废），sync-hotfix 的扫描锚点 |

**编号规则：** `HF-NNN`，按条目数自增，由 fix-skill 自动生成或用户手写时手动递增。

---

## fix-skill 改动范围

仅修改 **Step 3a（成功路径）**，在末尾新增一个 append 动作，其余流程不变。

**新增输入字段（可选）：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `platform` | 否 | 当前平台标识，不传则写 `unknown` |

**Step 3a 末尾新增步骤：**

1. 检查 `skill_dir/references/HOTFIXES.md` 是否存在，不存在则创建并写入 `# HOTFIXES\n` 头部
2. 读现有条目数，生成 HF 编号（`HF-NNN`）
3. 根据本轮修复内容生成条目：
   - `platform`：来自新增可选输入，未传则 `unknown`
   - `date`：当前日期
   - `file`：`file` 输入字段的文件名部分
   - `section`：从实际修复位置定位到的章节标题
   - `change`：根据实际改动生成的前后差异描述
   - `reason`：`error` 字段压缩摘要
   - `merged_back: false`
4. 将条目 append 到 HOTFIXES.md 末尾

**手动热修场景：** 用户修改安装版 SKILL.md 后，直接手写条目到 HOTFIXES.md，无需调用任何 skill。

---

## sync-hotfix Skill 设计

**用户主动调用，指定目标 skill 名称。**

**输入：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `skill_name` | 是 | 目标 skill 名称（如 `extract-url`） |

**路径解析（无需用户手动传入）：**

- `skill_dir`：由平台上下文自动推断（Claude Code → `~/.claude/skills/<skill_name>`；Codex / Hermes 同理），与 extract-url 平台补丁的 `SKILL_DIR` 解析方式一致
- `source_dir`：首次运行时引导用户输入源仓库路径，写入 `~/.hskill/sync-hotfix/config.json`，后续自动读取

**初始化流程（首次运行或 config 不存在时）：**

首次运行时询问用户两项信息，写入 `~/.hskill/sync-hotfix/config.json`：

1. 源仓库根目录路径
2. 目标 skill 所在 category（如 `research`）

配置格式：

```json
{
  "source_root": "/Users/you/Projects/harveyz-skill",
  "skills": {
    "extract-url": "research",
    "fix-skill": "meta"
  }
}
```

`source_dir` = `source_root/skills/<category>/<skill_name>`，从 `skills` 映射表直接读取 category，无需搜索。后续调用同一 skill 时直接读配置，无需重复询问。

**执行流程：**

### Step 1：扫描未合并条目

读 `skill_dir/references/HOTFIXES.md`，筛出所有 `merged_back: false` 的条目。若无，输出"无待合并条目"并退出。

### Step 2：逐条处理

对每条条目依次执行：

1. 打开源仓库对应 `file`，定位 `section` 章节，读取当前内容
2. 向用户展示：
   - 条目的 `change`（改前/改后描述）
   - 条目的 `reason`
   - 源仓库该章节当前内容
3. 用户三选一：
   - **应用**：LLM 根据 `change` 描述修改源文件，展示修改结果，用户确认后写入
   - **跳过**：本次不处理，`merged_back` 保持 `false`，下次 sync 时继续出现
   - **作废**：源仓库已有相同改动或该热修不再适用，标记 `merged_back: true`

### Step 3：更新标记

每条处理完（应用或作废）后，立即将 HOTFIXES.md 中对应条目的 `merged_back` 改为 `true`。

### Step 4：收尾

输出处理摘要：已应用 N 条、跳过 N 条、作废 N 条。提示用户在源仓库提交变更。

---

## 文件结构变化

```
skills/research/extract-url/         ← 源仓库（不变）
└── references/
    └── HOTFIXES.md                  ← 不存在（源仓库无此文件，仅安装版有）

~/.claude/skills/extract-url/        ← 安装版（新增）
└── references/
    └── HOTFIXES.md                  ← 热修记录，由 fix-skill 或用户维护

skills/meta/fix-skill/SKILL.md       ← 改动：Step 3a 新增 append 逻辑
skills/meta/sync-hotfix/SKILL.md     ← 新建 skill
```

---

## 不在此设计范围内

- 跨平台补丁同步（某平台的 hotfix 是否需要应用到其他平台）：人工判断，sync-hotfix 展示 `platform` 字段供参考
- HOTFIXES.md 的自动清理（merged_back: true 的条目归档）：留待后续需要时处理
- 版本绑定（hotfix 基于哪个版本产生）：`date` 字段间接反映，不做强约束
