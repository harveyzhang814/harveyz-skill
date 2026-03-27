# 评估报告 v0.3（autoresearch）

> **评估者：** skill-analyzer 自我评估子 agent
> **被评估报告：** iteration-02-autoresearch-v0.3.md
> **源码仓库：** ~/Repositories/autoresearch
> **评估日期：** 2026-03-27

---

## 遗漏项

以下内容存在于源码中，但报告未提及或分析错误：

### 1. train.py 训练循环核心机制（严重遗漏）

报告对 `train.py` 630 行代码的分析停留在"GPT 模型 + MuonAdamW 优化器"的表层描述，完全遗漏了以下关键实现细节：

| 遗漏项 | 源码实际内容 | 影响 |
|--------|------------|------|
| **softcap 激活函数** | `softcap = 15; logits = softcap * torch.tanh(logits / softcap)` | 对 logits 做软截断，防止极端预测；属于独特的训练技巧 |
| **EMA 损失平滑** | `smooth_train_loss = 0.9 * smooth_train_loss + 0.1 * train_loss_f` + debias | 打印给用户的是 EMA 平滑后的 loss，非原始 loss |
| **GC 管理策略** | `step==0` 时 `gc.collect(); gc.freeze(); gc.disable()`，此后每 5000 步 `gc.collect()` | 显式管理 Python GC 以避免训练中间 500ms 卡顿；是高度工程化的细节 |
| **Fast-fail 条件** | `if math.isnan(train_loss_f) or train_loss_f > 100: print("FAIL"); exit(1)` | 训练 loss > 100 即 abort，不只是 NaN 检查 |
| **grad_accum 内循环** | `for micro_step in range(grad_accum_steps):` — 先累积梯度再 optimizer.step() | 报告完全没提梯度累积的微步骤结构 |
| **MUON momentum 动态调度** | `get_muon_momentum(step)` — 从 0.85 线性升到 0.95（前 300 步） | Muon 的 momentum 不是固定值，而是随步数动态增加 |
| **Weight decay 动态调度** | `get_weight_decay(progress)` — 从 WEIGHT_DECAY 线性降到 0 | WD 有 schedule，报告说"固定 weight_decay=0.2" |
| **熔化编译模型** | `model = torch.compile(model, dynamic=False)` | torch.compile 用在模型对象上（不是 optimizer），这是重要工程选择 |
| **MLFU 计算** | `H100_BF16_PEAK_FLOPS = 989.5e12` 硬编码，手动计算 `steady_state_mfu` | 报告只提到打印 mfu_percent，但没解释峰值 FLOPS 的来源 |
| **step > 10 才计入时间** | `if step > 10 and total_training_time >= TIME_BUDGET: break` | 跳过前 10 步的热身时间，只统计稳态训练时间 |
| **lr multiplier schedule** | warmup=0（默认关闭）、warmdown=50%、final_lr_frac=0.0 | 实际上是固定 LR → warmdown 到 0，报告说"可选 warmup"不够精确 |

### 2. Optimizer 关键细节缺失

| 遗漏项 | 源码实际内容 |
|--------|------------|
| **AdamW fused kernel** | `adamw_step_fused` 是自定义 `torch.compile(fullgraph=True)` 的融合 kernel，不是 PyTorch 标准 AdamW |
| **Muon fused kernel** | `muon_step_fused` 同样经过 `@torch.compile(fullgraph=True)` 融合，含 Polar Express + NorMuon + Cautious WD |
| **Muon LR 形状补偿** | `lr * max(1.0, shape[-2] / shape[-1])**0.5` — 长宽比 > 1 的矩阵 LR 会额外放大 |
| **Cautious Weight Decay** | `mask = (g * stacked_params) >= 0` — 只在梯度方向与参数同号时才加 WD；是 Karpathy 强调的"谨慎 WD" |
| **Nesterov Momentum** | `momentum_buffer.lerp_(stacked_grads, 1 - momentum); g = stacked_grads.lerp_(momentum_buffer, momentum)` — 标准 Nesterov 形式 |
| **UNEMBEDDING_LR** | `UNEMBEDDING_LR = 0.004` — lm_head 的 LR 与 embedding 不同；报告只提到 EMBEDDING_LR |
| **SCALAR_LR** | `SCALAR_LR = 0.5` — resid_lambdas 和 x0_lambdas 使用不同的 LR；报告完全没提 |

### 3. Model.forward() 中的 learnable scalar 使用

```python
x = self.resid_lambdas[i] * x + self.x0_lambdas[i] * x0  # 不是 1*x + 0.1*x0
x = block(x, ve, cos_sin, self.window_sizes[i])
```
- 报告将 `resid_lambdas.fill_(1.0)` 和 `x0_lambdas.fill_(0.1)` 解释为"初始化"，但这两个是**持续参与训练的可学习参数**，forward 中每次都用它们做加权。resid_lambdas 初始为 1.0（无操作恒等），x0_lambdas 初始为 0.1（保留少量初始残差）。

