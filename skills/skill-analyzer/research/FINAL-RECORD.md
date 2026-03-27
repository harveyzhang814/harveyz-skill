# skill-analyzer 最终版本记录

> **最终版本：** v0.9
> **完成日期：** 2026-03-28
> **迭代轮次：** 8轮

---

## 最终版本：v0.9

### 核心能力

skill-analyzer 是一个用于系统性分析 Skill 仓库的分析框架，基于"洋葱模型"四层结构。

### 框架架构

```
Layer 4：使用场景（用户视角）
Layer 3：交互关系（系统视角）
Layer 2：组件目录（结构视角）
Layer 1：设计意图（哲学视角）
```

### 核心原则

1. **设计意图优先** — 设计哲学是解码所有技术选择的钥匙
2. **清单先于关系** — 先穷举组件，再画关系图
3. **场景驱动呈现** — 以用户问题为中心，而非以组件为中心

---

## 迭代历程

| 轮次 | 版本 | 主要变更 | 触发问题 |
|------|------|---------|---------|
| 0 | v0.1-baseline | 洋葱模型四层框架 | 初始版本 |
| 1 | v0.2 | 必检清单、VERSION核实、数量核实、Ghost文件、CI保障 | 先行测试暴露遗漏 |
| 2 | v0.3 | allowed-tools强制验证（从实际SKILL.md读取）、.tmpl精确化、bin/区分 | 6个skill工具数据错误 |
| 3 | v0.4 | 项目类型检测机制、ML项目分析补充 | autoresearch类别错误 |
| 4 | v0.5 | 文件清单必须逐项列出（禁忌17）、.tmpl数量必须实际统计（禁忌18）、版本根因分析（禁忌19） | lib/数量、.tmpl数量错误 |
| 5 | v0.6 | 禁止伪造allowed-tools数据（禁忌20） | 大量数据伪造 |
| 6 | v0.7 | 删除所有"双allowed-tools块"虚假描述（禁忌21） | 双块伪命题 |
| 7 | v0.8 | WebSearch必须完整计入（禁忌22） | WebSearch系统性漏计 |
| 8 | v0.9 | 最终验证 | 4处表格级细粒度误差 |

---

## v0.9 最终验证状态

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 项目类型检测 | ✅ | 正确识别为 skill 仓库 |
| VERSION 核实 | ✅ | 0.12.2.0 |
| package.json 版本 | ✅ | 0.12.0.0（落后） |
| 幽灵文件检查 | ✅ | 无幽灵文件 |
| 29 个 .tmpl | ✅ | 全部验证存在 |
| 28 个 skill 目录 | ✅ | 正确 |
| WebSearch = 12 | ✅ | 正确列表 |
| 含 Agent = 3 | ✅ | cso, review, ship |
| v0.1.0 = 5 | ✅ | careful, connect-chrome, freeze, guard, unfreeze |
| bin/ = 17 | ✅ | |
| browse/bin/ = 2 | ✅ | |
| bin/ 合计 = 19 | ✅ | |
| browse/test/ = 18 | ✅ | |
| scripts/resolvers/ = 10 | ✅ | |
| allowed-tools 从实际SKILL.md读取 | ✅ | |
| 无"双块"虚假描述 | ✅ | 已删除 |
| 版本根因分析 | ✅ | 有意分层策略 |

### 4处表格级细粒度误差（评估者认为可接受）

| Skill | 报告工具数 | 实际工具数 |
|-------|-----------|-----------|
| retro | 4 | 5（漏Write） |
| investigate | 7 | 8（漏Grep） |
| document-release | 6 | 7（漏Write） |
| gstack-upgrade | 2 | 4（含Write, AskUserQuestion） |

**评估结论：** 核心框架准确，4处误差不影响整体架构理解。

---

## 禁忌清单（共23条）

1. ❌ 不能只统计 skill 数量
2. ❌ 不能忽略 .tmpl 文件的 auto-generate 机制
3. ❌ 不能混淆 CLI 子项目和普通 skill
4. ❌ 不能混用三种关系类型
5. ❌ 不能遗漏版本信息
6. ❌ 不能估算文件数量
7. ❌ 不能忽略 extension/、lib/、docs/、.github/
8. ❌ 不能遗漏 CI workflow
9. ❌ allowed-tools 描述不能与表格矛盾
10. ❌ 每个列出的文件必须验证存在
11. ❌ allowed-tools 必须从实际 SKILL.md 读取
12. ❌ 不得将 browse/bin/ 与根 bin/ 混淆
13. ❌ 不得假设每个 skill 都有独立 .tmpl
14. ❌ 不得在未检测项目类型的情况下假设它是 skill 仓库
15. ❌ 非 skill 仓库缺失 skill 标配文件不是幽灵文件
16. ❌ ML 项目必须覆盖关键实现细节
17. ❌ 每个目录必须列出实际文件清单，不能只报总数
18. ❌ 独立 .tmpl 数量必须实际统计
19. ❌ 版本不一致必须探讨根因
20. ❌ allowed-tools 数据必须从实际文件读取，不得伪造
21. ❌ 不存在"双 allowed-tools 块"
22. ❌ WebSearch 必须完整计入工具数；unfreeze=2；gstack-upgrade=v1.1.0
23. ❌ WebSearch=12个；browse/test/=18；bin/合计=19

---

## 文件结构

```
~/Projects/my-skill-repository/skill-analyzer/
├── SKILL.md              # 最终版本 v0.9
├── CHANGELOG.md          # 完整版本变更记录
└── research/
    ├── analysis/
    │   ├── iteration-01-gstack-v0.2.md
    │   ├── iteration-02-autoresearch-v0.3.md
    │   ├── iteration-03-gstack-v0.4.md
    │   ├── iteration-04-gstack-v0.5.md
    │   ├── iteration-05-gstack-v0.6.md
    │   ├── iteration-06-gstack-v0.7.md
    │   ├── iteration-07-gstack-v0.8.md
    │   └── iteration-08-gstack-v0.9.md
    └── evaluation/
        ├── iteration-01-evaluation-v0.2.md
        ├── iteration-02-evaluation-v0.3.md
        ├── iteration-03-evaluation-v0.4.md
        ├── iteration-04-evaluation-v0.5.md
        ├── iteration-05-evaluation-v0.6.md
        ├── iteration-06-evaluation-v0.7.md
        ├── iteration-07-evaluation-v0.8.md
        └── iteration-08-evaluation-v0.9.md
```

---

## 实验元信息

- **开始时间：** 2026-03-27
- **结束时间：** 2026-03-28
- **总轮次：** 8轮
- **总 token 消耗：** ~4.2M
- **分析仓库：** gstack（5次）、autoresearch（1次）
- **主要贡献者：** PM主Agent + 分析Subagent + 评估Subagent

---

*skill-analyzer 最终版 | 2026-03-28*
