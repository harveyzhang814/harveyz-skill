# QM 执行环境层深入分析（非 skill 部分）

> 关联文档：
> - [[qm-overview]]（QM 项目整体调研：产品目标、哲学与功能模块分解）
> - [[qm-memory-layer]]（记忆层深入分析）
>
> 调研对象：`yc-software/qm` 的 `src/sandbox/`、`src/workspace/`、`src/files/`、`src/processes/`、`src/tools/`
> 本地路径：`~/Repositories/qm`
> 调研时间：2026-08-09
> 仓库版本：`main` @ `0f0e0ad`
>
> 范围说明：对应整体调研中的功能模块组 **E. 执行环境**，**不含 `src/skills/`**（技能生命周期另议）。
> 共约 5175 行：`sandbox/` 17 个文件、`workspace/` 1 个、`files/` 3 个、`processes/` 3 个、`tools/primitives.ts`。

---

## 一、这一层在做什么

README 的隐喻是 **agent 的「耐用电脑」（durable computer）**——装过的工具会一直在。

但代码里的抽象名字更准确：`AgentComputerProfile`、`AgentComputerBackupEntry`、`AgentComputerSpec`。它们把这件事定义成了一个**可协商能力的计算机**，而不是一个统一的沙箱抽象。

这是整组模块最重要的设计决定，下面几乎所有细节都由它派生。

---

## 二、Sandbox 接口：能力协商，而不是统一抽象

`sandbox.ts` 只有 215 行，但它是整组的宪法。

### 2.1 后端要自报家门

```ts
interface AgentComputerProfile {
  backend: string;
  writablePersistence: "snapshot_to_workspace" | "resident_disk";
  processSessions: boolean;
  egressEnforcement?: "none" | "ip_port" | "domain";
  spec?: { os, runtimes, tools, notInstalled, cpus, memoryMb, diskGb, homeDir, workdir };
}
```

`spec` 里连 **`notInstalled`** 都有——四个后端各自声明「我没装 gcloud / kubectl / flyctl / glab」。这些字段会进 prompt，让模型知道自己坐在什么机器前，别去调不存在的工具。

`visibleTools()` / `visibleNotInstalled()`（`sandbox.ts:48-61`）还做了去重和抵消：部署层额外声明装了某个工具，就把它从 notInstalled 里剔掉。

### 2.2 可选能力用结构化类型守卫探测

`Sandbox` 接口里一半的方法是可选的（`stageIn?` / `backupComputer?` / `startProcess?` / `reapDeepIdle?`…），配套一组类型守卫：

```ts
supportsAgentComputerBackup(s)   // 有 backupComputer 吗
supportsBlobStaging(s)           // stageIn + stageOut + extractFiles 三件套齐吗
supportsProcessSessions(s)       // profile 声明 + 五个方法都在
supportsScopeProfile(s)
```

`supportsProcessSessions` 是**双重校验**：既要 `profile.processSessions === true`（声明），也要五个方法都是 function（实现）。声明和实现不一致时不通过。

不支持就抛 `CapabilityUnsupportedError`，错误消息是写给人看的：

> this computer's substrate (aws-microvm) does not support startProcess

### 2.3 迁移前先报价

```ts
capabilitiesLostMovingTo(from, to): string[]
```

对比两个后端，返回**会丢失的能力清单**——进程会话、home 备份、以及 egress 强制等级的降级（`ENFORCEMENT_RANK: none=0 < ip_port=1 < domain=2`）。

这个函数只有一个调用者：迁移器。它把「换后端」从一个运维动作变成了一次**明码标价的交易**。

---

## 三、四个后端

| | **local-docker** | **sprites** | **aws-microvm** | (mock) |
|---|---|---|---|---|
| 用途 | 只用于开发（profile 里写死 `dev only`） | 生产 | 生产 | 测试 |
| 可写持久化 | `resident_disk`（docker volume） | `resident_disk`（整盘持久，空闲自动休眠） | **`snapshot_to_workspace`** | — |
| 进程会话 | 有 | 有 | 有 | — |
| Egress 强制 | `none` | `domain`（配了代理时） | `none` | — |
| Home | `/root` | `/home/sprite` | `/root` | — |
| OS | Debian 12 | Ubuntu 26.04 | Amazon Linux 2023 | — |

