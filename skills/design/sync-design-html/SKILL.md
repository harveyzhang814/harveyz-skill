---
name: sync-design-html
description: Use after any UI source file change — detects changed view/component files via git diff and syncs them to high-fidelity HTML design backups. Maintains a manifest as the source-of-truth mapping between source files and HTML previews. Also invocable as a post-step from /ship or /review. Trigger when user says "sync design", "update HTML preview", "design changed", or after UI code edits.
version: "3.0.0"
user_invocable: true
---

# Sync Design HTML

检测前端视图文件变动，同步更新高保真 HTML 设计备份文件。

**Announce at start:** "I'm using sync-design-html to detect UI changes and update HTML design backups."

---

## 步骤 ①：读取 Manifest

读取 `docs/reference/design-html-manifest.json`。

**如果文件不存在：**
执行【附录 A：首次初始化流程】，完成后继续步骤 ②。

**如果文件存在且 `entries` 为空：**
执行【附录 B：已有 HTML 扫描流程】，完成后继续步骤 ②。

**如果文件存在且有 entries：**
直接继续步骤 ②。

## 步骤 ②：全局 Diff 检测

将 `manifest.config.platforms` 中所有平台的 `uiFilePatterns` 和 `designSystemFile`（非 null）汇总，传给 git 作为过滤参数：

```bash
git diff <manifest.baseBranch>...HEAD --name-only -- <pattern1> <pattern2> ...
```

用 git 原生 glob 支持过滤（`**` 跨目录 glob 可正确处理），而非先拉全量再手动筛。

**如果过滤后列表为空：**
输出："当前分支相对于 `<baseBranch>` 无 UI 文件变动，无需同步。" 然后退出。

**否则：** 将过滤后的文件列表记为 `<changedFiles>`，继续步骤 ③。

## 步骤 ③：识别设计系统文件变动

检查 `<changedFiles>` 中是否包含各平台的 `designSystemFile`（跳过值为 `null` 的平台）。

**如果包含设计系统文件：**

对每个包含的设计系统文件，询问用户：

> "`<设计系统文件名>` 发生变动。是否重新生成所有 `<platform>` HTML 设计文件？（推荐：是，确保全局 token 一致）"

- **用户选「是」：** 将该平台 manifest 中的所有 entries 加入待处理队列，后续执行全量重新生成。将设计系统文件从 `<changedFiles>` 中移除。
- **用户选「否」：** 保留 `<changedFiles>` 中的设计系统文件，后续按普通视图文件处理。

**如果不包含设计系统文件：** 直接继续步骤 ④。

## 步骤 ④：Entry 查找与路由

对 `<changedFiles>` 中的每个文件（去重：同一 entry 只触发一次）：

1. **检查是否在 `manifest.ignoredFiles` 中：** 如果是，跳过。

2. **在 manifest.entries 中查找 sourceFiles 包含该文件的 entry：**
   - 找到 → 加入**更新队列**
   - 未找到 → 加入**新建队列**

处理完所有文件后：
- 更新队列非空 → 执行【步骤 ⑤-A：更新流程】
- 新建队列非空 → 执行【步骤 ⑤-B：新建流程】
- 两者均为空 → 输出"所有变动文件已在忽略列表中，无需同步。"，退出。

## 步骤 ⑤-A：更新流程

对更新队列中的每个 entry，按顺序执行：

### a. 获取精确增量 Diff

```bash
git diff <entry.lastSyncCommit 或 manifest.baseBranch（如无 lastSyncCommit）>...HEAD -- <entry.sourceFiles 用空格分隔>
```

### b. 读取上下文

依次读取，**后读的内容优先级更高，可覆盖前面的通用指引**：

1. `manifest.config.designSpec`（设计规范文件；若不存在则跳过）
2. 该 entry 所属平台的 `designSystemFile`（若有）
3. 该平台 `stackRef` 指向的 reference 文件（通用技术栈策略）
4. 该平台 `styleStrategy` 字段 —— 在 reference 的多种样式策略中，只执行与此字段匹配的那一条；若字段为 `null` 或 reference 中无对应策略，则从源文件内容自行判断
5. 该平台 `notes` 字段 —— 项目特定约定（如需读取额外文件、某类组件的特殊处理方式等），与 reference 冲突时以 `notes` 为准
6. `<entry.htmlFile>`（当前 HTML 文件；若不存在则降级为全量生成：读取所有 `entry.sourceFiles` 完整源码）

### c. 判断更新范围

- **全量重新生成**（entry 在步骤 ③ 的全量队列中）：读取所有 `entry.sourceFiles` 完整源码重新生成。
- **增量更新**（普通视图变动）：根据 diff 判断受影响的 UI 状态或组件区块，只替换该部分，保留未变动结构。

