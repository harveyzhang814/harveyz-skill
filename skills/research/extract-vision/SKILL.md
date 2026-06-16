---
name: extract-vision
description: "Use when the user shares an image (screenshot, photo, receipt, invoice, menu, or any picture containing text) and wants to extract specific information from it — such as prices, dates, names, totals, or any structured data. Trigger this skill whenever the user says things like 'find X in this image', 'extract the total from this receipt', 'pull out all the items from this menu', or shares an image file and asks for specific fields or values. Use even if the user doesn't mention OCR — if they share a picture and want data out of it, this skill applies."
version: 1.2.0
user_invocable: true
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [OCR, image, text-extraction, screenshots, vision, subagent]
    related_skills: [ocr-and-documents]
---

# 图像文字提取：PaddleOCR + 子智能体过滤

两步流水线：
1. **第一步**：运行 `scripts/ocr_extract.py` 提取图像中的全部文字
2. **第二步**：将 OCR 结果交给子智能体，按用户需求过滤出目标信息

## 第一步 — OCR 提取

```bash
python <skill_dir>/scripts/ocr_extract.py <图像路径> [--lang en|ch|ch+en|fr|de|ja|ko]
```

| lang | 语言 | lang | 语言 |
|------|------|------|------|
| `en`（默认）| 英文 | `fr` | 法文 |
| `ch` | 纯中文 | `de` | 德文 |
| `ch+en` | 中英混合 | `ja` / `ko` | 日文 / 韩文 |

脚本会自动缩放超过 4000px 的图像，并将结果以 `{文字} | conf={置信度}` 格式输出到 stdout。

若 PaddleOCR 未安装，脚本会提示：`pip install paddleocr`。

退出码：`0` 成功，`2` 未识别出任何文字（此时降级至第二步直接用视觉子智能体）。

## 第二步 — 子智能体过滤

将 OCR 文字委托给子智能体处理（Claude Code 用 Agent tool，其他平台用对应委托机制）。子智能体只需文字，无需访问原始图像。

**goal 模板：**

```
以下是从图像中提取的原始 OCR 文字：

--- OCR RESULT START ---
{ocr_text}
--- OCR RESULT END ---

用户需求：<用户的自然语言描述>

请从上述 OCR 结果中，仅提取用户所要求的信息：
- 若用户要求特定字段（如"日期"、"总金额"），以 JSON 对象形式返回
- 若用户要求列出条目，返回结构化列表
- 只返回过滤后的结果，不要描述图像或做任何总结
```

## 常见问题

- **首次运行慢**：PaddleOCR 首次会下载推理模型（约 300MB），缓存在 `~/.paddlex/`
- **小字模糊**：小于约 10px 的文字准确率低，此时跳过第一步，直接用视觉子智能体处理原始图像
- **OCR 返回空**：退出码为 2，降级为直接对图像启动视觉子智能体
