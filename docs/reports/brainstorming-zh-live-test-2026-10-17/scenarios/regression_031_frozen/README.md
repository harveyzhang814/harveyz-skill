# 冻结源码的补充只读检查（实际为 0.1.32）

本目录的 [SKILL.md](SKILL.md) 是在三轮结束后从活动工作树复制的快照，SHA-256 为 `f95901a720b53ba7a89eb4ada208eb7d08077023345327d80efcf81536f71f03`，frontmatter 明确写 `0.1.32`。先前把它称为 0.1.31 是错误的。`run-turn.py` 通过 `BRAINSKILL_SOURCE` 将这一快照作为 `--append-system-prompt-file`，直接审查 `regression_031` 的最终已批准 Spec。它是源码快照，不是已安装副本。

单轮 exit code 为 0，3 次工具调用。模拟用户要求只读交付前检查；完整[对话与调用](transcript.md)、[原始事件](logs/turn-01.jsonl)、[产物哈希](artifacts.json) 均保留。助手正确暂停制定计划，识别 AC-26 与补记真实结果的冲突，以及锁等待上限歧义；但未指出原 Spec 第 388 行 AC-03 与第 413 行 AC-28 的直接矛盾。这个结果只说明冻结的 0.1.32 在该单轮检查中的表现，不能替代 0.1.31 完整复测。
