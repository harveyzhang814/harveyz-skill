# 初始化子流程

由 SKILL.md「初始化」的检查清单调用；每个子流程完成后回到清单，按清单写明的去向继续。

## 首次初始化

（manifest 文件不存在时执行）

### 1. 询问基础配置

1. `这个项目的 base 分支是什么？（如 main / staging）`
2. `HTML 设计备份存放在哪个目录？（默认：.hskill/sync-design/html/）`
3. `设计规范文件路径是什么？（如 DESIGN.md；若无请留空）`
4. `这个项目有设计系统目录（设计标准、令牌、共用组件样式）吗？`：有则在第 5 步写 manifest 前执行下文「设计系统配置」第 1–3 步，把结果一并写入；没有则不写 `designSystem`。

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
  "version": 6,
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
    },
    "designSystem": "<见「设计系统配置」；没有设计系统时不写这个键>"
  },
  "entries": [],
  "drafts": [],
  "ignoredFiles": []
}
```

完成后回到 SKILL.md 初始化清单第 7 项（路由）。

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

3. 全部处理完毕后写入 manifest，回到 SKILL.md 初始化清单第 4 项。

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

**否：** 保持现有路径。

无论是否迁移，完成后回到 SKILL.md 初始化清单第 3 项。

---

## 设计系统配置

（首次初始化第 4 问答「有」、初始化清单第 6 项选是，或本次模式为配置设计系统时执行）

### 字段

写在 `manifest.config.designSystem`，路径都相对项目根。示例：

```json
"designSystem": {
  "dir": "design-system",
  "standard": "design-system/STANDARD.md",
  "tokens": "design-system/tokens.css",
  "componentStyles": ["design-system/shared/sample.css"],
  "scripts": ["design-system/shared/icons.js"],
  "themes": [{ "name": "dark", "query": "" }, { "name": "light", "query": "?theme=light" }],
  "themeSwitch": "引用 scripts 里的 icons.js：它在首次绘制前读 ?theme=，给 <html> 打 data-theme",
  "guard": "node design-system/tools/check-rules.mjs {files}",
  "scratchDir": ".design-scratch",
  "gapsFile": "design-system/GAPS.md",
  "modes": ["design"]
}
```

| 字段 | 必填 | 含义 |
|---|---|---|
| `dir` | 是 | 设计系统根目录。标准怎么改，以这里自己的说明为准 |
| `standard` | 是 | 设计标准（规则与判据）；启用时替代 `designSpec` |
| `tokens` | 是 | 令牌文件；稿子用 `<link>` 引用 |
| `componentStyles` | 否 | 共用组件样式文件列表；稿子用 `<link>` 引用 |
| `scripts` | 否 | 共用脚本列表（图标、主题切换等）；稿子用 `<script src>` 引用 |
| `themes` | 是 | 主题列表，第一个是默认主题；`query` 是打开该主题时接在稿子路径后的查询串，默认主题一般为空 |
| `themeSwitch` | 多主题时必填 | 稿子怎样按 `query` 切主题；项目共用脚本已实现时，写明引用哪个 |
| `guard` | 否 | 项目守卫命令，在项目根运行。必须含 `{files}`，运行时替换为要检查的稿子路径（相对项目根，逐个加引号，空格分隔）；退出码 0 为通过，非 0 为有违规，违规写在输出里 |
| `scratchDir` | 是 | 局部对比视图的临时目录，应被 git 忽略 |
| `gapsFile` | 是 | 标准缺口清单；sync-design 只往里追加条目 |
| `modes` | 是 | 对哪些模式启用：`["design"]`；同步模式改用设计系统后为 `["design", "sync"]` |

### 步骤

1. **登记或修改：** 问设计系统根目录（已登记过就以现有值为准，只问要改什么）。在目录里找各字段的候选：标准文档、定义令牌的 CSS、共用组件样式与脚本、守卫脚本（读它的用法说明，找检查指定文件的参数）、缺口清单；主题从令牌文件里的主题选择器（如 `[data-theme="light"]`）和目录说明、样例页面推断。`scratchDir` 默认 `.design-scratch`，`modes` 默认 `["design"]`。
2. **核对：** `scratchDir` 没被 git 忽略（`git check-ignore -q <scratchDir>/` 失败）时提醒用户。守卫还不支持只检查指定文件时，`guard` 先不写，告诉用户守卫要先支持，此前生成后检查会跳过守卫并在摘要里写明。
3. **确认：** 展示整块配置，请用户确认或修改。
4. **同步模式改用设计系统：** 用户要求时，先问「代码里的令牌和样式已经和设计系统一致了吗？」；用户确认一致才在 `modes` 加上 `"sync"`。切换后，已有完成稿在下次同步改到时按 SKILL.md「设计系统」的旧写法规则转换。
5. **写回：** 写入 `config.designSystem`；`version` 小于 `6` 时一并更新为 `6`（本次模式为配置设计系统时，初始化清单第 6 项没有执行，版本要在这里补上，否则下次运行还会再问），写回 manifest。

### 完成标准

- `config.designSystem` 已写回，必填字段齐全，路径都存在；`guard` 有值时含 `{files}`；`version` 不小于 `6`。
- 本次是首次初始化时回到初始化子流程第 5 步；是初始化清单第 6 项时回到清单；本次模式为配置设计系统时输出配置摘要后结束。
