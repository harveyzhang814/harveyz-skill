# 把 vocab.md 里的功能词迁成功能对象

一次性迁移办法。**只在把某个项目已有的 `vocab.md` 词条迁入功能地图时读。** 前提：capture-feature 与 capture-vocab 已装在同一 skill 根目录，且版本匹配。

## 步骤

1. **拟清单。** 逐条读 `vocab.md`，按「用户能不能直接看到或操作」分成「迁移」和「保留」两组。对每个迁移项拟好 `id`、`type`、`parent`、`code`、`aliases`、`avoid`、`description`。`introduced` 一律填 `"unknown"`。
2. **一次性列出清单**，逐条请用户确认。表头：

   | 词条 | 归属 | 新增 | type | id | parent | aliases | avoid | code |
   |---|---|---|---|---|---|---|---|---|

   「保留」的词条也要列出并写明理由。
3. **写入。** 确认后按**父节点在前**的顺序逐个 `put --new`；全部成功后才从 `vocab.md` 删除对应段落；最后跑 `feature.py check --code`，结果必须是 `ok`。中途 `put` 失败时已写入的对象保留，`vocab.md` 先不动，修正后继续，这样不会出现两边都没有的词。
4. **抽查。** 拿 3 个只出现在 `avoid` / `aliases` 里的旧叫法（至少 1 句同时含 vocab 术语），经 capture-vocab 查，应拿到对应功能卡片；再查一个留在 vocab 的机制类词，定义与迁移前一致。

## 字段转换规则

- `_Avoid_` 一律转入 `avoid`，括号里的说明转入 `note`。其中确实可以通用的别称，在清单里提议改放 `aliases`，由用户确认。
- `_Reference_` 里的 `文件:行号` 改成 `{path, symbol}`：路径去掉行号，符号名从 `_Reference_` 的文字或那一行代码里取；取不到就只留路径。不记行号。
- 层级需要、但 vocab 里没有的父节点（例如「应用窗口」），可以在清单里新增，标「新增」，同样逐条确认。
- 定义原文放进 `description`，压到一到两句话。
