# sync-design 设计阶段扩展 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `sync-design` SKILL.md 中新增设计阶段支持——在开发前创建/修改设计稿 HTML，并在开发后通过三重检查点安全删除设计稿。

**Architecture:** 所有改动集中在 `skills/design/sync-design/SKILL.md` 一个文件。在现有同步流程之上新增三个模块：模式检测（设计 vs 同步）、设计阶段流程（创建/修改设计稿）、设计稿删除生命周期。manifest schema 从 v3 升至 v4，新增 `drafts[]` 数组。

**Tech Stack:** Markdown (SKILL.md), JSON (manifest schema examples)

## Global Constraints

- 向后兼容：读取 v3 manifest 时 `drafts` 视为 `[]`，写回时自动升级至 v4
- 设计稿存入 `outputDir/drafts/`，完成稿存入 `outputDir/`，命名格式相同：`<screenName>-<platform>-design.html`
- draft entry 固定字段：`{ id, platform, htmlFile, uiStates, description, linkedEntryId }`
- 删除必须经过三重检查点（linkedEntryId 存在 · uiStates 全覆盖 · HTML 比对），所有通过后需用户最终确认
- 版本号 frontmatter 从 `4.0.0` 升至 `5.0.0`

---

### Task 1: frontmatter 更新 + 模式检测节 + v4 升级步骤

**Files:**
- Modify: `skills/design/sync-design/SKILL.md`（第 1–28 行：frontmatter、标题区、初始化区）

**Interfaces:**
- Produces: 本次调用模式（设计 / 同步）在后续路由中可用；manifest 保证为 v4 格式后再路由

- [ ] **Step 1: 更新 frontmatter**

将文件开头第 1–6 行替换为：

```yaml
---
name: sync-design
description: Use after any UI source file change — detects changed view/component files via git diff and syncs them to high-fidelity HTML design backups. Also supports pre-development design phase: creates or updates design draft HTML based on user feature descriptions. Maintains a manifest as the source-of-truth mapping between source files, design drafts, and HTML previews. Trigger when user says "sync design", "update HTML preview", "design changed", "设计", "create design", "帮我设计", or after UI code edits.
version: "5.0.0"
user_invocable: true
---
```

- [ ] **Step 2: 在 H1 描述行之后插入模式说明**

在 `**Announce at start:**` 行之前，插入：

```markdown
支持两种模式：
- **同步模式**（默认）：检测 UI 源文件变动，更新高保真 HTML 完成稿（存于 `outputDir/`）
- **设计模式**：根据功能描述创建或修改设计稿 HTML（存于 `outputDir/drafts/`）

```

- [ ] **Step 3: 在「## 初始化（run first）」之前插入「## 模式检测」节**

```markdown
## 模式检测

读取用户消息和上下文，判断调用意图，**记录为本次模式**（设计 / 同步），初始化完成后据此路由。

**设计模式触发词：** 「设计」「create design」「做个设计稿」「帮我设计」「design this」；或描述功能需求/界面改动但无代码变动信号。

**同步模式触发词：** 「sync design」「同步」「update HTML preview」「design changed」；或存在 UI 源文件 git diff。

**歧义时辅助判断：**
- `drafts[]` 非空且无 UI 文件 git diff → 倾向设计模式
- 检测到 UI 文件 git diff → 倾向同步模式
- 仍不确定 → 询问：「你是想更新设计稿，还是同步代码变动到 HTML？」

---
```

- [ ] **Step 4: 在「## 初始化」末尾、`---` 分隔符之前插入 v4 升级步骤和路由跳转**

在 `**\`entries\` 为空：** 执行[已有 HTML 导入]...` 这行之后插入：

```markdown
**`version` 小于 4：** 在现有字段基础上追加 `"drafts": []`，将 `version` 更新为 `4`，写回文件后继续。

**路由：** 根据本次模式，跳转至[设计阶段](#设计阶段)或继续[同步流程](#流程strict--不可跳过或合并阶段)。
```

- [ ] **Step 5: 验证**

通读 `## 模式检测` 和 `## 初始化` 两节，确认：
- description 中所有触发词都在模式检测节中有对应
- v4 升级步骤位置在 entries 检查之后（不影响「已有 HTML 导入」分支）
- 路由跳转锚点与后续实际标题文字一致

- [ ] **Step 6: Commit**

```bash
git add skills/design/sync-design/SKILL.md
git commit -m "feat(sync-design): add mode detection and manifest v4 upgrade (v5.0.0)"
```

---

