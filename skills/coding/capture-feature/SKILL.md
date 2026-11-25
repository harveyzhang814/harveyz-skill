---
name: capture-feature
version: "0.3.0"
description: Use when looking up or adding product features and user-interactive interfaces, their hierarchy and code locations — invoke with /capture-feature query|add|update|remove|check <term>; normally routed from capture-vocab, against the feature map at .hskill/capture-feature/
user_invocable: true
---

# Feature Map

项目级产品功能地图：`feature`（功能）与 `interface`（可交互界面）两类对象，各自单父成树，附代码线索与版本。数据在 `<project-root>/.hskill/capture-feature/features/<id>.json`，只经脚本读写。

`SKILL_DIR` 为本 skill 的安装目录（含 `scripts/`）。

```
/capture-feature query <term>     # 高频，流程见下
/capture-feature add|update|remove <term>
/capture-feature check
```

## query `<term>` —— 查功能

参数可以是一个词，也可以是用户的一整句话。

1. 跑 `python3 SKILL_DIR/scripts/feature.py lookup "<词或整句>"`
2. **exit 0** → 按卡片回答；要看代码就按「代码」行直接打开文件，或在文件里 `rg` 符号，不用全仓搜
3. **输出 `N matches: a, b, …`** → 挑最相关的一个再 `lookup`
4. **exit 1** → 地图里没有这个功能，如实说明
5. **exit 2 或脚本不可用** → 说明功能地图不可用；不要去读 `features/` 整个目录

卡片「避免」行里的叫法不得出现在回复、文档、commit 里。

## 其余操作，用到时才读

| 要做的事 | 读哪份 |
|---|---|
| `add` / `update` / `remove` / `check`，对象格式与字段规则 | `references/manage.md` |
| 把 `vocab.md` 里的功能词迁成功能对象 | `references/migrate.md` |

**不要整份读取 `features/`**——那正是本 skill 要消除的成本。
