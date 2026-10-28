# clip-url — Claude Code 补丁

适用平台：Claude Code（harveyz-skill）

---

## ① Subagent 派发

用 Agent 工具派发（`subagent_type: general-purpose`），prompt 为替换好占位符的任务内容；Agent 调用返回即视为完成，从返回文本中读取 `RESULT:` 等报告字段。

## ② 变量来源

`SKILL_DIR` 为本平台固定值，在 subagent 任务代码中直接使用此路径字符串：

```
$HOME/.claude/skills/clip-url
```
