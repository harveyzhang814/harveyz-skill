# Vue / Nuxt 技术栈指南

适用于 Vue 3 + Vite、Vue 2、以及 Nuxt 3 / Nuxt 2 项目。

> **使用方式：** 同步时从 manifest 读取 `styleStrategy` 字段，只执行"样式方案"中对应策略的那一节。若 `notes` 字段非空，以 `notes` 覆盖本文件中的冲突建议。

---

## 发现命令

```bash
# 判断是否为 Nuxt
ls nuxt.config.ts nuxt.config.js 2>/dev/null

# Nuxt 3：发现页面文件
find pages -type f -name "*.vue" | grep -v node_modules | sort

# Vue 通用：发现视图/页面组件
find src -type f -name "*.vue" \
  | grep -v node_modules | grep -v __tests__ | grep -v ".test." \
  | grep -E "(views|pages|screens|layouts)" | sort

# Vue 通用：发现所有组件
find src -type f -name "*.vue" \
  | grep -v node_modules | grep -v __tests__ | sort

# 设计系统文件候选
ls src/styles/variables.css src/styles/tokens.css \
   src/styles/variables.scss src/assets/styles/variables.scss \
   src/theme.ts src/plugins/theme.ts \
   tailwind.config.js tailwind.config.ts \
   uno.config.ts 2>/dev/null
```

---

## 平台配置模板

**Vue + Vite：**
```json
{
  "web": {
    "label": "Web",
    "stackRef": "references/stack-vue.md",
    "uiFilePatterns": [
      "src/views/**/*.vue",
      "src/pages/**/*.vue"
    ],
    "designSystemFile": "<token 文件或 null>"
  }
}
```

**Nuxt 3：**
```json
{
  "web": {
    "label": "Web",
    "stackRef": "references/stack-vue.md",
    "uiFilePatterns": [
      "pages/**/*.vue",
      "layouts/**/*.vue"
    ],
    "designSystemFile": "<token 文件或 null>"
  }
}
```

---

## 源文件读取策略

### 单文件组件（SFC）结构

Vue SFC（`.vue`）把模板、脚本、样式放在同一文件：

```vue
<template>  ← UI 结构，重点读取
<script setup lang="ts">  ← 状态定义
<style scoped>  ← 局部样式，直接使用
```

读取顺序：
1. 先读 `<template>` 确定 UI 结构和状态分支
2. 读 `<script setup>` 中的 `ref`、`computed`、`defineProps` 确定状态来源
3. 读 `<style scoped>` / `<style module>` 提取样式规则，直接内联到 HTML `<style>` 中

### Composition API 状态识别

```ts
const isLoading = ref(false)           // → uiState: loading
const error = ref<string | null>(null)  // → uiState: error
const props = defineProps<{            // → 多态变体
  variant: 'primary' | 'ghost'
}>()
```

### Options API 状态识别

```js
data() {
  return { isOpen: false, activeTab: 'general' }
}
computed: {
  isEmpty() { return this.items.length === 0 }
}
```

### 样式方案

**`<style scoped>`（最常见）：**
直接提取样式规则，添加到 HTML `<style>` 中（去掉 scoped 特性）。

**`<style module>`：**
通过 `$style.className` 引用，将 CSS Modules 的类名提取并内联。

**Tailwind / UnoCSS：**
参考 `stack-react.md` 中的 Tailwind 处理策略（class 映射为实际 CSS 值）。
UnoCSS class 处理方式与 Tailwind 相同。

**全局变量（SCSS variables）：**
若 `<style>` 中有 `@use '~/styles/variables' as *`，需同时读取对应变量文件。

---

## Nuxt 特有

- **`layouts/`**：类似 Next.js 的 layout，包裹页面的壳（导航、侧边栏）。当 page 依赖某个 layout 时，一并读取
- **Nuxt auto-imports**：`useRoute()`、`useFetch()` 等不需要显式 import，读取时知道这些是 Nuxt 内置即可，不影响 HTML 生成
- **`server/` 目录**：API 路由，不是 UI 文件，排除
- **`composables/`**：状态逻辑，按需读取影响 UI 的部分

---

## 常见 Gotchas

- **`v-if` / `v-show`**：条件渲染分支通常就是不同的 `uiState`，在 HTML 中分别展示
- **`v-for`**：用 2-3 个典型数据项展示列表状态
- **`<RouterView>` / `<NuxtPage>`**：在 HTML 中用占位区域替代，标注"子页面区域"
- **`<Transition>`**：HTML 中只展示静态状态，不还原动画
- **图片**：`<img :src="...">`、`<NuxtImg>` → `<img>` 占位，设置尺寸
- **Slot**：`<slot>` 用有代表性的内容填充（参考组件的典型用法）
