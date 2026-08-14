# QM 技能层深入分析

> 关联文档：
> - [[qm-overview]]（QM 项目整体调研：产品目标、哲学与功能模块分解）
> - [[qm-execution-layer]]（执行环境层——技能最终物化进的那台"电脑"）
> - [[qm-memory-layer]]（记忆层）
> - [[qm-resolution-layer]]（解析层——技能可见 scope 的顺序由它算出）
> - [[qm-turn-slice]]（纵切面——技能索引与懒加载在 turn 时序里的位置）
> - [[qm-harness-layer]]（Harness 层——技能索引进的那个 systemPrompt 由谁消费）
> - [[qm-run-lifecycle]]（执行内核运行时——技能物化发生在 `GapPhase.skills_materialize` 相）
>
> 调研对象：`yc-software/qm` 的 `src/skills/`
> 本地路径：`~/Repositories/qm`
> 调研时间：2026-08-09
> 仓库版本：`main` @ `0f0e0ad`
>
> 范围：`src/skills/` 13 个文件共 1904 行，加上 `core/orchestrator/sandboxes.ts`、
> `api/app-skills.ts`、`api/control-service.ts`、`api/artifact-share.ts` 的接入点。
> 这是功能模块组 **E. 执行环境** 剩下的一半（另一半见 [[qm-execution-layer]]）。

**总体印象：这不是一个"技能加载器"，是一个带所有权、审核状态、能力授权和供应链防护的技能注册表。**

---

## 一、数据模型

```ts
interface SkillManifest {
  name: string;                    // 唯一标识，不可改名
  description: string;             // 进 prompt 索引的那一行
  requiredCapabilities: string[];  // 声明需要什么能力
  body: string;                    // SKILL.md 正文
  files?: SkillFile[];             // 附带资产（path / content / executable）
}

interface Skill {
  id, scopeId, manifest,
  signature: string;               // HMAC-SHA256(canonical manifest)
  status: "draft" | "reviewed" | "published" | "archived";
  createdBy, version, grantedCapabilities, approvals,
  createdAt, updatedAt, lastUsedAt,
  pack?: { packId, commit, upstreamName };
}
```

关键点：**skill 归属一个 scope**（`personal:alice` / `channel:eng` / `team:x` / `org:acme`），而不是全局安装。这一条决定了后面所有设计。

### 1.1 两道名字/路径的安全阀

```js
// skill-name.ts —— 1-128 ASCII，字母数字开头，不能以点结尾
const SAFE_SKILL_NAME = /^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,126}[A-Za-z0-9_-])?$/;

// skill-store.ts safeSkillFilePath —— 拒绝绝对路径、`.`、`..`、NUL
```

`assertSafeSkillName` 在 `create` / `update` / `review` / `publish` / `promote` / `move` / `restore` **每一个**写入点都被调用了一次。不是在入口校验一次就信任，是每个状态迁移都重新校验。

### 1.2 签名：防篡改，不是防伪造

```js
function sign(manifest) {
  const canonical = JSON.stringify({
    name, description,
    requiredCapabilities: [...].sort(),
    body,
    ...(files.length ? { files } : {}),   // 已按 path 排序
  });
  return createHmac("sha256", secret).update(canonical).digest("hex");
}
```

`review()` 和 `promote()` 都会先验签，不过就抛「manifest was tampered with」。

**定位要看清**：secret 在服务端，任何合法的 `update()` 都会重新签名。所以它检测的是**存储层被绕过修改**（有人直接改了数据库行），不是「谁写的这个 skill」。作者身份靠 `createdBy` + `approvals`。

---

## 二、命名空间：有序解析 + 显式遮蔽

这是 qm 相对于「全局技能目录」最本质的差别。

```js
function resolveFromIndex(index, name, orderedScopes) {
  const published = orderedScopes.map((sc) => index.get(`${sc}\0${name}`)).filter(Boolean);
  const [skill, ...shadowed] = published;
  return { skill: skill ?? null, shadowed };
}
```

同名 skill 可以在多个 scope 并存。按 scope 顺序取第一个，**其余的不是错误，是 `shadowed`**。

一次 turn 里的顺序（`turn-helpers.ts:94`）：

```js
visibleSkillScopes = [ 可写scope(个人或频道), ...团队ro层, org ]
```

即 **个人/频道 > 团队 > 组织**。你可以在自己的 DM 里写一个同名 skill 覆盖公司版本，不需要改名、不需要卸载、不需要任何人批准。

> **补正**（来自 [[qm-resolution-layer]]）：「团队」那一段来自 `resolution.layers` 里的非 org 只读层，而这些层**只在 DM 会话里存在**。所以频道会话里的实际解析顺序是「频道 > org」，看不到 team scope——与记忆层、沙箱层同因。

