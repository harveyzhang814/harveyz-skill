---
title: Skill 热修补丁的生命周期管理
date: 2026-07-01
status: 已实现（fix-skill v2.1.0 + sync-hotfix v1.1.1）
related:
  - ../reference/hotfix-lifecycle.md
  - ../superpowers/specs/2026-07-01-skill-hotfix-lifecycle-design.md
---

# Skill 热修补丁的生命周期管理

> 本文解释这套机制**为什么这样设计**，而非如何使用。  
> 操作指南见 [reference/hotfix-lifecycle.md](../reference/hotfix-lifecycle.md)。

---

## 核心问题：速度与完整性的张力

Skill 在各平台安装后，难免遭遇平台 API 变更、路径差异、权限行为等问题，需要就地修复。完整流程是：

```
源仓库修改 → 发布 npm → hskill 重装
```

但问题紧急时，这条路太长。于是出现**热修**：直接改安装版文件，让 skill 立即可用。

热修解决了速度问题，但引入了两个新问题：

1. **记忆缺失**：修了什么、为什么改，只存在于操作者的记忆中
2. **来源漂移**：安装版与源仓库产生差异，下次重装会覆盖掉热修

这套机制的目标：**在不牺牲热修速度的前提下，让每个补丁都能被追踪和回归**。

---

## 设计原则

### 原则一：记录位置与被修改对象共置

最直接的记录位置是 `~/.hskill/<skill-name>/`（数据目录）。但这样做有一个隐蔽的问题：记录与被记录对象分离，跨机器同步时可能各自更新，产生不一致。

选择将 `HOTFIXES.md` 放在安装版 skill 的 `references/` 目录下，是因为：

- 记录文件与被修改文件**天然共置**，调用 sync-hotfix 时路径关系确定
- 安装版 skill 作为整体管理，不产生"记录在 A，文件在 B"的割裂
- 如果平台重装覆盖安装版，HOTFIXES.md 也随之清零——这是正确的行为（重装意味着热修已经集成进正式版，或者放弃热修）

### 原则二：自动路径和手动路径同等一等公民

热修有两种发生方式：

- **脚本报错**：fix-skill 自动诊断、修复、写 HOTFIXES.md
- **手动修改**：人工直接改 SKILL.md，然后手写条目

设计时的一个诱惑是：为手动场景单独做一个 log-hotfix skill（调用它来记录）。但这增加了认知摩擦——人需要先改文件，再调用另一个 skill 记录。

最终选择：手动场景直接写 HOTFIXES.md，无需调用任何 skill。格式足够简单，参照 `HF-NNN` 模板手写即可。fix-skill 的自动写入行为只是这个手动流程的机器化版本，两者产出格式完全相同。

### 原则三：结构化条目，不是自由文本日志

HOTFIXES.md 的条目是结构化的（7 个字段），而不是自由文本 changelog。这样设计是因为：

- sync-hotfix 需要机器读取 `file` 和 `section` 定位到源仓库中的具体位置
- `platform` 字段在多平台场景下提供决策上下文（某个补丁是否只适用于 Claude Code？）
- `merged_back` 字段是状态机，不是人工标注，sync-hotfix 扫描它来决定需要处理哪些条目

`change` 字段是人机混读的：人工理解"改了什么"，LLM 据此生成实际文件改动。

---

## 两层同步：有据可查 + 安全网

早期设计只依赖 HOTFIXES.md。但这有一个结构性盲点：**热修可能在没有被记录的情况下发生**。

例如：
- 用户忘记写 HOTFIXES.md 条目
- 辅助脚本（非 SKILL.md）被修改，超出了 fix-skill 的作用域
- 平台补丁文件（如 `platforms/SKILL.claude.md`）被直接修改

只扫描 HOTFIXES.md 会静默放过这些差异，直到某次重装后用户才发现功能消失。

所以 sync-hotfix 引入了 **Step 5 安全网**：处理完所有 HOTFIXES.md 条目后，无论有无条目，都执行安装版与源仓库的全文件 diff。

### 差异分类系统

全文件 diff 不能简单地"一律同步"，因为差异的性质不同：