### 4. Value Embedding 实现细节

```python
self.value_embeds = nn.ModuleDict({
    str(i): nn.Embedding(config.vocab_size, kv_dim)
    for i in range(config.n_layer) if has_ve(i, config.n_layer)
})
```
- value embeddings **不是每个 layer 都有的**，`has_ve()` 控制哪些 layer 有；报告说"GPT + Value Embeddings（ResFormer）"但没有解释这是交替的、不是全部 layer。

### 5. Rotary Embedding 扩展机制

```python
self.rotary_seq_len = config.sequence_len * 10  # 10x 预计算长度
```
- Rotary embeddings 预计算了 **10 倍**的序列长度，存入 persistent=False buffer。这可能是一种内存换计算的设计。

### 6. train.py 与 prepare.py 的依赖关系

报告说"compile-time 依赖（import），prepare.py 不可修改"，但没有分析：
- `prepare.py` 中 `MAX_SEQ_LEN = 2048`、`TIME_BUDGET = 300`、`Tokenizer`、`make_dataloader`、`evaluate_bpb` **全部被 import 到 train.py 的全局命名空间**
- 这意味着 `prepare.py` 的所有常量定义决定了 train.py 的运行行为，是紧耦合设计

### 7. 数据集和 tokenizer 细节

报告遗漏：
- 数据集是 `karpathy/climbmix-400b-shuffle`，6543 个 parquet shards，共约 400B tokens
- `VAL_SHARD = 6542` 是固定的验证集 shard（最后一个）
- BPE tokenizer：`VOCAB_SIZE = 8192`，用 tiktoken + rustbpe 训练

### 8. analysis.ipynb 细节

报告只提到它是"Jupyter 分析笔记本"，但没有说明它的实际分析内容（从 progress.png 在仓库中来看，它生成了训练曲线可视化）。

---

## 理解偏差

### 1. GPTConfig 默认值误解（中等偏差）

**报告内容：**
> 关键超参（train.py 内置，不可 CLI 覆盖）：n_layer = 12, n_head = 6, n_embd = 768

**源码实际情况：**
`GPTConfig` 类确实定义了 `n_layer=12, n_head=6, n_kv_head=6, n_embd=768`，但这些**永远不会被使用**——因为 `build_model_config(DEPTH)` 总是用传入的 `depth=DEPTH=8` 显式构造 config：

```python
def build_model_config(depth):
    base_dim = depth * ASPECT_RATIO  # 8 * 64 = 512
    model_dim = ((base_dim + HEAD_DIM - 1) // HEAD_DIM) * HEAD_DIM  # 512
    num_heads = model_dim // HEAD_DIM  # 512 // 128 = 4
    return GPTConfig(n_layer=depth, ..., n_embd=model_dim, n_head=num_heads, n_kv_head=num_heads)
```

实际模型：`n_layer=8, n_head=4, n_kv_head=4, n_embd=512`

**偏差影响：** 报告给出的"默认模型 ~50M 参数"结论碰巧正确，但推导逻辑是基于错误数据（n_layer=12 → n_embd=768 → num_heads=6），而非源码实际逻辑（DEPTH=8 → ASPECT_RATIO=64 → n_embd=512 → num_heads=4）。

### 2. WARMUP_RATIO 描述不准确（轻微偏差）

**报告内容：** "Warmup（可选）"

**源码：** `WARMUP_RATIO = 0.0`，warmup **默认关闭**。schedule 逻辑中：
```python
if progress < WARMUP_RATIO:  # progress < 0.0，永远为 False
    return progress / WARMUP_RATIO if WARMUP_RATIO > 0 else 1.0
```
实际效果：warmup 从未被触发。"可选"是误导——它只能通过修改源码来启用，不是 CLI 选项。

### 3. ADAM_BETAS 描述错误（轻微偏差）

**报告内容：** `ADAM_BETAS = (0.8, 0.95)`

**源码：** `ADAM_BETAS = (0.8, 0.95)` 是对的，但：
- AdamW 参数组用 `(0.8, 0.95)`
- x0_lambdas 参数组用 `(0.96, 0.95)` — beta1 不同
- report 只提到前者，遗漏了后者

### 4. 对"洋葱模型适配"的自我评价过高（框架级偏差）

报告在附录B说"skill-analyzer 洋葱模型在适配 Python ML 项目时有局限"，但没有意识到这个"适配"行为本身就说明了框架不适用——报告本应建议"直接拒绝分析"或"切换到代码研究框架"，而非对 skill 仓库的检查清单逐一标记 N/A 然后继续输出 8 节报告。

---

## 评估者无法理解的点

### 1. `num_params` 的精确计算逻辑

