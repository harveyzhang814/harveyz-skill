---
migrated: 2026-06-21
docs:
  - explanation/how-to-read-papers.md  # Agent 版三遍阅读法适配原理（附录节）
implemented_in:
  - skills/experiment/learn-paper/SKILL.md  # 实现时命名为 learn-paper
---

# read-paper Skill 设计文档

**日期**: 2026-06-16  
**Bundle**: experiment  
**路径**: `skills/experiment/read-paper/`

---

## 概述

`read-paper` 是一个供 Agent 精读单篇学术论文的 skill。输入本地 PDF 文件，输出三层结构化分析报告，每层一个 Markdown 文件，存放在以论文命名的文件夹中。

---

## 方法论：Agent 版三遍阅读法

原始 Keshav 三遍法的本质是**认知资源分配**——人类工作记忆有限，需要渐进建立理解。Agent 无此约束，三遍改为三个**独立分析任务**，目的是产出质量而非节省认知资源。

| 遍次 | 人类目的 | Agent 目的 |
|------|----------|------------|
| 第一遍 | 判断是否值得读 | 建立论文坐标系（5C 结构化定向）|
| 第二遍 | 把握内容，跳过细节 | 全文提取：论点、证据、方法、图表 |
| 第三遍 | 批判性重构（脑内复现）| 假设审计 + 缺陷识别 + 对比已知工作 |

关键设计决策：
- Agent 每遍读取范围不同，但**用不同分析镜头**，不是同一内容反复读
- 第三遍"脑内复现"变为**显式质疑清单**，因为 Agent 没有"脑内"，必须说出来
- 第三遍基于第二遍产出文件推理，不重读 PDF，避免 context 超限
- 图表逐张解读，需要 vision 能力（Read 工具支持 PDF 图像）

---

## 输入

```
/read-paper ~/path/to/paper.pdf [--pass 1|2|3|all]
```

- **输入**: 本地 PDF 文件路径
- **`--pass`**: 指定运行哪一遍，默认 `all`（全部三遍）
- 若指定单遍且依赖前遍（如 `--pass 3` 需要 `2-extraction.md`），检查依赖文件是否存在；不存在则提示先跑前置遍

---

## 输出结构

```
{output_dir}/{paper-slug}/
├── 1-orientation.md    ← 第一遍：5C 定向
├── 2-extraction.md     ← 第二遍：内容提取
└── 3-critique.md       ← 第三遍：批判性重构
```

每个文件顶部带论文元数据（标题、作者、来源、PDF 路径、分析日期），内容独立完整。

### 1-orientation.md 结构

```markdown
# {论文标题} — 定向

**作者**: ...
**年份**: ...
**来源**: arXiv / 期刊 / 会议
**PDF**: ~/path/to/paper.pdf
**分析日期**: YYYY-MM-DD

## 5C 评估

- **Category（类别）**: 测量 / 系统描述 / 理论分析 / ...
- **Context（背景）**: 与哪些工作相关，依赖什么理论基础
- **Correctness（正确性）**: 假设是否合理，有无明显前提问题
- **Contributions（贡献）**: 核心创新点是什么
- **Clarity（清晰度）**: 表达是否清晰，结构是否合理
```

### 2-extraction.md 结构

```markdown
# {论文标题} — 内容提取

（元数据）

## 核心论点与证据
## 实验设计与结果
## 方法论摘要
## 图表解读（逐图）
## 作者承认的局限
## 值得追踪的关键引用
```

### 3-critique.md 结构

```markdown
# {论文标题} — 批判性重构

（元数据）

## 隐含假设清单
## 已识别缺陷
## 与已知工作对比
## 开放问题 / 延伸方向
```

---

## 配置

输出目录存在 `~/.hskill/read-paper/config.json`：

```json
{
  "output_dir": "~/Documents/papers"
}
```

- 首次运行若无配置，询问用户目录并写入
- 后续直接读取，无需每次指定

---

## PDF 读取策略

Claude 的 Read 工具支持直接读取 PDF，每次最多 20 页。长论文按遍次拆分：

| 遍次 | 读取范围 |
|------|----------|
| 第一遍 | 前 5 页（标题/摘要/引言）+ 最后 2 页（结论）+ 目录页（若有）|
| 第二遍 | 分段读取全文，每段提取后合并 |
| 第三遍 | 读取 `2-extraction.md`，不重读 PDF |

---

## 执行流程

```
步骤 0：初始化
  → 读取 ~/.hskill/read-paper/config.json
  → 若不存在：询问输出目录，写入配置
  → 从 PDF 路径生成 slug，创建 {output_dir}/{slug}/

步骤 1：第一遍（orientation）
  → 读取 PDF 关键页
  → 产出 1-orientation.md

步骤 2：第二遍（extraction）
  → 分段读取全文，逐段提取合并
  → 产出 2-extraction.md

步骤 3：第三遍（critique）
  → 读取 2-extraction.md
  → 批判性推理
  → 产出 3-critique.md
```

---

## 依赖关系

- Read 工具（PDF 读取，含图像 vision）
- 无外部脚本依赖（纯 Agent 推理任务）

---

## 不在范围内

- URL 输入（另见 screen-papers 或 extract-url）
- 批量处理多篇论文（另见 screen-papers skill）
- 论文对比、文献综述生成