### Task 2: 新增「设计阶段」流程节

**Files:**
- Modify: `skills/design/sync-design/SKILL.md`（在「## 流程」之前插入新节）

**Interfaces:**
- Consumes: 本次模式 = 设计；manifest v4（含 `drafts[]`；`entries[]` 用于查找完成稿）
- Produces: `outputDir/drafts/` 下新增/更新的 HTML；`drafts[]` 写回 manifest

- [ ] **Step 1: 在「## 流程（STRICT）」之前插入完整的「## 设计阶段」节**

```markdown
## 设计阶段

（模式检测为「设计」时执行）

### 1. 推断受影响页面

从用户描述和上下文中识别涉及哪些页面或组件，列出清单：

> 「我理解以下页面需要更新：\<列表\>，是否正确？」

等待用户确认或修正后继续。

---

### 2. 逐一处理每个页面

#### 情况 A：drafts[] 中已有对应 entry（修改现有设计稿）

1. 读取 `<draft.htmlFile>`
2. 读取上下文（后读优先级更高，可覆盖前面内容）：
   - `manifest.config.designSpec`（若存在）
   - 该 entry 所属平台的 `designSystemFile`（若有）
   - 该平台 `stackRef` 指向的 reference 文件中与 `styleStrategy` 匹配的样式策略
   - 该平台 `notes`
3. 根据用户描述确定修改范围（哪些 UI 状态或区块）
4. 增量修改 HTML，只替换受影响区块；若有新 UI 状态，追加 `uiStates`
5. 写回 HTML 文件，更新 `drafts[].uiStates`（去重后写入，不写回 manifest，等步骤 3 统一写回）

#### 情况 B：无对应 draft entry（创建新设计稿）

**B1. 检查是否有对应完成稿**

在 `manifest.entries[]` 中查找 `id` 与目标页面相同的 entry：

**有对应完成稿 →**

1. 将完成稿 HTML（`entry.htmlFile`）复制到 `<outputDir>/drafts/<screenName>-<platform>-design.html` 作为基底
2. 读取上下文（同情况 A 的优先级顺序）
3. 根据用户描述增量修改（同情况 A 步骤 3–4）
4. 新增 draft entry（`linkedEntryId` 直接填入，无需等待 sync 阶段回填）：
   ```json
   {
     "id": "<screenName>-<platform>",
     "platform": "<platform>",
     "htmlFile": "<outputDir>/drafts/<screenName>-<platform>-design.html",
     "uiStates": ["<继承完成稿 uiStates，按用户描述追加新状态>"],
     "description": "<从用户描述提炼>",
     "linkedEntryId": "<screenName>-<platform>"
   }
   ```

**无对应完成稿 →**

1. 询问用户（最少必要信息）：
   - `屏幕/组件名是什么？（kebab-case，如 "task-history"）`
   - `这个界面有哪些 UI 状态？（逗号分隔，如 idle, loading, error）`
   - `一句话描述这个界面的功能：`
2. 读取上下文（后读优先级更高，可覆盖前面内容）：
   - `manifest.config.designSpec`（若存在）
   - 该平台的 `designSystemFile`（若有）
   - 该平台 `stackRef` 指向的 reference 文件中与 `styleStrategy` 匹配的样式策略
   - 该平台 `notes`
   - `outputDir/drafts/` 下已有的同平台 HTML（选一个作风格参考）
3. 生成完整高保真 HTML（质量要求见[HTML 生成质量要求](#html-生成质量要求)）
4. 输出路径：`<outputDir>/drafts/<screenName>-<platform>-design.html`
5. 新增 draft entry：
   ```json
   {
     "id": "<screenName>-<platform>",
     "platform": "<platform>",
     "htmlFile": "<outputDir>/drafts/<screenName>-<platform>-design.html",
     "uiStates": ["<用户输入的状态列表>"],
     "description": "<用户输入的描述>",
     "linkedEntryId": null
   }
   ```

根据文件路径匹配 `manifest.config.platforms` 确定所属平台；无法自动匹配时询问用户。

---

### 3. 写回与摘要

所有页面处理完毕后：
1. 将更新后的 `drafts[]` 写回 `manifest.json`
2. 输出摘要，按页面列出：已修改 / 已创建，以及变动内容

---
```

- [ ] **Step 2: 验证**

