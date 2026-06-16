---
name: learn-paper
version: "0.1.0"
description: "Deep-read a single academic PDF in three passes: 5C structural orientation, full content extraction, and critical reconstruction. Each pass produces a standalone Markdown file. Triggers: 'read this paper', 'deep-read paper', 'analyze this paper', 'take notes on this PDF', 'summarize paper', or when user provides a PDF path and wants to understand its content."
user_invocable: true
---

# read-paper

三遍精读单篇 PDF 论文。每遍独立产出一个 Markdown 文件。

底层方法论说明见 `docs/superpowers/specs/2026-06-16-read-paper-design.md`。

---

## 路径变量

```
ConfigPath: ~/.hskill/read-paper/config.json
```

---

## 执行流程

### Step 0：初始化配置

用 Read 工具读取 `~/.hskill/read-paper/config.json`。

若文件不存在，询问用户：

```
论文分析笔记保存到哪个目录？（直接回车使用默认：~/Documents/papers）
```

用户回复后，用 Bash 工具写入配置（路径必须用 `$HOME` 展开，不可写字面量 `~`）：

```bash
mkdir -p "$HOME/.hskill/read-paper"
output_dir="${用户指定路径/#\~/$HOME}"
echo "{\"output_dir\": \"$output_dir\"}" > "$HOME/.hskill/read-paper/config.json"
```

若文件已存在，解析 JSON 取出 `output_dir` 字段，并将其中可能残留的 `~` 展开为 `$HOME` 后使用：

```bash
output_dir=$(python3 -c "import json,os; d=json.load(open('$HOME/.hskill/read-paper/config.json')); print(d['output_dir'].replace('~', os.environ['HOME'], 1))")
```

---

### Step 1：提取 PDF 路径，准备输出目录

从用户消息中提取 PDF 文件路径（绝对路径或 `~` 开头路径均可）。

**安全净化（在 Bash 中执行）：**

```bash
pdf_path=$(echo "<用户提供路径>" | tr -d '\000-\037\177' | xargs)
pdf_path="${pdf_path/#\~/$HOME}"
```

**验证文件存在：**

```bash
test -f "$pdf_path" || { echo "ERROR: 文件不存在: $pdf_path"; exit 1; }
```

若不存在，报错并终止。

**生成 paper slug：**

取 PDF 文件名（去掉扩展名），将空格和特殊字符替换为 `-`，转小写。汉字保留原样：

```bash
filename=$(basename "$pdf_path" .pdf)
slug=$(echo "$filename" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9一-鿿]/-/g' | sed -E 's/-+/-/g' | sed 's/^-//;s/-$//')
```

示例：`Attention Is All You Need.pdf` → `attention-is-all-you-need`

**创建输出目录：**

```bash
mkdir -p "<output_dir>/$slug"
```

**解析 `--pass` 参数（若用户在触发消息中指定）：**

| 参数 | 行为 |
|------|------|
| `--pass 1` | 只执行第一遍 |
| `--pass 2` | 只执行第二遍，需检查 `1-orientation.md` 已存在 |
| `--pass 3` | 只执行第三遍，需检查 `2-extraction.md` 已存在 |
| 无参数 | 执行全部三遍 |

**依赖检查（单遍模式）：**

```bash
# --pass 2
test -f "<output_dir>/$slug/1-orientation.md" || { echo "请先运行 --pass 1 生成前置文件"; exit 1; }

# --pass 3
test -f "<output_dir>/$slug/2-extraction.md" || { echo "请先运行 --pass 2 生成前置文件"; exit 1; }
```

---

### Step 2：第一遍 — 5C 定向

**读取范围：**

先读前 5 页获取标题、摘要、引言：

```
Read(file_path="<pdf_path>", pages="1-5")
```

再从论文末尾向前搜索结论章节（最多尝试 3 次，每次窗口 4 页）：

**策略：** 先读最后 4 页，若未见"Conclusion"/"结论"/"Discussion"关键词，则继续向前读前 4 页，如此最多 3 次。

```
# 第 1 次：读最后 4 页
Read(file_path="<pdf_path>", pages="<total-3>-<total>")

# 若未找到，第 2 次：再往前 4 页
Read(file_path="<pdf_path>", pages="<total-7>-<total-4>")

# 若仍未找到，第 3 次：再往前 4 页
Read(file_path="<pdf_path>", pages="<total-11>-<total-8>")
```

`<total>` 通过读第 1 页时 PDF 工具返回的总页数判断，或从前 5 页内容中的页码推断。找到结论即停，不继续往前读。

**分析任务：**

基于读取内容完成 5C 评估：

| 维度 | 分析问题 |
|------|----------|
| **Category（类别）** | 测量类 / 系统描述 / 理论分析 / 综述 / 其他？ |
| **Context（背景）** | 解决什么问题？与哪些已知工作相关？ |
| **Correctness（正确性）** | 核心假设是否明确合理？有无明显漏洞？ |
| **Contributions（贡献）** | 主要创新点是什么？ |
| **Clarity（清晰度）** | 结构是否清晰？摘要是否准确概括内容？ |

