---
name: sync-agent
description: "Manage Syncthing sync folders and devices at runtime. Query sync status, add/remove sync folders, add/remove devices, pause/resume folders, force scan. Reads Syncthing API credentials from ~/.hskill/sync-agent/state.json. Does NOT start/stop the daemon — use hskill sync start/setup for that. Triggers: sync status, add sync folder, remove device, pause sync, check sync, syncthing, show sync."
user_invocable: true
version: "1.0.0"
---

# sync-agent

Manage Syncthing sync configuration and query status via the REST API.

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

从输出提取：`API_KEY`、`API_URL`（默认 `http://127.0.0.1:8384`）

**Step 2 — 确认 daemon 在运行**

```bash
curl -sf -H "X-API-Key: ${API_KEY}" "${API_URL}/rest/system/ping"
```

若失败（curl 返回非零）：
> Error: Syncthing daemon is not running. Run `hskill sync start` to start it.

---

## 操作：查看同步状态

```bash
# 获取 folder 列表
curl -s -H "X-API-Key: ${API_KEY}" "${API_URL}/rest/config/folders"

# 获取 device 连接状态
curl -s -H "X-API-Key: ${API_KEY}" "${API_URL}/rest/system/connections"

# 对每个 folder 获取同步进度
curl -s -H "X-API-Key: ${API_KEY}" "${API_URL}/rest/db/completion?folder={FOLDER_ID}"
```

**输出格式：**
```
Folders (N):
  {id:<20} {path:<35} {completion:.0f}%  {paused ? "paused" : "syncing/synced"}

Devices (N):
  {name:<20} {deviceID[:15]}...  {online/offline}
```

---

## 操作：添加 Folder

1. 确认路径存在（`ls {path}`）；若不存在告知用户并询问是否继续
2. 调用 REST API：
```bash
curl -s -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"id":"{ID}","path":"{PATH}","label":"{LABEL}","type":"sendreceive","devices":[]}' \
  "${API_URL}/rest/config/folders"
```
3. 若返回 4xx/5xx：输出状态码和响应体，不静默失败
4. 回写 config.json：将新 folder 追加到 `~/.hskill/sync-agent/config.json` 的 `folders` 数组

---

## 操作：删除 Folder

```bash
curl -s -X DELETE \
  -H "X-API-Key: ${API_KEY}" \
  "${API_URL}/rest/config/folders/{FOLDER_ID}"
```

从 `config.json` 的 `folders` 数组中移除对应条目。

---

## 操作：添加 Device

验证 device ID 格式：必须是 8 组 7 个大写字母数字，以 `-` 分隔（如 `XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX`），共 56 字符加 7 个分隔符 = 63 字符总长。

```bash
curl -s -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"deviceID":"{DEVICE_ID}","name":"{NAME}"}' \
  "${API_URL}/rest/config/devices"
```

回写 config.json：追加到 `devices` 数组。

---

## 操作：删除 Device

```bash
curl -s -X DELETE \
  -H "X-API-Key: ${API_KEY}" \
  "${API_URL}/rest/config/devices/{DEVICE_ID}"
```

从 `config.json` 的 `devices` 数组中移除对应条目。

---

## 操作：暂停 / 恢复 Folder

先获取当前 folder 配置：
```bash
curl -s -H "X-API-Key: ${API_KEY}" "${API_URL}/rest/config/folders/{FOLDER_ID}"
```

修改 `paused` 字段后 PUT 回去：
```bash
curl -s -X PUT \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{...updated config with paused: true/false...}' \
  "${API_URL}/rest/config/folders/{FOLDER_ID}"
```

回写 config.json（paused 状态不持久化到 config.json，仅在 Syncthing 内部生效）。

---

## 操作：强制扫描

```bash
curl -s -X POST \
  -H "X-API-Key: ${API_KEY}" \
  "${API_URL}/rest/db/scan?folder={FOLDER_ID}"
```

---

## 错误处理原则

- 所有 curl 调用加 `-w "\nHTTP %{http_code}"` 捕获状态码
- 4xx/5xx：输出状态码 + 响应体，不继续后续步骤
- 路径不存在、device ID 格式错误：在调用 API 前就报错
