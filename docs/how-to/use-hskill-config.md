# 如何设置 hskill 默认配置

使用 `hskill config` 子命令持久化常用默认值，避免每次调用都传相同的 `--target` 和 `--scope`。

> 设计原理见 [explanation/hskill-architecture.md](../explanation/hskill-architecture.md#config-子命令的设计原理)。  
> 完整命令接口见 [reference/agent-cli-guide.md](../reference/agent-cli-guide.md#config)。

---

## 设置默认 target

```bash
# 第一步：设置默认 target
hskill config set default.target claude

# 第二步：之后的安装命令可以省略 --target
hskill install --skill skill-analyzer --scope user
# 等价于：hskill install --skill skill-analyzer --target claude --scope user
```

## 查看当前配置

```bash
hskill config list
hskill config list --json   # 机器可读输出
```

## 重置默认值

```bash
hskill config unset default.target
```

## 读取单个配置项

```bash
hskill config get default.target
```
