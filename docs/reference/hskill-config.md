# hskill config 命令参考

`hskill config` 子命令用于读写用户级和项目级默认配置。

---

## 命令接口

```bash
hskill config set <key> <value>   # 写入配置
hskill config get <key>           # 读取单个值
hskill config unset <key>         # 删除配置项
hskill config list [--json]       # 列出所有配置
```

---

## 配置文件格式

```json
{
  "default": {
    "target": "claude",
    "scope": "user"
  }
}
```

### 存储路径

| 层级 | 路径 |
|------|------|
| User-level | `~/.config/hskill/config.json` |
| Project-level | `<cwd>/.hskillrc`（JSON 格式） |

Project-level 同名字段覆盖 user-level。

---

## `config list --json` 输出

```json
{
  "default.target": "claude",
  "default.scope": "user",
  "source": "user"
}
```

`source` 字段说明当前生效的配置来自哪个层级（`"user"` 或 `"project"`）。

---

## 支持的配置键

| 键 | 说明 | 示例值 |
|----|------|--------|
| `default.target` | 默认安装目标 | `claude` |
| `default.scope` | 默认安装范围 | `user` |
