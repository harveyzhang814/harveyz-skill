# extract-url 完成回报格式 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 extract-url 完成后向用户展示结构化回报卡片，包含统计脚本 + SKILL.md 批量流程更新。

**Architecture:** 新增 `count_article_stats.py` 脚本，由主 agent 在 Subagent 2 完成后调用，统计译文的字符数、代码块数、图片数；SKILL.md 步骤 4 已在设计阶段写入，批量流程新增对步骤 4 的显式引用和最终汇总行。

**Tech Stack:** Python 3，pytest，标准库（re、pathlib、sys）

## Global Constraints

- 脚本接受 CLI 参数（article path），不读 config.json，不依赖 env var
- 输出格式严格为三行：`CHARS: N` / `CODE_BLOCKS: N` / `IMAGES: N`
- 字符统计跳过 frontmatter（`---` 到第二个 `---\n` 之间的内容）
- 代码块：统计 body 中 ` ``` ` 开头行的数量除以 2（成对计数）
- 图片：统计 `![` 出现次数
- 测试放到 `skills/research/extract-url/tests/test_count_article_stats.py`，遵循已有 conftest fixture 风格（subprocess 调用脚本）

---

### Task 1: 创建 count_article_stats.py + 测试

**Files:**
- Create: `skills/research/extract-url/scripts/count_article_stats.py`
- Create: `skills/research/extract-url/tests/test_count_article_stats.py`

**Interfaces:**
- Produces: CLI `python3 count_article_stats.py <article_path>` → stdout 三行（供 Task 2 的 SKILL.md 引用）

- [ ] **Step 1: 写失败测试**

新建 `skills/research/extract-url/tests/test_count_article_stats.py`：

```python
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'
SCRIPT = str(SCRIPTS_DIR / 'count_article_stats.py')

_ARTICLE = """\
---
title: Test Article
description: Test description.
---

Body text here.

\`\`\`python
print("hello")
\`\`\`

\`\`\`bash
echo "world"
\`\`\`

![img1](Image/img1.png)
![img2](Image/img2.png)
"""


def _parse(stdout: str) -> dict:
    result = {}
    for line in stdout.strip().splitlines():
        k, v = line.split(':', 1)
        result[k.strip()] = int(v.strip())
    return result


def test_counts_code_and_images(tmp_path):
    f = tmp_path / 'article.md'
    f.write_text(_ARTICLE, encoding='utf-8')
    r = subprocess.run(['python3', SCRIPT, str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = _parse(r.stdout)
    assert d['CODE_BLOCKS'] == 2
    assert d['IMAGES'] == 2


def test_chars_exclude_frontmatter(tmp_path):
    f = tmp_path / 'article.md'
    f.write_text(_ARTICLE, encoding='utf-8')
    r = subprocess.run(['python3', SCRIPT, str(f)], capture_output=True, text=True)
    d = _parse(r.stdout)
    body_start = _ARTICLE.index('---\n', 4) + 4
    assert d['CHARS'] == len(_ARTICLE[body_start:])


def test_no_code_no_images(tmp_path):
    f = tmp_path / 'plain.md'
    f.write_text('---\ntitle: X\n---\n\nJust plain text.\n', encoding='utf-8')
    r = subprocess.run(['python3', SCRIPT, str(f)], capture_output=True, text=True)
    d = _parse(r.stdout)
    assert d['CODE_BLOCKS'] == 0
    assert d['IMAGES'] == 0


def test_missing_file_exits_nonzero(tmp_path):
    r = subprocess.run(['python3', SCRIPT, str(tmp_path / 'missing.md')],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert 'not found' in r.stderr


def test_no_frontmatter(tmp_path):
    body = 'Just text, no frontmatter.\n'
    f = tmp_path / 'nofm.md'
    f.write_text(body, encoding='utf-8')
    r = subprocess.run(['python3', SCRIPT, str(f)], capture_output=True, text=True)
    assert r.returncode == 0
    d = _parse(r.stdout)
    assert d['CHARS'] == len(body)
```

- [ ] **Step 2: 运行测试，确认全部失败**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -m pytest skills/research/extract-url/tests/test_count_article_stats.py -v
```

预期：全部 FAILED，`count_article_stats.py` 不存在。

- [ ] **Step 3: 实现 count_article_stats.py**

新建 `skills/research/extract-url/scripts/count_article_stats.py`：

```python
#!/usr/bin/env python3
"""
Count article stats for the completion report card.
Usage: python3 count_article_stats.py <article_path>
Output:
  CHARS: N
  CODE_BLOCKS: N
  IMAGES: N
"""
import sys, re
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: count_article_stats.py <article_path>", file=sys.stderr)
    sys.exit(1)

article_path = Path(sys.argv[1])
if not article_path.exists():
    print(f"ERROR: file not found: {article_path}", file=sys.stderr)
    sys.exit(1)

text = article_path.read_text(encoding='utf-8')

body = text
fm_match = re.match(r'^---\n.*?\n---\n', text, re.DOTALL)
if fm_match:
    body = text[fm_match.end():]

chars = len(body)
code_blocks = len(re.findall(r'^```', body, re.MULTILINE)) // 2
images = len(re.findall(r'!\[', body))

print(f"CHARS: {chars}")
print(f"CODE_BLOCKS: {code_blocks}")
print(f"IMAGES: {images}")
```

- [ ] **Step 4: 运行测试，确认全部通过**

```bash
python3 -m pytest skills/research/extract-url/tests/test_count_article_stats.py -v
```

预期：5 passed。

- [ ] **Step 5: Commit**

```bash
git add skills/research/extract-url/scripts/count_article_stats.py \
        skills/research/extract-url/tests/test_count_article_stats.py
git commit -m "feat(extract-url): add count_article_stats.py for completion report"
```

---

### Task 2: 更新 SKILL.md 批量流程，引用步骤 4 + 汇总行

**Files:**
- Modify: `skills/research/extract-url/SKILL.md`（批量流程 `每篇 Subagent 2 完成后...` 段落）

**Interfaces:**
- Consumes: `count_article_stats.py`（Task 1 产出）

- [ ] **Step 1: 定位要修改的段落**

在 `SKILL.md` 找到以下文本（批量流程中）：

```
每篇 Subagent 2 完成后，**在主 session 中随机等待**再发下一篇：
```

- [ ] **Step 2: 替换为引用步骤 4 + 汇总行**

将该段落替换为：

```markdown
每篇 Subagent 2 完成后，执行**步骤 4**（运行统计脚本、读取 description、输出完成卡片），再**随机等待**后发下一篇：
```

在 `time.sleep(wait)` 代码块之后、`---` 分隔线之前，插入：

```markdown
所有篇完成后输出汇总行：

```
共 N 篇 | 完成 X  失败 Y  跳过 Z
```

（主 session 自行统计每篇的最终状态，将 N / X / Y / Z 替换为实际数字）
```

- [ ] **Step 3: 核对 SKILL.md 批量流程段落格式正确**

在编辑器中阅读批量流程节，确认：
1. "步骤 2" 末尾有对步骤 4 的引用
2. sleep 代码块之后有汇总行示例

- [ ] **Step 4: Commit**

```bash
git add skills/research/extract-url/SKILL.md
git commit -m "feat(extract-url): 批量流程引用步骤 4 回报 + 汇总行"
```

---

## Self-Review

**Spec coverage:**
- ✅ `count_article_stats.py` 脚本：Task 1
- ✅ 主 agent 运行脚本（SKILL.md 步骤 4）：已在设计阶段写入
- ✅ 批量每篇完成即时报告 + 汇总行：Task 2
- ✅ 通用卡片规范写入 knowledge：已在设计阶段完成
- ✅ 四种状态卡片（完成/失败/部分完成/已跳过）：已在设计阶段写入步骤 4

**Placeholder scan:** 无 TBD / TODO / 未完成项。

**Type consistency:** 脚本 CLI 接口（`python3 count_article_stats.py <path>`）与 SKILL.md 步骤 4 中的调用方式一致。