| 类型 | 标记 | 含义 | 默认处置 |
|------|------|------|---------|
| 未登记热修 | `[UNLOGGED]` | 安装版有功能改动，源仓库没有 | 询问：同步/登记/忽略 |
| 平台适配 | `[PLATFORM]` | 差异源于平台特性，非通用逻辑 | 推荐忽略，不回源 |
| 源仓库超前 | `[SRC_AHEAD]` | 源仓库已更新，安装版尚未同步 | 提示重装，无需决策 |
| 双向冲突 | `[CONFLICT]` | 双方都改了同一段，互不兼容 | 三选一：取安装版/取源仓库/手动处理 |

这套分类的核心假设：LLM 能从 diff 内容推断差异的语义性质，而不需要依赖文件名或路径规则。推断理由需要展示给用户，以便人工校正误判。

**真实案例（2026-07-01 extract-url 测试）：**

全文件扫描发现 8 处差异，包括：
- `[UNLOGGED]`：`scripts/playwright_xcom.py` 有 SSL certifi 修复（在安装版），源仓库没有 — 未登记的真实热修
- `[PLATFORM]`：`platforms/SKILL.claude.md` 路径字段写了 `url-extract`（旧名），源仓库写的是 `extract-url`（当前名）
- `[SRC_AHEAD]`（×6）：源仓库在多个文件上已超前于安装版

没有安全网的话，SSL certifi 修复会在下次重装后静默丢失。

---

## 配置的设计决策

sync-hotfix 需要知道源仓库在哪里、skill 属于哪个 category。这两个值不能从平台环境自动推断，需要用户提供。

设计了 `~/.hskill/sync-hotfix/config.json` 来持久化这些值：

```json
{
  "source_root": "/Users/you/Projects/harveyz-skill",
  "skills": {
    "extract-url": "research",
    "fix-skill": "meta"
  }
}
```

几个决策点：

**为什么按 skill 存 category，而不是直接存 source_dir？**  
`source_dir` 是 `source_root/skills/<category>/<skill_name>` 的派生值。如果直接存 source_dir，多个 skill 会重复存 source_root 部分，且后续 source_root 变更（如换电脑）需要逐条修改。分离存储让更新 source_root 只改一处。

**为什么不在源仓库配置中存这些信息？**  
源仓库是多平台共享的，但每个平台的安装路径不同（`~/.claude/skills/` vs `~/.codex/skills/`）。把配置存在 `~/.hskill/` 中，是"每台机器自己知道自己的情况"的正确归属。

---

## 生命周期全流程

```
热修发生
  ├── 脚本报错
  │     └── fix-skill 自动修复
  │           └── Step 3a 成功 → append HOTFIXES.md（自动）
  └── 手动改安装版文件
        └── 用户手写 HOTFIXES.md 条目

（若干天后）
用户调用 sync-hotfix <skill_name>
  ├── 初始化 config（首次运行）
  ├── Step 1：扫描 HOTFIXES.md → 筛出 merged_back: false 条目
  ├── Step 2-3：逐条处理（应用/跳过/作废）→ 标记 merged_back: true
  ├── Step 4：输出摘要，提示 git commit
  └── Step 5：全文件 diff 安全网
        ├── 收集共同文件、仅安装版、仅源仓库
        ├── 逐文件 diff → 分类 [UNLOGGED/PLATFORM/SRC_AHEAD/CONFLICT]
        ├── 按类型引导用户决策
        └── 输出扫描摘要，有改动则再次提示 git commit
```

---

## 未纳入范围的决策

**跨平台补丁传播**：某平台上发现的补丁是否需要应用到其他平台，由人工判断。sync-hotfix 展示 `platform` 字段作为参考，不自动传播。原因：不同平台的同类问题可能有不同的修法，强制同步可能引入错误。

**HOTFIXES.md 历史清理**：`merged_back: true` 的条目保留不删。归档策略留待后续。保留的价值在于提供热修历史，便于理解 skill 演化路径。

**版本绑定**：条目未记录"基于哪个版本产生"。`date` 字段可间接定位（与版本发布日期对比），暂不做强约束。
