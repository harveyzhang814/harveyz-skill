# 第2轮迭代实验记录

**日期：** 2026-03-27
**起点：** v0.3 Skill
**目标仓库：** autoresearch

---

## 迭代流程

| 阶段 | 执行者 | 运行时长 | Token 消耗 | 输出文件 |
|------|--------|---------|-----------|---------|
| 分析 Subagent | think=high | 4m45s | 192.0k | iteration-02-autoresearch-v0.3.md |
| 评估 Subagent | think=medium | 3m50s | 115.1k | iteration-02-evaluation-v0.3.md |
| 主 Agent 整合 | PM | — | — | v0.4 |

---

## 评估结果统计

| 维度 | 评级 | 说明 |
|------|------|------|
| 项目类型检测 | ❌ | **类别错误**：将 non-skill 项目误作 skill 仓库分析 |
| 幽灵文件清单 | ❌ | 全部 28 项标配文件被错误标记为幽灵文件 |
| train.py 关键实现 | ❌ | 遗漏 11+ 项（softcap、EMA、Muon调度、torch.compile等） |
| GPTConfig 描述 | ⚠️ | n_layer=12/n_head=6/n_embd=768 被描述为"内置超参"，实际被 build_model_config 覆盖 |
| 框架反思 | ✅ | 评估者正确识别了 skill-analyzer 的类别错误问题 |

---

## 主要问题（v0.3 → v0.4 改进）

### 1. 类别错误（最严重）

**问题：** skill-analyzer 假设所有仓库都是 skill 仓库，把 non-skill 项目（ML 训练项目）的标配文件缺失全部标记为"幽灵文件"。autoresearch 是 Python ML 项目（program.md + train.py + prepare.py），根本不是 skill 仓库。

**修复：** 
- 新增第一步：项目类型检测
- 非 skill 仓库缺失标配文件不是幽灵文件
- ML 项目需切换到 ML 分析框架

### 2. train.py 关键实现遗漏

**遗漏 11+ 项：**
- softcap 激活函数（`softcap * torch.tanh(logits/softcap)`）
- EMA 损失平滑
- 显式 GC 管理策略
- Fast-fail loss>100 检查
- Muon momentum 动态调度（0.85→0.95）
- WD 动态降为 0 调度
- grad_accum 微步骤循环
- `torch.compile(model)`
- UNEMBEDDING_LR=0.004、SCALAR_LR=0.5
- learnable scalar（resid_lambdas/x0_lambdas）

**修复：** ML 项目分析必须覆盖这些关键实现细节

---

## 版本演进

| 版本 | 主要变更 |
|------|---------|
| v0.1-baseline | 洋葱模型四层框架 |
| v0.2 | 必检清单、VERSION核实、数量核实、Ghost文件、CI保障 |
| v0.3 | allowed-tools强制验证、.tmpl精确化、bin/区分 |
| **v0.4** | **项目类型检测（禁忌14-15）、ML项目分析补充（禁忌16）** |

---

## 文件清单

```
skill-analyzer/
├── SKILL.md              # v0.4（当前）
├── CHANGELOG.md          # 版本记录
└── research/
    ├── analysis/
    │   ├── iteration-01-gstack-v0.2.md
    │   └── iteration-02-autoresearch-v0.3.md
    └── evaluation/
        ├── iteration-01-evaluation-v0.2.md
        └── iteration-02-evaluation-v0.3.md
```

---

## 下一步

进行**第3轮迭代**：
1. 用 **v0.4** Skill 对 **gstack** 再次进行分析（验证类型检测是否生效）
2. 评估 Subagent 评估报告
3. 主 Agent 整合反馈，生成 v0.5