生成要求见【HTML 生成质量约束】。

### d. 写回 HTML 文件

## 步骤 ⑤-B：新建流程

对新建队列中的每个文件，依次执行：

### a. 检查 pattern 覆盖（配置演进）

在询问用户之前，先检查：该文件所在目录是否被现有任一 `uiFilePatterns` 覆盖？

- **未覆盖** → 在后续询问中附带提示：
  > "此文件目录 `<dir>/` 未在当前配置中。是否将 `<建议 pattern>` 加入 `<platform>.uiFilePatterns`，以便未来自动检测此目录下的变动？"
  - 用户选「是」→ 更新 `manifest.config.platforms[platform].uiFilePatterns`，并在步骤 ⑥ 一并写回
  - 用户选「否」→ 此文件作为 one-off entry 处理，不修改 patterns

### b. 询问用户

依次提问：

1. `发现未映射的 UI 文件：<文件路径>。要为它创建 HTML 设计备份吗？`
   - **跳过并永久忽略：** 加入 `manifest.ignoredFiles`，结束此文件处理。
   - **本次跳过：** 不修改 ignoredFiles。
   - **是：** 继续。

2. `屏幕/组件名是什么？（kebab-case，如 "task-history"）`

3. `这个界面有哪些 UI 状态？（逗号分隔，如 idle, loading, error）`

4. `一句话描述这个界面的功能：`

根据文件路径匹配 `manifest.config.platforms` 确定所属平台；无法自动匹配时询问用户。

### c. 读取上下文

依次读取，**后读的内容优先级更高，可覆盖前面的通用指引**：

1. `manifest.config.designSpec`（若存在）
2. 该平台的 `designSystemFile`（若有）
3. 该平台 `stackRef` 指向的 reference 文件（通用技术栈策略）
4. 该平台 `styleStrategy` 字段 —— 只执行 reference 中与此字段匹配的样式处理策略；若为 `null` 则从源文件自行判断
5. 该平台 `notes` 字段 —— 项目特定约定，与 reference 冲突时以 `notes` 为准
6. 源文件完整内容（及 `notes` 或 reference 中指定的关联文件）
7. `manifest.config.outputDir` 下**已有的同平台** HTML 文件（选一个作风格参考）

### d. 生成完整高保真 HTML

生成要求见【HTML 生成质量约束】。

输出路径：`<manifest.config.outputDir>/<screenName>-<platform>-design.html`

### e. 在 Manifest 新增 Entry

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

## 步骤 ⑥：确认与 Manifest 写回

### 输出同步摘要

```
本次同步摘要：
  更新：
    · <entry.id>（<htmlFile>）— <变动范围>
  新建：
    · <screenName>-<platform>-design.html（<description>）
  配置变更：
    · <platform>.uiFilePatterns 新增 <pattern>
  忽略：
    · <文件路径>（加入 ignoredFiles）
```

**用户选「是」：**
1. `git rev-parse HEAD` 获取当前 commit hash
2. 将所有已处理 entry 的 `lastSyncCommit` 更新为该 hash
3. 写回 `docs/reference/design-html-manifest.json`（含配置演进的 patterns 变更）
4. 询问是否 `git add` 并给出建议 commit message：
   `chore: sync HTML design backups — <entry id 列表>`

**用户选「否」：**
输出："同步未确认。HTML 文件已写入磁盘但 manifest 未更新。"

---

## HTML 生成质量约束

1. **Token 来源：** 所有颜色、字体、间距值从当次读取的设计规范和设计系统文件中提取，不得凭记忆填写。

2. **CSS 变量命名：** 与设计规范文件中的 token 名完全一致（以实际读取为准，不预设变量名）。

3. **UI 状态完整性：** `entry.uiStates` 中的每个状态必须在 HTML 中有对应可视区块或 class 切换。

4. **离线可用：** 禁止引用任何外部 URL。样式全部内联在 `<style>` 中，单文件可直接在浏览器打开预览。

5. **风格对齐：** 与同项目已有 HTML 文件保持一致的代码风格：CSS 变量声明格式、状态区块注释格式（`/* ── 状态名 ── */`）、整体结构顺序。

6. **高保真要求：** 尺寸、圆角、阴影、字号、行高尽量还原设计规范；规范未涉及的参考设计系统文件中的具体值。

---

## 附录 A：首次初始化流程

（manifest 文件不存在时执行）

### A-1. 询问基础配置

1. `这个项目的 base 分支是什么？（如 main / staging）`
2. `HTML 设计备份存放在哪个目录？（默认：docs/reference/design-previews/）`
3. `设计规范文件路径是什么？（如 DESIGN.md；若无请留空）`

### A-2. 自动检测技术栈

