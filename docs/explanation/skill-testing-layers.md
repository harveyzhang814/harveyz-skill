# Skill 测试体系：两层设计

## 为什么有两层

一个 SKILL.md 可以格式完美，但跟着它的模型仍然不能正确执行它的约束。
反过来，行为完全正确的 skill 也可能缺了一个 `version:` 字段。

这两类错误的性质不同，需要不同的测试机制：

| 层 | 命令 | 捕获什么 |
|---|---|---|
| Layer 1 结构 | `npm test` | 作者失误：字段缺失、版本格式错误、未在 index 注册 |
| Layer 2 行为 | `npm run eval` | 语义失效：约束写了但模型不执行，HARD-GATE 被绕过 |

两层独立运行，互不依赖。结构测试快（纯文本解析），行为测试慢（需要调用模型）。

---

## Layer 1 如何工作

`npm test` 运行 `bats tests/skills.bats`，读取 `skills-index.json` 中所有注册的 skill，对每个 skill 的 SKILL.md 做静态校验。失败会被收集后一次性报告，一个 skill 出错不会遮蔽其他 skill 的问题。

`npm test` 还运行 `scripts/run-skill-tests.sh`，自动发现并执行 `skills/*/tests/*.bats` 和 `*.py` 文件。这些是 skill 作者为有外部副作用的技能手动编写的自定义测试（如文件生成、CLI 输出）。

---

## Layer 2 如何工作

```
scripts/run-skill-evals.js
  └─ 发现 skills/*/tests/*.eval.json
       └─ 每个用例：
            1. 读 SKILL.md 作为系统提示
            2. 拼接用户请求 → 调用 claude -p ... --model claude-haiku-4-5-20251001
            3. 对响应执行 check（contains / not_contains / regex / rubric）
            4. rubric check → 再次调用 claude -p 作为 LLM judge
       └─ 写入 eval-results/<timestamp>.json
```

**为什么用 Haiku：** 行为约束如果在 Haiku 级别无法被遵守，说明 skill 指令本身不够清晰，需要修改。如果 Haiku 确实太弱（某些需要推理的场景），再切换到 Sonnet。

**为什么不集成到 `npm test`：** 行为测试需要调用模型，慢且有成本。结构测试应该始终快速、零成本地运行在 CI 中。