而且这个事实**会告诉模型**——`skillsIndex()` 渲染 prompt 时：

```
- **deploy** — 部署到生产 (shadows a broader-scope skill of the same name)  → read `skills/deploy/SKILL.md`
```

Web 端的可见顺序略有不同（`app-skills.ts:220`）：个人 → 你是成员的频道/群 → 团队 → org。多了一步「你确实在那个房间里」的成员校验。

三种上下文各自算出一份 `orderedScopes`，汇入同一个 `resolveFromIndex`；箭头方向即数据流向——三条上边是「输入」，下面两条是解析后的「输出」。

```mermaid
flowchart TD
    subgraph DM["DM 会话 visibleSkillScopes"]
        D1["可写 scope<br/>personal"] --> D2["team 只读层<br/>仅 DM 存在"] --> D3["org"]
    end
    subgraph CH["频道会话"]
        C1["可写 scope<br/>channel"] --> C2["org<br/>看不到 team 层"]
    end
    subgraph WEB["Web 端 listVisibleSkills"]
        W1["personal"] --> W2["你是成员的<br/>channel / group"] --> W3["team"] --> W4["org"]
    end

    DM --> RESOLVE
    CH --> RESOLVE
    WEB --> RESOLVE

    RESOLVE["resolveFromIndex(index, name, orderedScopes)<br/>按顺序取第一个命中"] --> HIT["首个命中 -> skill"]
    RESOLVE --> REST["其余命中 -> shadowed"]
    HIT --> PROMPT["skillsIndex() 写入 prompt<br/>若有 shadowed 追加<br/>shadows a broader-scope skill of the same name"]

    style DM fill:#00205B,color:#fff,stroke:#1E4A9A
    style CH fill:#003E96,color:#fff,stroke:#1A6AC4
    style WEB fill:#1E5C9E,color:#fff,stroke:#3A8ACC
    style D1 fill:#0A2E7A,color:#fff,stroke:#1E4A9A
    style D2 fill:#0A2E7A,color:#fff,stroke:#1E4A9A
    style D3 fill:#0A2E7A,color:#fff,stroke:#1E4A9A
    style C1 fill:#0050B8,color:#fff,stroke:#1A6AC4
    style C2 fill:#0050B8,color:#fff,stroke:#1A6AC4
    style W1 fill:#2A6EAE,color:#fff,stroke:#3A8ACC
    style W2 fill:#2A6EAE,color:#fff,stroke:#3A8ACC
    style W3 fill:#2A6EAE,color:#fff,stroke:#3A8ACC
    style W4 fill:#2A6EAE,color:#fff,stroke:#3A8ACC
    style RESOLVE fill:#004060,color:#fff,stroke:#1A5E80
    style HIT fill:#1A5E3A,color:#fff,stroke:#2A7E50
    style REST fill:#7B1010,color:#fff,stroke:#B52020
    style PROMPT fill:#004060,color:#fff,stroke:#1A5E80
```

---

## 三、状态机

```
create ──> draft
             │ review(reviewer, grantCapabilities)   ← 验签
             v
          reviewed
             │ publish()   ← requiredCapabilities ⊆ grantedCapabilities
             v
        published ──> archive() ──> archived
             │
             │ promote(org)   ← 只有 published + 验签 + 管理员 + 活人
             v
        org 作用域的一份新副本
```

状态名直接取自源码 `SkillStatus`，转移标签对应 `SkillStore` 的同名方法：

```mermaid
stateDiagram-v2
    direction TB
    classDef archivedStyle fill:#7B1010,stroke:#B52020,color:#fff
    classDef orgStyle fill:#1A5E3A,stroke:#2A7E50,color:#fff

    state "org 作用域新副本 (published)" as OrgCopy

    [*] --> draft : create()
    draft --> reviewed : review(reviewer, grantCapabilities) 验签
    reviewed --> draft : update() 非个人 scope 打回
    reviewed --> published : publish() 需能力已全部授权
    published --> draft : update() 非个人 scope 打回
    published --> archived : archive()
    published --> OrgCopy : promote(org) 需活人 管理员 验签

    class archived archivedStyle
    class OrgCopy orgStyle
```

四条硬规则：

| 规则 | 位置 | 报错文案 |
|---|---|---|
| 不能改名 | `update` | `skill update cannot rename — create a new skill instead` |
| 非个人 scope 的修改会打回 draft | `update` | （静默，`s.status = "draft"`） |
| 未 review 不能发布 | `publish` | `skill must be reviewed before it is published` |
| 声明的能力必须先被授予 | `publish` | `skill requires ungranted capabilities: ...` |
| 让渡给 org 不走 move | `move` | `ceding a skill to the org goes through promote (admin-gated), not move` |

