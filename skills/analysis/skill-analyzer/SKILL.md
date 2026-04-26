# SKILL.md — skill-analyzer

> **版本：** v0.9
> **版本日期：** 2026-03-28
> **基于：** v0.8 + 第7轮评估反馈
> **定位：** 对 Skill 仓库进行系统性分析的工具 Skill

---

## 触发条件

当用户提供以下任意表述时触发本 Skill：
- "分析这个 skill 仓库"
- "对这个 skill 仓库做系统性研究"
- "输出 skill 仓库的分析报告"
- "理解这个 skill 系统的设计意图"

---

## ⚠️ 第一步：项目类型检测

1. 检查是否存在 `SKILL.md` 或 `SKILL.md.tmpl` → 有则继续
2. 检查是否存在 `program.md` 或 ML 关键词 → 非 skill 仓库
3. 项目类型分类：Skill 仓库 / ML项目 / CLI工具 / 未知

---

## 分析框架：洋葱模型（四层）

```
┌─────────────────────────────────────────┐
│  Layer 4：使用场景（用户视角）              │
├─────────────────────────────────────────┤
│  Layer 3：交互关系（系统视角）              │
├─────────────────────────────────────────┤
│  Layer 2：组件目录（结构视角）              │
├─────────────────────────────────────────┤
│  Layer 1：设计意图（哲学视角）              │
└─────────────────────────────────────────┘
```

---

## ⚠️ 必检清单

### 版本信息
- [ ] VERSION 文件内容
- [ ] package.json version
- [ ] CHANGELOG 最新版本
- [ ] 版本根因分析

### 文件数量（必须实际计数）
```bash
ls ~/Repositories/gstack/bin/ | wc -l          # bin/ 文件数
ls ~/Repositories/gstack/browse/bin/ | wc -l   # browse/bin/ 文件数
ls ~/Repositories/gstack/browse/test/*.test.ts | wc -l  # browse/test/ .test.ts 数
ls ~/Repositories/gstack/scripts/ | wc -l      # scripts/ 文件数
ls ~/Repositories/gstack/scripts/resolvers/ | wc -l  # scripts/resolvers/ 文件数
```

**正确数量（必须全部记住）：**
- **bin/ = 17**（不是20！）
- **browse/bin/ = 2**（find-browse, remote-slug）
- **bin/ + browse/bin/ 合计 = 19**
- **browse/test/ = 18**（.test.ts 文件，不是11！）
- **scripts/resolvers/ = 10**（含 index.ts）

### 目录覆盖
- [ ] 所有目录均列出实际文件清单

### 独立 .tmpl 数量
- [ ] 29 个（已验证）

---

## ⚠️ allowed-tools（最关键！）

### 含 WebSearch 的 Skill（12个，不是16个！）

**正确列表（12个）：**
autoplan, cso, design-consultation, design-review, investigate, office-hours, plan-ceo-review, plan-eng-review, qa, qa-only, review, ship

**不含 WebSearch 的 Skill（不要误列）：**
- benchmark ❌（无 WebSearch）
- canary ❌（无 WebSearch）
- document-release ❌（无 WebSearch）
- setup-deploy ❌（无 WebSearch，只有 Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion）

### 正确工具数参考

| Skill | 正确工具数 | 注意事项 |
|-------|-----------|---------|
| browse | 3 | Bash, Read, AskUserQuestion |
| qa | 8 | 含 WebSearch，无 Agent |
| review | 9 | 含 Agent 和 WebSearch |
| ship | 9 | 含 Agent 和 WebSearch |
| cso | 8 | 含 Agent 和 WebSearch |
| office-hours | 8 | 含 WebSearch |
| setup-browser-cookies | 3 | Bash, Read, AskUserQuestion |
| **unfreeze** | **2** | Bash, Read |
| setup-deploy | 7 | 无 WebSearch |
| benchmark | — | 无 WebSearch |
| canary | — | 无 WebSearch |
| document-release | — | 无 WebSearch |

### v0.1.0 skill（5个）
careful, connect-chrome, freeze, guard, unfreeze

### 含 Agent 的 skill（3个）
cso, review, ship

---

## Layer 1-4

按照洋葱模型框架执行。

---

## 输出格式

```markdown
# {仓库名} 系统分析报告

## 元信息
- 分析版本：
- 项目类型：
- VERSION / package.json / CHANGELOG：
- 版本根因分析：

## 1-6. 各层分析
...

## 附录
### 幽灵文件列表（如有）
### allowed-tools 完整读取记录
（每个 skill：工具数 + 具体工具名称）
```

---

## 禁忌（共 23 条）

1-22 条沿用 v0.8（略）

**23. ❌ WebSearch 数量必须为 12 个（不是16！）。benchmark/canary/document-release/setup-deploy 均不含 WebSearch。browse/test/ = 18（不是11）。bin/ + browse/bin/ = 19（不是20）。**  ← 新增

---

*skill-analyzer v0.9 | 2026-03-28*
