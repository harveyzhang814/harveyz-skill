# autoresearch 系统分析报告

> **分析工具：** skill-analyzer v0.3
> **分析日期：** 2026-03-27
> **仓库路径：** ~/Repositories/autoresearch

---

## ⚠️ 前置声明：分析对象类型不匹配

**本报告面临根本性挑战：** `autoresearch` 是一个 **Python ML 研究项目**，而非 Skill 仓库。

skill-analyzer v0.3 的必检清单（如 VERSION 文件、SKILL.md、allowed-tools、.tmpl 模板系统、.agents/skills/、bin/、scripts/、extension/、supabase/ 等）大量条目**在本仓库中不存在**。

本报告采取以下策略：
- **如实报告**每个必检条目的实际存在状态
- **不适用的检查项**标注为 N/A（不适用）
- **幽灵文件**（.tmpl、SKILL.md 等本应存在但实际不存在的 skill 仓库文件）标注为 ⚠️ 幽灵文件
- 将洋葱模型**适配到 Python ML 项目的语境**中，而非强行套用 skill 框架

---

## 元信息

| 字段 | 值 | 备注 |
|------|-----|------|
| 仓库 VERSION 文件 | ⚠️ **不存在** | 无独立 VERSION 文件 |
| package.json version | ⚠️ **不存在** | 这是 Python 项目，无 package.json |
| pyproject.toml version | `0.1.0` | 来自 pyproject.toml |
| CHANGELOG.md | ⚠️ **不存在** | 无 CHANGELOG |
| SKILL.md frontmatter version | ⚠️ **不存在** | 整个仓库无任何 SKILL.md |
| 仓库类型 | Python ML 研究项目 | 不是 skill 仓库 |
| 分析框架适配 | 洋葱模型（Layer 1-4）已适配到 Python ML 语境 | 详见各 Layer 说明 |

---

## 0. 目录结构（实测）

```
~/Repositories/autoresearch/
├── .git/                      # Git 仓库
├── .gitignore                 # ⚠️ 幽灵文件（skill 仓库标配）
├── .python-version            # Python 版本约束（3.10+）
├── README.md                  # 主文档（92 行）
├── analysis.ipynb             # Jupyter 分析笔记本（可视化结果）
├── prepare.py                 # 数据准备脚本（389 行，固定不变）
├── program.md                 # Agent 指令文件（114 行，"轻量级 skill"）
├── progress.png               # 训练曲线图
├── pyproject.toml             # uv 依赖配置
├── train.py                   # 训练脚本（630 行，agent 可修改）
└── uv.lock                    # uv 锁文件
```

**实际文件计数（根目录）：**
```bash
$ ls ~/Repositories/autoresearch/ | wc -l
9
```

---

## 1. 定位与哲学（Layer 1 — 设计意图）

### 1.1 系统定位

**这是什么系统？**

autoresearch 是 Andrej Karpathy 的**自主 LLM 预训练实验框架**。核心思想：给 AI agent 一个真实的 LLM 训练环境，让它在固定 5 分钟时间预算内自主实验——修改代码、训练、检查 val_bpb（验证集 bits per byte）是否提升、保留或丢弃、周而复始。

**核心资产：**
- `train.py`（唯一可修改文件）—— GPT 模型、Muon+AdamW 优化器、训练循环
- `program.md`（Agent 指令）—— 实验流程的"轻量级 skill"

**非 skill 仓库典型资产（均不存在）：**
- SKILL.md、.tmpl、bin/、scripts/、.agents/skills/、extension/、supabase/、setup/

### 1.2 哲学文档

- **README.md** 引言：完整陈述了设计哲学——"meat computers → autonomous AI agent swarms"，有自述性的历史叙事
- **program.md**：作为 Agent 指令文档，承担了 skill 的角色，内含 Setup → Experimentation → Logging → Experiment Loop 的完整流程定义
- **ETHOS.md / DESIGN.md / ARCHITECTURE.md**：均不存在 ⚠️

### 1.3 设计原则（从源码提炼）