**`requiredCapabilities` 这个机制值得单拎出来**：skill 在 frontmatter 里声明自己要什么（`egress:api.github.com` 之类），`review` 时由审核者显式授予，`publish` 时校验没有未授予的项。声明和授权分离，发布是二者的交汇点。

---

## 四、三条入口

技能进入注册表有三条完全不同的路径，各有各的信任级别。

| 入口 | 来源 | 解析严格度 | 审核 | 用途 |
|---|---|---|---|---|
| **seed** | 本地目录 `skills-seed/` + `plugins/*/skills` | **严格** | 自动（`system:skills-reviewer`） | 开箱技能，随部署走 |
| **pack** | git 仓库 | **宽容** | 自动（`system:pack-reviewer`） | 导入外部技能库 |
| **agent/人** | self-API / web | — | 个人 scope 免审；共享 scope 自动重新发布 | 日常创作 |

### 4.1 严格 vs 宽容：两个解析器

同一个 frontmatter 解析器（`parseFrontmatter`）之上，套了两层语义：

**`parseSeedSkillFrontmatter`（严格）**——name / description / body 缺一不可，`requiredCapabilities` 必须是字符串数组，名字必须过 `assertSafeSkillName`，否则**抛错**。自己的代码，写错就该崩。

**`normalizeSkill`（宽容）**——外部仓库的 SKILL.md 什么样都有，所以：

```js
name        := frontmatter.name ?? 目录名（去掉 .md）
description := frontmatter.description ?? 正文第一段散文 ?? 第一个标题 ?? name  （截断到 200 字符）
requiredCapabilities := frontmatter.requiredCapabilities
                     ?? frontmatter.egress 映射成 egress:<host>
scopeHint   := frontmatter.scope ?? frontmatter.visibility
private     := private/agent_only 为真 ?? 正文含 /THE-AGENT-ONLY/
declaredCreds := frontmatter.declaredCreds ?? 正文里扫出来的 $ALLCAPS 环境变量引用
```

还有 `fieldOverrides` 配置项做字段改名映射。**没有认出来的 frontmatter 字段全部原样收进 `meta`**，不丢。

只有正文为空或 frontmatter 根本没有围栏才 `{ skip: true, reason: "malformed" }`。

> 顺带：`parseFrontmatter` 是手写的（105 行），不是 YAML 库。支持标量、流式数组 `[a, b]`、块标量 `>` `|` `>-` `|-`、块序列 `- item`。**不支持嵌套 map**，且解析不了的行是 `continue` 静默跳过。

### 4.2 seed 安装的三个细节

```js
// readSkillFiles
if (st.isSymbolicLink()) { warn("skipping symlink asset"); continue; }
if (isProbablyBinary(bytes)) { warn("skipping binary asset (v1 stores text only)"); continue; }
out.push({ ..., executable: (st.mode & 0o111) !== 0 });   // 保留可执行位
```

`upsertSeedSkill` 有个我很欣赏的概念——**foreign collision**：

```js
if (!existing && foreignSkillCollision(all, scopeId, name, createdBy)) return "foreign";
```

同一个 scope 里已经有同名 skill，但**是别人建的**（`createdBy` 不同）——不覆盖，返回 `"foreign"`，调用方记成 skipped。seed 只管自己种下的那些。

整个 upsert 包在 `createKeyedQueue` 里，key 是 `scope\0name`，并发安全。

---

## 五、Pack 导入：一条有供应链防护的管线

```
resolveRef / fetch  ──>  planIngest  ──>  collision precheck  ──>  importPack  ──>  archiveRemoved
   （网络 + git）        （筛选 + 计数）      （全有或全无）        （逐个 upsert）    （上游删了就归档）
```

### 5.1 fetch 的安全措施

`pack-fetcher.ts` 284 行里有相当大比例是防护，值得逐条列：

**URL 层**

```js
if (url.protocol !== "https:" || !url.hostname || url.username || url.password)
  throw new Error("skill pack url must use credential-free https");
```

只允许 https，且**不允许 URL 里带凭证**（`https://user:pass@host`）。

**SSRF / DNS rebinding**

```js
addresses = literal ? [host] : await lookup(host);
if (!addresses.length || addresses.some(isPrivateNetworkIp))
  throw new Error("skill pack repository must resolve to a public network address");
// 然后把解析结果钉死：
["http.curloptResolve", `${host}:${port}:${resolved}`]
```

先解析 DNS、拒绝私网地址，**再把解析结果通过 `http.curloptResolve` 钉给 git**——这样 git 自己不会再解析一次拿到不同的（内网）地址。这是标准的 DNS rebinding 防护，做得很正规。

