# BCG 品牌设计标准

> 本文件由 `/style-scout` 自动分析 bcg.com 报告页面生成。
> 来源：https://www.bcg.com/publications/2026/from-ai-skills-to-business-performance

---

## 1. 品牌概述

BCG 数字端设计特征：
- **极简现代**：近黑正文色 `#212427`，白色背景，极少装饰
- **深墨绿权威**：专属标题色 `#0C2B15`，传递专业与自然感
- **轻字重大标题**：H1/H2 使用 300 Light 字重衬线字体，与正文形成强烈对比
- **暖米底色**：分区背景用 `#F1EEEA` 而非纯灰，增加温度感
- **亮绿小面积点缀**：`#96F878` 仅用于 CTA 按钮、标签徽章

---

## 2. 色彩体系

### 2.1 主色板

| 角色 | 色值 | 用途 |
|------|------|------|
| Deep Forest Green | `#0C2B15` | H1/H2 标题色、链接色、blockquote 左色条 |
| Near Black | `#212427` | 正文、H3、分隔线 |
| Bright Lime | `#96F878` | CTA 按钮、高亮标签（小面积） |
| Dark Card Green | `#0E3E1B` | 报告卡片/图片背景块 |

### 2.2 背景与辅助色

| 用途 | 色值 |
|------|------|
| 分区背景 | `#F1EEEA`（暖米色） |
| 分隔线/边框 | `#DCD5CE` |
| Meta/辅助文字 | `#696969` |
| 次级 CTA 按钮 | `#FF5B4D`（橙红色） |

---

## 3. 字体体系

### 3.1 官方字体（专有，需授权）

| 场景 | 字体 |
|------|------|
| H1/H2 标题 | `henderson-bcg-serif`（衬线，Light 300 字重） |
| 正文/H3/导航 | `henderson-bcg-sans`（无衬线） |

### 3.2 降级字体栈

**衬线（标题）：** `"Georgia", "STSong", "Songti SC", "SimSun", serif`

**无衬线（正文）：** `"PingFang SC", "Helvetica Neue", "Arial", "STHeiti", sans-serif`

### 3.3 字号体系（实测）

| 元素 | 字号 | 字重 | 颜色 |
|------|------|------|------|
| H1 | 34.5pt | 300 | `#0C2B15` |
| H2 | ~10–18pt | 700 或 300 | `#0C2B15` |
| H3 | 30pt | 300 | `#212427` |
| 正文 | 12pt | 400 | `#212427` |
| Meta | ~10pt | 400 | `#696969` |

---

## 4. 组件规则

### 4.1 标题装饰

| 级别 | 装饰方式 |
|------|---------|
| H1 | 下方细横线 `#DCD5CE`（暖米色，轻装饰） |
| H2 | 下方细横线 `#DCD5CE` |
| H3 | 左侧色条 `#0C2B15`（深墨绿） |
| H4 | 无装饰，uppercase + letter-spacing，颜色 `#696969` |

### 4.2 表格

- 麦肯锡风格水平线，颜色 `#212427`
- 无背景色，无竖线

### 4.3 引用块

- 左侧色条 `#0C2B15`，衬线字体，Light 字重，斜体

### 4.4 代码块

- 背景 `#F1EEEA`（暖米色），左侧装饰线 `#0C2B15`

---

## 5. 格式推导指南

### → DOCX（bcg-style.json）

- `headings.h1.color` = `0C2B15`，`bold: false`
- `headings.h1.font_en` = `Georgia`（衬线降级）
- `table.border_mode` = `mckinsey`，`rule_color` = `212427`
- 正文无首行缩进（`first_line_indent_chars: 0`）

### → PDF（bcg.css）

- H1/H2 用 `font-family: Georgia, serif`，`font-weight: 300`
- H1/H2 下方用 `border-bottom: 1px solid #DCD5CE`
- H3 左侧色条 `border-left: 3px solid #0C2B15`
- `pre` 背景 `#F1EEEA`，左色条 `#0C2B15`
- blockquote 用衬线字体 + `#0C2B15` 左色条
