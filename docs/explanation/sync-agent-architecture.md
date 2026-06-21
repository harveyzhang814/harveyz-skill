# sync-agent 架构与设计原理

解释 sync-agent 的组件分工、Syncthing REST 集成方式，以及 config/state 分离的原因。

---

## 组件分工

sync-agent 由两个独立组件构成：

| 组件 | 位置 | 职责 |
|------|------|------|
| hskill tool | `tools/sync-agent/sync_agent.py` | daemon 生命周期 + 初始 setup |
| Agent skill | `skills/meta/sync-agent/SKILL.md` | 运行时配置管理（folder/device 增删、状态查询） |

**原因：** daemon 的启动/停止是系统级操作，需要 shell 执行环境；运行时的配置变更（添加 folder、暂停同步）是 REST API 调用，适合 Agent 处理。分开后 Agent 不需要管理进程生命周期，tool 不需要理解 Syncthing 的配置语义。

---

## 数据层：config/state 分离

```
~/.hskill/sync-agent/
├── config.json      # 用户声明的同步配置（source of truth，可手动编辑）
├── state.json       # 运行时状态（API key、device ID，自动生成，不纳入 git）
└── syncthing.log    # daemon 日志
```

**config.json** 是用户可读可编辑的声明式配置，描述"想要同步什么"：

```json
{
  "folders": [
    { "id": "hskill-data", "path": "~/.hskill", "label": "hSkill Runtime Data" }
  ],
  "devices": [
    { "id": "XXXX-...", "name": "MacBook Pro" }
  ]
}
```

**state.json** 是运行时产物，存储 Syncthing API key 和本机 device ID，由 `hskill sync setup` 自动生成。与 config.json 分离的原因：state 包含敏感值（API key），不应被纳入 git 或手动编辑；config 则应可版本控制、跨机器共享。

**数据流：**

```
config.json  ←──────── Skill（变更操作后回写）
     │                        ↑
     ↓                   REST API（读 state.json 获取 api_key）
hskill sync setup ──→ Syncthing daemon（127.0.0.1:8384）
     ↓
state.json（自动生成）
```

---

## setup 幂等性设计

`hskill sync setup` 可重复运行而不产生副作用：

1. 检查 daemon 是否运行，未运行则自动启动
2. 轮询 `GET /rest/system/ping`，最多等待 10 秒
3. 从 Syncthing config XML 提取 API key 和 device ID，写入 `state.json`
4. 对 config.json 中每个 folder 调用 `POST /rest/config/folders`（已存在则跳过）
5. 对 config.json 中每个 device 调用 `POST /rest/config/devices`（已存在则跳过）
6. 将每个 folder 与所有 device 关联
7. 安装 launchd plist 实现开机自启

launchd plist 路径：`~/Library/LaunchAgents/com.harveyz.syncthing.plist`

启动命令：
```bash
syncthing serve --no-browser --logfile=~/.hskill/sync-agent/syncthing.log
```

---

## Skill 的前置检查

Skill 每次执行前必须验证运行时环境：

1. 读取 `~/.hskill/sync-agent/state.json` — 不存在则提示运行 `hskill sync setup`
2. `GET /rest/system/ping` — 失败则提示运行 `hskill sync start`

这两步分开检查，给出具体的修复建议，而不是统一报"连接失败"。

---

## 变更操作的回写策略

添加/删除 folder 或 device 后，Skill 调用 `GET /rest/config` 获取最新 Syncthing 配置，同步回写 `config.json`。这保证 config.json 始终与 Syncthing 实际配置一致，下次 `setup`（如在新设备初始化）能复现完整配置。

---

## 错误处理原则

| 场景 | 行为 |
|------|------|
| daemon 未运行 | 报错 + 提示 `hskill sync start` |
| state.json 不存在 | 报错 + 提示 `hskill sync setup` |
| REST 4xx / 5xx | 展示 HTTP 状态码和错误体，不静默失败 |
| folder 路径不存在 | 添加前检查，提示用户确认 |
| device ID 格式错误 | 验证 Syncthing device ID 格式（63 字符 Base32 + 校验位） |

静默失败比显式错误更难调试，所有 REST 错误都暴露给用户。