配套还有 `["http.followRedirects", "false"]`（防重定向到内网）和 `["http.proxy", ""]`。

**git 进程隔离**

```js
for (const k of Object.keys(env)) if (/^(GIT_|SSH_)/.test(k)) delete env[k];
env.HOME = cwd;                        // 临时目录，不是真 HOME
env.GIT_TERMINAL_PROMPT = "0";
env.GIT_CONFIG_NOSYSTEM = "1";
env.GIT_CONFIG_GLOBAL = "/dev/null";
env.GIT_ALLOW_PROTOCOL = "https";      // 挡掉 ext:: 之类的协议注入
```

配置通过 `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_n` / `GIT_CONFIG_VALUE_n` 传，不落盘。

**ref 校验 + 两段式 checkout**

```js
const SHA_RE = /^[0-9a-f]{7,40}$/;
const BRANCH_RE = /^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$/;
...
await git(["clone", "--no-checkout", "--quiet", repo.url, "repo"], work, auth, repo.gitConfig);
await git(["checkout", "--detach", "--quiet", ref || "HEAD"], repoDir, undefined);
                                                              // ↑ 注意：auth = undefined
```

clone 带认证，checkout 不带——**凭证只在真正需要联网的那一步存在**。

**读树的配额**

```js
if (ent.name === ".git") continue;
if (ent.isSymbolicLink()) continue;
if (files.length >= maxFiles) throw ...       // 5000
if (totalBytes > maxTotalBytes) throw ...     // 32 MB
```

**错误脱敏**

```js
const scrub = (s, auth) => auth ? s.split(auth.secret).join("***").split(auth.value).join("***") : s;
```

git 报错原文里可能带 token，返回给用户前先擦。

这些防护不是并列清单，是 `fetch()` 里严格的先后顺序——箭头就是调用顺序，红色是拒绝出口：

```mermaid
flowchart TD
    START["fetch(pack) / resolveRef(pack)"] --> REF["ref 格式校验<br/>SHA_RE 或 BRANCH_RE"]
    REF -->|"格式非法"| R1["拒绝: invalid skill pack ref"]
    REF --> URL["validateRepoUrl<br/>仅 https 且 URL 不带凭证"]
    URL -->|"protocol 非 https 或带用户名密码"| R2["拒绝: credential-free https"]
    URL --> DNS["DNS 解析 host<br/>lookup()"]
    DNS -->|"解析出内网地址"| R3["拒绝: must resolve to<br/>public network address"]
    DNS --> PIN["钉死解析结果<br/>http.curloptResolve host:port:ip<br/>followRedirects=false, proxy=''"]
    PIN --> AUTH["opts.resolveAuth(pack)<br/>可选，取凭证"]
    AUTH --> ENV["gitEnv 隔离<br/>清空 GIT_/SSH_ 环境变量<br/>HOME=临时目录<br/>GIT_ALLOW_PROTOCOL=https"]
    ENV --> CLONE["git clone --no-checkout<br/>带 auth"]
    CLONE --> CHECKOUT["git checkout --detach<br/>ref (auth=undefined)"]
    CHECKOUT --> TREE["readTree 配额<br/>跳过 .git 与 symlink<br/>maxFiles 5000 / maxTotalBytes 32MB"]
    TREE --> DONE["FetchedRepo { commit, files }"]

    CLONE -.->|"git 调用失败"| SCRUB["scrub() 脱敏错误信息<br/>擦除 auth.secret / auth.value"]
    CHECKOUT -.->|"git 调用失败"| SCRUB

    style R1 fill:#7B1010,color:#fff,stroke:#B52020
    style R2 fill:#7B1010,color:#fff,stroke:#B52020
    style R3 fill:#7B1010,color:#fff,stroke:#B52020
    style SCRUB fill:#7B1010,color:#fff,stroke:#B52020
    style DONE fill:#1A5E3A,color:#fff,stroke:#2A7E50
    style PIN fill:#004060,color:#fff,stroke:#1A5E80
    style ENV fill:#004060,color:#fff,stroke:#1A5E80
```

### 5.2 凭证的作用域校验

`resolvePackAuth` 不是「拿到凭证就用」：

```js
if (repoHost !== credentialHost && connectorHostFor(pack.url) !== credentialHost)
  throw new Error(`skill pack credential is not authorized for ${repoHost}`);
if (methods && (!methods.includes("GET") || !methods.includes("POST")))
  throw new Error("skill pack credential must allow Git HTTP GET and POST");
if (allowedPathPrefixes?.length && !allowedPathPrefixes.some((p) => repo.pathname.startsWith(p)))
  throw new Error(`skill pack credential is not authorized for ${repo.pathname}`);
```