**最大的分歧是 `writablePersistence`：**

- `resident_disk`：盘就在那儿，关机再开还在。
- `snapshot_to_workspace`（AWS）：home 靠定期打 tar 快照回 workspace store（`aws-sandbox.ts:175` `snapshotHome`），下次开机再 `tar -xf` 恢复。快照时会 prune 掉 `.cache` / `.npm` / `.aws` / `__pycache__`。

这个差异不是实现细节——它决定了「agent 装的东西活多久」这个用户可感知的产品属性，所以被提到了 profile 层面。

---

## 四、三层文件模型

文件在这个系统里有**三个家**：

```
+- WorkspaceStore（core 侧，Node fs）-----------------+
|  workspaces/<scopeKey>/...                          |
|  真正的持久层，safeJoin 防路径逃逸                   |
+--------------+--------------------------------------+
               | provision 时物化 ro 层 / 双写 rw
               v
+- Sandbox 内文件系统 --------------------------------+
|  $HOME/workspace/  (rootDir, 可写)                  |
|  $HOME/global/     (ro 层挂载点)                    |
+--------------+--------------------------------------+
               | write(share) / publish
               v
+- FileArtifactStore + DurableByteStore --------------+
|  内容寻址 blob：files/<sha256>，天然去重             |
|  元数据行：owner / createdBy / path / mime / 授权     |
+-----------------------------------------------------+
```

### 4.1 WorkspaceLayer：读写分层

`provision(layers)` 收的是一组层，每层带 `mode: "rw" | "ro"` 和 `mountPath`。典型是：个人 scope 可写、org scope 只读挂在 `global/`。

**只读层的物化很讲究**（`ro-layers.ts`）：

1. 遍历所有 ro 层的文件，算一个**排序后的内容指纹**（每个文件 `path\0 sha256(data)\n` 再整体 sha256）
2. 读盒子里已有的 `.ro-layers.manifest`
3. **指纹相同就直接返回**——不传任何字节
4. 不同才打 tar、写进去、`tar -xf`、删 tar

热启动时 ro 层是零成本的。

### 4.2 双写：sandbox 是工作面，workspace store 是真相

`primitives.ts:593`：

```js
await deps.sandbox.writeFile(handle, path, data);
if (writableScopeId && persistExclude && !isUnderAnyDir(path, persistExclude)) {
  await deps.workspace.write(writableScopeId, path, data);
}
```

`write` 工具同时写盒子和 workspace store（除非路径在 `excludeDirs` 里）。所以即使盒子被销毁重建，`write` 写过的东西还在。

而 `execute` 里 `echo > file` 写的东西**只在盒子里**。这个不对称在 `memory` 工具描述里被显式说明过：「文件是这次对话自己的……盘比记忆更不持久」（见 [[qm-memory-layer]] 第十节）。

`WorkspaceStore` 本身很小（71 行），关键是 `safeJoin`：

```js
const rel = relative(baseDir, target);
if (rel.startsWith("..") || isAbsolute(rel)) throw new Error(`path escapes workspace: ${relPath}`);
```

### 4.3 内容寻址去重

`DurableByteStore` 三个实现（memory / local fs / S3），key 统一是 `files/<sha256>`：

```js
const BLOB_KEY = /^files\/[0-9a-f]{64}$/;
```

同一份字节永远只存一次。本地实现还做了 `.part` 临时文件 + `rename` 原子落盘，且 put 前先 `stat`，已存在就直接返回。

代价 SECURITY.md 认了：**「文件产物没有过期机制，产物退休和字节回收未实现，所以产物和去重后的字节会无限累积」**。

---

## 五、主线：用 shell 长出所有能力

这是这一层最漂亮的地方。`Sandbox` 的必需方法里，真正需要每个后端各自实现的其实只有 `provision` / `run` / 读写文件 / `teardown`。**其余能力全部是在 `run()` 之上用 shell 脚本长出来的通用实现**，四个后端共享。

### 5.1 进程会话 = 文件系统里的进程表

`exec-process-session.ts` 190 行，实现了后台进程的启动 / 增量读输出 / 写 stdin / 发信号 / 列表——**全部通过拼 shell 脚本调 `run()`**。

进程表就是 `$HOME/.agent-proc/<uuid>/` 目录：

