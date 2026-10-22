---
name: sync-design
description: Use after any UI source file change — detects changed view/component files via git diff and syncs them to high-fidelity HTML design backups. Also supports pre-development design phase: creates or updates design draft HTML based on user feature descriptions. Maintains a manifest as the source-of-truth mapping between source files, design drafts, and HTML previews. Trigger when user says "sync design", "update HTML preview", "design changed", "create design", "design this", "migrate design drafts", or the Chinese equivalents, or after UI code edits.
version: "5.2.0"
user_invocable: true
---

# Sync Design HTML

检测前端视图文件变动，同步更新高保真 HTML 设计备份文件。

支持两种模式：
- **同步模式**（默认）：检测 UI 源文件变动，更新高保真 HTML 完成稿（存于 `outputDir/`）
- **设计模式**：根据功能描述创建或修改设计稿 HTML（存于 `outputDir/drafts/`）

**Announce at start:** "I'm using sync-design to detect UI changes and update HTML design backups."

`SKILL_DIR` 为当前 host 安装本 skill 的目录（包含 `scripts/`）。

---

## 模式检测

读取用户消息和上下文，判断调用意图，**记录为本次模式**（设计 / 同步 / 迁移），初始化完成后据此路由。

**设计模式触发词：** 「设计」「create design」「做个设计稿」「帮我设计」「design this」；或描述功能需求/界面改动但无代码变动信号。

**同步模式触发词：** 「sync design」「同步」「update HTML preview」「design changed」；或存在 UI 源文件 git diff。

**迁移模式触发词：** 「迁移设计稿」「migrate design drafts」。

**歧义时辅助判断：**
- `drafts[]` 非空且无 UI 文件 git diff → 倾向设计模式
- 检测到 UI 文件 git diff → 倾向同步模式
- 仍不确定 → 询问：「你是想更新设计稿，还是同步代码变动到 HTML？」

---

## 初始化（run first）

读取 `.hskill/sync-design/manifest.json`，按顺序检查（子流程见 `references/init.md`）：

