---
name: extract-vision
description: "Use when the user shares an image (screenshot, photo, receipt, invoice, menu, or any picture containing text) and wants to extract specific information from it — such as prices, dates, names, totals, or any structured data. Trigger this skill whenever the user says things like 'find X in this image', 'extract the total from this receipt', 'pull out all the items from this menu', or shares an image file and asks for specific fields or values. Use even if the user doesn't mention OCR — if they share a picture and want data out of it, this skill applies."
version: 1.2.1
user_invocable: true
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [OCR, image, text-extraction, screenshots, vision, subagent]
    related_skills: [ocr-and-documents]
---

# 图像文字提取：PaddleOCR + 结构化过滤

两步流水线：
1. **第一步**：运行 `scripts/ocr_extract.py` 提取图像中的全部文字
2. **第二步**：按用户需求过滤 OCR 结果，产出目标信息

## 第一步 — OCR 提取

```bash
python <skill_dir>/scripts/ocr_extract.py <图像路径> [--lang ch|en|latin|korean|arabic|cyrillic]
```

| lang | 适用语言 |
|------|----------|
| `ch`（默认）| 中文 / 中英混排 |
| `en` | 纯英文（速度更快） |
| `latin` | 法、德、西、葡等拉丁语系 |
| `korean` | 韩文 |
| `arabic` | 阿拉伯文 |
| `cyrillic` | 俄文等西里尔字母 |

脚本会自动缩放超过 4000px 的图像，并将结果以 `{文字} | conf={置信度}` 格式输出到 stdout。

若 PaddleOCR 未安装，脚本会提示：`pip install paddleocr paddlepaddle`。

退出码：`0` 成功，`2` 未识别出任何文字。保留该退出码和依赖提示；OCR 为空时按下方原图视觉能力分支处理，不可据此断言图像没有内容。

## 第二步 — OCR 结果过滤

先检查当前会话是否有可用且适合处理该文本的委派能力。有则把 OCR 文字交给子智能体，使用下列同一 goal 模板；无委派能力时，由当前 agent 顺序处理 OCR 文本，严格使用同一字段或列表规则。执行者变化不得改变结果形状或遗漏用户要求；两条路径都只需要 OCR 文字，无需访问原始图像。

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

## OCR 为空或原图小字模糊

OCR 返回空、或小字模糊导致文本不可靠时，检查当前 agent 或可用委派目标能否查看原图。能查看则直接进行视觉提取；无原图视觉能力则停止，并向用户报告“当前会话无法可靠读取原图，不能判断图片是否含目标文字”。不得把 OCR 空结果说成图片没有内容。

## 常见问题

- **首次运行慢**：PaddleOCR 首次会下载推理模型（约 300MB），缓存在 `~/.paddlex/`
- **小字模糊**：小于约 10px 的文字准确率低，按上方能力检查决定视觉提取或安全停止
- **OCR 返回空**：退出码为 2，按上方能力检查决定视觉提取或安全停止
