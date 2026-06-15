# Electron 技术栈指南

适用于 Electron 应用的渲染进程 UI。

> **使用方式：** 同步时从 manifest 读取 `styleStrategy` 字段，只执行渲染层对应 stack 文件中匹配策略的那一节。若 `notes` 字段非空，以 `notes` 覆盖本文件中的冲突建议。Electron 渲染层通常是 React 或 Vue，本文件处理 Electron 特有的目录结构和注意事项；样式方案细节参考 `stack-react.md` 或 `stack-vue.md`。

---

## 发现命令

```bash
# 识别渲染层框架
cat package.json | grep -E '"react"|"vue"|"svelte"'

# 发现渲染进程目录结构（常见布局）
ls src/renderer src/renderer/src src/web src/ui 2>/dev/null

# 发现页面/视图级组件
find src -type d \( -name "pages" -o -name "views" -o -name "screens" -o -name "windows" \) \
  | grep -v node_modules | head -10

# 发现所有渲染层 UI 文件（根据检测到的框架选扩展名）
find src/renderer -type f \( -name "*.tsx" -o -name "*.jsx" -o -name "*.vue" \) \
  | grep -v node_modules | grep -v __tests__ | grep -v ".test." | sort

# 发现设计系统文件
ls src/renderer/src/styles/tokens.css \
   src/renderer/styles/variables.css \
   src/renderer/src/theme.ts \
   src/styles/tokens.css \
   tailwind.config.js tailwind.config.ts 2>/dev/null
```

---

## 平台配置模板

```json
{
  "renderer": {
    "label": "Renderer",
    "stackRef": "references/stack-electron.md",
    "uiFilePatterns": [
      "src/renderer/src/pages/**/*.tsx",
      "src/renderer/src/views/**/*.tsx"
    ],
    "designSystemFile": "<检测到的 token 文件，或 null>"
  }
}
```

---

## Electron 特有目录结构

常见项目布局（不同脚手架有差异）：

```
# electron-vite / electron-builder + Vite
src/
  main/          ← 主进程（Node.js），不含 UI
  preload/       ← preload 脚本，不含 UI
  renderer/      ← 渲染进程（React/Vue）← 扫描这里
    src/
      pages/
      components/
      styles/

# Electron Forge
src/
  index.ts       ← 主进程入口
  renderer.ts    ← 渲染进程入口
  components/    ← UI 组件 ← 扫描这里
  pages/
```

初始化时通过 `ls src/main src/preload src/renderer` 判断是哪种结构，只扫描渲染层目录。

---

## 多窗口支持

Electron 应用可能有多个独立窗口（主窗口、偏好设置、托盘弹窗等），每个窗口对应不同的入口。若发现多个窗口目录，每个窗口可配置为独立的 platform（或在同一 platform 下作为不同 entry）：

```json
{
  "main-window": {
    "label": "主窗口",
    "uiFilePatterns": ["src/renderer/pages/**/*.tsx"],
    "designSystemFile": "src/renderer/styles/tokens.css"
  },
  "settings-window": {
    "label": "设置窗口",
    "uiFilePatterns": ["src/settings/**/*.tsx"],
    "designSystemFile": "src/renderer/styles/tokens.css"
  }
}
```

---

## 源文件读取策略

渲染层框架对应的样式读取策略见：
- React 渲染层 → `stack-react.md` 中的"源文件读取策略"
- Vue 渲染层 → `stack-vue.md` 中的"源文件读取策略"

Electron 特有补充：
- **IPC 调用**（`ipcRenderer.invoke()`）在 HTML 备份中显示为占位状态（loading 或默认值），不需还原真实数据
- **Node.js API**（`fs`、`path`、`shell`）只在主进程中使用，渲染层不会出现

---

## 常见 Gotchas

- **主进程文件**：`src/main/`、`src/background.ts`、`preload.ts` 等不是 UI 文件，`uiFilePatterns` 中明确排除
- **Electron 特定 API**：`remote.app`、`nativeTheme` 等在 HTML 中取固定值（如 `nativeTheme` 取 light 模式）
- **窗口尺寸**：Electron 窗口通常有固定或最小尺寸，HTML 预览设置对应的 `max-width` 和最小高度以还原真实比例
- **系统原生控件**：标题栏、`<webview>`、系统对话框在 HTML 中用灰色矩形占位，标注"系统原生控件"
