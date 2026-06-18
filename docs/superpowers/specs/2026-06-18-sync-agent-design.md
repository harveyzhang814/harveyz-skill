# sync-agent 设计文档

**日期：** 2026-06-18
**状态：** 已批准

---

## 概述

让 Agent 通过 Syncthing 在多台 macOS 设备间同步任意文档。支持同步 `.hskill/` 运行时数据、Hermes 性格文件等 Agent 配置，未来可扩展至任意路径。

**范围：** macOS 设备之间，Syncthing v2.x，REST API 交互。

---

## 架构

```
~/.hskill/sync-agent/
├── config.json      # 用户声明的同步配置（source of truth，可手动编辑）
├── state.json       # 运行时状态（API key、device ID，自动生成，不纳入 git）
└── syncthing.log    # Syncthing daemon 日志

harveyz-skill/
├── tools/sync-agent/
│   ├── sync_agent.py      # hskill tool：daemon 生命周期 + 初始 setup
│   └── tool.json          # hskill tool 元数据
└── skills/meta/sync-agent/
    └── SKILL.md           # Agent skill：运行时配置管理
```

**数据流：**

```
config.json  ←──────── Skill（运行时变更回写）
     │                        ↑
     ↓                   REST API（读取 state.json 获取 api_key）
hskill sync setup ──→ Syncthing daemon（127.0.0.1:8384）
     ↓
state.json（自动生成）
```

---

## config.json 格式

```json
{
  "folders": [
    {
      "id": "hskill-data",
      "path": "~/.hskill",
      "label": "hSkill Runtime Data"
    },
    {
      "id": "hermes-config",
      "path": "~/Projects/hermes/config",
      "label": "Hermes Config"
    }
  ],
  "devices": [
    {
      "id": "XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX",
      "name": "MacBook Pro"
    }
  ]
}
```

## state.json 格式（自动生成，勿手动编辑）

```json
{
  "api_key": "abc123",
  "device_id": "XXXX-XXXX-...",
  "api_url": "http://127.0.0.1:8384"
}
```

---

## hskill Tool（`tools/sync-agent/sync_agent.py`）

**职责：** daemon 生命周期管理 + 初始配置 setup。

### 命令接口

| 命令 | 说明 |
|------|------|
| `hskill sync setup` | 从 config.json 初始化 Syncthing（幂等，可重复运行） |
| `hskill sync start` | 启动 Syncthing daemon（已运行则跳过） |
| `hskill sync stop` | 停止 Syncthing daemon |
| `hskill sync status` | 检查 daemon 是否运行、输出 device ID 和 API key |

### `setup` 执行逻辑（幂等）

1. 检查 Syncthing 是否已运行，未运行则自动 `start`
2. 等待 REST API 就绪（最多 10s，轮询 `GET /rest/system/ping`）
3. 从 Syncthing config XML（`~/.config/syncthing/config.xml`）提取 API key 和本机 device ID，写入 `state.json`
4. 对 `config.json` 中每个 folder：调用 `POST /rest/config/folders`（已存在则跳过）
5. 对 `config.json` 中每个 device：调用 `POST /rest/config/devices`（已存在则跳过）
6. 将每个 folder 与所有 device 关联（share）
7. 安装 launchd plist（`~/Library/LaunchAgents/com.harveyz.syncthing.plist`）实现开机自启

**启动命令：**
```bash
syncthing serve --no-browser --logfile=~/.hskill/sync-agent/syncthing.log
```

---

## Skill（`skills/meta/sync-agent/SKILL.md`）

**职责：** 运行时配置管理与状态查询。不管理 daemon 生命周期。

**触发词：** "sync status"、"add sync folder"、"remove device"、"pause sync"、"check sync"、"syncthing" 等。

### 前置检查

1. 读取 `~/.hskill/sync-agent/state.json`
   - 若不存在 → 报错，提示运行 `hskill sync setup`
2. `GET /rest/system/ping`
   - 若失败 → 报错，提示运行 `hskill sync start`

### 操作能力

| 操作 | REST 调用 | 回写 config.json |
|------|-----------|-----------------|
| 查看同步状态 | `GET /rest/config/folders` + `GET /rest/db/completion` | 否 |
| 查看在线设备 | `GET /rest/system/connections` | 否 |
| 添加 folder | `POST /rest/config/folders` | 是 |
| 删除 folder | `DELETE /rest/config/folders/{id}` | 是 |
| 添加 device | `POST /rest/config/devices` | 是 |
| 删除 device | `DELETE /rest/config/devices/{id}` | 是 |
| 暂停/恢复 folder | `PUT /rest/config/folders/{id}`（修改 `paused` 字段）| 是 |
| 强制扫描 | `POST /rest/db/scan?folder={id}` | 否 |

**变更操作后：** 调用 `GET /rest/config` 获取最新状态，同步回写 `config.json`。

**状态查询输出格式（示例）：**
```
Folders (2):
  hskill-data   ~/.hskill          100%  synced   2 devices
  hermes-config ~/Projects/hermes   87%  syncing  1 device

Devices (2):
  MacBook Pro    XXXX-XXXX-...  online
  Mac mini       YYYY-YYYY-...  offline
```

---

## 错误处理

| 场景 | 行为 |
|------|------|
| daemon 未运行 | 报错 + 提示 `hskill sync start` |
| state.json 不存在 | 报错 + 提示 `hskill sync setup` |
| REST 4xx/5xx | 展示 HTTP 状态码和错误体，不静默失败 |
| folder 路径不存在 | 添加前检查，提示用户确认路径 |
| device ID 格式错误 | 验证 Syncthing device ID 格式（63 字符 Base32 + 校验位） |

---

## 不在范围内

- iOS/Android/Linux 设备支持
- Syncthing relay 配置（使用默认 global discovery）
- 加密 folder（Syncthing Untrusted Device 模式）
- 冲突解决策略（使用 Syncthing 默认行为）