| 文件 | 内容 |
|---|---|
| `cmd` | 命令（base64 传入后解码落盘） |
| `env` | 环境变量 export 语句（首次 source 后立即 `rm`） |
| `cwd` | 工作目录 |
| `started` | 启动时间戳 |
| `boot` | 启动时的 boot_id |
| `in` | 命名管道（mkfifo），stdin 入口 |
| `out` | 合并的 stdout+stderr |
| `code` | 退出码（**存在即已退出**） |
| `pid` | 进程组 leader 的 pid |

几个精细处：

**（a）setsid + 进程组**
`setsid sh -c "$LAUNCH"`，信号发给 `-$pid`（整个进程组），子进程杀得干净。trap 捕获 TERM/INT/HUP/QUIT，兜底写 `code=143`。

**（b）boot_id 检测重启**（`REAP_SH`，`exec-process-session.ts:30-33`）

```sh
b=$(cat /proc/sys/kernel/random/boot_id)
o=$(cat "$1/boot")
[ "$b" != "$o" ] && echo 137 > "$1/code"
```

机器重启过（microVM 休眠唤醒、容器重建）时目录还在但进程早没了。对比 boot_id，不一致就标记成「被 KILL 退出」。**这是在无状态的文件系统上恢复出「进程已死」这个事实**，而且不需要 core 侧记任何东西。

**（c）游标式增量读**
`readProcess(sinceCursor, maxBytes, waitMs)`，脚本里 `tail -c +$((cur+1)) | head -c $n | base64`。waitMs 变成盒子里 `while` 循环的 `sleep 0.1`——在盒子里等，而不是在 core 里轮询。

**（d）输入校验**
只允许信号 `TERM/KILL/INT/HUP/QUIT`；processId 必须匹配 `/^[0-9a-f-]{36}$/`。

**（e）列表时脱敏**
`redactCommand()` 走 `createSecretValueMasker(env)` + 一串正则，把 `--token xxx`、`export FOO_SECRET='xxx'` 打码，再截断到 500 字符。**进程列表是会进模型上下文的，所以命令行里的密钥必须先擦掉。**

### 5.2 文件操作 = tar + find

`exec-file-ops.ts`：

- `extractFiles` → 打 tar 写进去 → `tar -xf` → `rm`
- `listDir` → `find <dir> -type f`
- `removeDir` → `rm -rf`（有 `abs === rootDir` 的自杀保护）
- `backupComputer` → `find ... -print0 | tar --null -T - -cf` → 读回来 → `parseTar`

`backupComputer` 的 prune 列表值得看：默认排除 `.aws` / `__pycache__` / `.cache` / `venv`，以及**临时凭证软链路径**（`ephemeralCredentialPrefixes`）。备份 agent 的电脑，绝不能把注入进去的凭证一起备份走。

`parseTar` 还检查 **end-of-archive marker**（末尾 1024 字节必须全 0），截断的 tar 直接报错——防止半截备份被当成完整备份。

### 5.3 中断在途命令 = pgid 标记文件

`exec-kill.ts` 25 行：

```js
killableScript(script, uid)  // exec setsid sh -c 'echo $$ > /tmp/.exec-<uid>.pgid; ...'
killScript(uid)              // 轮询读 marker，kill -KILL -"$pgid"
```

用户中断一个 turn 时，core 发一条**新的 exec** 去杀掉旧的。因为两次调用之间没有共享句柄，只能靠盒子里的一个标记文件传递 pgid。

### 5.4 大文件传输 = 盒子里 curl 回 core

`createExecBlobStaging`——`stageOut` 是在盒子里 `sha256sum` + `curl --upload-file` 打到 core 的 `/v1/blobs`，`stageIn` 是 `curl -o` 下来，都带**短期 capability token**（`mintToken({dir:"read"|"write"})`）。

好处：大文件不经过 core 的内存。`copyHome` 里优先走这条，两边都支持才用，否则退化成读字节再写字节。

### 5.5 迁移 = tar + sha256 双向校验

`sandbox-migrate.ts` 的 `copyHome`：

1. 源盒子里 `tar czf` + `sha256sum` + `wc -c` + `find | wc -l`，一条命令拿到清单
2. 校验清单格式（sha 必须是 64 位 hex），不合格直接报错
3. blob staging 或字节搬运
4. 目标盒子里**先校验 sha 再解压**——不匹配 `exit 3`
5. `fromHome !== toHome` 时跑路径翻译脚本
6. 两边都 `rm -f` 临时 tar

