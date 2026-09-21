# capture-vocab 写操作细则

`add` / `update` / `remove` 的完整流程，以及词汇文件格式。**只在真的要执行这三个命令时才读这份**——查词（`query`）用不到它，`SKILL.md` 已经自带。

脚本路径下面一律简写为 `vocab.py`，完整命令是：

```
python3 ~/.claude/skills/capture-vocab/scripts/vocab.py <子命令> [参数]
```

## 词汇文件格式

`<project-root>/.hskill/capture-vocab/vocab.md`

```markdown
# Domain Vocabulary

## 术语名
定义文本（一到两句话，说清楚概念是什么）。
_Avoid_: 旧叫法, 混用词
_Reference_: src/models/order.ts:42, docs/business/order-flow.md
```

`_Avoid_:` 和 `_Reference_:` 均为可选，不填时省略该行。`_Reference_:` 为自由文本，可写代码文件路径+行号、文档位置、任意引用。

**`_Avoid_` 写得全不全，直接决定查词准不准**——`lookup` 靠术语名和 Avoid 别名做匹配，接不住语义近似。录入时把想得到的别的叫法都写进去。

## add `<term>`

**分层查重，按成本从低到高，严格顺序：**

1. 跑 `vocab.py lookup "<term>"`。命中（exit 0）→ 输出"术语 '<term>' 已存在，请用 `update` 修改"并退出
2. 从当前对话上下文推断该词的**定义 / Avoid / Reference**（Reference 留空则跳过第 3 层）
3. 对推断出的每个 Reference 路径，跑 `vocab.py refs "<path>"`，收集分档候选（`same-file` / `dir-contains`）
4. **仅当第 1、3 步均空手**（`lookup` 未命中 且 `refs` 无候选）时，才跑 `vocab.py list`，比对全量术语名+别名找语义相近候选；否则跳过这一步，不付这个 O(N) 成本
5. 对已得到的候选（第 3 或第 4 步产出的）逐个 `lookup` 取完整定义，**必须显式判一个结论并说给用户**，三选一：
   - **同一实体两个名字** → 建议改用 `update`，把新叫法并进该条目的 `_Avoid_`
   - **父子实体各有其名** → 正常新增，建议在两条定义里互相点名
   - **无关** → 正常新增
6. 展示条目 + 查重结论，等用户确认（`y` 或直接输入修改内容），格式：
   ```
   准备添加以下条目，请确认或直接修改：

   ## <term>
   <推断的定义，或"（请输入）"若无法推断>
   _Avoid_: <推断的 avoid，或省略>
   _Reference_: <推断的 reference，或省略>

   查重结论：<同一实体两个名字 / 父子实体各有其名 / 无关，附简要理由>

   确认添加？(y / 直接输入修改内容)
   ```
7. 若目录 `.hskill/capture-vocab/` 不存在，创建它；若 `vocab.md` 不存在，创建并写入 `# Domain Vocabulary\n`
8. 在文件末尾追加新 section，Avoid/Reference 为空时省略对应行

**第 5 步不能省。** Reference 重叠区分不了「同一实体两个名字」和「父子实体各有其名」——脚本只负责把候选分档摆出来，判断必须由用户拍板。默默放过等于没做查重。

**退路**：`vocab.py` 不存在或 python3 不可用时，退回读取整份 `vocab.md` 手动检查 `## <term>` 是否已存在，跳过第 3/4 层查重（无法自动化），仅凭对话上下文判断是否重复。

## update `<term>`

1. 跑 `vocab.py lookup "<term>"` 确认存在；exit 1 或 2 → 输出对应错误后退出
2. 展示当前条目的完整内容
3. **从当前对话上下文推断**需要更新的字段（定义/Avoid/Reference）；若无新信息可推断，各字段显示为原值
4. 展示推断后的新条目，请用户确认或修改（格式同 add 第 6 步）
5. 用最终值替换该 section 内容，写回文件；未修改的字段保持原值不变

## remove `<term>`

1. 跑 `vocab.py lookup "<term>"` 确认存在；exit 1 或 2 → 输出对应错误后退出
2. 展示该术语的当前条目
3. 提示"确认删除 '<term>'？(y/N)"，等待用户输入
4. 若输入 `y`：删除该 section（含前后空行），写回文件
5. 若输入其他：输出"已取消"并退出

删除后不需要重建任何索引——本 skill 没有落盘索引，`vocab.md` 是唯一真相源。
