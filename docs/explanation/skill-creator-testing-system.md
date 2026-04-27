# skill-creator 测试体系详解

## 概览

skill-creator 内置了一套完整的 skill 测试体系，核心思路是：把 LLM 行为当作可测试的软件——写测试用例、跑对照实验、量化评估、迭代改进。它不是一个测试框架的薄封装，而是一套专门为 LLM skill 设计的评估方法论。

---

## 设计哲学

### 1. 对照实验而非绝对判断

skill-creator 不问"skill 的输出好不好"，而是问"有 skill 比没有 skill 好多少"。每个测试用例都会同时运行两个 agent：

- **with_skill**：读取 skill，按照 skill 的指引执行任务
- **without_skill（或 old_skill）**：不使用 skill（或使用旧版本），直接靠 LLM 的默认行为

这种对照设计消除了"任务本身难度"对结果的干扰——同一个任务，两个 agent 的差异就来自 skill 本身的贡献。

### 2. 人机协同评估

纯自动评分擅长检查文件是否存在、内容是否包含某些字段，但无法判断"这份总结写得好不好""逻辑是否清晰"。skill-creator 的解决方案是：

- **自动断言**：覆盖可客观验证的行为（文件路径、状态字段、章节标题）
- **人工 review**：通过 eval viewer 让人类查看实际输出，留下质性反馈

两者互补，自动化断言给出量化分数，人工反馈捕捉 LLM 的主观质量问题。

### 3. 快速迭代循环

测试不是终点，而是改进的起点。整个体系被设计成一个可反复执行的循环：

```
写 skill → 跑测试 → 看结果 → 改 skill → 跑测试 → ...
```

每次迭代的结果保存在独立的 `iteration-N/` 目录，viewer 支持与上一轮对比，让改进效果一目了然。

### 4. 尽早让人类介入

框架明确要求：**先生成 eval viewer 让人类看，再自己分析和修改**。这避免了"AI 自己改、自己评、自己满意"的闭环——人类视角才是最终标准。

---

## 目录结构

```
skill-name/
└── SKILL.md

skill-name-workspace/
├── evals/
│   └── evals.json              # 测试用例定义
└── iteration-1/
    ├── eval-<name>/
    │   ├── eval_metadata.json  # 断言定义
    │   ├── with_skill/
    │   │   ├── run-1/
    │   │   │   ├── grading.json   # 评分结果
    │   │   │   └── timing.json    # 耗时/token 数据
    │   │   └── outputs/           # agent 产出文件
    │   └── without_skill/
    │       └── run-1/
    │           ├── grading.json
    │           └── timing.json
    ├── benchmark.json          # 聚合统计
    └── benchmark.md            # 可读报告
```

workspace 与 skill 目录并列放置，不混入 skill 本身的代码。

---

## 核心机制

### evals.json：测试用例

测试用例的格式极简——只需描述"给什么输入、期望什么输出"：

```json
{
  "skill_name": "my-skill",
  "evals": [
    {
      "id": 1,
      "name": "descriptive-name",
      "prompt": "用户实际会输入的内容",
      "expected_output": "对期望行为的自然语言描述",
      "files": []
    }
  ]
}
```

`prompt` 应该是真实用户会说的话，不是抽象描述。`expected_output` 是给人类看的，不是机器判断的依据——机器判断依靠断言（assertions）。

### eval_metadata.json：断言

断言是测试体系的核心量化机制，每个 eval 有一个对应的 `eval_metadata.json`：

```json
{
  "eval_id": 1,
  "eval_name": "descriptive-name",
  "prompt": "...",
  "assertions": [
    {
      "id": "unique-id",
      "text": "断言的自然语言描述（会显示在 viewer 里）",
      "check": "检查方式描述"
    }
  ]
}
```

好的断言具备两个特征：
1. **客观可验证**：能通过读文件、检查字段来判断通过/失败
2. **描述性强**：`text` 字段应该让人一眼看懂在检查什么，而不是写 `assertion_3`

### grading.json：评分结果

grader agent 读取断言和实际输出，产出评分文件：

```json
{
  "eval_id": 1,
  "eval_name": "...",
  "expectations": [
    {
      "text": "断言描述",
      "passed": true,
      "evidence": "grader 观察到的具体证据"
    }
  ],
  "summary": {
    "pass_rate": 1.0,
    "passed": 7,
    "failed": 0,
    "total": 7
  }
}
```

注意字段名：`text`/`passed`/`evidence`，而非 `name`/`met`/`details`——eval viewer 依赖这些精确的字段名渲染界面。