| 原则 | 描述 |
|------|------|
| **单一可变文件** | Agent 只修改 `train.py`，保持 diff 可审查 |
| **固定时间预算** | 5 分钟wall clock，不受硬件影响，保证实验可比性 |
| **单一评估指标** | val_bpb（越低越好，vocab-size-independent） |
| **自包含** | 无分布式、无复杂配置，一块 GPU、一个文件 |
| **静默失败** | agent 不得停下来问人，LOOP FOREVER |
| **Simplify first** | 删除代码达到同等效果优先于增加代码获得小幅提升 |

---

## 2. 目录结构（Layer 2 — 组件清单）

### 2.1 根目录配置文件

| 文件 | 存在 | 行数 | 备注 |
|------|------|------|------|
| VERSION | ⚠️ 不存在 | — | Python 项目无此文件 |
| package.json | ⚠️ 不存在 | — | 这是 Python 项目 |
| pyproject.toml | ✅ 存在 | 27 | uv 配置，version=0.1.0 |
| CHANGELOG.md | ⚠️ 不存在 | — | 无变更日志 |
| ETHOS.md | ⚠️ 不存在 | — | 无独立哲学文档 |
| ARCHITECTURE.md | ⚠️ 不存在 | — | 无架构文档 |
| DESIGN.md | ⚠️ 不存在 | — | 无设计文档 |
| BROWSER.md | ⚠️ 不存在 | — | 无浏览器相关内容 |
| TODOS.md | ⚠️ 不存在 | — | 无 TODO 清单 |
| CONTRIBUTING.md | ⚠️ 不存在 | — | 无贡献指南 |
| CLAUDE.md | ⚠️ 不存在 | — | Agent 提示文件（由 launcher 生成，.gitignore 中排除）|
| AGENTS.md | ⚠️ 不存在 | — | 同上 |
| .env.example | ⚠️ 不存在 | — | 无环境变量模板 |
| .gitignore | ✅ 存在 | — | 标准 Python gitignore |

### 2.2 Skill 目录

**本仓库无任何 SKILL.md 文件。** 以下为 skill 仓库的标配检查项，全部标注为 ⚠️ 幽灵文件：

| 检查项 | 状态 |
|--------|------|
| `.agents/skills/` | ⚠️ 不存在（幽灵文件） |
| `SKILL.md`（任意位置） | ⚠️ 不存在（幽灵文件） |
| `SKILL.md.tmpl` | ⚠️ 不存在（幽灵文件） |
| `gen-skill-docs.ts` | ⚠️ 不存在（幽灵文件） |
| `discover-skills.ts` | ⚠️ 不存在（幽灵文件） |

**替代组件：program.md（轻量级 skill）**

| 属性 | 值 |
|------|---|
| 文件名 | `program.md` |
| 行数 | 114 |
| 角色 | Agent 指令文档（等同于 skill 的 SKILL.md） |
| 内容覆盖 | Setup、Experimentation、Output Format、Logging、Experiment Loop |
| 版本字段 | 无（纯 Markdown，无 frontmatter） |

### 2.3 Agent 适配层

| 目录/文件 | 存在 | 备注 |
|-----------|------|------|
| `.agents/skills/` | ⚠️ 不存在 | skill 仓库标配，本仓库无 |
| `.agents/skills/skills/` | ⚠️ 不存在 | skill 仓库中间层，本仓库无 |

**实际替代：** README.md 和 program.md 直接面向 agent，无中间适配层。

### 2.4 模板文件

| 文件 | 存在 | 备注 |
|------|------|------|
| `SKILL.md.tmpl`（根） | ⚠️ 不存在 | skill 仓库模板，本仓库无 |
| `SKILL.md.tmpl`（browse） | ⚠️ 不存在 | 本仓库无 browse 子项目 |
| `gen-skill-docs.ts` | ⚠️ 不存在 | 自动生成流水线，本仓库无 |
| `discover-skills.ts` | ⚠️ 不存在 | skill 发现模块，本仓库无 |

**结论：** 本仓库不存在 .tmpl → SKILL.md 的自动生成流水线。

### 2.5 CLI 子项目

| 检查项 | 状态 | 备注 |
|--------|------|------|
| `browse/` 目录 | ⚠️ 不存在 | 本仓库无 browse CLI 子项目 |
| `browse/bin/` | ⚠️ 不存在 | 本仓库无独立 bin/ |
| `browse/src/` | ⚠️ 不存在 | 本仓库无 browse 子项目 |
| `browse/test/` | ⚠️ 不存在 | 本仓库无 browse 子项目 |

