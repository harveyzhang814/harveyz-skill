# 初始化子流程

由 SKILL.md「初始化」的检查清单调用；每个子流程完成后回到清单，按清单写明的去向继续。

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

完成后回到 SKILL.md 初始化清单第 5 项（路由）。

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
