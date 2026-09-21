---
name: capture-vocab
version: "1.2.0"
description: Use when you need to look up, add, update, or remove project-specific domain terms — invoke with /capture-vocab query|add|update|remove <term>, or whenever an unfamiliar project-coined noun appears and you need its definition, against a shared vocabulary file at .hskill/capture-vocab/vocab.md
user_invocable: true
---

# Domain Vocabulary

管理项目级领域术语字典，词汇表存于 `<project-root>/.hskill/capture-vocab/vocab.md`。只存业务领域概念（跨前后端、跨 AI/人类对话都会出现的词）；函数名、变量名等技术命名不进词汇表。

```
/capture-vocab query <term>     # 高频，流程见下
/capture-vocab add <term>
/capture-vocab update <term>    # 三个写操作的流程见 references/manage.md
/capture-vocab remove <term>
```

## query `<term>` —— 查词

也用于「agent 拿不准某个词指什么」这个高频场景，参数可以是一个词，也可以是用户的一整句话。

1. 跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py lookup "<词或整句>"`
2. **exit 0** → 按输出的 section 定义理解/回答
3. **输出 `N matches: a, b, c, d`**（命中超过 3 条时的降级档）→ 挑最相关的那个再 `lookup` 一次
4. **exit 1**（`no match`）→ 该词没有定义，按字面理解，不必追问；用户显式跑 `query` 时再跑一次 `list` 列出全部术语名供其挑选
5. **exit 2 或脚本不可用**（如 python3 缺失）→ 退回读取整份 `vocab.md`，用 `## <term>` 标题手动定位（大小写不敏感）

匹配规则是「两边归一化后任一方是另一方的子串」，术语名和 `_Avoid_` 里的短别名都算。**接不住语义近似**——用户说「右边那个滑出来的框」而术语叫「工作区」，除非 `_Avoid_` 里写了那个叫法，否则查不到。

## 低频操作，用到时才读

| 要做的事 | 读哪份 |
|---|---|
| `add` / `update` / `remove`，词汇文件格式，`add` 的三层查重 | `references/manage.md` |
| 把本 skill 接进一个新项目（项目 `CLAUDE.md` 该写什么） | `references/project-setup.md` |

**不要在 session 开始时读取整份 `vocab.md`**——那会让整份词汇表每个 session 进一次上下文，正是本 skill 要消除的成本。

> 维护者注：本文件每次 invoke 都会被完整注入上下文（多次 invoke 注入多份副本），所以刻意只留查词路径。设计理由与代价见 `docs/superpowers/specs/2026-09-20-capture-vocab-retrieval-design.md` §4.1 / §5.3。