### 5.6 非交互环境前缀

`sandbox-env.ts` 每条命令前都会拼上：

```sh
exec </dev/null; export PAGER="${PAGER:-cat}"; export GIT_PAGER=...;
export GIT_TERMINAL_PROMPT="${GIT_TERMINAL_PROMPT:-0}"; export DEBIAN_FRONTEND=...;
```

34 行的小文件，防的是最常见的 agent 死法：**命令等在一个没人会回答的交互提示上，直到超时**。`exec </dev/null` 关掉 stdin，`GIT_TERMINAL_PROMPT=0` 让 git 认证失败而不是问密码，`PAGER=cat` 防 less 卡住。

用 `${VAR:-default}` 而不是直接赋值——尊重调用方已经设过的值。

---

## 六、路由与迁移

### 6.1 SandboxRouter：per-scope 选后端

`sandbox-routing.ts` 是一个**实现了 `Sandbox` 接口的 `Sandbox`**（装饰器模式），按 scope 查路由表决定用哪个真后端。

```ts
interface SandboxRoute {
  backend: "sprites" | "aws" | "local";
  migratedAt?, migrationSha?, capabilitiesLost?;
  pinned?: boolean;   // 钉死，不许迁
  reason?: string;
}
```

三个细节：

**（a）handle 自带 backend 标记**
`provision` 返回时打上 `{ backend: name, scopeId: scope }`，后续所有操作用 `forHandle(handle)` 找回同一个后端。路由查一次，句柄记住。

**（b）路由表 15 秒缓存**（`ROUTE_CACHE_TTL_MS`）避免每次 provision 都打 DB。

**（c）可选能力按「有没有任一后端支持」条件性挂载**

```js
...(some(supportsProcessSessions) ? { startProcess: ..., ... } : {})
```

只要**任一**已构造的后端支持进程会话，router 就暴露这些方法；调用时才用 `requireCap` 检查**具体这个 handle 的后端**支不支持，不支持抛 `CapabilityUnsupportedError`。能力缺口**每种只上报一次**（`reportedGaps` Set 去重），不刷屏。

后端没构造时不是崩溃，是降级到默认后端 + 记一条 `backend_unavailable` 错误。

### 6.2 迁移器：五道闸

`sandbox-migration-runner.ts` 的 `migrateScope`：

1. 目标后端在本部署构造了吗
2. 源和目标相同 → 报错
3. `route.pinned` → 拒绝，「先 unpin」
4. `hasLiveWork(scopeId)` → 有在跑的后台任务就拒绝
5. `capabilitiesLostMovingTo` 非空且没传 `force` → 拒绝，错误消息里列出会丢什么

过闸之后：

```
provision 两边 -> copyHome -> 写路由表 -> sleep(settleMs)
  -> 在【源】上 find -newermt <开始时间> 检查有没有新文件
  -> 有的话【再 copy 一次】+ 再写路由表，标记 resynced
  -> 两边 park
```

**二次 resync 是关键**：路由表切换和数据拷贝之间有窗口，期间可能有 turn 落在旧盒子上。用 `find -newermt` 检测「拷贝开始后源上有没有变化」，有就重来一遍。

整个操作包在 `advisoryLock.withLock("sandbox-migration:<scope>")` 里，跨实例互斥。

---

## 七、进程生命周期：三层真相

背景进程的状态同时存在三个地方，这是本组最需要小心的部分。

| 层 | 位置 | 角色 |
|---|---|---|
| **真相** | 盒子里 `$HOME/.agent-proc/<id>/` | 进程到底活没活，只有这里知道 |
| **索引** | Postgres `process_sessions` 表 | 谁在跑、属于哪个 scope、什么时候过期 |
| **对账** | `reconcile.ts`（22 行） | 把索引拉回真相 |

`ProcessRecord` 有 `kind: "build" | "dev-server" | "background"`（**必须是声明过的三种之一**，否则 `register` 抛错）、`expiresAt`（TTL）、`sessionRef`、`runId`。