凭证声明过自己能用在哪个 host、哪些 HTTP 方法、哪些路径前缀，这里逐条比对。这跟 SECURITY.md 里坦白的「credential purposes are not enforced authorization」形成对比——**在这条路径上，凭证的作用域是真的强制了的**。

### 5.3 planIngest：五类排除，各自计数

```js
const counts = { total, eligible, scope, private, collision, "binary-asset", malformed };
```

| 排除原因 | 判据 |
|---|---|
| `malformed` | 没有 frontmatter 围栏，或正文为空 |
| `private` | `private`/`agent_only` 为真，或正文含 `THE-AGENT-ONLY` |
| `scope` | scopeHint 落在 `{personal, person, private, owner, me, self, individual}` 里 |
| `collision` | 名字撞上目标 scope 里已有的原生 skill |
| `binary-asset` | 该 skill 目录下有二进制文件或非法路径 |

**每一类都计数**，写进 `lastImport.counts`。导入一个 50 个 skill 的仓库只成功 12 个时，用户能看到另外 38 个分别死在哪一类上。这是很好的可观测性设计。

### 5.4 共享 bundle：仓库级的公共文件

`collectSharedBundle` 收集**不属于任何 skill 目录**的文件——共享脚本、模板、参考资料：

```js
if (hasRootSkill) return [];                     // 根目录有 SKILL.md 就整个放弃
if (underSkillDir(f.path)) continue;             // 属于某个 skill 的归那个 skill
if (isRepoMetadata(f.path)) continue;            // .github/ .claude/ .claude-plugin/ README LICENSE ...
```

它们最终落在沙箱的 `skills/.packs/<packId>/`，并且 skill 正文会被自动追加一段说明：

```
## Pack files
Resolve repository-relative shared-file paths against `skills/.packs/<packId>/`;
pack files never overwrite the workspace root.
```

**这解决了一个真实问题**：外部技能库里的 SKILL.md 常写「运行 `./scripts/foo.sh`」，那个路径在原仓库是仓库相对的。qm 不改写正文，而是**告诉模型基准路径在哪**。

### 5.5 碰撞预检：全有或全无

```js
const incomingSkillPaths = toWrite.flatMap((w) => skillRecordPaths(w.manifest.name, w.manifest.files));
const incomingBundlePaths = bundleFilePaths(ctx.bundleFiles ?? []);

const controlCollisions = materializationControlPathCollisions(incomingBundlePaths);
if (controlCollisions.length) throw new SkillPackCollisionError(controlCollisions);

if (ctx.claimedPaths) { ...detectPathCollisions(incoming, ctx.claimedPaths)... throw }
if (ctx.claimedBundlePaths) { ...  throw }
```

**在写入任何一条记录之前**，把这次导入会占用的全部路径算出来，跟已被占用的路径表比对。有冲突就整体抛 `SkillPackCollisionError`，错误消息列出前 5 条冲突和各自的属主：

```
skill pack import would clobber 3 existing path(s):
  skills/deploy/SKILL.md (owned by …); skills/deploy/.tree (owned by …); … 
```

其中 `materializationControlPathCollisions` 专门挡一类攻击：**pack 里带一个叫 `skills/.index` 或 `skills/<x>/.tree` 的文件**，试图覆盖 core 的物化元数据。这类路径的 owner 被写死成 `"core skill materialization metadata"`。

---

## 六、物化：两级投影 + 标记文件 + 懒加载

这是技能层和[[qm-execution-layer]]的接缝，也是设计最密的一段。

### 6.1 两级

| 级别 | 写什么 | 时机 |
|---|---|---|
| **index** | 每个可见 skill 的 `skills/<name>/SKILL.md`（**只有正文**）+ `skills/.index` 标记 | 每轮 provision 后 |
| **tree** | 某一个 skill 的全部资产文件 + 它所属 pack 的 bundle + `skills/<name>/.tree` 标记 | **agent 真的去读它的时候** |

懒加载的触发点在 `execute`（`primitives.ts:508`）：

```js
if (local && deps.ensureSkillTree) {
  for (const skillDir of skillTreeDirsInCommand(command)) await deps.ensureSkillTree(skillDir);
}
```

命令文本里提到 `skills/<x>/` 就把那棵树铺下去，顺便 `recordUse` 打时间戳。

**为什么这么设计**：prompt 里只放一行索引（name + description + 「去读 SKILL.md」），正文进盒子但不进 context，资产文件连盒子都先不进。三级递进的成本控制。跟记忆层「记忆是索引不是数据仓」是同一条哲学（见 [[qm-memory-layer]] 第十节）。

两级各自的判定都是「算 hash、比对标记、一致则跳过」，形状相同但触发时机不同：

