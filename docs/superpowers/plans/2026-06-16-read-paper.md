# read-paper Skill 实施计划

**目标：** 实现 `skills/experiment/read-paper/` — Agent 三遍精读单篇 PDF 论文，每遍产出独立 Markdown 文件

**架构：** 纯 Agent skill，无外部脚本。Agent 用 Read 工具直接读取 PDF，按三遍结构执行分析，输出写入 `{output_dir}/{paper-slug}/`。配置持久化到 `~/.hskill/read-paper/config.json`。

**工作区：** `.worktrees/experiment` 分支 `chore/experiment`

**技术栈：** SKILL.md（Agent 指令）、JSON 配置、Markdown 输出

**参考规格：** `docs/superpowers/specs/2026-06-16-read-paper-design.md`

---

### Task 1：搭建目录结构 + 注册 skill

**文件：**
- 创建: `skills/experiment/read-paper/SKILL.md`（空骨架）
- 修改: `skills-index.json`（添加 experiment/read-paper 条目）

- [ ] **Step 1：创建目录和空 SKILL.md**

在 `.worktrees/experiment` 中执行：

```bash
mkdir -p skills/experiment/read-paper
cat > skills/experiment/read-paper/SKILL.md << 'EOF'
---
name: read-paper
version: "0.1.0"
description: "placeholder"
user_invocable: true
---
EOF
```

- [ ] **Step 2：在 skills-index.json 添加条目**

找到 `"experiment/probe-chrome-session"` 条目，在其后添加：

```json
{ "path": "experiment/read-paper", "bundle": "experiment" }
```

- [ ] **Step 3：验证格式合法**

在主 repo 目录执行：

```bash
npm test 2>&1 | grep -E "read-paper|PASS|FAIL"
```

预期：read-paper 出现在输出中且无 FAIL

- [ ] **Step 4：提交**

```bash
git add skills/experiment/read-paper/SKILL.md skills-index.json
git commit -m "feat(read-paper): scaffold skill directory and register in skills-index"
```

---

### Task 2：SKILL.md 主体 — frontmatter + Step 0 配置初始化

**文件：**
- 修改: `skills/experiment/read-paper/SKILL.md`

- [ ] **Step 1：写入 frontmatter 和配置初始化流程**

完整替换 `SKILL.md` 内容为：

````markdown
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

读取 `~/.hskill/read-paper/config.json`。

若文件不存在：

```
询问用户：论文分析笔记保存到哪个目录？（默认：~/Documents/papers）
```

用户回复后写入配置：

```json
{
  "output_dir": "<用户指定路径>"
}
```

写入命令（在 Bash 工具中执行）：

```bash
mkdir -p ~/.hskill/read-paper
echo '{"output_dir": "<用户路径>"}' > ~/.hskill/read-paper/config.json
```

若文件已存在，直接读取 `output_dir`。
````

- [ ] **Step 2：手动确认**

检查 `SKILL.md` 中 frontmatter 字段完整（name/version/description/user_invocable），Step 0 流程无歧义。

- [ ] **Step 3：提交**

```bash
git add skills/experiment/read-paper/SKILL.md
git commit -m "feat(read-paper): add frontmatter and Step 0 config init"
```

---

### Task 3：Step 1 — 从用户消息提取 PDF 路径

**文件：**
- 修改: `skills/experiment/read-paper/SKILL.md`（追加 Step 1）

- [ ] **Step 1：追加 Step 1 内容**

在 Step 0 之后追加：

````markdown
### Step 1：提取 PDF 路径，准备输出目录

从用户消息中提取 PDF 文件路径（绝对路径或 `~` 开头路径均接受）。

**安全净化：**

```python
import re, os
pdf_path = re.sub(r'[\x00-\x1f\x7f]', '', pdf_path).strip()
pdf_path = os.path.expanduser(pdf_path)
```

**验证文件存在：**

```bash
test -f "<pdf_path>" || echo "ERROR: 文件不存在"
```

若文件不存在，报错并终止。

**生成 paper slug：**

取 PDF 文件名（去掉扩展名），将空格和特殊字符替换为 `-`，转小写：

```python
import re
slug = re.sub(r'[^a-z0-9一-鿿]+', '-', filename.lower()).strip('-')
```

示例：`Attention Is All You Need.pdf` → `attention-is-all-you-need`

**创建输出目录：**

```bash
mkdir -p "<output_dir>/<slug>"
```

**解析 `--pass` 参数（若用户指定）：**

- `--pass 1` → 只跑第一遍
- `--pass 2` → 只跑第二遍（需检查 `1-orientation.md` 是否存在，不存在则提示）
- `--pass 3` → 只跑第三遍（需检查 `2-extraction.md` 是否存在，不存在则提示）
- 无参数 → 跑全部三遍（`all`）

**依赖检查（单遍模式）：**

| 指定遍次 | 依赖文件 |
|----------|----------|
| `--pass 2` | `{output_dir}/{slug}/1-orientation.md` |
| `--pass 3` | `{output_dir}/{slug}/2-extraction.md` |

