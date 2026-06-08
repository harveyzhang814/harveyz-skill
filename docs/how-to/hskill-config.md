# 如何使用 hskill config 设置默认值

使用 `hskill config` 子命令持久化常用参数（如 `--target`、`--scope`），避免每次安装时重复输入。

---

## 设置默认 target

```bash
# 第一步：设置默认 target
hskill config set default.target claude

# 第二步：之后的安装命令可以省略 --target
hskill install --skill skill-analyzer --scope user
# 等价于：hskill install --skill skill-analyzer --target claude --scope user
```

## 重置默认值

```bash
hskill config unset default.target
```

## 查看当前配置

```bash
hskill config list
hskill config list --json
```