先读取 `references/stacks.md`（包含所有已知栈的检测信号），然后依次执行以下检测：

```bash
# 1. 语言级特征文件
find . -maxdepth 4 -name "*.xcodeproj" -o -name "Package.swift" 2>/dev/null | grep -v node_modules | head -3
find . -maxdepth 3 -name "pubspec.yaml" 2>/dev/null | head -3

# 2. 读取 package.json（若存在）
cat package.json 2>/dev/null

# 3. 框架配置文件
ls next.config.js next.config.ts nuxt.config.ts nuxt.config.js svelte.config.js angular.json astro.config.mjs tauri.conf.json 2>/dev/null
```

根据 `references/stacks.md` 中的检测规则匹配技术栈，加载对应的 `references/stack-<name>.md`。

**可能检测到多个栈**（如 Electron 同时含 `electron` 和 `react`）：按 `stacks.md` 中的优先级取最具体的一个，次要技术作为备注记录。

### A-3. 运行发现命令

从加载的 `stack-*.md` 中读取【发现命令】，执行以发现项目中实际存在的 UI 文件：

```bash
# 示例（实际命令见各 stack-*.md）
find src -type f \( -name "*.tsx" -o -name "*.vue" \) | grep -v node_modules | grep -v test | grep -v spec | grep -v __tests__ | sort
```

将发现的文件按目录分组，推导出 `uiFilePatterns`（取最小覆盖的 glob，避免过于宽泛）。

同时按 `stack-*.md` 中的【设计系统文件候选】自动探测是否存在对应文件：
```bash
ls <候选路径1> <候选路径2> ... 2>/dev/null
```

同时探测实际样式方案（`styleStrategy`）：
```bash
# Tailwind
ls tailwind.config.js tailwind.config.ts 2>/dev/null

# CSS Modules
find src -name "*.module.css" -o -name "*.module.scss" 2>/dev/null | head -3

# vanilla-extract
find src -name "*.css.ts" -o -name "*.css.js" 2>/dev/null | head -3

# styled-components / emotion
grep -E '"styled-components"|"@emotion/react"' package.json 2>/dev/null

# UnoCSS
ls uno.config.ts uno.config.js 2>/dev/null

# 若以上均无匹配，检查是否有全局 CSS 或 SCSS
find src -name "*.scss" -o -name "variables.css" 2>/dev/null | head -3
```

按检测结果确定 `styleStrategy` 值：`tailwind` / `css-modules` / `vanilla-extract` / `styled-components` / `emotion` / `unocss` / `scss` / `css` / `unknown`。若检测到多种混用，记录主要策略，其余在 `notes` 中说明。

### A-4. 展示检测结果并请用户确认

输出检测摘要，格式如下：

```
检测到技术栈：<栈名称>（参考文件：references/stack-<name>.md）

建议平台配置：
  <platform-id>（<label>）
    uiFilePatterns:
      · <pattern1>（发现 N 个文件）
      · <pattern2>（发现 M 个文件）
    designSystemFile: <路径 或 未检测到>
    styleStrategy:    <检测到的样式方案>

以上配置是否正确？可告知我需要调整的部分。
```

等待用户确认或修改。若用户提出调整，按其意见修改配置后再次展示确认。

确认后，追加询问：

> `这个项目有哪些与参考文档不同的约定需要记录？（如特殊的全局组件、非标准文件位置、样式混用规则等；若无请留空）`

将用户输入记为该平台的 `notes`（空字符串或 `null` 均可）。这些 notes 在每次同步时会覆盖 reference 中冲突的通用建议。

### A-5. 创建 Manifest

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

**字段说明：**
- `stackRef`：通用技术栈参考，同步时作为基础策略加载
- `styleStrategy`：样式方案标识，同步时从 reference 中只执行对应策略，避免猜测
- `notes`：项目特定约定，优先级高于 reference，记录与通用参考不符的部分

继续执行主流程步骤 ②。

---

## 附录 B：已有 HTML 扫描流程

（manifest 存在但 `entries` 为空时执行）

1. 扫描 `manifest.config.outputDir` 下所有 `*.html` 文件。
2. 对每个 HTML 文件，询问用户：

   > `发现现有 HTML 文件：<文件名>。要为它建立 manifest 映射吗？`

   - **跳过：** 不处理，继续下一个。
   - **是：** 依次询问：
     1. `对应哪些源文件？（相对于项目根的路径，多个用逗号分隔）`
     2. `覆盖哪些 UI 状态？（如 idle, loading，用逗号分隔）`
     3. `一句话描述：`
   - 构造 entry（`lastSyncCommit` 设为 `null`）加入 `entries`。

3. 全部处理完毕后，写入 manifest，继续步骤 ②。
