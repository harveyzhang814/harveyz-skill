# 为 Skill 编写行为测试

在 `skills/<category>/<skill>/tests/<skill>.eval.json` 中添加测试用例。
格式规范见 [reference/skill-eval-reference.md](../reference/skill-eval-reference.md)。

---

## 第一步：判断要测什么

```
这个 skill 有明确的 HARD 约束（禁止做某事）？
  是 → 用 not_contains 或 rubric 验证约束未被违反
  否 → skill 要求特定输出结构？
          是 → 用 contains 检查结构标记
          否 → 用 rubric 检查整体行为意图
```

---

## 第二步：写用例

每个用例只测一个行为。模板：

```json
{
  "id": "constraint-name",
  "description": "Given X, must do Y before Z",
  "prompt": "触发约束的真实用户请求",
  "checks": [
    { "type": "not_contains", "value": "禁止出现的内容" },
    { "type": "rubric", "criteria": "响应在 Z 之前先完成了 Y。它没有跳过 Y。" }
  ]
}
```

---

## 选 check 类型

优先确定性 check：

1. `contains` / `not_contains` — 能用就用，最快最稳定
2. `regex` — 需要模式匹配或多选一时
3. `rubric` — 以上三种都无法表达时才用

**rubric criteria 写法：** 描述行为意图，不要描述具体措辞。

| 差 | 好 |
|---|---|
| "The response says '我需要了解更多'" | "The response asks a clarifying question before implementing" |
| "Mentions 根本原因" | "Begins with investigation rather than proposing a code fix" |

---

## 数量建议

- 每个 skill **3–5 个**用例
- 覆盖 skill 最核心的 1–2 个约束，不要穷举所有规则
- skill 有明显的多个模式（如触发词 vs 非触发词）时可以每个模式一个用例

---

## 运行验证

```bash
node scripts/run-skill-evals.js --skill <skill-name>
```

---

## 常见错误

| 错误 | 正确做法 |
|---|---|
| rubric criteria 描述具体措辞 | 描述行为意图 |
| 一个用例测多个约束 | 每个约束拆成独立用例 |
| 能用 contains 的地方用了 rubric | 改用确定性 check |
| eval 文件放在 tests/ 之外 | 必须在 `skills/<category>/<skill>/tests/` 下 |
| `skill_path` 带前导或尾部斜杠 | 使用相对路径，如 `skills/category/skill` |
| 将 eval 加入 npm test | eval 独立运行，永远不加入 npm test |
