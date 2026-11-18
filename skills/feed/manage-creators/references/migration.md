# manage-creators — 旧版关注列表迁移

旧版 sync-xtimeline / sync-ytchannel 的关注列表（`watchlist.json`）**不再迁移**：`feedr roster` 没有 `migrate` 命令（旧 `roster migrate` 只用于把早期 watchlist.json 迁入名册；这次迁移只服务 hskill 时期的文件，在本机已经完成，所以 feedr 不再带这条迁移）。

要关注的人和渠道，用 `feedr roster registry add <url>` 逐个加入名册。加完后每个 handle 各自是一个人，同一个人的 X 和 YouTube 需要用 `merge` 合并，并主动列出名字相近的候选对给用户确认——**不要自己替用户合并**。

名册数据本身（`registry.json`、`state.json`、画像）由 `feedr init` 复制进 feedr，但只有旧 `DATA_DIR` 位于 `~/.hskill` 之下时才复制；在别处则 `roster_dir` 仍指向原路径、不复制，见 [SKILL.md](../SKILL.md) 的初始化小节；`feedr roster migrate-schema` 只负责名册内部 schema 升级，与 watchlist.json 无关。