通读「设计阶段」节，确认：
- 情况 A / B 分支条件互斥且完整（有 draft entry → A；无 → B）
- B1 中有完成稿路径的 `linkedEntryId` 直接写入正确值
- B1 中无完成稿路径的 `linkedEntryId = null`
- 两种情况的上下文读取优先级顺序与同步阶段「b. 读取上下文」保持一致
- draft entry JSON schema 字段与 Global Constraints 中定义完全匹配

- [ ] **Step 3: Commit**

```bash
git add skills/design/sync-design/SKILL.md
git commit -m "feat(sync-design): add design phase flow (create/modify design drafts)"
```

---

### Task 3: 同步阶段修订（linkedEntryId 回填 + 删除提示）

**Files:**
- Modify: `skills/design/sync-design/SKILL.md`（Phase 3 更新队列、新建队列；Phase 4 确认流程）

**Interfaces:**
- Consumes: Phase 3 已写回 HTML；manifest v4 含 `drafts[]`
- Produces: `draft.linkedEntryId` 回填；Phase 4 确认后触发删除提示

- [ ] **Step 1: 在「更新队列」的「d. 写回 HTML 文件」之后插入步骤 e**

```markdown
**e. 回填 linkedEntryId**

在 `manifest.drafts[]` 中查找 `id` 与本 entry 相同的 draft。若存在且 `linkedEntryId` 为 `null`，将其更新为本 entry 的 `id`（即 `<screenName>-<platform>`）。
```

- [ ] **Step 2: 在「新建队列」的「e. 在 Manifest 新增 Entry」之后插入步骤 f**

```markdown
**f. 回填 linkedEntryId**

在 `manifest.drafts[]` 中查找 `id` 与新 entry 相同的 draft。若存在，将其 `linkedEntryId` 更新为本 entry 的 `id`。
```

- [ ] **Step 3: 在「阶段 4」的「用户选「确认」」第 4 步（git add 建议）之后追加第 5 步**

```markdown
5. 在本次确认写回的所有 entry 中，检查 `manifest.drafts[]` 是否有 `linkedEntryId` 与之匹配且 `htmlFile` 对应文件仍存在的 draft。若有，逐一提示：
   > "`<id>` 的完成稿已同步，是否检查并删除对应设计稿？"
   - **是：** 跳转至[设计稿删除](#设计稿删除)流程。
   - **否：** 跳过，不修改 `drafts[]`。
```

- [ ] **Step 4: 验证**

确认：
- 步骤 e / f 分别在各自队列的 HTML 写回之后、Phase 4 之前
- Phase 4 删除提示仅在用户选「确认」后触发，「取消」路径不触发
- 跳转锚点 `#设计稿删除` 与 Task 4 中将创建的标题一致

- [ ] **Step 5: Commit**

```bash
git add skills/design/sync-design/SKILL.md
git commit -m "feat(sync-design): write linkedEntryId on sync and prompt draft deletion after confirm"
```

---

### Task 4: 新增「设计稿删除」流程节

**Files:**
- Modify: `skills/design/sync-design/SKILL.md`（在「## 首次初始化」之前插入新节）

**Interfaces:**
- Consumes: `draft.linkedEntryId`；对应 `entry.htmlFile`；`draft.htmlFile`
- Produces: draft HTML 删除；`drafts[]` entry 移除；manifest 写回

- [ ] **Step 1: 在「## 首次初始化」之前插入「## 设计稿删除」节**

```markdown
## 设计稿删除

（可由以下任意方式触发）
- 同步阶段 Phase 4 确认后的提示（见[阶段 4](#阶段-4确认与写回)）
- 用户显式指令：「设计稿可以删了」「design done」「清理 \<页面\> 的设计稿」
- 上下文信号含「合并」「删除草稿」等

### 检查点 1：linkedEntryId 存在

查找目标 draft 的 `linkedEntryId`：
- 为 `null` → 输出「❌ 阻止：该页面完成稿尚未生成，无法验证。」退出。
- 非 null → 在 `manifest.entries[]` 中定位对应 entry，继续。

### 检查点 2：uiStates 全覆盖

对比 `draft.uiStates` 与 `entry.uiStates`：
- draft 中有、entry 中无的状态 → 输出「❌ 阻止：以下 UI 状态尚未反映到完成稿：\<列表\>。建议先运行 sync 补全。」退出。
- 全部覆盖 → 继续。

### 检查点 3：HTML 设计意图比对

读取 `draft.htmlFile` 和 `entry.htmlFile`，确认 draft 中的主要布局结构与组件区块在完成稿中有对应实现：
- 发现明显缺失（主要区块或关键组件未出现在完成稿中）→ 输出「❌ 阻止：以下设计元素未在完成稿中实现：\<列表\>。建议先运行 sync 补全。」退出。
- 通过 → 继续。

### 确认与删除

输出确认摘要：
> 「设计稿 `\<draft.htmlFile\>` 的所有设计意图已在完成稿中实现。确认删除设计稿？」

- **取消：** 保留设计稿，不做任何修改。
- **确认：**
  1. 删除 `draft.htmlFile` 对应的 HTML 文件
  2. 从 `manifest.drafts[]` 中移除该 entry
  3. 写回 `manifest.json`
  4. 输出：「设计稿 `\<id\>` 已删除。」

---
```