```mermaid
flowchart TD
    TURN["每轮 provision 后"] --> IH["indexHash(resolved)"]
    IH --> IM{"skills/.index 标记<br/>合法且 hash 与 names 一致?"}
    IM -->|"是"| ISKIP["跳过写盘，直接返回"]
    IM -->|"否"| IWRITE["按上次 names 清理陈旧路径<br/>写入各 SKILL.md 正文<br/>+ 新 .index 标记"]

    ISKIP --> EXE["agent 调用 execute 执行命令"]
    IWRITE --> EXE
    EXE --> MATCH{"命令文本含<br/>skills/{name}/ ?"}
    MATCH -->|"否"| NOOP["不物化该 skill 的资产"]
    MATCH -->|"是"| ENSURE["ensureSkillTree(skillDir)"]
    ENSURE --> TH["treeHash(resolution, bundles)"]
    TH --> TM{"skills/{name}/.tree<br/>标记合法且 hash 一致?"}
    TM -->|"是"| TSKIP["跳过写盘"]
    TM -->|"否"| TWRITE["铺资产文件 + pack bundle<br/>写新 .tree 标记<br/>recordUse 打时间戳"]

    style IM fill:#004060,color:#fff,stroke:#1A5E80
    style TM fill:#004060,color:#fff,stroke:#1A5E80
    style MATCH fill:#004060,color:#fff,stroke:#1A5E80
    style IWRITE fill:#0050B8,color:#fff,stroke:#1A6AC4
    style TWRITE fill:#0050B8,color:#fff,stroke:#1A6AC4
    style ISKIP fill:#1A5E3A,color:#fff,stroke:#2A7E50
    style TSKIP fill:#1A5E3A,color:#fff,stroke:#2A7E50
```

### 6.2 标记文件与幂等

```json
skills/.index          → {"version":2,"hash":"…","names":["a","b"]}
skills/<name>/.tree    → {"version":2,"hash":"…","skillPaths":[…],"bundlePaths":[…]}
```

每次物化先算 want-hash，读标记比对，**一致就直接返回**。跟 ro 层的指纹比对是同一招。

标记本身被当作**不可信输入**校验：

```js
// names 必须全是合法 skill 名
if (!parsed.names.every((n) => typeof n === "string" && isSafeSkillName(n))) return null;
// skillPaths 必须安全、必须在本目录下、不能是控制路径
if (!parsed.skillPaths.every((p) => isSafeMaterializedPath(p) && p.startsWith(`${dir}/`) && !isControl(p))) return null;
```

校验不过就当**标记不存在**（返回 null）→ 走全量重建路径。盒子里的文件是 agent 能写的，所以 core 读回自己的元数据时不能盲信。

### 6.3 陈旧清理：只删自己登记过的

标记里记着「上次我铺了哪些路径」。这次重建时：

```js
for (const path of prev.skillPaths) {
  if (!currentSkillPaths.has(path) && !otherBundlePaths.has(path)) await sandbox.removeDir(handle, path);
}
```

**只删上次自己登记过、这次不要了、且没有被别的 skill 的 bundle 占着的路径。** 不会 `rm -rf skills/` 了事——agent 在那个目录里放的别的东西不会被误伤。

`otherBundlePaths` 那一层尤其细：两个 skill 来自同一个 pack，共享同一份 bundle 文件。删掉其中一个 skill 时，bundle 文件不能删，因为另一个还在用。代码逐个读其他 skill 的 `.tree` 标记，把它们声明的 bundlePaths 收成一个"别动"集合。

还有一个 legacy 分支：读到了标记文件但解析不出 v2 结构（`raw && !prev`），说明是老版本或被改坏了 → `removeDir(SKILLS_DIR)` 全清重建，并在新标记里打上 `legacyExternalPathsPreserved: true`。

### 6.4 并发

```js
const key = materializationKey(handle);   // sha256(handle.id + "\0" + handle.rootDir)
queue(key, () => advisoryLock?.withLock(key, fn) ?? fn());
```

进程内 keyed queue + 跨实例 advisory lock，双层。而且 `materializeIndex/Tree` 都接一个 `current()` 回调——**在拿到锁之后才重新读最新状态**，避免用排队期间已经过期的数据去写盒子。

---

## 七、同步引擎：pinned vs tracked

`skill-sync-engine.ts` 62 行，5 分钟一轮，leader lease 保证多实例只有一个在跑。

```js
if (pack.syncMode === "tracked") {
  const head = await fetcher.resolveRef(pack);
  if (pack.lastImport?.status === "ok" && head === pack.lastImport.commit) return;
  await deps.reconcile(packId);            // 自动重新导入
} else {
  const head = await fetcher.resolveRef(pack);
  const available = pack.lastImport ? head !== pack.lastImport.commit : false;
  if (available !== Boolean(pack.updateAvailable)) {
    await deps.packs.update(packId, { updateAvailable: available });   // 只挂个红点
  }
}
```