### timing.json：性能数据

每个 run 目录下还有一个 timing 文件，记录资源消耗：

```json
{
  "total_tokens": 20388,
  "duration_ms": 58471,
  "total_duration_seconds": 58.5
}
```

这份数据**只能从 agent 完成通知中捕获**，任务完成后不再持久化。如果错过了通知就丢失了，所以必须在收到每个 agent 完成通知时立即保存。

### aggregate_benchmark.py：聚合统计

所有 grading.json 写好后，运行聚合脚本：

```bash
python3 -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
```

脚本遍历所有 `eval-*/with_skill/run-*/grading.json` 和 `eval-*/without_skill/run-*/grading.json`，计算：

- 每个 config 的 pass_rate 均值 ± 标准差
- with_skill vs without_skill 的 delta
- 耗时和 token 对比

产出 `benchmark.json`（机器读）和 `benchmark.md`（人类读）。

---

## 工作流程

### 第一轮完整流程

```
1. 写 evals.json（测试用例）
2. 准备前置状态（如需要预建文件）
3. 同一轮次启动所有 with_skill + without_skill agent（并行）
4. agent 跑的同时：写 eval_metadata.json 断言
5. 收到 agent 完成通知时：立即保存 timing.json
6. 所有 agent 完成后：运行 grader agent
7. 运行 aggregate_benchmark.py
8. 启动 eval viewer
9. 人类在 viewer 里看输出、留反馈
10. 读取 feedback.json，分析改进方向
11. 修改 skill，进入下一轮迭代
```

关键约束：**with_skill 和 without_skill 必须在同一轮次同时启动**，不能先跑完 with_skill 再跑 without_skill，否则环境状态可能变化，对照实验失去意义。

### Eval Viewer 的两个视角

**Outputs 标签**：逐个查看每个测试用例的实际输出。可以看到：
- 给定的 prompt
- with_skill 的产出
- without_skill（或上轮）的产出（折叠对比）
- 自动断言的通过/失败明细
- 反馈输入框（支持自动保存）

**Benchmark 标签**：汇总统计视图。显示每个配置的 pass_rate、耗时、token 用量，以及逐 eval 的分项数据。

用完点"Submit All Reviews"，feedback 下载为 `feedback.json`。

---

## 量化指标的局限与补充

### 哪些场景适合自动断言

- 产出是文件：检查文件是否存在、内容是否包含特定字段
- 产出有固定结构：frontmatter 字段、章节标题、状态值
- 有明确的禁止行为：某个文件不应该被创建

### 哪些场景不适合

- 写作质量、语言流畅度
- 推理过程是否合理
- 是否问了"正确"的澄清问题（只能看有没有问，不能评估问得好不好）

这些场景依赖人工 review，自动断言给不了有意义的分数。强行打分只会制造虚假的量化感。

### 非区分性断言

有些断言 with_skill 和 without_skill 都能通过——比如"停止执行时没有创建文件"，LLM 默认行为也会这样做。这类断言不能衡量 skill 的贡献，但仍有价值：它们确保 skill 没有引入副作用。

---

## Description Optimization（触发优化）

测试体系还包含一个独立的子系统：优化 skill 的 `description` 字段，让 Claude 在该触发的时候触发 skill。

流程：
1. 生成 20 条 eval query（10 条应触发、10 条不应触发）
2. 人类在 HTML 界面审核并编辑
3. 运行 `scripts/run_loop.py` 自动优化描述（最多 5 轮迭代）
4. 脚本对每条 query 运行 3 次取平均触发率，避免随机性干扰
5. 用 held-out test set 选最优描述，防止过拟合到训练集

这个优化与行为测试独立进行，通常在 skill 功能已经稳定后再做。

---

## 实践建议

**测试用例设计**
- 覆盖正常路径、边界条件、错误处理各至少一个
- prompt 要真实，不要写"测试 skill 是否能处理模糊输入"这种抽象描述
- 断言要细，一个断言只检查一件事，方便定位失败原因

**迭代策略**
- 第一轮跑完后，先看 without_skill 哪里失败——失败的地方才是 skill 真正能提供价值的场景
- 如果 with_skill 和 without_skill 都失败，说明任务本身有问题，不是 skill 的问题
- 如果两者都通过，说明这个断言检查的行为是 LLM 默认就会做的，考虑换一个更有区分度的断言

**避免的错误**
- 不要在所有 agent 完成前就开始改 skill——改了之后重跑才有意义
- 不要自己分析完就直接改，先让人类看 viewer
- 不要跳过 timing.json 的保存——性能数据在通知里只出现一次
