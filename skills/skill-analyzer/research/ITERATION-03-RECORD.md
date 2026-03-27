# 第3轮迭代实验记录

**日期：** 2026-03-27
**起点：** v0.4 Skill
**目标仓库：** gstack（重试）

---

## 迭代流程

| 阶段 | 执行者 | 运行时长 | Token 消耗 | 输出文件 |
|------|--------|---------|-----------|---------|
| 分析 Subagent（第1次） | think=high | 16m34s | 463.5k | ❌ 失败（文件未写入） |
| 分析 Subagent（第2次） | think=high | 4m32s | 561.4k | ✅ iteration-03-gstack-v0.4.md |
| 评估 Subagent | think=medium | 7m30s | 504.2k | iteration-03-evaluation-v0.4.md |
| 主 Agent 整合 | PM | — | — | v0.5 |

---

## 评估结果统计

| 维度 | 评级 | 说明 |
|------|------|------|
| 项目类型检测 | ✅ | 正确识别为 skill 仓库 |
| 幽灵文件 | ✅ | 无幽灵文件 |
| allowed-tools | ✅ | 28个skill全部读取 |
| bin/ 区分 | ✅ | 根bin/(17) vs browse/bin/(2) |
| **lib/ 数量** | ❌ | 报告10个，实际1个（worktree.ts） |
| **独立 .tmpl 数量** | ❌ | 报告4个，实际29个（每个skill都有） |
| **supabase/ 文件** | ⚠️ | 遗漏 verify-rls.sh（应为6个） |
| 版本根因分析 | ❌ | 未探讨 package.json 落后的原因 |

---

## 主要问题（v0.4 → v0.5 改进）

### 1. 文件清单只报总数不列姓名（禁忌 17）

**问题：** lib/ 报告"10个文件"，实际只有 worktree.ts 一个文件
**修复：** 每个目录必须列出实际文件名清单，不能只报总数

### 2. 独立 .tmpl 数量假设错误（禁忌 18）

**问题：** 报告称只有4个独立 .tmpl（根/browse/setup-browser-cookies/setup-deploy），实际**每个 skill 目录都有自己独立的 .tmpl**
**修复：** 必须用 `find` 实际统计每个有 .tmpl 的 skill，报告要列出名称

### 3. supabase/ 遗漏 verify-rls.sh

**修复：** 所有支撑目录都要完整列出文件清单

### 4. 版本不一致未探讨根因（禁忌 19）

**问题：** package.json=0.12.0.0，VERSION=0.12.2.0，未探讨是"有意分层"还是"遗忘"
**修复：** 增加"版本不一致根因分析"小节

---

## 版本演进

| 版本 | 主要变更 |
|------|---------|
| v0.1-baseline | 洋葱模型四层框架 |
| v0.2 | 必检清单、VERSION核实、数量核实、Ghost文件、CI保障 |
| v0.3 | allowed-tools强制验证、.tmpl精确化、bin/区分 |
| v0.4 | 项目类型检测、ML项目分析补充 |
| **v0.5** | **文件清单必须逐项列出（禁忌17）、.tmpl数量必须实际统计（禁忌18）、版本根因分析（禁忌19）** |

---

## 文件清单

```
skill-analyzer/
├── SKILL.md              # v0.5（当前）
├── CHANGELOG.md          # 版本记录
└── research/
    ├── analysis/
    │   ├── iteration-01-gstack-v0.2.md
    │   ├── iteration-02-autoresearch-v0.3.md
    │   └── iteration-03-gstack-v0.4.md
    └── evaluation/
        ├── iteration-01-evaluation-v0.2.md
        ├── iteration-02-evaluation-v0.3.md
        └── iteration-03-evaluation-v0.4.md
```

---

## 轮次状态

- 第1轮：✅ 完成（gstack，v0.1→v0.2）
- 第2轮：✅ 完成（autoresearch，v0.3，类别错误修复）
- 第3轮：✅ 完成（gstack重试，v0.4→v0.5）
- 第4轮：待执行
- 停止条件：至少3轮，最多10轮；评估认为充分则停止