若依赖文件不存在，提示：「请先运行 `--pass N` 生成前置文件。」并终止。
````

- [ ] **Step 2：检查 slug 生成规则是否处理中文论文标题**

中文标题中的汉字应保留（`一-鿿` 范围已包含），非汉字非字母数字替换为 `-`。

- [ ] **Step 3：提交**

```bash
git add skills/experiment/read-paper/SKILL.md
git commit -m "feat(read-paper): add Step 1 PDF path extraction and output dir setup"
```

---

### Task 4：Step 2 — 第一遍（5C 定向）

**文件：**
- 修改: `skills/experiment/read-paper/SKILL.md`（追加 Step 2）

- [ ] **Step 1：追加 Step 2 内容**

````markdown
### Step 2：第一遍 — 5C 定向

**读取范围：**

```
页码 1-5（标题、摘要、引言）
最后 2 页（结论）
若存在目录页（"Contents" / "目录"），读取该页
```

用 Read 工具读取：

```
Read(file_path="<pdf_path>", limit=5)
Read(file_path="<pdf_path>", offset=<total_pages-2>)
```

**分析任务：**

基于读取内容，完成以下 5C 评估：

| 维度 | 问题 |
|------|------|
| **Category（类别）** | 这是什么类型的论文？（测量/系统描述/理论分析/综述/其他） |
| **Context（背景）** | 它与哪些工作相关？依赖什么理论基础？ |
| **Correctness（正确性）** | 核心假设是否合理？有无明显前提问题？ |
| **Contributions（贡献）** | 主要创新点是什么？解决了什么问题？ |
| **Clarity（清晰度）** | 表达是否清晰？结构是否合理？ |

**产出文件 `1-orientation.md`：**

```markdown
# {论文标题} — 定向

**作者**: ...
**年份**: ...
**来源**: ...（期刊/会议/arXiv，从首页提取）
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

（2-3 句话：整体质量判断，是否值得进入第二遍精读）
```

**写入文件：**

用 Write 工具写入 `{output_dir}/{slug}/1-orientation.md`。

写完后告知用户：「✓ 第一遍完成 → `{output_dir}/{slug}/1-orientation.md`」
````

- [ ] **Step 2：检查歧义**

`Read` 工具的 `offset` 参数是行号，不是页码。对于 PDF，Read 工具的 `pages` 参数用于指定页码范围（如 `pages: "1-5"`）。确认 Step 2 中使用正确参数。

修正：

```
Read(file_path="<pdf_path>", pages="1-5")
Read(file_path="<pdf_path>", pages="<last-2>-<last>")
```

但总页数在读取前未知。解决方案：先读 `pages="1-5"`，从首页内容推断总页数（通常 PDF 在首页或末页标注页码）；或直接读 `pages="1-5"` 和 `pages="40-45"`（假设常见论文长度，实际内容中若结论不在该范围则顺延）。

在 SKILL.md 中写明：「若读取的末尾页不含结论，向前扩展 5 页继续读取，直到找到结论章节。」

- [ ] **Step 3：提交**

```bash
git add skills/experiment/read-paper/SKILL.md
git commit -m "feat(read-paper): add Step 2 Pass 1 orientation with 5C analysis"
```

---

### Task 5：Step 3 — 第二遍（内容提取）

**文件：**
- 修改: `skills/experiment/read-paper/SKILL.md`（追加 Step 3）

- [ ] **Step 1：追加 Step 3 内容**

````markdown
### Step 3：第二遍 — 全文内容提取

**读取策略（分段处理长论文）：**

每次读取 10 页，逐段提取，最后合并：

```
Read(file_path="<pdf_path>", pages="1-10")   → 提取本段内容
Read(file_path="<pdf_path>", pages="11-20")  → 提取本段内容
...（循环直到读完）
```

每段提取时，识别并记录：
- **核心论点**：该段提出的主要主张
- **实验/数据**：实验设置、数据集、评估指标、关键数值结果
- **方法步骤**：算法/流程/架构的关键步骤
- **图表**：图/表的编号、标题、核心结论（若为图像，用 vision 解读）
- **引用标记**：文中提及的关键参考文献（记编号，留作后续追踪）

**产出文件 `2-extraction.md`：**

```markdown
# {论文标题} — 内容提取

**作者**: ...
**PDF**: <pdf_path>
**分析日期**: YYYY-MM-DD

---

## 核心论点与证据

（列出所有主要论点，每条附支撑证据来源：实验数据/理论推导/引用）

## 实验设计与结果

- **数据集**: 
- **评估指标**: 
- **关键数值**: 
- **与基线对比**: 

## 方法论摘要

（核心方法的步骤/架构/算法，用自己的语言重述）

## 图表解读

| 图/表 | 标题 | 核心结论 |
|-------|------|----------|
| Fig.1 | ... | ... |

## 作者承认的局限

（作者在 limitation/future work 章节明确承认的不足）

## 值得追踪的关键引用

（反复出现或支撑核心论点的参考文献，记录编号和推测内容）
```