**实际可执行脚本：**
```bash
uv run prepare.py   # 数据准备
uv run train.py     # 训练实验
```

### 2.6 工具链

| 检查项 | 状态 | 备注 |
|--------|------|------|
| `bin/`（根目录） | ⚠️ 不存在 | skill 仓库工具链目录，本仓库无 |
| `scripts/` | ⚠️ 不存在 | skill 仓库脚本目录，本仓库无 |
| `scripts/resolvers/` | ⚠️ 不存在 | 本仓库无 resolvers |

### 2.7 外部依赖 / 支撑目录

| 检查项 | 状态 | 备注 |
|--------|------|------|
| `lib/` | ⚠️ 不存在 | 本仓库无共享库目录 |
| `supabase/` | ⚠️ 不存在 | 无数据库配置 |
| `setup/` | ⚠️ 不存在 | 无独立安装脚本 |
| `test/` | ⚠️ 不存在 | 无独立测试目录 |
| `extension/` | ⚠️ 不存在 | 无 Chrome 扩展 |
| `docs/` | ⚠️ 不存在 | 无文档子项目 |
| `.github/` | ⚠️ 不存在 | 无 GitHub CI/CD |

### 2.8 浏览器扩展 / 文档 / 基础设施

| 检查项 | 状态 |
|--------|------|
| `extension/` | ⚠️ 不存在 |
| `docs/` | ⚠️ 不存在 |
| `.github/workflows/` | ⚠️ 不存在 |
| `.github/docker/` | ⚠️ 不存在 |

---

## 3. 组件清单（Layer 2 — 详细）

### 3.1 program.md（轻量级 Skill 等效物）

**文件：** `~/Repositories/autoresearch/program.md`（114 行）

**功能：** Agent 实验指令手册

**触发条件：** 用户对 agent 说"have a look at program.md and let's kick off a new experiment"

**内容结构：**

```
1. Setup（6 步初始化流程）
   - 约定 run tag（日期格式）
   - 创建 git branch
   - 读取 in-scope 文件
   - 验证数据存在
   - 初始化 results.tsv
   - 确认并开始

2. Experimentation（5 分钟固定预算）
   - CAN: 修改 train.py（唯一可变文件）
   - CANNOT: 修改 prepare.py、安装新包、修改评估函数
   - 目标：最低 val_bpb
   - 软约束：VRAM 不应暴增
   - 简化原则：小幅提升 + 复杂度 = 不值得

3. Output format
   - val_bpb, training_seconds, total_seconds, peak_vram_mb, mfu_percent 等

4. Logging results
   - results.tsv（tab-separated，untracked by git）
   - 5 列：commit, val_bpb, memory_gb, status, description

5. Experiment loop
   - LOOP FOREVER: 改代码 → git commit → 训练 → 记录结果 → 判断 keep/discard
   - NEVER STOP（静默失败，不问人）
```

**allowed-tools 分析：** program.md 是 Markdown 文件，无 YAML frontmatter，无 allowed-tools 字段。这是 skill 仓库 SKILL.md 的本质差异——program.md 只是自然语言指令，不通过结构化字段限制工具权限。

### 3.2 train.py（可变核心组件）

**文件：** `~/Repositories/autoresearch/train.py`（630 行）

**角色：** Agent 唯一可修改的文件，包含完整的 GPT 模型和训练循环

**架构亮点：**

| 组件 | 技术细节 |
|------|---------|
| **模型架构** | GPT + Value Embeddings（ResFormer）+ Softcap |
| **Attention** | Flash Attention 3（Hopper）/ kernels-community（非Hopper）|
| **窗口模式** | 可配置 SSSL（Short/Long 交替） |
| **优化器** | MuonAdamW（2D 矩阵用 Muon，其他用 AdamW） |
| **Muon** | Polar Express 正交化 + NorMuon 方差缩减 + Cautious Weight Decay |
| **初始化** | init_weights() 方法，精细初始化策略 |
| **编译** | torch.compile(fullgraph=True) |
| **学习率调度** | Warmup（可选） + Warmdown（默认 50%）|
| **模型规模** | 由 DEPTH × ASPECT_RATIO 驱动，默认 ~50M 参数 |

**关键超参（train.py 内置，不可 CLI 覆盖）：**

