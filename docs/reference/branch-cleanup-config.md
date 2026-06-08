# .claude/branch-cleanup.md 配置格式

`git-cleanup` skill 在项目根目录查找此文件，按其中规则对本地分支分类。文件不存在时 skill 使用内置默认规则运行，结束后提示生成。

---

## 文件格式

Markdown 格式，供 Claude 直接读取。包含三段：

```markdown
# Branch Cleanup Rules

## Always Delete
- `<glob-pattern>` — <说明>

## Always Keep
- `<glob-pattern>` — <说明>

## LLM 判断上下文
<自由文本，描述项目性质和保留/删除判断标准>
```

---

## Always Delete

命中此段规则的分支（已合并进 staging）直接归入"明显可删"组，无需 LLM 分析。

```markdown
## Always Delete
- `chore/bump-*`   — 版本号 bump，每次发布新建，无需保留
- `chore/fix-*`    — 一次性 chore 修复
- `doc/*`          — 文档更新，完成即归档
- `chore/sync-*`   — 同步类任务
```

---

## Always Keep

命中此段规则的分支（无论是否已合并）直接归入保留，不参与 LLM 分析。Always Keep 优先级高于 Always Delete——同一分支同时命中两段规则时保留。

```markdown
## Always Keep
- `test/*`             — 测试基础设施，持续迭代
- `feature/core-*`     — 核心功能，预期持续扩展
```

---

## LLM 判断上下文

未命中任何规则的已合并分支会送 LLM 分析。此段文本作为判断上下文传入：

```markdown
## LLM 判断上下文
这是一个 Claude Code skills 仓库。
保留标准：skill 开发中可能继续迭代的功能分支、eval/测试框架、基础设施类。
删除标准：一次性任务（版本 bump、lockfile 修复）、已完成且不再扩展的独立功能。
```

---

## Glob 匹配规则

- `*` 匹配任意字符，不含 `/`
- `chore/bump-*` 匹配 `chore/bump-0.3.0`，不匹配 `feature/bump-test`
- 大小写敏感

---

## 内置默认规则

无配置文件时使用：

| 段 | 规则 |
|----|------|
| Always Delete | `chore/bump-*`、`chore/sync-*`、`chore/fix-*` |
| Always Keep | `test/*`、`main`、`staging` |
| LLM context | 「通用项目。保留标准：功能仍在迭代的分支、测试框架。删除标准：一次性任务、已完成的独立功能。」 |

---

## 始终跳过（不受配置控制）

无论配置文件内容如何，以下分支永远跳过，不参与分析：

- `main`
- `staging`
- 当前所在分支（`git branch --show-current` 输出）
