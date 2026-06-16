---
name: read-paper
version: "0.1.0"
description: "三遍精读单篇学术论文 PDF。第一遍：5C 结构化定向；第二遍：全文内容提取；第三遍：批判性重构。每遍产出独立 Markdown 文件，存放在以论文命名的文件夹中。触发场景：用户想精读一篇论文、分析论文质量、生成论文笔记。"
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

用户回复后，用 Bash 工具写入配置：

```bash
mkdir -p ~/.hskill/read-paper
echo '{"output_dir": "用户指定路径"}' > ~/.hskill/read-paper/config.json
```

若文件已存在，解析 JSON 取出 `output_dir` 字段直接使用。

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
slug=$(echo "$filename" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9一-鿿]/-/g' | sed 's/-\+/-/g' | sed 's/^-\|-$//g')
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

再读最后 3 页找结论（若第一次未找到结论章节，向前扩展继续读）：

```
Read(file_path="<pdf_path>", pages="X-Y")
```

其中 X-Y 从论文末尾往前推，直到读到含"Conclusion"/"结论"的页面。常见论文 8-15 页，先尝试 `pages="10-15"`，不含结论则改 `pages="7-12"`。

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
