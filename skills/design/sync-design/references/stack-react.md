# React 技术栈指南

适用于 React + Vite / CRA / 纯 React 项目（不含 Next.js，见 stack-nextjs.md）。

> **使用方式：** 同步时从 manifest 读取 `styleStrategy` 字段，只执行下方"源文件读取策略"中对应策略的那一节，忽略其他节。若 `styleStrategy` 为 `unknown`，则读取源文件内容后自行判断。若 `notes` 字段非空，以 `notes` 覆盖本文件中的冲突建议。

---

## 发现命令

```bash
# 发现页面/视图级组件（优先）
find src -type f \( -name "*.tsx" -o -name "*.jsx" \) \
  | grep -v node_modules | grep -v __tests__ | grep -v ".test." | grep -v ".spec." \
  | grep -E "(pages|views|screens|Page|View|Screen)" | sort

# 发现所有 React 组件（若上面结果太少）
find src -type f \( -name "*.tsx" -o -name "*.jsx" \) \
  | grep -v node_modules | grep -v __tests__ | grep -v ".test." | grep -v ".spec." | sort

# 发现设计系统文件候选
ls src/styles/tokens.css src/styles/variables.css src/styles/theme.ts src/theme.ts \
   src/styles/design-tokens.ts tailwind.config.js tailwind.config.ts \
   src/design-system/index.ts 2>/dev/null
```

---

## 平台配置模板

```json
{
  "web": {
    "label": "Web",
    "stackRef": "references/stack-react.md",
    "uiFilePatterns": [
      "src/pages/**/*.tsx",
      "src/views/**/*.tsx"
    ],
    "designSystemFile": "<检测到的 token 文件，或 null>"
  }
}
```

`uiFilePatterns` 根据发现命令的实际结果推导目录层级，优先选择 `pages/`、`views/`、`screens/` 等语义目录，避免把整个 `src/components/**` 都纳入（太宽泛）。

---

## 样式方案识别

初始化时检测项目使用的样式方案，记录到 manifest 的平台配置中（`styleStrategy` 字段）：

```bash
# 检测 Tailwind
ls tailwind.config.js tailwind.config.ts 2>/dev/null
grep -r "tailwindcss" package.json 2>/dev/null

# 检测 CSS Modules
find src -name "*.module.css" -o -name "*.module.scss" | head -3 2>/dev/null

# 检测 styled-components / emotion
grep -E '"styled-components"|"@emotion/react"' package.json 2>/dev/null

# 检测 CSS-in-JS (vanilla-extract, stitches, etc.)
grep -E '"@vanilla-extract"|"@stitches"' package.json 2>/dev/null
```

---

## 源文件读取策略

### Tailwind CSS

- 读取 `tailwind.config.js` / `tailwind.config.ts` 中的 `theme.extend`，提取自定义颜色、字体、间距
- class 名（如 `text-sm font-medium text-gray-700`）映射为实际 CSS 值，写入 HTML `<style>` 块中
- 不要直接在 HTML 中使用 Tailwind class（离线时无法渲染）
- 颜色：`text-gray-700` → `color: #374151`；布局：`flex flex-col gap-4` → `display:flex; flex-direction:column; gap:1rem`

### CSS Modules

- 同时读取与源文件同名的 `.module.css` / `.module.scss`
- 将 class 中的样式声明提取到 HTML `<style>` 块中
- `styles.container` → 对应 `.container` 选择器的内容

### styled-components / emotion

- CSS 定义内联在 JS 中，从组件定义处提取样式字符串
- 动态样式（依赖 props 的）取默认态或最常见态的值

### 普通 CSS / SCSS

- 读取源文件 `import` 的 CSS 文件，提取相关规则

### 内联 style prop

- 直接转换为 HTML `style` 属性

---

## 组件 Props 与 UI 状态

React 组件的 UI 状态通常来自：
- `useState`：`const [isLoading, setIsLoading] = useState(false)`
- Props：`interface Props { variant: 'primary' | 'ghost'; disabled?: boolean }`
- 外部 store（Zustand/Redux）：查看组件订阅的 slice

识别 UI 状态时，检查 TypeScript 类型定义和 `if/switch` 条件渲染分支，这些分支就是需要在 HTML 中体现的 `uiStates`。

---

## 常见 Gotchas

- **Context / Provider**：`ThemeProvider`、`AuthContext` 等 wrapper 不需要在 HTML 中体现，只还原视觉层
- **lazy import**：`React.lazy(() => import('./Page'))` 中的组件路径是真实源文件，正常处理
- **动态 className**：`clsx(styles.btn, { [styles.active]: isActive })` → 生成所有可能的 class 组合，在 HTML 中用独立区块展示各状态
- **图片 / SVG import**：`import logo from './logo.svg'` → HTML 中用占位矩形替代，标注尺寸和描述
- **国际化字符串**：`t('key')` → 保留 key 名或使用中文描述性文字
