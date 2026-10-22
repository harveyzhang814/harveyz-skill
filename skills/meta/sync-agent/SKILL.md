---
name: sync-agent
description: "Manage Syncthing sync folders and devices at runtime. Query sync status, add/remove sync folders, add/remove devices, pause/resume folders, force scan. Reads Syncthing API credentials from ~/.hskill/sync-agent/state.json. Does NOT start/stop the daemon — use hskill sync start/setup for that. Triggers: sync status, add sync folder, remove device, pause sync, check sync, syncthing, show sync."
user_invocable: true
version: "1.1.2"
---

# sync-agent

**Announce at start:** "Using sync-agent to [describe action]."

---

## 前置检查

每次执行前必须先完成前置检查，若任一检查失败则报错退出，不继续后续步骤。

**Step 1 — 读取 state.json**

```bash
cat ~/.hskill/sync-agent/state.json
```

若文件不存在：
> Error: state.json not found. Run `hskill sync setup` first to initialize.

从输出提取 `api_key`、`api_url`（缺省 `http://127.0.0.1:8384`），下文记作 `API_KEY`、`API_URL`。

**Step 2 — 确认 daemon 在运行**

```bash
curl -sf -H "X-API-Key: ${API_KEY}" "${API_URL}/rest/system/ping"
```

若失败（curl 返回非零）：
> Error: Syncthing daemon is not running. Run `hskill sync start` to start it.

---

## 调用约定

所有请求：`curl -s -w "\nHTTP %{http_code}" -H "X-API-Key: ${API_KEY}"`，带 body 的再加 `-H "Content-Type: application/json"`。返回 4xx/5xx：输出状态码和响应体，不继续后续步骤。

`config.json` 指 `~/.hskill/sync-agent/config.json`。条目格式须与 `hskill sync setup` 一致：folder 写 `{"id","path","label"}`，device 写 `{"id","name"}`（键是 `id`，不是 REST 的 `deviceID`）。

## 操作

| 操作 | 请求 | body | 回写 config.json |
|---|---|---|---|
| 查看状态 | `GET /rest/config/folders`；`GET /rest/system/connections`；每个 folder 再 `GET /rest/db/completion?folder={ID}` | — | 不改 |
| 添加 folder | `POST /rest/config/folders` | `{"id","path","label","type":"sendreceive","devices":[]}` | `folders` 追加 |
| 删除 folder | `DELETE /rest/config/folders/{ID}` | — | `folders` 移除该 id |
| 添加 device | `POST /rest/config/devices` | `{"deviceID","name"}` | `devices` 追加 |
| 删除 device | `DELETE /rest/config/devices/{ID}` | — | `devices` 移除该 id |
| 暂停/恢复 | `GET /rest/config/folders/{ID}`，改 `paused` 后 `PUT` 回同一路径 | 完整 folder 配置 | 不改（paused 只在 Syncthing 内生效） |
| 强制扫描 | `POST /rest/db/scan?folder={ID}` | — | 不改 |

调 API 前校验，不通过不发请求：
- 添加 folder：`ls {path}` 确认路径存在；不存在则告知用户并询问是否继续
- 添加 device：device ID 须匹配 `^[A-Z0-9]{7}(-[A-Z0-9]{7}){7}$`，否则报错

**查看状态输出格式：**
```
Folders (N):
  {id:<20} {path:<35} {completion:.0f}%  {paused ? "paused" : "syncing/synced"}

Devices (N):
  {name:<20} {deviceID[:15]}...  {online/offline}
```

**`.stignore` 规则**（查看状态时检查每个 folder；添加 folder 成功后检查新 folder）：folder 路径（`~` 展开为 `$HOME`）下有 `.gitignore`，且 `.stignore` 不存在或不含 `#include .gitignore` → 执行 `echo '#include .gitignore' > "$FOLDER_PATH/.stignore"`，并告知 `✓ Created .stignore for {id} ({path}) — linked to .gitignore`（查看状态时放在状态输出末尾）。
