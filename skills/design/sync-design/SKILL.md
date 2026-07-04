---
name: sync-design
description: Use after any UI source file change — detects changed view/component files via git diff and syncs them to high-fidelity HTML design backups. Also supports pre-development design phase: creates or updates design draft HTML based on user feature descriptions. Maintains a manifest as the source-of-truth mapping between source files, design drafts, and HTML previews. Trigger when user says "sync design", "update HTML preview", "design changed", "设计", "create design", "帮我设计", or after UI code edits.
version: "5.0.0"
user_invocable: true
---

# Sync Design HTML

检测前端视图文件变动，同步更新高保真 HTML 设计备份文件。

支持两种模式：
- **同步模式**（默认）：检测 UI 源文件变动，更新高保真 HTML 完成稿（存于 `outputDir/`）
- **设计模式**：根据功能描述创建或修改设计稿 HTML（存于 `outputDir/drafts/`）

**Announce at start:** "I'm using sync-design to detect UI changes and update HTML design backups."

---

## 模式检测

读取用户消息和上下文，判断调用意图，**记录为本次模式**（设计 / 同步），初始化完成后据此路由。

**设计模式触发词：** 「设计」「create design」「做个设计稿」「帮我设计」「design this」；或描述功能需求/界面改动但无代码变动信号。

**同步模式触发词：** 「sync design」「同步」「update HTML preview」「design changed」；或存在 UI 源文件 git diff。

**歧义时辅助判断：**
- `drafts[]` 非空且无 UI 文件 git diff → 倾向设计模式
- 检测到 UI 文件 git diff → 倾向同步模式
- 仍不确定 → 询问：「你是想更新设计稿，还是同步代码变动到 HTML？」

---

## 初始化（run first）

读取 `.hskill/sync-design/manifest.json`。

