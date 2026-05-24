# Next.js 技术栈指南

适用于 Next.js 13+（App Router）和 Next.js 12 以下（Pages Router）。

> **使用方式：** 同步时从 manifest 读取 `styleStrategy` 字段，只执行"源文件读取策略"中对应策略的那一节。若 `notes` 字段非空，以 `notes` 覆盖本文件中的冲突建议。样式方案细节参考 `stack-react.md`。

---

## 发现命令

```bash
# 判断 App Router 还是 Pages Router
ls app/ src/app/ pages/ src/pages/ 2>/dev/null

# App Router：发现页面和布局文件
find app src/app -type f -name "page.tsx" -o -name "layout.tsx" -o -name "loading.tsx" -o -name "error.tsx" \
  | grep -v node_modules | sort

# Pages Router：发现页面文件
find pages src/pages -type f \( -name "*.tsx" -o -name "*.jsx" \) \
  | grep -v node_modules | grep -v "_app" | grep -v "_document" | grep -v "api" | sort

# 发现共享组件
find components src/components -type f \( -name "*.tsx" -o -name "*.jsx" \) \
  | grep -v node_modules | sort

# 设计系统文件候选
ls tailwind.config.js tailwind.config.ts \
   styles/globals.css src/styles/globals.css \
   styles/tokens.css src/styles/tokens.css \
   lib/theme.ts src/lib/theme.ts 2>/dev/null
```

---

## 平台配置模板

**App Router：**
```json
{
  "web": {
    "label": "Web",
    "stackRef": "references/stack-nextjs.md",
    "uiFilePatterns": [
      "app/**/page.tsx",
      "app/**/layout.tsx"
    ],
    "designSystemFile": "<token 文件或 null>"
  }
}
```

**Pages Router：**
```json
{
  "web": {
    "label": "Web",
    "stackRef": "references/stack-nextjs.md",
    "uiFilePatterns": [
      "pages/**/*.tsx",
      "src/pages/**/*.tsx"
    ],
    "designSystemFile": "<token 文件或 null>"
  }
}
```

---

## 源文件读取策略

### App Router 特有

- **`page.tsx`**：页面主体，是主要的 UI 源文件
- **`layout.tsx`**：包裹 page 的壳（导航栏、侧边栏等）。若 page 的外观依赖 layout，同时读取最近一层的 layout.tsx
- **`loading.tsx`**：骨架屏或加载态，是一个独立的 `uiState`
- **`error.tsx`**：错误态，也是独立的 `uiState`
- **Server Components vs Client Components**：对 HTML 生成无影响，都读取 `return` 的 JSX 结构

### 路由参数

- `[id]`、`[slug]` 等动态段在 HTML 备份中用占位值替代（如 `123`、`example-post`）

### Metadata

- `export const metadata = { title: '...' }` → 设置 HTML `<title>`

### 样式方案

参考 `stack-react.md` 中对应样式方案的读取策略（Tailwind / CSS Modules / styled-components）。

---

## 常见 Gotchas

- **API Routes**：`app/api/` 或 `pages/api/` 下的文件不是 UI，`uiFilePatterns` 中排除（用 `grep -v api` 过滤）
- **`_app.tsx` / `_document.tsx`**：全局配置文件，不直接对应某个界面；若影响全局样式（如注入 CSS 变量），在生成 HTML 时纳入上下文
- **Middleware**：`middleware.ts` 不是 UI 文件
- **图片优化**：`<Image>` 组件 → HTML 中用 `<img>` 替代，设置对应的 `width`/`height`/`object-fit`
- **Link 组件**：`<Link href="...">` → HTML 中用 `<a>` 替代
- **`use client` / `use server`**：不影响 HTML 生成，忽略这些指令