**写入文件：**

用 Write 工具写入 `{output_dir}/{slug}/2-extraction.md`。

写完后告知用户：「✓ 第二遍完成 → `{output_dir}/{slug}/2-extraction.md`」
````

- [ ] **Step 2：提交**

```bash
git add skills/experiment/read-paper/SKILL.md
git commit -m "feat(read-paper): add Step 3 Pass 2 full content extraction"
```

---

### Task 6：Step 4 — 第三遍（批判性重构）

**文件：**
- 修改: `skills/experiment/read-paper/SKILL.md`（追加 Step 4）

- [ ] **Step 1：追加 Step 4 内容**

````markdown
### Step 4：第三遍 — 批判性重构

**读取来源：**

只读 `{output_dir}/{slug}/2-extraction.md`，不重读 PDF。

```
Read(file_path="{output_dir}/{slug}/2-extraction.md")
```

**分析任务（针对每条核心论点）：**

1. **假设审计**：该论点依赖哪些隐含假设？这些假设在论文中是否被明确说明？
2. **缺陷识别**：
   - 实验设计是否有遗漏的对照组？
   - 结论是否超出实验结果所能支撑的范围？
   - 评估指标是否存在偏差？
3. **对比已知工作**：与训练知识中的相关工作相比，该方法的新颖性是否属实？有无遗漏的重要对比基线？
4. **开放问题**：若要延伸或改进这项工作，最有价值的方向是什么？

**诚实性标注（重要）：**

在 `3-critique.md` 的每条批判意见后，标注其来源：

- `[基于论文]` — 论文自身数据支持
- `[Agent推断]` — 基于训练知识的推断，可能存在错误
- `[需核实]` — 需要查阅外部文献才能确认

**产出文件 `3-critique.md`：**

```markdown
# {论文标题} — 批判性重构

**作者**: ...
**PDF**: <pdf_path>
**分析日期**: YYYY-MM-DD
**注：** 标注 [Agent推断] 的内容基于训练知识，非论文原文，请独立核实。

---

## 隐含假设清单

（每条假设注明是否在论文中被明确说明）

## 已识别缺陷

（每条附来源标注）

## 与已知工作对比

（基于训练知识的对比，标注 [Agent推断]）

## 开放问题 / 延伸方向

（值得未来研究的方向）
```

**写入文件：**

用 Write 工具写入 `{output_dir}/{slug}/3-critique.md`。

写完后总结：

```
✓ 三遍分析完成

  {output_dir}/{slug}/
  ├── 1-orientation.md   ← 5C 定向
  ├── 2-extraction.md    ← 内容提取
  └── 3-critique.md      ← 批判性重构
```
````

- [ ] **Step 2：提交**

```bash
git add skills/experiment/read-paper/SKILL.md
git commit -m "feat(read-paper): add Step 4 Pass 3 critical reconstruction"
```

---

### Task 7：安装验证

**目标：** 在真实 PDF 上跑一遍，确认三遍输出结构正确

- [ ] **Step 1：安装 skill 到本地**

```bash
cp -r skills/experiment/read-paper ~/.claude/skills/
```

- [ ] **Step 2：运行 npm test 确认格式合法**

```bash
npm test 2>&1 | grep -E "read-paper|error|FAIL"
```

预期：无 FAIL，read-paper 格式校验通过

- [ ] **Step 3：找一篇本地 PDF，触发 skill**

用一篇已有的本地论文 PDF 测试全流程：

```
/read-paper ~/path/to/any-paper.pdf
```

验证：
- 询问输出目录（首次运行）或直接读取配置（非首次）
- 创建 `{output_dir}/{slug}/` 目录
- 三个文件依次生成
- `3-critique.md` 中含 `[Agent推断]` 诚实性标注

- [ ] **Step 4：提交最终版本**

```bash
git add skills/experiment/read-paper/SKILL.md
git commit -m "feat(read-paper): complete skill v0.1.0 ready for experiment"
```

---

## 自检

### 规格覆盖

| 规格要求 | 对应 Task |
|----------|-----------|
| 三遍结构，每遍独立分析镜头 | Task 4/5/6 |
| 输出目录可配置，存 `~/.hskill/` | Task 2 |
| `--pass` 参数 + 依赖检查 | Task 3 |
| PDF 分段读取（每次最多 20 页）| Task 5 |
| 第三遍只读 extraction，不读 PDF | Task 6 |
| 诚实性来源标注 | Task 6 |
| 每遍产出独立 Markdown 文件 | Task 4/5/6 |
| paper slug 生成 | Task 3 |

### 占位符扫描

无 TBD / TODO / 后续实现。

### 类型一致性

`output_dir`、`slug`、`pdf_path` 在所有 Task 中保持一致命名。`Read` 工具使用 `pages` 参数（字符串格式如 `"1-5"`）。