**文件不存在：** 执行[首次初始化](#首次初始化)，完成后继续流程。

**文件存在，检查 `config.outputDir`：**
- 不以 `.hskill/` 开头（旧路径）→ 执行[旧路径迁移](#旧路径迁移)，迁移完成后继续。
- 以 `.hskill/` 开头 → 继续。

**`entries` 为空：** 执行[已有 HTML 导入](#已有-html-导入)，完成后继续。

**`version` 小于 4：** 在现有字段基础上追加 `"drafts": []`，将 `version` 更新为 `4`，写回文件后继续。

**路由：** 根据本次模式，跳转至[设计阶段](#设计阶段)或继续[同步流程](#流程strict--不可跳过或合并阶段)。

---

## 设计阶段

（模式检测为「设计」时执行）

### 1. 推断受影响页面

从用户描述和上下文中识别涉及哪些页面或组件，列出清单：

> 「我理解以下页面需要更新：<列表>，是否正确？」

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

## 流程（STRICT — 不可跳过或合并阶段）

### 阶段 1：Diff 检测

将 `manifest.config.platforms` 中所有平台的 `uiFilePatterns` 和 `designSystemFile`（非 null）汇总，传给 git 作为过滤参数：

```bash
git diff <manifest.baseBranch>...HEAD --name-only -- <pattern1> <pattern2> ...
```

**如果过滤后列表为空：**
输出："当前分支相对于 `<baseBranch>` 无 UI 文件变动，无需同步。" 然后退出。

**否则：** 将过滤后的文件列表记为 `<changedFiles>`，继续阶段 2。

---

### 阶段 2：变动分类与路由

#### 设计系统文件检测

检查 `<changedFiles>` 中是否包含各平台的 `designSystemFile`（跳过值为 `null` 的平台）。

对每个包含的设计系统文件，询问用户：

> "`<设计系统文件名>` 发生变动。是否重新生成所有 `<platform>` HTML 设计文件？（推荐：是，确保全局 token 一致）"

- **是：** 将该平台所有 entries 加入**更新队列（全量重生成）**，从 `<changedFiles>` 中移除该设计系统文件。
- **否：** 保留设计系统文件在 `<changedFiles>` 中，后续按普通视图文件处理。

#### 文件路由

对 `<changedFiles>` 中的每个文件（去重：同一 entry 只触发一次）：

1. 在 `manifest.ignoredFiles` 中 → 跳过。
2. 在某个 `manifest.entries[].sourceFiles` 中 → 加入**更新队列**。
3. 未找到 → 加入**新建队列**。

两者均为空 → 输出"所有变动文件已在忽略列表中，无需同步。"，退出。

---

### 阶段 3：执行同步

#### 更新队列（有 manifest entry）

对队列中的每个 entry：

**a. 获取增量 Diff**

```bash
git diff <entry.lastSyncCommit 或 manifest.baseBranch（如无 lastSyncCommit）>...HEAD -- <entry.sourceFiles 用空格分隔>
```

**b. 读取上下文**（后读优先级更高，可覆盖前面内容）

1. `manifest.config.designSpec`（若不存在则跳过）
2. 该 entry 所属平台的 `designSystemFile`（若有）
3. 该平台 `stackRef` 指向的 reference 文件
4. 该平台 `styleStrategy` — 只执行 reference 中与此字段匹配的样式策略；若为 `null` 则从源文件自行判断
5. 该平台 `notes` — 优先级高于 reference，记录项目特定约定
6. `<entry.htmlFile>`（若不存在则降级为全量生成：读取所有 `entry.sourceFiles` 完整源码）

**c. 确定更新范围**

- entry 在全量重生成队列中 → 读取所有 `entry.sourceFiles` 完整源码重新生成。
- 否则 → 根据 diff 判断受影响的 UI 状态或组件区块，只替换该部分。

**d. 写回 HTML 文件**（质量要求见[HTML 生成质量要求](#html-生成质量要求)）

**e. 回填 linkedEntryId**

在 `manifest.drafts[]` 中查找 `id` 与本 entry 相同的 draft。若存在且 `linkedEntryId` 为 `null`，将其更新为本 entry 的 `id`（即 `<screenName>-<platform>`）。

---

#### 新建队列（无 manifest entry）

对队列中的每个文件：

**a. 检查 pattern 覆盖**

该文件所在目录是否被现有任一 `uiFilePatterns` 覆盖？

**未覆盖** → 在后续询问中附带提示：
> "此文件目录 `<dir>/` 未在当前配置中。是否将 `<建议 pattern>` 加入 `<platform>.uiFilePatterns`？"
- 是 → 更新 `manifest.config.platforms[platform].uiFilePatterns`，阶段 4 一并写回。
- 否 → 作为 one-off entry 处理，不修改 patterns。

**b. 询问用户**

1. `发现未映射的 UI 文件：<文件路径>。要为它创建 HTML 设计备份吗？`
   - **跳过并永久忽略：** 加入 `manifest.ignoredFiles`，结束此文件处理。
   - **本次跳过：** 不修改 ignoredFiles。
   - **是：** 继续。
2. `屏幕/组件名是什么？（kebab-case，如 "task-history"）`
3. `这个界面有哪些 UI 状态？（逗号分隔，如 idle, loading, error）`
4. `一句话描述这个界面的功能：`

根据文件路径匹配 `manifest.config.platforms` 确定所属平台；无法自动匹配时询问用户。

**c. 读取上下文**（后读优先级更高，可覆盖前面内容）

1. `manifest.config.designSpec`（若存在）
2. 该平台的 `designSystemFile`（若有）
3. 该平台 `stackRef` 指向的 reference 文件
4. 该平台 `styleStrategy` — 只执行 reference 中与此字段匹配的样式策略
5. 该平台 `notes` — 优先级高于 reference
6. 源文件完整内容（及 `notes` 或 reference 中指定的关联文件）
7. `manifest.config.outputDir` 下**已有的同平台** HTML 文件（选一个作风格参考）

**d. 生成完整高保真 HTML**（质量要求见[HTML 生成质量要求](#html-生成质量要求)）

输出路径：`<manifest.config.outputDir>/<screenName>-<platform>-design.html`

**e. 在 Manifest 新增 Entry**

```json
{
  "id": "<screenName>-<platform>",
  "platform": "<platform>",
  "htmlFile": "<outputDir>/<screenName>-<platform>-design.html",
  "sourceFiles": ["<文件路径>"],
  "uiStates": ["<状态列表>"],
  "lastSyncCommit": null,
  "description": "<用户输入的描述>"
}
```

**f. 回填 linkedEntryId**

在 `manifest.drafts[]` 中查找 `id` 与新 entry 相同的 draft。若存在且 `linkedEntryId` 为 `null`，将其 `linkedEntryId` 更新为本 entry 的 `id`。

---

#### HTML 生成质量要求

1. **Token 来源：** 所有颜色、字体、间距值从当次读取的设计规范和设计系统文件中提取，不得凭记忆填写。
2. **CSS 变量命名：** 与设计规范文件中的 token 名完全一致（以实际读取为准，不预设变量名）。
3. **UI 状态完整性：** `entry.uiStates` 中的每个状态必须在 HTML 中有对应可视区块或 class 切换。
4. **离线可用：** 禁止引用任何外部 URL。样式全部内联在 `<style>` 中，单文件可直接在浏览器打开预览。
5. **风格对齐：** 与同项目已有 HTML 文件保持一致的代码风格：CSS 变量声明格式、状态区块注释格式（`/* ── 状态名 ── */`）、整体结构顺序。
6. **高保真要求：** 尺寸、圆角、阴影、字号、行高尽量还原设计规范；规范未涉及的参考设计系统文件中的具体值。

---

### 阶段 4：确认与写回

输出同步摘要，包含以下分类（有内容的分类才展示）：更新的 entry（id + htmlFile + 变动范围）、新建的 HTML 文件（文件名 + 描述）、配置变更（哪个 platform 的 uiFilePatterns 新增了什么 pattern）、忽略的文件（路径）。

**用户选「确认」：**
1. `git rev-parse HEAD` 获取当前 commit hash
2. 将所有已处理 entry 的 `lastSyncCommit` 更新为该 hash
3. 写回 `.hskill/sync-design/manifest.json`（含配置演进的 patterns 变更）
4. 询问是否 `git add` 并给出建议 commit message：
   `chore: sync HTML design backups — <entry id 列表>`
5. 在本次确认写回的所有 entry 中，检查 `manifest.drafts[]` 是否有 `linkedEntryId` 与之匹配且 `htmlFile` 对应文件仍存在的 draft。若有，逐一提示：
   > "`<id>` 的完成稿已同步，是否检查并删除对应设计稿？"
   - **是：** 跳转至[设计稿删除](#设计稿删除)流程。
   - **否：** 跳过，不修改 `drafts[]`。

**用户选「取消」：**
输出："同步未确认。HTML 文件已写入磁盘但 manifest 未更新。"

---

## 设计稿删除

（可由以下任意方式触发）
- 同步阶段 Phase 4 确认后的提示（见[阶段 4](#阶段-4确认与写回)）
- 用户显式指令：「设计稿可以删了」「design done」「清理 <页面> 的设计稿」
- 上下文信号含「合并」「删除草稿」等

### 检查点 1：linkedEntryId 存在

查找目标 draft 的 `linkedEntryId`：
- 为 `null` → 输出「❌ 阻止：该页面完成稿尚未生成，无法验证。」退出。
- 非 null → 在 `manifest.entries[]` 中定位对应 entry，继续。

### 检查点 2：uiStates 全覆盖

对比 `draft.uiStates` 与 `entry.uiStates`：
- draft 中有、entry 中无的状态 → 输出「❌ 阻止：以下 UI 状态尚未反映到完成稿：<列表>。建议先运行 sync 补全。」退出。
- 全部覆盖 → 继续。

### 检查点 3：HTML 设计意图比对

读取 `draft.htmlFile` 和 `entry.htmlFile`，确认 draft 中的主要布局结构与组件区块在完成稿中有对应实现：
- 发现明显缺失（主要区块或关键组件未出现在完成稿中）→ 输出「❌ 阻止：以下设计元素未在完成稿中实现：<列表>。建议先运行 sync 补全。」退出。
- 通过 → 继续。

### 确认与删除

输出确认摘要：
> 「设计稿 `<draft.htmlFile>` 的所有设计意图已在完成稿中实现。确认删除设计稿？」

- **取消：** 保留设计稿，不做任何修改。
- **确认：**
  1. 删除 `draft.htmlFile` 对应的 HTML 文件
  2. 从 `manifest.drafts[]` 中移除该 entry
  3. 写回 `manifest.json`
  4. 输出：「设计稿 `<id>` 已删除。」

---

## 首次初始化

（manifest 文件不存在时执行）

### 1. 询问基础配置

1. `这个项目的 base 分支是什么？（如 main / staging）`
2. `HTML 设计备份存放在哪个目录？（默认：.hskill/sync-design/html/）`
3. `设计规范文件路径是什么？（如 DESIGN.md；若无请留空）`

### 2. 自动检测技术栈

先读取 `references/stacks.md`，根据其中的检测信号（特征文件、package.json 依赖、框架配置文件等）扫描项目，匹配技术栈，加载对应的 `references/stack-<name>.md`。

多个栈同时检测到时，按 `stacks.md` 中的优先级取最具体的一个，次要技术在 `notes` 中说明。

### 3. 运行发现命令

从加载的 `stack-*.md` 读取【发现命令】，执行以发现实际存在的 UI 文件，推导 `uiFilePatterns`（取最小覆盖的 glob）。

同时按 `stack-*.md` 中的【设计系统文件候选】探测是否存在对应文件，确定 `designSystemFile`。

同时通过特征文件判断 `styleStrategy`：tailwind.config 文件 → `tailwind`；*.module.css/scss → `css-modules`；*.css.ts → `vanilla-extract`；package.json 中的 styled-components/emotion → 对应值；uno.config → `unocss`；以上均无则看全局 SCSS/CSS 文件。多种混用时记录主要策略，其余在 `notes` 中说明。

`styleStrategy` 取值：`tailwind` / `css-modules` / `vanilla-extract` / `styled-components` / `emotion` / `unocss` / `scss` / `css` / `unknown`。

### 4. 展示检测结果并请用户确认

向用户展示检测结果：说明检测到的技术栈名称（及对应的 reference 文件），列出建议的平台配置（每个平台的 uiFilePatterns 及发现的文件数、designSystemFile、styleStrategy），询问配置是否正确，允许用户提出调整。

等待用户确认或修改。确认后追加询问：

> `这个项目有哪些与参考文档不同的约定需要记录？（若无请留空）`

将用户输入记为该平台的 `notes`。

### 5. 创建 Manifest

创建 `.hskill/sync-design/` 目录，写入 `manifest.json`：

```json
{
  "version": 3,
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
  "ignoredFiles": []
}
```

继续执行流程阶段 1。

---

## 已有 HTML 导入

（manifest 存在但 `entries` 为空时执行）

1. 扫描 `manifest.config.outputDir` 下所有 `*.html` 文件。
2. 对每个 HTML 文件询问：

   > `发现现有 HTML 文件：<文件名>。要为它建立 manifest 映射吗？`

   - **跳过：** 不处理，继续下一个。
   - **是：** 依次询问：
     1. `对应哪些源文件？（相对于项目根的路径，多个用逗号分隔）`
     2. `覆盖哪些 UI 状态？（如 idle, loading，用逗号分隔）`
     3. `一句话描述：`
   - 构造 entry（`lastSyncCommit` 设为 `null`）加入 `entries`。

3. 全部处理完毕后，写入 manifest，继续流程阶段 1。

---

## 旧路径迁移

（manifest 存在，且 `config.outputDir` 不以 `.hskill/` 开头时执行）

询问用户：

> `检测到 HTML 设计备份位于旧路径 "<outputDir>"。是否自动迁移至 .hskill/sync-design/html/？`

**是：**

1. 将旧目录下所有 `*.html` 文件移动到 `.hskill/sync-design/html/`。
2. 更新 manifest：`config.outputDir` → `.hskill/sync-design/html`；所有 `entries[].htmlFile` 替换旧路径前缀。
3. 写回 manifest。
4. 询问是否删除旧目录（仅当已清空时）。
5. 输出迁移摘要：`迁移完成：旧路径 <outputDir> → .hskill/sync-design/html（N 个文件）`

**否：** 保持现有路径，继续后续流程。

---

## 完成标准

- `.hskill/sync-design/manifest.json` 已写回，所有已处理 entry 的 `lastSyncCommit` 为当前 commit hash。
- 更新或新建的每个 HTML 文件在 `outputDir` 下存在，可直接在浏览器打开预览。
- HTML 文件满足阶段 3「HTML 生成质量要求」的 6 条约束。

## 反模式

| 错误行为 | 正确做法 |
|----------|----------|
| 跳过初始化直接进流程 | 必须先读取 manifest，确认 outputDir 和 baseBranch 正确 |
| HTML 中引用外部 URL（CDN、字体服务） | 所有资源内联，无外部依赖 |
| 用户取消后仍写回 manifest | 用户取消 = manifest 不更新，HTML 文件已写入磁盘但状态未记录 |
| 未更新 `lastSyncCommit` 就退出 | 下次 diff 基准错误，导致漏同步 |
| 手动编辑 manifest.json 绕过流程 | 通过 Skill 流程维护，保持 entries 与实际文件一致 |
