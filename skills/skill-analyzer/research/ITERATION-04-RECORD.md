# 第4轮迭代实验记录

**日期：** 2026-03-27
**起点：** v0.5 Skill
**目标仓库：** gstack

---

## 迭代流程

| 阶段 | 执行者 | 运行时长 | Token 消耗 | 输出文件 |
|------|--------|---------|-----------|---------|
| 分析 Subagent | think=high | 6m15s | 294.7k | iteration-04-gstack-v0.5.md |
| 评估 Subagent | think=medium | 7m31s | 946.6k | iteration-04-evaluation-v0.5.md |
| 主 Agent 整合 | PM | — | — | v0.6 |

---

## 评估结果统计

| 维度 | 评级 | 说明 |
|------|------|------|
| 禁忌 17（文件清单） | ✅ | lib/=1, supabase/=4 ✅ |
| 禁忌 18（.tmpl 数量） | ✅ | 29个逐项列出 ✅ |
| 禁忌 19（版本根因） | ✅ | 分层策略分析合理 ✅ |
| **禁忌 20（allowed-tools 数据）** | ❌ | **严重伪造数据** |

---

## 最严重问题：allowed-tools 数据大量伪造

### 伪造数据详情

| Skill | 报告声称 | 实际值 | 问题 |
|-------|---------|--------|------|
| browse | 8个（第一块），3个（第二块） | **仅3个**（Bash, Read, AskUserQuestion） | 数量完全错误 |
| qa | 9个（含Agent） | **8个**（无Agent） | 多了Agent |
| setup-browser-cookies | 7个+3个（两个块） | **仅3个**（Bash, Read, AskUserQuestion） | 捏造双块 |
| review | 9个+双块 | **9个单块** | 捏造双块 |
| **双重块总数** | 报告称10个 | **实际0个** | 完全捏造 |

### 根因

分析 subagent **未从实际 SKILL.md 文件读取**，而是从记忆/上轮报告复制或凭空捏造。

---

## v0.6 核心修复

**禁忌 20：** allowed-tools 数据必须从实际文件读取并验证，不得从记忆/上轮报告复制，不得伪造第二个块

**强制验证步骤：**
- `cat <skill>/SKILL.md | head -50` 读取实际 frontmatter
- `grep -A20 "allowed-tools"` 验证
- 提供已知基准数据交叉验证

---

## 版本演进

| 版本 | 主要变更 |
|------|---------|
| v0.1-baseline | 洋葱模型四层框架 |
| v0.2 | 必检清单、Ghost文件、CI保障 |
| v0.3 | allowed-tools强制验证、.tmpl精确化、bin/区分 |
| v0.4 | 项目类型检测、ML项目补充 |
| v0.5 | 文件清单逐项列出、版本根因分析 |
| **v0.6** | **禁止伪造allowed-tools数据（禁忌20）** |

---

## 文件清单

```
skill-analyzer/
├── SKILL.md              # v0.6（当前）
├── CHANGELOG.md          # 版本记录
└── research/
    ├── analysis/
    │   ├── iteration-01-gstack-v0.2.md
    │   ├── iteration-02-autoresearch-v0.3.md
    │   ├── iteration-03-gstack-v0.4.md
    │   └── iteration-04-gstack-v0.5.md
    └── evaluation/
        ├── iteration-01-evaluation-v0.2.md
        ├── iteration-02-evaluation-v0.3.md
        ├── iteration-03-evaluation-v0.4.md
        └── iteration-04-evaluation-v0.5.md
```

---

## 轮次状态

- 第1轮：✅ 完成（gstack，v0.1→v0.2）
- 第2轮：✅ 完成（autoresearch，v0.3）
- 第3轮：✅ 完成（gstack，v0.4→v0.5）
- 第4轮：✅ 完成（gstack，v0.5→v0.6）
- 第5轮：待执行
- 停止条件：至少3轮，最多10轮；评估认为充分则停止
