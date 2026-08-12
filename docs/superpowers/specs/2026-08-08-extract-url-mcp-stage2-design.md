---
migrated: false
---

# extract-url-mcp Stage 2：设计

## 背景

Stage 1（已合并进 `staging`）验证了"通过真实 MCP 协议调用 browser-fetch-mcp 抓取网页并存原文"这条链路。Stage 2 在此基础上补上 extract-url 真实流程里的后半段：打标 + 翻译 + 存文件，让 `extract-url-mcp` 的整体形状（两个 subagent：抓取→打标翻译）跟 extract-url 对齐。

依然是验证性构建：不注册进 `skills-index.json`，不碰 `extract-url` / `probe-session`。

## 范围

**做：**
- 调整 `mcp_fetch_client.py` 的输出路径结构，从 Stage 1 的扁平 `<output_dir>/<hash8>.md` 改为 `<output_dir>/<hash8>/Origin/article.md`，为 Translation 腾出并列目录（`<output_dir>/<hash8>/Translation/article.md`），结构上对齐 extract-url。
- 新增 `references/subagent2-tag-translate-prompt.md`：全新写的 Subagent 2 派发 prompt——读 Origin 文件，生成 2-4 个自由标签（不用固定词表）、一句话摘要（description）、翻译正文，写 Translation 文件。
- `SKILL.md` 补上步骤 3（派发 Subagent 2）、步骤 4（汇总报告 origin_path + translation_path）。
- 用一个真实 URL 跑通完整两阶段流程（不是自动化测试——Subagent 2 是 LLM 任务，靠真实派发一次子代理验证，不是 pytest）。

**不做：**
- URL 去重（meta.json）——已在澄清阶段确认跳过
- 固定词表打标——已确认简化为模型自由打标
- 真实 Obsidian Vault 写入——继续写单独的测试输出目录，不碰用户真实 Vault
- `CHROME_PROFILE` / `use_auth` 认证态抓取——Stage 1 就没做，Stage 2 也不做

## 输出结构

```
<output_dir>/<hash8>/
  Origin/article.md        — 原文（Stage 1 已产出，这次调整路径）
  Translation/article.md   — 翻译 + frontmatter（tags/description）
```

Translation frontmatter 字段（对齐 extract-url 的最小子集）：`source_url`、`fetch_date`、`tags`（数组）、`description`（一句话摘要）、`origin_title`。

## 验证方式

真实派发 Subagent 2（不是自动化测试），对 Stage 1 已经抓取成功的一篇真实文章（例如 Wikipedia 那篇）执行打标+翻译，人工检查 Translation 文件的标签、摘要、译文质量是否合理。