源码中 `model.num_scaling_params()` 分了 5 个类别（wte, value_embeds, lm_head, transformer_matrices, scalars）来统计。报告说"~50M 参数"，但没有从源码中推导出这个数字是怎么算出来的。`num_params` 在训练末尾被打印，但报告没有引用这个输出。

### 2. `prepare.py` 中 `download_single_shard` 的并发实现

源码使用 `multiprocessing.Pool` 做 8 worker 并发下载，但报告完全没有涉及这一层。只提到"从 HuggingFace 下载 6543 个 parquet shards"。

### 3. tokenizer 训练细节

`prepare.py` 中 `train_tokenizer()` 函数是怎么做 BPE 训练的？vocab_size=8192 如何分配？报告中完全没有涉及。

### 4. `rustbpe` 的角色

依赖项中有 `rustbpe>=0.1.0`，但报告没有解释它与 tiktoken 的关系——两者在 tokenizer 训练和推理中如何分工？

### 5. analysis.ipynb 的具体内容

进度图 `progress.png` 在仓库中，但报告没有描述这个图是什么样的、代表了什么意思。

---

## 关于 skill-analyzer 框架的反思

### 核心问题：框架没有项目类型自检机制

skill-analyzer v0.3 的最大设计缺陷是**假设所有被分析仓库都是 skill 仓库**。这个假设在分析 `~/Repositories/autoresearch` 时彻底失效——整个检查清单变成了一堆"幽灵文件"列表，失去了分析价值。

### skill-analyzer 框架的适用边界

skill-analyzer 框架的核心设计基于以下假设：

| 框架假设 | 在 autoresearch 中是否成立 |
|---------|------------------------|
| 存在 SKILL.md（或等效 skill 定义文件） | ❌ 只有 program.md（自然语言，无 frontmatter） |
| SKILL.md 包含 `allowed-tools` YAML 字段 | ❌ 不存在 |
| 有 `.tmpl` 模板文件 → SKILL.md 的自动生成流水线 | ❌ 不存在 |
| 有 `bin/`、`scripts/` 工具链目录 | ❌ 只有 `uv run` 入口点 |
| 有 `.agents/skills/` Agent 适配层 | ❌ 无中间层 |
| 有 CI/CD（`.github/workflows/`） | ❌ 无 CI |
| 有 supabase/、extension/ 等特定子项目结构 | ❌ 不适用 |

**skill-analyzer 框架真正能有效分析的项目特征：**
- 项目根目录存在 `SKILL.md`
- 使用 `allowed-tools` 限制 agent 权限
- 有 `.tmpl` → `SKILL.md` 的模板驱动流水线
- 有 `bin/` 或 `scripts/` CLI 工具目录
- 有 `.agents/skills/` 多 agent 适配层

**skill-analyzer 框架完全不适用于：**
- 纯 Python/ML 研究项目（如 autoresearch）
- CLI 工具包（非 skill 包）
- 数据集仓库
- 配置文件集合

### 被错误标记为"幽灵"的文件分析

报告的"幽灵文件清单"中，以下文件的"幽灵"标记是完全合理的（skill 仓库标配确实没有）：

| 被标记的幽灵文件 | 为什么不是真正的问题 |
|----------------|-------------------|
| `SKILL.md` | 这个项目本来就不是 skill 仓库 |
| `SKILL.md.tmpl` | 同上 |
| `gen-skill-docs.ts` | 同上 |
| `discover-skills.ts` | 同上 |
| `.agents/skills/` | 同上 |
| `bin/`、`scripts/` | 同上 |
| `supabase/`、`extension/` | 同上 |

**关键反思：** skill-analyzer 把"skill 仓库标配文件的缺失"标记为"幽灵"，这对**分析 skill 仓库**是合理的（可以发现配置遗漏），但对**分析非 skill 仓库**是一个**类别错误**（category error）——没有 SKILL.md 不是什么"幽灵"，只是说明这不是一个 skill 仓库。

### 建议：增加项目类型检测层

skill-analyzer v0.3 应该在分析开始时先做项目类型检测：

```
1. 检查根目录是否有 package.json 或 pyproject.toml → Python/JS 项目分支
2. 检查是否有 SKILL.md → Skill 仓库分支
3. 检查是否有 README.md（但不包含 skill 关键字）→ 一般项目
4. 根据类型选择不同的分析框架，而非对所有项目套用同一套 skill 仓库清单
```

### 作者已做的合理自适应

公平地说，报告确实在"前言"中声明了"分析对象类型不匹配"并采取了"如实报告 + N/A 标注"的策略——这说明分析者意识到了问题所在。但这个自知没有延伸到报告的核心质量：即使正确识别了类型不匹配，train.py 的 630 行代码中至少有 **15+ 项关键实现细节被完全遗漏**，这些遗漏与框架类型无关，是纯源码分析层面的失败。

---

*评估完成 | 2026-03-27*