| 超参 | 默认值 | 说明 |
|------|--------|------|
| ASPECT_RATIO | 64 | model_dim = depth × 64 |
| HEAD_DIM | 128 | Attention head 维度 |
| WINDOW_PATTERN | "SSSL" | 窗口模式 |
| TOTAL_BATCH_SIZE | 2^19 (~524K tokens) | 每步 token 数 |
| DEPTH | 8 | Transformer 层数 |
| DEVICE_BATCH_SIZE | 128 | 每设备 batch size |
| EMBEDDING_LR | 0.6 | Embedding 学习率 |
| MATRIX_LR | 0.04 | Muon 学习率 |
| WEIGHT_DECAY | 0.2 | 谨慎权重衰减 |

### 3.3 prepare.py（固定基础设施）

**文件：** `~/Repositories/autoresearch/prepare.py`（389 行）

**角色：** 一次性数据准备和运行时工具，**不可修改**

**关键组件：**

| 组件 | 功能 |
|------|------|
| `MAX_SEQ_LEN = 2048` | 上下文长度 |
| `TIME_BUDGET = 300` | 5 分钟训练预算 |
| `EVAL_TOKENS` | 验证 token 数 |
| `Tokenizer` | BPE 分词器（tiktoken + rustbpe） |
| `make_dataloader()` | 训练数据加载器 |
| `evaluate_bpb()` | 评估函数（ground truth 指标）|

**数据：** 从 HuggingFace 下载 6543 个 parquet shards，缓存到 `~/.cache/autoresearch/`

### 3.4 analysis.ipynb（Jupyter 分析笔记本）

**文件：** `~/Repositories/autoresearch/analysis.ipynb`

**角色：** 训练结果可视化（val_bpb 曲线等），非实验执行必需

### 3.5 pyproject.toml（依赖管理）

```toml
[project]
name = "autoresearch"
version = "0.1.0"
requires-python = ">=3.10"

dependencies = [
    "kernels>=0.11.7",      # Flash Attention 接口
    "matplotlib>=3.10.8",
    "numpy>=2.2.6",
    "pandas>=2.3.3",
    "pyarrow>=21.0.0",
    "requests>=2.32.0",
    "rustbpe>=0.1.0",
    "tiktoken>=0.11.0",
    "torch==2.9.1",
]
# torch 从 pytorch-cu128（CUDA 12.8）索引安装
```

---

## 4. 调用关系（Layer 3 — 交互关系）

### 4.1 自动触发关系（类型 1）

```
prepare.py → train.py
  - prepare.py 导出: MAX_SEQ_LEN, TIME_BUDGET, Tokenizer, make_dataloader, evaluate_bpb
  - train.py 导入以上全部符号
  - 关系: compile-time 依赖（import），prepare.py 不可修改

train.py → HuggingFace / kernels
  - 动态下载 flash-attention-3 内核
  - 运行时依赖（网络）
```

### 4.2 建议序列关系（类型 2）

```
用户 → program.md → train.py → results.tsv
  1. 用户提供 program.md 作为 agent 上下文
  2. Agent 读取 in-scope 文件（README.md, prepare.py, train.py）
  3. 验证数据（~/.cache/autoresearch/）
  4. 实验循环：修改 train.py → git commit → uv run train.py → 解析结果 → 记录 results.tsv
  5. 分析结果：analysis.ipynb（可选）
```

### 4.3 前置配置关系（类型 3）

| 前置条件 | 检查方式 | 失败处理 |
|---------|---------|---------|
| Python 3.10+ | `.python-version` | 报错 |
| NVIDIA GPU | `torch.cuda.is_available()` | 不可运行 |
| 数据已下载 | `~/.cache/autoresearch/` | 提示运行 `uv run prepare.py` |
| uv 已安装 | `which uv` | 提示安装 |
| 依赖已同步 | `uv sync` | 提示运行 |

### 4.4 闭环系统