1. 文件不存在 → 首次初始化，完成后直接跳到第 6 项。
2. `config.outputDir` 不以 `.hskill/` 开头（旧路径）→ 旧路径迁移，无论用户选是或否，完成后继续第 3 项。
3. `entries` 为空 → 已有 HTML 导入，完成后继续第 4 项。
4. `version` 小于 4 → 在现有字段基础上追加 `"drafts": []`，将 `version` 更新为 `4`，写回文件。
5. `version` 小于 5 且本次模式不是迁移 → 询问「已有设计稿是旧格式，要现在批量迁移吗？（迁移后改稿只读相关区块；稍后也可以说"迁移设计稿"）」；选是则执行 `references/migrate.md`。无论选什么，将 `version` 更新为 `5` 写回，只问这一次。
6. 路由：根据本次模式，跳转至[设计阶段](#设计阶段)、继续[同步流程](#流程strict--不可跳过或合并阶段)，或执行 `references/migrate.md`。

---

## 标准上下文（后读覆盖先读）

1. `manifest.config.designSpec`（若有）
2. 所属平台的 `designSystemFile`（若有）
3. 所属平台 `stackRef` 指向的 reference 中，与 `styleStrategy` 匹配的那一节；`styleStrategy` 为 `unknown`（或旧 manifest 里的 `null`）时，读源文件自行判断
4. 所属平台 `notes`（优先于 reference，记录项目特定约定）

---

## 稿子结构

生成规范和读取规则都以这一节为准。

| 层 | 按什么分 | 说明 |
|----|---------|------|
| 目录 | 阶段 | `outputDir/` 放完成稿（跟代码同步），`outputDir/drafts/` 放设计稿（代码之前） |
| 文件 | 界面单元 × 平台 | 一个窗口、面板、弹窗或跨界面体系一份，文件名 `<screenName>-<platform>-design.html`；单元粒度在建稿时由用户定 |
| 区段 | 内容类型，顺序固定 | ① 样式段：token 子段在前，组件样式按组件分块（`/* ── 组件名 ── */`）；② 图标定义区：重复图标只定义一次；③ 状态画面区：按 UI 状态分块；④ 脚本段（可选） |
| 状态块 | 不再切分 | 一块是一个状态的完整画面，是读取的最小单位 |

**状态标记：** 每个状态块前一行写 `<!-- ── <名称> ── -->`，标记独占一行。名称中以完整词出现该状态在 `uiStates` 里的名字，可加注记（如 `<!-- ── 状态 2：loading (DRAFT) ── -->`）。一块画面承载多个状态（组合状态、靠切换实现的状态）时，在标记里写 `覆盖：状态1 | 状态2`。被脚本拼接的共享内容块同样加标记，名称自取。块里嵌套的标记不切分外层块。

### 局部读取

稿子小于 40KB 时直接全量读。否则先跑 `python3 SKILL_DIR/scripts/design_html.py outline <htmlFile>` 拿到各区段与各状态块的行号范围，再按行号只读需要的部分：

| 要做的事 | 读取范围 |
|---------|---------|
| 改某个状态的画面（含同步时 diff 只牵涉某几个状态） | 样式段 + 目标状态块 |
| 新增状态 | 样式段 + 一个相近状态块作模板；新块带标记，追加到状态画面区 |
| 只改组件样式 | 样式段 |
| 换图标 | 图标定义区里该图标 + grep 到的引用处 |
| 改切换、拼接逻辑 | 脚本段 + 相关状态块 |
| 改 token、改在多个状态里重复出现的组件结构、`outline` 显示没有状态标记、全量重生成 | 全量读 |

图标定义区一般不读：状态块里只有引用，改画面用不到图标形状。

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

1. 读[标准上下文](#标准上下文后读覆盖先读)
2. 根据用户描述确定修改范围（哪些 UI 状态或区块）
3. 按[局部读取](#局部读取)读 `<draft.htmlFile>` 中该范围
4. 增量修改 HTML，只替换受影响区块；若有新 UI 状态，追加 `uiStates`
5. 写回 HTML 文件，更新 `drafts[].uiStates`（去重后写入，不写回 manifest，等步骤 3 统一写回）

#### 情况 B：无对应 draft entry（创建新设计稿）

新增的 draft entry 格式：

```json
{
  "id": "<screenName>-<platform>",
  "platform": "<platform>",
  "htmlFile": "<outputDir>/drafts/<screenName>-<platform>-design.html",
  "uiStates": ["<见下表>"],
  "description": "<见下表>",
  "linkedEntryId": "<见下表>"
}
```

| 字段 | 有完成稿 | 无完成稿 |
|------|---------|---------|
| `uiStates` | 继承完成稿 uiStates，按用户描述追加新状态 | 用户输入的状态列表 |
| `description` | 从用户描述提炼 | 用户输入的描述 |
| `linkedEntryId` | `<screenName>-<platform>`（直接填入，无需等待 sync 阶段回填） | `null` |

**B1. 检查是否有对应完成稿**

在 `manifest.entries[]` 中查找 `id` 与目标页面相同的 entry：

**有对应完成稿 →**

1. 用文件复制命令将完成稿 HTML（`entry.htmlFile`）复制到 `<outputDir>/drafts/<screenName>-<platform>-design.html` 作为基底，不经模型读写
2. 对新副本执行情况 A 步骤 1–4
3. 新增 draft entry（见上方 JSON 与差异表）

**无对应完成稿 →**

1. 询问用户（最少必要信息）：
   - `屏幕/组件名是什么？（kebab-case，如 "task-history"）`
   - `这个界面有哪些 UI 状态？（逗号分隔，如 idle, loading, error）`
   - `一句话描述这个界面的功能：`
2. 读[标准上下文](#标准上下文后读覆盖先读)，再从 `outputDir/drafts/` 选一个已有的同平台 HTML，只读其样式段作风格参考
3. 生成完整高保真 HTML（质量要求见[HTML 生成质量要求](#html-生成质量要求)）
4. 输出路径：`<outputDir>/drafts/<screenName>-<platform>-design.html`
5. 新增 draft entry（见上方 JSON 与差异表）

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

**b. 读取上下文**

读[标准上下文](#标准上下文后读覆盖先读)。`<entry.htmlFile>` 不存在时降级为全量生成：读取所有 `entry.sourceFiles` 完整源码。

**c. 确定更新范围**

- entry 在全量重生成队列中 → 读取所有 `entry.sourceFiles` 完整源码重新生成。
- 否则 → 根据 diff 判断受影响的 UI 状态或组件区块，按[局部读取](#局部读取)读 `<entry.htmlFile>` 中该范围，只替换该部分。

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

**c. 读取上下文**

读[标准上下文](#标准上下文后读覆盖先读)，再读源文件全文（及 `notes` 或 reference 中指定的关联文件），再从 `manifest.config.outputDir` 选一个**已有的同平台** HTML，只读其样式段作风格参考。

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

**f. 回填 linkedEntryId**（同更新队列 e）

---

#### HTML 生成质量要求

1. **Token 来源：** 所有颜色、字体、间距值从当次读取的设计规范和设计系统文件中提取，不得凭记忆填写。
2. **CSS 变量命名：** 与设计规范文件中的 token 名完全一致（以实际读取为准，不预设变量名）。
3. **UI 状态完整性：** `entry.uiStates` 中的每个状态必须在 HTML 中有对应可视区块或 class 切换。
4. **离线可用：** 禁止引用任何外部 URL。样式全部内联在 `<style>` 中，单文件可直接在浏览器打开预览。字体不得 base64 内嵌，只写字体名并带系统字体回退（如 `"Inter", system-ui, sans-serif`）。
5. **风格对齐：** 与同项目已有 HTML 文件保持一致的代码风格：CSS 变量声明格式、组件样式注释格式（`/* ── 组件名 ── */`）、整体结构顺序。
6. **高保真要求：** 尺寸、圆角、阴影、字号、行高尽量还原设计规范；规范未涉及的参考设计系统文件中的具体值。
7. **结构：** 区段顺序与状态标记见[稿子结构](#稿子结构)。`uiStates` 中每个状态都能在某个标记里找到（名称或 `覆盖`）。
8. **图标只定义一次：** 同一图标出现两次以上时，放进正文开头的图标定义区（`<svg class="sd-sprite" aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden">` 内的 `<symbol id="sd-icon-N">`，不写 viewBox），用到的地方保留原 `<svg>` 的属性、内容换成 `<use href="#sd-icon-N"/>`。样式里有选择器指向图标内部元素（如 `.x svg path`）的图标不收。

---

### 阶段 4：确认与写回

输出同步摘要，包含以下分类（有内容的分类才展示）：更新的 entry（id + htmlFile + 变动范围）、新建的 HTML 文件（文件名 + 描述）、配置变更（哪个 platform 的 uiFilePatterns 新增了什么 pattern）、忽略的文件（路径）。询问用户确认或取消。

**用户选「确认」：**
1. `git rev-parse HEAD` 获取当前 commit hash
2. 将所有已处理 entry 的 `lastSyncCommit` 更新为该 hash（不更新则下次 diff 基准错误、漏同步）
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

触发后先读 `references/draft-delete.md` 并按其执行：三个检查点全部通过且用户确认后才删除。

---

## 完成标准

**同步模式：**
- `.hskill/sync-design/manifest.json` 已写回，所有已处理 entry 的 `lastSyncCommit` 为当前 commit hash。
- 更新或新建的每个 HTML 文件在 `outputDir/` 下存在，可直接在浏览器打开预览。
- HTML 文件满足阶段 3「HTML 生成质量要求」的 8 条约束；本次写过的稿子不出现在 `python3 SKILL_DIR/scripts/design_html.py check <manifest>` 的待迁移列表里。

**设计模式：**
- 所有确认处理的页面，其设计稿 HTML 已写入 `outputDir/drafts/`，可直接在浏览器打开预览。
- `manifest.drafts[]` 已写回，entry 的 `uiStates` 与 HTML 内容一致；本次写过的稿子不出现在 `check` 的待迁移列表里。
- 有对应完成稿的 draft，其 `linkedEntryId` 已正确填写；无对应完成稿的 draft，`linkedEntryId` 为 `null`。

**迁移模式：** 见 `references/migrate.md` 的完成标准。

不手动编辑 manifest.json；entries 与实际文件的一致性靠本流程维护。
