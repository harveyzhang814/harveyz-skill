# Skill Eval 参考

## 运行命令

```bash
npm run eval                                              # 所有 skill
node scripts/run-skill-evals.js --skill brainstorming    # 单个 skill
```

结果写入 `eval-results/<timestamp>.json`。

---

## Eval 文件位置与命名

```
skills/<category>/<skill>/tests/<skill>.eval.json
```

示例：`skills/superpowers-fork/brainstorming/tests/brainstorming.eval.json`

---

## Eval 文件格式

```json
{
  "skill": "<skill-name>",
  "skill_path": "skills/<category>/<skill>",
  "cases": [
    {
      "id": "kebab-case-id",
      "description": "一句话：这个用例断言什么行为",
      "prompt": "触发测试的用户请求",
      "checks": [
        { "type": "contains", "value": "必须出现的字符串" },
        { "type": "not_contains", "value": "```" },
        { "type": "regex", "pattern": "option [123]", "flags": "i" },
        { "type": "rubric", "criteria": "响应在做 Y 之前先做了 X。" }
      ]
    }
  ]
}
```

---

## Check 类型

| 类型 | 通过条件 | 适用场景 |
|---|---|---|
| `contains` | 响应包含该字符串 | 必须出现的关键词、输出路径、结构标记 |
| `not_contains` | 响应不包含该字符串 | 禁止内容（如澄清前不得出现代码块） |
| `regex` | 正则匹配（支持 `flags`） | 格式约束、多选一 |
| `rubric` | LLM judge 回答 YES | 无法用字符串表达的细粒度行为约束 |

优先使用确定性 check（contains / not_contains / regex）。只有确实无法用字符串表达时才用 rubric。

---

## 结构测试检查项（skills.bats）

`npm test` 对每个注册 skill 校验：

1. `SKILL.md` 文件存在
2. 前置 frontmatter 分隔符（`---`）存在且不少于两个
3. `name`、`description`、`version` 字段非空
4. `version` 符合 `X.Y.Z` semver
5. `name` 与目录名完全一致
6. `bundle` 在 `bundleMeta` 中有定义

---

## 自定义 skill 测试发现规则

`scripts/run-skill-tests.sh` 自动发现并运行：

```
skills/<category>/<skill>/tests/*.bats  → bats
skills/<category>/<skill>/tests/*.py    → python3
```

---

## 现有 eval 用例

### brainstorming — `skills/superpowers-fork/brainstorming/tests/brainstorming.eval.json`

| 用例 ID | 断言 |
|---|---|
| `no-code-before-clarification` | 裸实现请求 → 无代码块，先提澄清问题 |
| `propose-multiple-options` | 功能请求 → 提出 2+ 个方案 |
| `hard-gate-simple-task` | 即使"简单"任务也需先过设计阶段 |

### systematic-debugging — `skills/superpowers-fork/systematic-debugging/tests/systematic-debugging.eval.json`

| 用例 ID | 断言 |
|---|---|
| `no-fix-before-phase1` | bug 报告 → 无代码补丁，进入 Phase 1 调查 |
| `root-cause-first` | 测试失败 → 聚焦根本原因而非直接修复 |
| `investigation-steps-mentioned` | 偶发 bug → 描述具体调查步骤而非直接给方案 |

### skill-analyzer — `skills/analysis/skill-analyzer/tests/skill-analyzer.eval.json`

| 用例 ID | 断言 |
|---|---|
| `trigger-activates-framework` | 触发词 → 提及四层洋葱模型分析框架 |
| `output-path-correct` | 触发词 → 提及 `skill-analysis/` 输出目录而非 skill 自身目录 |
| `project-type-detection-first` | 触发词 → 第一步检查 `SKILL.md` 是否存在 |

---

## 结构测试失败速查

| 错误信息 | 修复 |
|---|---|
| `SKILL.md not found` | 在 `skills/<category>/<skill>/SKILL.md` 创建文件 |
| `frontmatter delimiters missing` | 确保有两个 `---` 分隔符 |
| `name field missing or empty` | 在 frontmatter 中添加 `name:` 字段 |
| `version does not match X.Y.Z` | 将 version 改为 `"1.0.0"` 格式 |
| `name != directory` | `name:` 字段值必须与目录名完全一致 |
| `bundle not in bundleMeta` | 在 `skills-index.json` 的 `bundleMeta` 中添加对应 bundle key |