```
┌─────────────────────────────────────────┐
│           EXPERIMENT LOOP (CLOSED)       │
│                                          │
│  1. READ train.py (current state)        │
│         ↓                                 │
│  2. MODIFY train.py (experimental idea)   │
│         ↓                                 │
│  3. GIT COMMIT                           │
│         ↓                                 │
│  4. uv run train.py (5 min budget)        │
│         ↓                                 │
│  5. PARSE run.log (val_bpb)              │
│         ↓                                 │
│  6. UPDATE results.tsv                   │
│         ↓                                 │
│  7. EVALUATE: improved?                   │
│         ↓              ↓                  │
│      KEEP         DISCARD                 │
│    (advance)    (git reset)               │
│         ↓              ↓                  │
│  8. LOOP FOREVER ←←←←←←←←←←←←←←←←←←←←   │
└─────────────────────────────────────────┘
```

---

## 5. 构建流水线

### 5.1 自动生成流水线

**⚠️ 不适用：** 本仓库不存在 .tmpl → SKILL.md → 的自动生成流水线。

skill 仓库的 `gen-skill-docs.ts` 在本仓库中等效为：
- `program.md`（手动维护的 Markdown 文档）
- 无版本控制、无结构化 frontmatter

### 5.2 CI 保障

**⚠️ 不存在：** 本仓库无 `.github/workflows/`、无 CI。

### 5.3 测试体系

**⚠️ 不存在独立测试目录：** `test/` 目录不存在。

**隐式测试机制：**
- 每次 `uv run train.py` 的成功/失败本身就是测试
- NaN loss 检查（`0be1e4f` commit 引入的 fast-fail）
- OOM 崩溃检测

### 5.4 gitignore 状态

| 忽略项 | 原因 |
|--------|------|
| `__pycache__/` | Python 运行时产物 |
| `*.py[oc]` | Python 字节码 |
| `build/`, `dist/`, `*.egg-info` | 打包产物 |
| `.venv` | 虚拟环境 |
| `worktrees/`, `queue/` | Git worktree 和实验队列 |
| `CLAUDE.md`, `AGENTS.md` | 每会话由 launcher 生成 |
| `dev/` | 实验性代码/产物 |
| `results.tsv` | 实验结果（不提交，留在本地）|

---

## 6. 使用场景（Layer 4 — 用户视角）

### 6.1 典型场景

| 场景 | 描述 | 步骤 |
|------|------|------|
| **新实验初始化** | 用户委托 agent 开始一轮新实验 | 1. 约定 run tag  2. 创建 branch  3. agent 读取 program.md  4. 验证数据  5. 初始化 results.tsv  6. 开始实验循环 |
| **单次训练验证** | 手动运行一次训练验证修改 | `uv run prepare.py`（如需要）→ `uv run train.py` → 查看 val_bpb |
| **结果可视化** | 分析实验历史 | `jupyter notebook analysis.ipynb` |

### 6.2 降级场景矩阵

| 降级场景 | 触发条件 | 处理方式 |
|---------|---------|---------|
| 数据不存在 | `~/.cache/autoresearch/` 为空 | 提示运行 `uv run prepare.py` |
| OOM | GPU 显存不足 | Agent 减小 DEVICE_BATCH_SIZE 或 DEPTH |
| NaN loss | 训练发散 | Agent 回退到上一个 git commit，记录 crash |
| 超时（>10min） | 训练未在预期时间完成 | Agent kill 进程，标记为 discard |
| 网络下载失败 | HuggingFace 连接问题 | prepare.py 有 retry 逻辑 |
| 非 NVIDIA GPU | 尝试在 Mac/AMD 运行 | 官方建议使用社区 fork |

### 6.3 平台适配矩阵

| 平台 | 状态 | 官方支持 |
|------|------|---------|
| NVIDIA H100 | ✅ 官方支持 | Flash Attention 3 (Hopper) |
| NVIDIA 非 H100 | ✅ 可运行 | kernels-community flash-attn3 |
| MacOS | ⚠️ 社区 fork | miolini/autoresearch-macos |
| MacOS MLX | ⚠️ 社区 fork | trevin-creator/autoresearch-mlx |
| Windows RTX | ⚠️ 社区 fork | jsegov/autoresearch-win-rtx |
| AMD ROCm | ⚠️ 社区 fork | andyluo7/autoresearch |

---

## 7. 版本信息（必检项）

| 来源 | 版本 | 备注 |
|------|------|------|
| `VERSION` 文件 | ⚠️ 不存在 | 无独立版本文件 |
| `package.json` | ⚠️ 不存在 | Python 项目 |
| `pyproject.toml` version | `0.1.0` | 唯一版本标识 |
| `SKILL.md` frontmatter | ⚠️ 不存在 | 无任何 SKILL.md |
| CHANGELOG 最新 | ⚠️ 不存在 | 无变更日志 |