**对账**（`reconcileProcesses`）：列出注册表里状态为 running 的，跟盒子里 `listProcesses()` 的实况对比，盒子里没有或已退出的，把注册表标成 exited。

**回收**（`process-reaper.ts`）：

- 周期 sweep，包在 `leaderLease.hold("processes:reaper")` 里——**多实例只有一个在收**
- 对过期记录先 TERM，等 5 秒；还没死再 KILL，等 2 秒；还没死抛错
- `processIsGone(e)` 判断「进程本来就没了」，这种不算失败
- kill 失败就 `continue`，不标记状态——下一轮再试
- `markStatus` 返回 false（别人已经改了）也 `continue`，防止重复计数

**独立的第四层**：`reapDeepIdle`（只有 AWS 实现）——回收长时间空闲的整台机器，由 wiring 里的 sweeper 按分数间隔驱动。

---

## 八、执行入口：四种「电脑」与两道闸

`primitives.ts:446` 的 `execute` 是所有这些的汇合点。

### 8.1 四种电脑，互斥

| 模式 | 含义 |
|---|---|
| `scoped`（默认） | 这个 scope 自己的持久电脑 |
| `scratch` | 一次性的临时盒子（按 key 复用，teardown 时 `rm -f`） |
| `ownerAuth` | owner 的登录态盒子（命令会过 `ownerAuthCommand` 包一层） |
| `reachTarget` | 另一个频道的电脑（要先 `resolveChannel` 校验可达） |

选了多个直接报错，错误消息写得像人话：

> a command runs on one computer — choose scoped, scratch, owner, or a reached room

reach 的额外约束：只能从 DM 发起，且**会写审计**（`action: "reach_exec"`）。

### 8.2 两道闸，在 provision 之前

```js
const { decision, reason, matched, approvalKey } =
  evaluateCommandWithLayer(command, deps.commandPolicy(), deps.layerCommandRules?.() ?? []);

if (decision === "deny") throw new CommandDenied(...);
if (decision === "require_approval" && !deps.authorizeCommand(command, approvalKey))
  throw new NeedsApproval(command, reason, "approval", matched, approvalKey);
```

注意顺序：**策略判定在 provision 之前**。被拒的命令连盒子都不会开。

`NeedsApproval` 不是普通错误——它是控制流。orchestrator 捕获它，把 turn 挂起等人批准。这也是为什么记忆层的 capture 在 `pausing` 时会跳过（见 [[qm-memory-layer]] 第 3.2 节）。

组织策略（`commandPolicy()`）和部署层规则（`layerCommandRules()`）合并评估——org 设地板，layer 只能加严。

### 8.3 超时有天花板

```js
const timeoutMs = resolvedMs != null && ceiling != null ? Math.min(resolvedMs, ceiling) : resolvedMs;
```

模型可以传 `timeoutSeconds`，但会被 `execTimeoutCeilingMs` 截断。超过 300 秒的活得走 `background` 工具——这条约束写在 `background` 的工具描述里。

---

## 九、设计哲学

**1. 能力协商优于统一抽象。**
不假装四个后端一样。差异被提升成可查询的 `profile`、可探测的类型守卫、可拒绝的 `CapabilityUnsupportedError`、可在迁移时报价的 `capabilitiesLostMovingTo`。这跟记忆层「写完回读探测能力」是同一种务实——[[qm-memory-layer]] 的 `degraded` 探测是运行时版本，这里是类型系统版本。

**2. shell 是最小公分母。**
只要一个后端能 `run(command)` 和读写文件，进程会话、目录操作、备份、blob 传输、迁移就全都免费获得。新增后端的成本被压到极低。代价是这些能力的实现是**拼字符串的 shell**，可读性和可测性都不如原生 API。

**3. 状态的真相在盒子里，索引在 Postgres，中间靠对账。**
不试图让两边永远一致，而是承认会漂移，然后定期拉回。`reconcile.ts` 只有 22 行，但它是这个架构成立的前提。

**4. 危险的东西要先报价。**
迁移会丢能力 → 必须 `force`。这跟 SECURITY.md 那套「授权未来行为的决定必须来自 agent 之外」一脉相承：把隐性损失变成显性确认。

**5. 每一层都假设自己会被杀掉。**
boot_id 检测重启、reaper 回收过期、reconcile 修正漂移、snapshot 定期落盘、`.part` + rename 原子落盘、tar end-marker 校验、sha256 双向校验。没有一处假设「上次的状态还在」。