**产出文件，用 Write 工具写入 `<output_dir>/<slug>/1-orientation.md`：**

```markdown
# {论文标题} — 定向

**作者**: {从首页提取}
**年份**: {从首页提取}
**来源**: {期刊/会议/arXiv，从首页提取}
**PDF**: <pdf_path>
**分析日期**: YYYY-MM-DD

---

## 5C 评估

- **Category（类别）**: 
- **Context（背景）**: 
- **Correctness（正确性）**: 
- **Contributions（贡献）**: 
- **Clarity（清晰度）**: 

---

## 初步印象

（2-3 句话：论文整体质量判断，是否值得继续第二遍精读）
```

写完后告知用户：`✓ 第一遍完成 → <output_dir>/<slug>/1-orientation.md`

---

### Step 3：第二遍 — 全文内容提取

**读取策略（分段处理，每次最多 10 页）：**

```
Read(file_path="<pdf_path>", pages="1-10")
Read(file_path="<pdf_path>", pages="11-20")
...循环直到读完全文
```

每段读取后立即提取，不等全文读完再汇总（避免 context 溢出）。

**终止条件：** 每段读取后检查是否出现 References / Bibliography / 参考文献 的独立章节标题（通常单独成行、后面紧跟编号列表）。一旦检测到，立即停止继续读取后续页面——References 之后已无需提取的正文内容。

**每段提取内容：**

- **核心论点**：该段提出的主要主张（用自己的语言转述，非直接引用）
- **实验与数据**：数据集名称、评估指标、关键数值、与基线的对比结果
- **方法步骤**：算法/架构/流程的关键步骤描述
- **图表**：图/表编号 + 标题 + 核心结论（图像内容用 vision 解读）
- **引用标记**：反复出现或支撑核心论点的参考文献编号

**产出文件，用 Write 工具写入 `<output_dir>/<slug>/2-extraction.md`：**

```markdown
# {论文标题} — 内容提取

**作者**: {从首页提取}
**PDF**: <pdf_path>
**分析日期**: YYYY-MM-DD

---

## 核心论点与证据

（每条论点附支撑来源：实验数据 / 理论推导 / 引用）

## 实验设计与结果

- **数据集**: 
- **评估指标**: 
- **关键数值**: 
- **与基线对比**: 

## 方法论摘要

（核心方法的步骤/架构/算法，用自己的语言重述，不直接抄论文）

## 图表解读

| 图/表 | 标题 | 核心结论 |
|-------|------|----------|
| Fig.1 | ... | ... |

## 作者承认的局限

（作者在 Limitation / Future Work 章节明确说明的不足，非推断）

## 值得追踪的关键引用

（反复出现或支撑核心论点的参考文献，记编号和推测主题）
```

写完后告知用户：`✓ 第二遍完成 → <output_dir>/<slug>/2-extraction.md`

---

### Step 4：第三遍 — 批判性重构

**读取来源（不重读 PDF）：**

```
Read(file_path="<output_dir>/<slug>/2-extraction.md")
```

**分析任务（针对 2-extraction.md 中每条核心论点）：**

1. **假设审计**：该论点依赖哪些隐含假设？论文是否明确说明了这些假设？
2. **缺陷识别**：
   - 实验是否缺少重要对照组？
   - 结论是否超出实验结果可支撑的范围？
   - 评估指标是否存在选择偏差？
3. **对比已知工作**：与训练知识中的相关方法相比，声称的创新点是否成立？有无遗漏的重要基线对比？
4. **延伸方向**：若要改进或扩展，最有价值的研究方向是什么？

**诚实性标注规则（每条批判意见必须标注）：**

- `[基于论文]` — 直接来自论文内容，可直接引用
- `[Agent推断]` — 基于训练知识的判断，可能存在时效性或准确性问题
- `[需核实]` — 需要查阅外部文献才能确认，不可直接引用

**产出文件，用 Write 工具写入 `<output_dir>/<slug>/3-critique.md`：**

```markdown
# {论文标题} — 批判性重构

**作者**: {从 2-extraction.md 复制}
**PDF**: <pdf_path>
**分析日期**: YYYY-MM-DD

> **注意：** 标注 `[Agent推断]` 的内容基于训练知识，非论文原文，存在时效性限制，请独立核实后引用。

---

## 隐含假设清单

（每条注明：论文是否明确说明 → 是/否）

## 已识别缺陷

（每条附来源标注：[基于论文] / [Agent推断] / [需核实]）

## 与已知工作对比

（[Agent推断] 标注，对比训练知识中的相关方法）

## 开放问题 / 延伸方向

（值得未来研究的方向，[基于论文] 或 [Agent推断] 标注）
```

写完后总结：

```
✓ 三遍分析完成

  <output_dir>/<slug>/
  ├── 1-orientation.md   ← 5C 定向
  ├── 2-extraction.md    ← 内容提取
  └── 3-critique.md      ← 批判性重构
```