---

## 8. 幽灵文件清单

以下为 skill-analyzer v0.3 必检清单中**skill 仓库应有但本仓库没有**的文件：

| 幽灵文件 | 类型 | skill 仓库中的用途 |
|---------|------|------------------|
| `VERSION` | 文件 | 显式版本声明 |
| `package.json` | 文件 | npm 包管理 |
| `SKILL.md` | 文件 | Skill 定义（核心） |
| `SKILL.md.tmpl` | 文件 | Skill 模板 |
| `gen-skill-docs.ts` | 文件 | 自动生成流水线 |
| `discover-skills.ts` | 文件 | Skill 发现模块 |
| `ETHOS.md` | 文件 | 设计哲学文档 |
| `ARCHITECTURE.md` | 文件 | 架构文档 |
| `DESIGN.md` | 文件 | 设计文档 |
| `BROWSER.md` | 文件 | 浏览器相关 |
| `CLAUDE.md` | 文件 | Agent 提示（由 launcher 动态生成，不在仓库内）|
| `AGENTS.md` | 文件 | Agent 提示（由 launcher 动态生成，不在仓库内）|
| `.env.example` | 文件 | 环境变量模板 |
| `CONTRIBUTING.md` | 文件 | 贡献指南 |
| `.github/workflows/` | 目录 | CI/CD |
| `bin/` | 目录 | CLI 工具 |
| `scripts/` | 目录 | 工具脚本 |
| `scripts/resolvers/` | 目录 | Resolver 脚本 |
| `lib/` | 目录 | 共享库 |
| `extension/` | 目录 | Chrome 扩展 |
| `supabase/` | 目录 | 数据库配置 |
| `docs/` | 目录 | 文档子项目 |
| `test/` | 目录 | 独立测试 |
| `.agents/skills/` | 目录 | Skill 适配层 |
| `browse/` | 目录 | CLI 子项目 |

---

## 附录

### A. 关键发现

1. **根本性类型错配：** skill-analyzer v0.3 的全部检查体系（SKILL.md、allowed-tools、.tmpl、bin/、scripts/、.agents/skills/、CI pipeline 等）均**完全不适用于** autoresearch 仓库。后者是一个纯 Python ML 项目。

2. **program.md 是本仓库唯一的 skill 等效物：** README.md 明言 "The `program.md` file is essentially a super lightweight 'skill'"。但它不包含 YAML frontmatter、无 allowed-tools、无结构化元数据。

3. **无版本控制体系：** pyproject.toml version=0.1.0 是唯一版本标识，无独立 VERSION 文件，无 CHANGELOG。考虑到这是活跃开发中的实验性项目（latest commit: `228791f Merge pull request #342`），版本管理较为粗放。

4. **社区 fork 生态健康：** 有 4 个官方认可的跨平台 fork（macOS × 2、Windows、AMD），说明项目影响力超出 NVIDIA 独占生态。

5. **极简主义设计：** 整个项目的复杂度上限极低——仅 3 个核心文件（train.py 630行 + prepare.py 389行 + program.md 114行），这是有意为之的设计决策，确保 agent 的操作空间边界清晰。

### B. 关于 skill-analyzer 框架的反思

skill-analyzer v0.3 的洋葱模型框架**在适配 Python ML 项目时有以下局限：**

| skill-analyzer 假设 | 实际情况 |
|--------------------|---------|
| Skill 是核心资产（SKILL.md 定义） | 核心资产是 Python 代码（train.py）|
| 有 allowed-tools 权限矩阵 | program.md 是自然语言，无结构化权限 |
| 有 .tmpl 自动生成系统 | 无模板系统 |
| 有 bin/、scripts/ 工具链 | 仅有 uv run 入口点 |
| 有 .agents/skills/ 适配层 | 无中间层，program.md 直连 agent |
| 有 CI/CD 保障 | 无 CI，全靠手动验证 |

**结论：** 如需对 autoresearch 进行系统性分析，建议采用"代码研究项目"专用框架，而非 skill 仓库框架。

---

*分析完成 | skill-analyzer v0.3 | 2026-03-27*