**6. 内容寻址 + 去重。** blob key 就是 sha256，天然幂等。

**7. 进模型的东西必须先脱敏。** `redactCommand` 在 `listProcesses` 里的位置很关键——进程列表是要给模型看的。

---

## 十、张力与风险

**1. `translateScript` 是这一层最脆的地方。**（`sandbox-migrate.ts:6-28`）

跨 home 迁移（`/root` ↔ `/home/sprite`）时用 `sed` 重写绝对路径，但只覆盖 `.gitconfig`、`.config`、`.bashrc`、`.profile`，加上 `-maxdepth 4` 内的 `.git/config`。任何其他地方硬编码的旧 home 路径都不会被翻译。

对 Python venv 它干脆放弃了——`find -name pyvenv.cfg | rm -rf $(dirname)`，**直接删掉整个虚拟环境**。这是诚实的（重建 venv 比修补它可靠），但用户会发现迁移后 `pip install` 装的东西都没了。

**2. AWS 的 snapshot 窗口。**
`writablePersistence: "snapshot_to_workspace"` 意味着 home 只在 teardown 和定期 rotate 时落盘。**实例非正常终止 → 上次快照之后的所有工作丢失。** 而 `SNAPSHOT_PRUNE` 排除了 `.cache` / `.npm` / `.aws`，恢复后这些缓存要重建。profile 把它暴露给了模型，但模型未必会因此改变行为。

**3. `.agent-proc` 会被快照进去。**
prune 列表里没有它。进程的 `out` 文件可能很大，会被打进 home 快照。恢复后 boot_id 机制会正确地把它们标成 137，但字节已经付过了。

**4. local-sandbox 的引用计数在 RAM。**
`activeByContainer` / `portByName` / `scopeByContainer` / `scratchByKey` 全是进程内 Map。按 AGENTS.md 自己的「Durable by default」标准这是违规的——不过 profile 里写死了 `(dev only)`，dev 场景单实例，可以接受。值得注意的是它被写在一个反复强调不要 RAM-only 的代码库里。

**5. 路由缓存 15 秒的迁移窗口。**
迁移写完路由表后，其他实例最长 15 秒内仍可能路由到旧后端。`settleMs` + 二次 resync 缓解了数据丢失，但没有消除窗口——期间的 turn 会在旧盒子上执行，然后被 resync 覆盖回来。

**6. `killScript` 可能静默失败。**
它轮询 5 次 × 0.1 秒去找 pgid marker 文件。如果被中断的 exec 还没来得及写 marker（进程刚启动），这 0.5 秒就白等了，kill 静默放弃，命令继续跑到超时。

**7. 双写不是原子的。**
`write` 先写 sandbox 再写 workspace store。中间失败会留下不一致——盒子里有、持久层没有。没有补偿逻辑。

**8. 命令策略是文本判断。**
SECURITY.md 自己说了：「它是防手滑和注入的减速带，不是沙箱边界」。obfuscation、编码、写脚本再执行都能绕过。这一层的真实安全边界是 microVM / 容器本身，不是 `command-policy.ts`。

---

## 十一、可迁移到自己项目的做法

- **后端自报 profile + 结构化类型守卫探测能力**——比「统一接口 + 部分方法抛 NotImplemented」清晰得多，且能在编译期收窄类型。
- **切换后端前列出会丢失的能力，非 force 不放行**——把隐性损失变显性。
- **在最小公分母（一个 `run(command)`）之上用 shell 长出高级能力**——新后端接入成本极低。
- **用 boot_id 在无状态文件系统上恢复「进程已死」**——不需要中心化记账。
- **真相在执行侧、索引在数据库、定期对账**——比强一致简单得多，也更符合现实。
- **要进模型上下文的任何列表都先脱敏**（进程命令行、环境变量）。
- **非交互环境前缀**（`exec </dev/null` + `PAGER=cat` + `GIT_TERMINAL_PROMPT=0`）——任何跑 shell 的 agent 都该有。
- **内容指纹 + manifest 比对，相同就跳过传输**——ro 层物化的零成本热启动。

---

> 相关：[[qm-overview]]（整体架构与其余模块） · [[qm-memory-layer]]（记忆层）