**tracked = 自动跟进，pinned = 只提示有更新。** 用 `ls-remote` 探 head，不用整仓 clone。

`reconcilePack`（`app-skills.ts:95`）几个稳健性设计：

1. **fetch 在锁外先做**，失败就 `recordImport({status:"error", error})` 再抛——失败也留痕。
2. 拿到数据后重读 pack，比对 `skillPackSourceIdentity`——「fetch 期间有人改了 pack 的 url/ref」就放弃（`skill pack changed while fetching`）。
3. **按 scope 分别 reconcile**：一个 pack 可能被导入到多个 scope，每个 scope 各自算 nativeNames 和 claimedPaths。
4. `archiveRemoved`——上游删掉的 skill 在本地**归档**而不是删除。历史留着。

---

## 八、权限模型汇总

| 动作 | 谁可以 | 强制点 |
|---|---|---|
| 在个人 scope 创建 | 本人 | — |
| 在 org/team scope **直接创建** | **没人** | `a skill cannot be created directly in an org or team scope — promote a published skill instead` |
| 编辑 | `canManageSkill` = 属主，或其共享 home（频道/群）的现成员 | `principalManagesArtifactHome` |
| 编辑共享 scope 的 skill | **只有活人，自动触发不行** | `triggerBlocksSharedSkill(homeScope, liveActor)` |
| share（加授权） | 管得了它的人，往自己所属的任何 context | `belongsToScope` |
| move（换 home） | 同上，但**不能 move 到 org** | `move()` 直接拒绝 |
| **promote 到 org** | **活的 org 管理员** | 三重校验 + 审计 |

promote 那三重校验（`app-sessions.ts:541`）：

```js
if (parseScopeId(targetScopeId).kind !== "org") throw …
if (liveActor !== true) throw new AdminError(403,
  "promoting a skill org-wide takes a live person, never an autonomous trigger");
if (!status.isAdmin) throw new AdminError(403, "only an org admin can promote a skill org-wide");
```

**`liveActor` 这个维度是整个权限模型里最有意思的一条。** 它区分的不是「谁」而是「这一轮有没有人在场」——cron 半夜触发的 turn 即使 actor 是管理员本人，也不能提升 skill、不能改共享 skill。

理由和 SECURITY.md 那三堵墙完全一致：**授权未来行为的决定，必须来自 agent 之外**。一个被 prompt injection 的自主轮，不能给自己扩大影响范围。

有一处放松值得注意：`republishIfShared`——编辑频道/群里的 skill 后，系统自动以 `system:skill-authoring` 重新 review 并 publish（有审计 `skill_review`）。所以共享 scope 的「审核」是自动的，**真正的人工闸门只有 org promotion 一处**。

---

## 九、设计哲学

**1. 技能是有主的资产，不是全局配置。**
scope 所有权 + 有序遮蔽 + 授权分享，整套模型跟文件、部署、cron 共用同一个 `share` 动词和同一套 `canManageArtifactHome` 判定。技能不特殊。

**2. 严格对内，宽容对外。**
自家 seed 解析失败就崩；外部仓库尽最大努力推导，推不出来就分类计数告诉你为什么。

**3. 排除要计数，不能静默。**
五类排除各自计数进 `lastImport.counts`。

**4. 写入前做全量碰撞预检，全有或全无。**
避免导入到一半失败留下半个 pack。

**5. 自己的元数据要能被别人污染而不出事。**
`.index` / `.tree` 是写在 agent 可写的盒子里的。读回来时严格校验，不合格就当不存在、全量重建。同时禁止任何 skill 或 bundle 声明这些路径。

**6. 只清理自己登记过的东西。**
标记文件同时是「幂等凭据」和「所有权清单」。

**7. 三级成本递进：索引进 prompt，正文进盒子，资产按需铺。**

**8. 「有没有活人在场」是一个独立的授权维度。**

---

## 十、对照 harveyz-skill：能抄什么

本仓库的模型是**静态注册表**：`skills-index.json` 是唯一真源，条目有 `path` + `bundle`；格式规范 F1–F7、注册规范 R1–R3；`hskill` 把它们装到 `~/.claude/skills/`。qm 是**动态注册表**。几处可以直接借鉴：

### 值得抄的

**① 排除要分类计数。**
`contribute-skill` / `publish-skill` 目前是「过了 / 没过」。qm 的 `counts = {total, eligible, scope, private, collision, binary-asset, malformed}` 模式适用于任何批量导入——用户看到「38 个没进来」时能立刻知道该修哪一类。

