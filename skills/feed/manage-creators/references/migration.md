# manage-creators — 旧版关注列表迁移

用户同意迁移旧版 sync-xtimeline / sync-ytchannel 关注列表后执行：

```bash
<roster_path> migrate \
  --from-xtimeline "$(python3 -c "import json,pathlib;print(pathlib.Path(json.loads((pathlib.Path.home()/'.hskill/sync-xtimeline/config.json').read_text())['DATA_DIR']).expanduser()/'watchlist.json')")" \
  --from-ytchannel "$(python3 -c "import json,pathlib;print(pathlib.Path(json.loads((pathlib.Path.home()/'.hskill/sync-ytchannel/config.json').read_text())['DATA_DIR']).expanduser()/'watchlist.json')")"
```

任一旧配置不存在就省掉对应的参数。迁移是幂等的，重复跑安全。迁移后告诉用户：每个 handle 现在各自是一个人，同一个人的 X 和 YouTube 需要用 `merge` 合并，并主动列出名字相近的候选对给用户确认——**不要自己替用户合并**。