- [ ] **Step 2: 验证**

确认：
- 三个检查点顺序正确（linkedEntryId → uiStates → HTML）
- 每个检查点失败路径有明确输出并退出，不继续到下一个检查点
- 删除步骤完整（文件删除 + drafts[] 移除 + manifest 写回）
- 取消路径不做任何修改

- [ ] **Step 3: Commit**

```bash
git add skills/design/sync-design/SKILL.md
git commit -m "feat(sync-design): add draft deletion flow with three-checkpoint verification"
```

---

### Task 5: 首次初始化 schema + 完成标准 + 反模式 更新

**Files:**
- Modify: `skills/design/sync-design/SKILL.md`（首次初始化节、完成标准节、反模式节）

- [ ] **Step 1: 更新「首次初始化 → 5. 创建 Manifest」中的 JSON schema**

将现有 JSON 示例（第 224–245 行）替换为 v4 格式（新增 `"version": 4` 和 `"drafts": []`）：

```json
{
  "version": 4,
  "baseBranch": "<用户输入>",
  "config": {
    "outputDir": "<用户输入>",
    "designSpec": "<路径 或 null>",
    "platforms": {
      "<platform-id>": {
        "label": "<平台展示名>",
        "stackRef": "references/stack-<name>.md",
        "uiFilePatterns": ["<自动推导的 glob>"],
        "designSystemFile": "<路径 或 null>",
        "styleStrategy": "<检测到的样式方案>",
        "notes": "<用户补充的项目特定约定，或 null>"
      }
    }
  },
  "entries": [],
  "drafts": [],
  "ignoredFiles": []
}
```

- [ ] **Step 2: 将「## 完成标准」替换为同步/设计双模式版本**

```markdown
## 完成标准

**同步模式：**
- `.hskill/sync-design/manifest.json` 已写回，所有已处理 entry 的 `lastSyncCommit` 为当前 commit hash。
- 更新或新建的每个 HTML 文件在 `outputDir/` 下存在，可直接在浏览器打开预览。
- HTML 文件满足阶段 3「HTML 生成质量要求」的 6 条约束。

**设计模式：**
- 所有确认处理的页面，其设计稿 HTML 已写入 `outputDir/drafts/`，可直接在浏览器打开预览。
- `manifest.drafts[]` 已写回，entry 的 `uiStates` 与 HTML 内容一致。
- 有对应完成稿的 draft，其 `linkedEntryId` 已正确填写；无对应完成稿的 draft，`linkedEntryId` 为 `null`。
```

- [ ] **Step 3: 在「## 反模式」表格末尾追加三行**

```markdown
| 跳过三重检查点直接删除设计稿 | 必须经过 linkedEntryId · uiStates · HTML 三个检查点，全部通过后再由用户确认删除 |
| 设计稿和完成稿存入同一目录 | 设计稿存 `outputDir/drafts/`，完成稿存 `outputDir/`，目录严格分离 |
| 完成稿不存在时尝试删除设计稿 | linkedEntryId 为 null 时阻止删除，输出明确提示 |
```

- [ ] **Step 4: 全文一致性检查**

通读完整 SKILL.md，逐项确认：
- 所有锚点链接（`[设计阶段]`、`[设计稿删除]`）有对应的实际标题
- manifest JSON schema 在「首次初始化」「设计阶段 B1 有完成稿」「设计阶段 B1 无完成稿」三处的 draft entry 字段完全一致
- `linkedEntryId` 的写入时机在以下三处描述前后一致：设计阶段 B1 有完成稿（直接填入）、设计阶段 B1 无完成稿（null）、同步阶段步骤 e/f（回填）
- frontmatter `version` 为 `5.0.0`

- [ ] **Step 5: Commit**

```bash
git add skills/design/sync-design/SKILL.md
git commit -m "feat(sync-design): update first-init schema, completion criteria, and anti-patterns"
```
