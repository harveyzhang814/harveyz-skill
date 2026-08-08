# Subagent 2 派发 prompt（打标 + 翻译）

由主 session 读取本文件，将 `<ORIGIN_PATH>` 替换为 Subagent 1 返回的 origin_path，替换后按平台的 subagent 派发机制原样作为任务内容派发。

Stage 2 简化：不使用固定词表，标签由模型根据内容自由生成；不做 URL 去重。

---

【Subagent 2 - 打标 + 翻译】读取原文，生成标签与摘要，翻译正文。

原文路径：<ORIGIN_PATH>

执行步骤：

1. 读取 `<ORIGIN_PATH>` 的完整内容（frontmatter + 正文）。

2. 基于正文内容：
   - 生成 2-4 个自由标签（英文小写、kebab-case，例如 `web-standards`、`ai-agent`），不依赖任何固定词表，按内容本身判断。
   - 生成一句话摘要（中文，20-40 字，`description` 字段用）。
   - 将正文翻译成中文（若原文已是中文，翻译结果等同原文，不做无意义的同语言转写）。

3. 计算 Translation 文件路径：`<ORIGIN_PATH>` 所在目录的上一级（`ArticleDir`）下的 `Translation/article.md`（与 `Origin/article.md` 并列）。

4. 写入 Translation 文件，frontmatter 对齐以下字段：

```yaml
---
source_url: {原 frontmatter 中的 source_url}
fetch_date: {原 frontmatter 中的 fetch_date}
origin_title: {原 frontmatter 中的 origin_title}
tags: [tag1, tag2, tag3]
description: "一句话摘要"
---

# {中文标题（若原标题非中文，翻译标题；若已是中文，沿用原标题）}

{翻译后的正文}
```

5. 完成后报告格式：
TRANSLATION_PATH: {translation_path}
打标+翻译完成（tags: {逗号分隔的标签列表}）
