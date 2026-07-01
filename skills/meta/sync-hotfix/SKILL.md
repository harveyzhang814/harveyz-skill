---
name: sync-hotfix
version: "1.1.1"
description: "Merge hotfixes recorded in the installed skill back to the source repo. Processes HOTFIXES.md entries first, then runs a full file diff safety net to detect and categorize undocumented differences between the installed and source skill."
user_invocable: true
---

# sync-hotfix

## 输入

| 字段 | 必填 | 说明 |
|------|------|------|
| `skill_name` | 是 | 目标 skill 名称（如 `extract-url`） |

---

## 路径解析

**`skill_dir`（安装版路径）** 根据当前平台自动推断，无需用户传入：

| 平台 | skill_dir |
|------|-----------|
| Claude Code | `~/.claude/skills/<skill_name>` |
| Codex | `~/.codex/skills/<skill_name>` |
| Hermes | `~/.hermes/skills/<skill_name>` |

**`source_dir`（源仓库路径）** 从 `~/.hskill/sync-hotfix/config.json` 读取，首次运行时引导初始化。

---

## 初始化流程

检查 `~/.hskill/sync-hotfix/config.json` 是否存在，或 `skills.<skill_name>` 字段是否缺失。若任一条件满足，引导用户填写：

1. **源仓库根目录路径**（如 `/Users/you/Projects/harveyz-skill`）
2. **`<skill_name>` 所在 category**（如 `research`、`meta`、`writing`）

写入配置（合并已有内容，不覆盖其他 skill 的记录）：

```json
{
  "source_root": "/Users/you/Projects/harveyz-skill",
  "skills": {
    "extract-url": "research"
  }
}
```

`source_dir` = `source_root/skills/<category>/<skill_name>`

---

## Step 1：扫描未合并条目

读取 `skill_dir/references/HOTFIXES.md`：

- 文件不存在 → 输出"HOTFIXES.md 不存在，跳过 Steps 2-3"，直接进入 Step 4
- 文件存在但无 `merged_back: false` 条目 → 输出"无待合并条目，跳过 Steps 2-3"，直接进入 Step 4
- 筛出所有 `merged_back: false` 的条目，记为待处理列表，输出条目数量及编号列表

无论哪种情况，Step 4 和 Step 5 都必须执行。

---

## Step 2：逐条处理

对待处理列表中每条条目依次执行：

**① 展示条目信息：**

```
[HF-NNN] platform: <platform> | date: <date>
file: <file> | section: <section>
change: <change 全文>
reason: <reason 全文>
```

**② 读取源仓库对应章节：**

打开 `source_dir/<file>`，定位 `section` 字段对应的章节标题，读取该章节全部内容并展示给用户。

**③ 用户选择（三选一）：**

- **应用（A）**：根据 `change` 描述，修改源仓库该章节内容，展示修改结果请用户确认，确认后写入文件 → 进入 Step 3 标记
- **跳过（S）**：本次不处理，`merged_back` 保持 `false`，下次调用时继续出现 → 跳至下一条
- **作废（D）**：源仓库已有相同改动或该 hotfix 不再需要 → 进入 Step 3 标记

---

## Step 3：更新标记

每条处理完（应用或作废）后，立即将 `skill_dir/references/HOTFIXES.md` 中该条目的 `merged_back: false` 改为 `merged_back: true`。

跳过的条目不修改标记。

---

## Step 4：收尾

输出 HOTFIXES.md 处理摘要：

```
HOTFIXES.md 处理完成
已应用：N 条
已作废：N 条
已跳过：N 条
```

若有"已应用"条目，提示用户在源仓库提交改动：

```
请在源仓库提交变更：
  cd <source_root>
  git add skills/<category>/<skill_name>/
  git commit -m "fix(<skill_name>): backport hotfix from <platform>"
```

---

## Step 5：安全网 — 全文件差异扫描

HOTFIXES.md 处理完成后，无论是否有条目，都执行此步骤。

### 5.1 文件收集

递归列出 `skill_dir/` 和 `source_dir/` 下所有文件，分三组：

- **共同文件**：两边都有 → 进入 diff
- **仅安装版**：排除 `references/HOTFIXES.md`（安装版专有，正常）；其余文件提示用户"此文件仅存在于安装版，是否需要同步到源仓库？(y/n)"
- **仅源仓库**：提示"源仓库有此文件，安装版未覆盖"，不要求操作

### 5.2 逐文件 diff 与分类

对每个共同文件比对内容，若完全一致则跳过。有差异时，分析属于以下哪类并标记（LLM 基于 diff 内容推断，展示时注明推断理由）：

| 类型 | 标记 | 判断依据 |
|------|------|---------|
| 未登记热修 | `[UNLOGGED]` | 安装版改动了功能逻辑、指令步骤、错误处理等，源仓库没有 |
| 平台适配 | `[PLATFORM]` | 差异内容涉及平台工具调用、路径、API 签名等平台相关内容 |
| 源仓库超前 | `[SRC_AHEAD]` | 源仓库有安装版没有的段落或内容 |
| 双向冲突 | `[CONFLICT]` | 两边都修改了同一段，内容互不相同 |

### 5.3 用户决策

对每处有差异的文件，展示：文件名、类型标记、推断理由、diff 内容，然后按类型给出选项：

**`[UNLOGGED]`（未登记热修）：**
- **同步（S）**：将安装版改动应用到源仓库文件，展示修改结果请用户确认后写入
- **登记（R）**：在 `skill_dir/references/HOTFIXES.md` 追加新条目（`merged_back: false`），`change` 由 LLM 根据 diff 生成描述，`reason` 填"差异扫描发现，未登记"
- **忽略（I）**：跳过，不处理

**`[PLATFORM]`（平台适配）：**
- **忽略（I）**（默认推荐，注明"平台适配无需回源"）
- **同步（S）**：若用户认为仍需同步

**`[SRC_AHEAD]`（源仓库超前）：**
- 仅展示提示，无需决策："源仓库在此处有更新，安装版未覆盖此内容，可重新安装 skill 获取最新版"

**`[CONFLICT]`（双向冲突）：**
- **取安装版（A）**：以安装版内容为准，覆盖源仓库该处
- **取源仓库（R）**：以源仓库内容为准，安装版改动放弃
- **手动处理（M）**：跳过，提示用户自行解决冲突

### 5.4 扫描收尾

若全部文件一致，输出：
```
差异扫描：安装版与源仓库内容完全一致 ✓
```

否则输出扫描摘要：
```
差异扫描完成
  共同文件：N 个，有差异：M 个
  [UNLOGGED] N 条：已同步 X / 已登记 Y / 已忽略 Z
  [PLATFORM] N 条：已忽略 N
  [SRC_AHEAD] N 条：已提示
  [CONFLICT] N 条：已处理 X / 待手动处理 Y
```

若本步骤有新的源仓库文件改动，再次提示用户提交：
```
请在源仓库提交扫描同步的变更：
  cd <source_root>
  git add skills/<category>/<skill_name>/
  git commit -m "fix(<skill_name>): sync undocumented diff from installed version"
```