**② 写入前的全量路径碰撞预检。**
本仓库的 skill 目录名冲突目前靠 `publish-skill` 逐个校验。qm 的做法是先算出全部将占用路径、跟已占用表比对、有冲突整体拒绝并列出属主。对 `contribute-skill`（从别的项目导入）尤其合适。

**③ 元数据标记 + 内容哈希幂等。**
`.index` / `.tree` 那套「算 hash → 比对 → 一致就跳过 → 不一致只删自己登记过的路径」，正是 `sync-hotfix` 在解决的问题（源与安装副本的差异检测）。qm 的版本更彻底：标记文件同时充当幂等凭据和所有权清单，所以能安全地在一个用户也会写东西的目录里做增量同步。

**④ 严格/宽容双解析器。**
`init-skill`（自己写的）应该严格报错；`contribute-skill`（导入别人的）应该宽容推导 + 报告推导了什么。目前两者共用一套 F1–F7 校验。

**⑤ 二进制资产的显式态度。**
qm 明说「v1 stores text only」，seed 遇到二进制**警告并跳过**，pack 遇到二进制**整个 skill 排除**。本仓库有 skill 带 Python 脚本和模板，值得明确一个同样清晰的立场。

**⑥ pinned vs tracked + updateAvailable。**
`sync-hotfix` 是单向手动的。「探 head、只更新一个红点、不自动改」是很轻的一步增强。

### 不适合抄的

- **scope 所有权与遮蔽**——本仓库是单人维护、面向自己安装，没有多租户，引入 scope 是纯负担。
- **签名与能力授权状态机**——没有多人审核流程，`draft → reviewed → published` 是空转。
- **git pack 的 SSRF 防护**——`contribute-skill` 读的是本地路径，不联网。

---

## 十一、张力与风险

**1. 签名密钥的默认值是个陷阱。**

```js
const secret = opts.signingSecret ?? randomUUID();
```

没配 `signingSecret` 时，每次进程启动都是新密钥。重启后所有已存 skill 的 `verify()` 都会失败，`review()` 和 `promote()` 直接抛「manifest was tampered with」。生产走 wiring 会传入配置，但这个默认值让「忘了配」的后果延迟到第一次重启后才暴露，且错误信息指向完全错误的方向（说你篡改了 manifest，实际是密钥丢了）。

**2. 状态机看起来比实际严。**
`update()` 把非个人 scope 的 skill 打回 draft，看着像强制重新审核。但 `republishIfShared` 紧接着自动 review + publish。除 org promotion 外没有真正的人工闸门——这是有意的产品选择（频道成员就该能改频道的 skill），但代码读起来的严格程度和运行时的实际严格程度有落差。

**3. `collectSharedBundle` 遇到根级 SKILL.md 会整体放弃。**

```js
if (hasRootSkill) return [];
```

一个「仓库根目录就是一个 skill」的仓库，共享 bundle 直接是空——所有非 skill 文件都不会被带进来。这个行为没有任何提示（零注释仓库），也不计入 counts。用户会看到 skill 导入成功但引用的脚本全都不在。

**4. 一个冲突炸掉整包。**
碰撞预检是全有或全无。50 个 skill 的 pack 里有 1 个名字撞了，整次导入抛异常。原子性是对的，但没有「跳过冲突项继续」的选项，对大仓库不友好。（`collision` 那一类排除只处理了「撞上原生 skill 名」，撞上另一个 pack 的路径就是硬失败。）

**5. `declaredCreds` 的正则回退会误报。**

```js
const re = /\$\{?([A-Z][A-Z0-9_]{2,})\}?/g;
```

正文里任何 `$FOO` 形式的东西都会被当成凭证声明，包括代码示例里的 shell 变量。只是个提示性字段，但会污染。

**6. 手写 frontmatter 解析器不支持嵌套。**
解析不了的行 `continue` 静默跳过。一个用嵌套 map 写 frontmatter 的 skill 会被解析成部分属性，且不报 malformed——它会以「description 靠正文推导」的降级形态被导入。

**7. 符号链接一律丢弃。**
seed 会 warn，pack 的 `readTree` **静默 skip**。依赖 symlink 组织文件的仓库会以缺文件的形态导入成功。

**8. 物化标记活在盒子里。**
盒子重建后标记消失，全量重铺。行为正确，成本是一次全量。这跟 [[qm-execution-layer]] 第十节第 2 条（AWS 快照窗口）叠加：非正常终止 + 快照未覆盖 → 下一轮全量重铺所有可见 skill 的 SKILL.md。

---

> 相关：[[qm-overview]]（整体架构） · [[qm-execution-layer]]（沙箱与文件） · [[qm-memory-layer]]（记忆层）
