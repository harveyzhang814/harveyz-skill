# 如何用 git-cleanup 梳理分支

`git-cleanup` skill 帮你周期性清理本地废弃分支，通过规则匹配 + LLM 语义分析的混合方式给出删除建议，分组确认后批量执行。

---

## 触发方式

```
清理分支
整理分支
branch cleanup
删除旧分支
```

---

## 执行流程（用户视角）

1. **读取规则** — 读取 `.claude/branch-cleanup.md`（不存在则用内置默认规则）
2. **收集分支数据** — 运行 `git branch` 和 `git branch --merged staging`
3. **分类** — 未合并分支全部保留；已合并分支按规则和 LLM 分析分组
4. **逐组确认** — 分三组展示，每组独立询问是否删除：
   - 组 A：规则命中可删
   - 组 B：LLM 建议删除
   - 组 C：保留清单（只展示，无操作）
5. **执行删除** — 用 `git branch -d`（安全模式）；remote 同名分支只提示，不自动删除
6. **收尾** — 打印摘要；若无配置文件，询问是否生成

---

## 配置文件（可选）

在项目根目录创建 `.claude/branch-cleanup.md`，自定义保留 / 删除规则：

```markdown
# Branch Cleanup Rules

## Always Delete
- `chore/bump-*` — 版本号 bump，每次发布新建
- `doc/*` — 文档更新，完成即归档

## Always Keep
- `test/*` — 测试基础设施
- `feature/long-running-*` — 长期功能分支

## LLM 判断上下文
这是一个 Claude Code skills 仓库。
保留标准：skill 开发中可能继续迭代的功能分支、eval/测试框架。
删除标准：一次性任务、已完成且不再扩展的独立功能。
```

不存在时使用内置规则（详见 [reference/branch-cleanup-config.md](../reference/branch-cleanup-config.md)），运行结束后会提示生成。

---

## 安全约束

- `main`、`staging`、当前分支永远跳过，不参与分析
- 未合并进 `staging` 的分支一律归入保留，不建议删除
- remote 分支只提示命令，不自动删除
- `git branch -d`（而非 `-D`）：未合并时 git 自动拒绝
